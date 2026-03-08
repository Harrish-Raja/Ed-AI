import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db_manager import get_user, get_topics, get_latest_roadmap
from core.error_tutor import analyze_code, run_code_safely, explain_error_message, get_code_review
from utils.session_manager import init_session, require_login, require_api_key

st.set_page_config(page_title="Error Tutor · EdAI", page_icon="🐛", layout="wide")
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session()
require_login()
require_api_key()

uid = st.session_state.user_id
user = get_user(uid)
lang  = user.get("preferred_language", "Python")
level = user.get("level", "Beginner")

st.markdown("# 🐛 Error Tutor")
st.markdown("Paste your code and let AI diagnose and teach you how to fix it.")

tab1, tab2 = st.tabs(["🔍 Code Analysis", "🔎 Code Review"])

with tab1:
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown("### 📋 Your Code")
        problem_desc = st.text_area(
            "Problem Description (optional)",
            placeholder="Describe what the code is supposed to do...",
            height=80
        )
        try:
            from streamlit_ace import st_ace
            buggy_code = st_ace(
                value=st.session_state.get("buggy_code", f"# Paste your {lang} code here\n"),
                language="python",
                theme="monokai",
                font_size=14,
                height=300,
                key="error_editor",
                auto_update=True,
            )
        except ImportError:
            buggy_code = st.text_area(
                "Your Code",
                value=st.session_state.get("buggy_code", f"# Paste your {lang} code here\n"),
                height=300,
                key="buggy_code_area",
                label_visibility="collapsed"
            )
        st.session_state.buggy_code = buggy_code

        col_run, col_analyze = st.columns(2)
        with col_run:
            run_btn = st.button("▶️ Run Code", use_container_width=True)
        with col_analyze:
            analyze_btn = st.button("🔍 Find & Fix Errors", use_container_width=True)

        if run_btn and buggy_code:
            with st.spinner("Running..."):
                result = run_code_safely(buggy_code)
                st.session_state.et_output = result

        # Run output
        out = st.session_state.get("et_output")
        if out:
            st.markdown("**Output:**")
            if out.get("success"):
                st.markdown(f"""
                <div class="success-box"><code style="white-space:pre-wrap;">{out.get('stdout','(no output)')}</code></div>
                """, unsafe_allow_html=True)
            else:
                err_text = out.get("stderr", "")
                st.markdown(f"""
                <div style="background:rgba(255,107,107,0.1);border:1px solid rgba(255,107,107,0.3);
                            border-radius:12px;padding:1rem;color:#FF6B6B;">
                    <strong>❌ Error:</strong><br>
                    <code style="white-space:pre-wrap;color:#ffa0a0;">{err_text}</code>
                </div>
                """, unsafe_allow_html=True)

                if st.button("🤖 Explain This Error"):
                    with st.spinner("Explaining..."):
                        explanation = explain_error_message(err_text, buggy_code, level)
                        st.session_state.error_explanation = explanation

                if st.session_state.get("error_explanation"):
                    st.markdown(f"""
                    <div class="info-box">{st.session_state.error_explanation}</div>
                    """, unsafe_allow_html=True)

    with col_right:
        st.markdown("### 🤖 AI Diagnosis")

        if analyze_btn and buggy_code:
            with st.spinner("🧠 Analyzing your code..."):
                feedback = analyze_code(buggy_code, problem_desc, lang, level)
                st.session_state.et_feedback = feedback

        feedback = st.session_state.get("et_feedback")
        if feedback:
            score = feedback.get("score", 0)
            score_color = "#00D4A8" if score >= 80 else "#FFC400" if score >= 50 else "#FF6B6B"

            # Score
            st.markdown(f"""
            <div style="display:flex;gap:1.5rem;margin-bottom:1.5rem;flex-wrap:wrap;">
                <div class="metric-card" style="flex:1;min-width:120px;">
                    <div class="metric-icon">📊</div>
                    <div class="metric-value" style="color:{score_color};">{score}</div>
                    <div class="metric-label">Code Score</div>
                </div>
                <div class="metric-card" style="flex:1;min-width:120px;">
                    <div class="metric-icon">{'✅' if not feedback.get('has_errors') else '❌'}</div>
                    <div class="metric-value" style="font-size:1.2rem;">{'No Errors' if not feedback.get('has_errors') else feedback.get('error_type','').title()}</div>
                    <div class="metric-label">Error Type</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Explanation
            if feedback.get("explanation"):
                st.markdown(f"""
                <div class="content-panel">
                    <div style="color:#a09cf7;font-size:0.8rem;font-weight:600;margin-bottom:0.5rem;">MENTOR EXPLANATION</div>
                    <p style="color:#c0c0d8;line-height:1.7;">{feedback['explanation']}</p>
                </div>
                """, unsafe_allow_html=True)

            # Errors list
            errors = feedback.get("errors", [])
            if errors:
                st.markdown("**🔴 Issues Found:**")
                for err in errors:
                    st.markdown(f"""
                    <div style="background:rgba(255,107,107,0.08);border-left:3px solid #FF6B6B;
                                border-radius:0 10px 10px 0;padding:0.75rem 1rem;margin-bottom:0.5rem;">
                        <div style="color:#FF6B6B;font-weight:600;">{err.get('issue','')}</div>
                        <code style="color:#ffa0a0;font-size:0.8rem;background:rgba(255,107,107,0.1);
                                    padding:2px 6px;border-radius:4px;">
                            {err.get('code_snippet','')}
                        </code>
                        <div style="color:#c0c0d8;margin-top:0.4rem;font-size:0.85rem;">🔧 <strong>Fix:</strong> {err.get('fix','')}</div>
                        <div style="color:#9090b8;font-size:0.8rem;margin-top:0.2rem;">📚 {err.get('concept','')}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # Optimizations
            opts = feedback.get("optimizations", [])
            if opts:
                with st.expander("⚡ Optimization Suggestions"):
                    for o in opts:
                        st.markdown(f"- {o}")

            # Best practices
            bps = feedback.get("best_practices", [])
            if bps:
                with st.expander("✅ Best Practice Tips"):
                    for bp in bps:
                        st.markdown(f"- {bp}")

            # Fixed code
            if feedback.get("fixed_code"):
                with st.expander("🔧 Corrected & Optimized Code"):
                    st.code(feedback["fixed_code"], language=lang.lower())
                    if st.button("📋 Use This Code"):
                        st.session_state.buggy_code = feedback["fixed_code"]
                        st.rerun()

            # Encouragement
            if feedback.get("encouragement"):
                st.markdown(f"""
                <div class="success-box">💪 {feedback['encouragement']}</div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-box">Paste your code on the left and click 🔍 Find & Fix Errors to get AI diagnosis.</div>',
                        unsafe_allow_html=True)
            
            # Tips
            st.markdown("#### 💡 Common Python Errors")
            tips = [
                ("IndentationError", "Python uses indentation for blocks. Use 4 spaces consistently."),
                ("NameError", "Variable used before assignment or typo in variable name."),
                ("TypeError", "Operation on incompatible types (e.g., int + string)."),
                ("IndexError", "Accessing a list index that doesn't exist."),
                ("KeyError", "Accessing a dictionary key that doesn't exist."),
                ("AttributeError", "Calling a method/attribute that doesn't exist on an object."),
            ]
            for err_type, desc in tips:
                st.markdown(f"""
                <div style="padding:0.5rem 1rem;border-left:3px solid #6C63FF;
                            background:rgba(108,99,255,0.05);border-radius:0 8px 8px 0;
                            margin-bottom:0.4rem;">
                    <code style="color:#a09cf7;">{err_type}</code>
                    <span style="color:#9090b8;font-size:0.85rem;margin-left:0.5rem;">{desc}</span>
                </div>
                """, unsafe_allow_html=True)

with tab2:
    st.markdown("### 🔎 Full Code Review")
    st.markdown("Get a comprehensive review of your code's quality, style, and performance.")
    
    roadmap = get_latest_roadmap(uid)
    topics = get_topics(uid, roadmap["id"] if roadmap else None) if roadmap else []
    topic_names = [t["topic_name"] for t in topics] if topics else ["General"]
    review_topic = st.selectbox("Topic Context", topic_names, key="review_topic")

    try:
        from streamlit_ace import st_ace
        review_code = st_ace(
            value="# Paste code for review\n",
            language="python", theme="monokai", font_size=14, height=250,
            key="review_editor", auto_update=True,
        )
    except ImportError:
        review_code = st.text_area("Code for Review", height=250, label_visibility="collapsed")

    if st.button("🔍 Full Code Review", use_container_width=True):
        with st.spinner("Reviewing your code..."):
            review = get_code_review(review_code, review_topic, lang)
            st.session_state.code_review = review

    review = st.session_state.get("code_review")
    if review:
        score = review.get("score", 0)
        quality = review.get("overall_quality", "fair")
        quality_colors = {"poor": "#FF6B6B", "fair": "#FFC400", "good": "#00D4A8", "excellent": "#6C63FF"}
        qc = quality_colors.get(quality, "#9090b8")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value" style="color:{qc};">{score}</div>
                <div class="metric-label">Quality Score</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value" style="color:{qc};">{quality.title()}</div>
                <div class="metric-label">Overall Quality</div></div>""", unsafe_allow_html=True)
        with c3:
            rs = review.get("readability_score", 0)
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{rs}/10</div>
                <div class="metric-label">Readability</div></div>""", unsafe_allow_html=True)

        st.markdown(f'<div class="info-box" style="margin-top:1rem;">{review.get("summary","")}</div>',
                    unsafe_allow_html=True)

        categories = [
            ("🎨 Style Issues", review.get("style_issues", []), "badge-yellow"),
            ("⚡ Performance Issues", review.get("performance_issues", []), "badge-red"),
            ("🔒 Security Issues", review.get("security_issues", []), "badge-red"),
            ("💡 Suggestions", review.get("suggestions", []), "badge-blue"),
        ]
        for label, items, badge_cls in categories:
            if items:
                with st.expander(f"{label} ({len(items)})"):
                    for item in items:
                        st.markdown(f'<span class="badge {badge_cls}">{item}</span><br>',
                                    unsafe_allow_html=True)

        with st.expander("✨ Refactored Code"):
            st.code(review.get("refactored_code", ""), language=lang.lower())
