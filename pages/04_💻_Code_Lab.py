import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db_manager import (get_user, get_topics, get_latest_roadmap,
                                   log_code_submission)
from core.adaptive_teacher import generate_practice_problem
from core.error_tutor import analyze_code, run_code_safely
from utils.session_manager import init_session, require_login, require_api_key

st.set_page_config(page_title="Code Lab · EdAI", page_icon="💻", layout="wide")
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session()
require_login()
require_api_key()

uid = st.session_state.user_id
user = get_user(uid)
roadmap = get_latest_roadmap(uid)
topics = get_topics(uid, roadmap["id"] if roadmap else None) if roadmap else []
lang = user.get("preferred_language", "Python")
level = user.get("level", "Beginner")

st.markdown("# 💻 Code Lab")
st.markdown("Write, run, and get AI feedback on your code in real time.")

# ── Layout ───────────────────────────────────────
left_col, right_col = st.columns([1, 1], gap="medium")

# ── Left: Problem + Editor ───────────────────────
with left_col:
    st.markdown("### 🎯 Problem")

    # Topic selector
    topic_names = [t["topic_name"] for t in topics] if topics else ["General Python"]
    default_topic = st.session_state.get("current_topic_name", topic_names[0] if topic_names else "")
    topic_sel = st.selectbox("Topic", topic_names,
                              index=topic_names.index(default_topic) if default_topic in topic_names else 0)
    selected_topic_obj = next((t for t in topics if t["topic_name"] == topic_sel), None)
    tid = selected_topic_obj["id"] if selected_topic_obj else None

    diff = st.select_slider("Difficulty", ["Easy", "Medium", "Hard"], value="Medium")

    if st.button("🎲 Get New Problem", use_container_width=True):
        with st.spinner("Generating problem..."):
            prob = generate_practice_problem(topic_sel, level, lang, diff.lower())
            st.session_state.current_problem = prob
            st.session_state.code_output = ""
            st.session_state.code_feedback = None

    prob = st.session_state.get("current_problem")
    if prob:
        st.markdown(f"""
        <div class="content-panel">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
                <h4 style="margin:0;color:#e8e8f0;">{prob.get('title','')}</h4>
                <span class="badge {'badge-green' if diff=='Easy' else 'badge-yellow' if diff=='Medium' else 'badge-red'}">{diff}</span>
            </div>
            <p style="color:#c0c0d8;line-height:1.7;font-size:0.9rem;">{prob.get('description','')}</p>
        </div>
        """, unsafe_allow_html=True)

        exs = prob.get("examples", [])
        if exs:
            st.markdown("**Examples:**")
            for ex in exs:
                st.markdown(f"""
                <div style="background:#11111f;border-radius:8px;padding:0.75rem;
                            font-family:'JetBrains Mono',monospace;font-size:0.8rem;margin-bottom:0.4rem;">
                    <span style="color:#00D4A8;">▶ Input:</span> {ex.get('input','')}
                    <span style="color:#6C63FF;"> | Output:</span> {ex.get('output','')}
                </div>
                """, unsafe_allow_html=True)

        with st.expander("💡 Hints"):
            for h in prob.get("hints", []):
                st.info(h)

    # ── Code Editor ──────────────────────────────
    st.markdown("### ✍️ Your Code")

    starter = prob.get("starter_code", f"# Write your {lang} solution here\n\n") if prob else f"# Write your {lang} code here\n"

    # Use streamlit-ace if available, else fallback to text_area
    try:
        from streamlit_ace import st_ace
        user_code = st_ace(
            value=st.session_state.get("user_code", starter),
            language=lang.lower() if lang.lower() in ["python","javascript","java","c_cpp"] else "python",
            theme="monokai",
            font_size=14,
            height=350,
            key="ace_editor",
            auto_update=True,
        )
    except ImportError:
        user_code = st.text_area(
            "Code Editor",
            value=st.session_state.get("user_code", starter),
            height=350,
            key="code_textarea",
            label_visibility="collapsed"
        )

    st.session_state.user_code = user_code

    stdin_inp = st.text_input("📥 stdin input (optional)", placeholder="space-separated values...")

    col_run, col_analyze = st.columns(2)
    with col_run:
        run_btn = st.button("▶️ Run Code", use_container_width=True)
    with col_analyze:
        analyze_btn = st.button("🔍 AI Analysis", use_container_width=True)

    if run_btn and user_code:
        with st.spinner("Running..."):
            result = run_code_safely(user_code, stdin_inp)
            st.session_state.code_output = result
            
    if analyze_btn and user_code and prob:
        with st.spinner("🤖 Analyzing your code..."):
            feedback = analyze_code(user_code, prob.get("description",""), lang, level)
            st.session_state.code_feedback = feedback
            # Log submission
            status = "correct" if feedback.get("correctness") == "correct" else "incorrect"
            log_code_submission(uid, tid or 0, topic_sel, prob.get("title","Custom"),
                                user_code, str(st.session_state.code_output),
                                feedback, status)

# ── Right: Output + Feedback ─────────────────────
with right_col:
    st.markdown("### 📤 Output")
    output = st.session_state.get("code_output", "")
    if output:
        if isinstance(output, dict):
            if output.get("success"):
                st.markdown(f"""
                <div class="success-box">
                    <code style="white-space:pre-wrap;">{output.get('stdout','(no output)')}</code>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background:rgba(255,107,107,0.1);border:1px solid rgba(255,107,107,0.3);
                            border-radius:12px;padding:1rem;color:#FF6B6B;">
                    <strong>❌ Error:</strong><br>
                    <code style="white-space:pre-wrap;color:#ffa0a0;">{output.get('stderr','')}</code>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="info-box">Click ▶️ Run Code to see output here.</div>',
                    unsafe_allow_html=True)

    # AI Feedback
    st.markdown("### 🤖 AI Feedback")
    feedback = st.session_state.get("code_feedback")
    if feedback:
        score = feedback.get("score", 0)
        correctness = feedback.get("correctness", "")
        score_color = "#00D4A8" if score >= 80 else "#FFC400" if score >= 50 else "#FF6B6B"

        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:1rem;background:rgba(255,255,255,0.03);border-radius:12px;
                    border:1px solid rgba(255,255,255,0.07);margin-bottom:1rem;">
            <div>
                <div style="color:#9090b8;font-size:0.8rem;">Code Score</div>
                <div style="font-size:2rem;font-weight:800;color:{score_color};">{score}/100</div>
            </div>
            <div>
                <span class="badge {'badge-green' if correctness=='correct' else 'badge-yellow' if correctness=='partially_correct' else 'badge-red'}">
                    {correctness.replace('_',' ').title()}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Errors
        errors = feedback.get("errors", [])
        if errors:
            st.markdown("**🔴 Issues Found:**")
            for err in errors:
                st.markdown(f"""
                <div style="background:rgba(255,107,107,0.08);border:1px solid rgba(255,107,107,0.2);
                            border-radius:10px;padding:0.75rem 1rem;margin-bottom:0.5rem;">
                    <div style="color:#FF6B6B;font-weight:600;">
                        {'Line ' + str(err.get('line','?')) + ': ' if err.get('line') else ''}{err.get('issue','')}
                    </div>
                    <div style="color:#c0c0d8;font-size:0.85rem;margin-top:0.25rem;">🔧 {err.get('fix','')}</div>
                    <div style="color:#9090b8;font-size:0.8rem;margin-top:0.25rem;">📚 Concept: {err.get('concept','')}</div>
                </div>
                """, unsafe_allow_html=True)

        # Logic analysis
        if feedback.get("logic_analysis"):
            st.markdown(f"""
            <div class="info-box" style="margin-bottom:0.75rem;">
                <strong>🧠 Logic Analysis:</strong><br>{feedback['logic_analysis']}
            </div>
            """, unsafe_allow_html=True)

        # Optimizations
        opts = feedback.get("optimizations", [])
        if opts:
            with st.expander("⚡ Optimizations"):
                for o in opts:
                    st.markdown(f"- {o}")

        # Best practices
        bps = feedback.get("best_practices", [])
        if bps:
            with st.expander("✅ Best Practices"):
                for bp in bps:
                    st.markdown(f"- {bp}")

        # Fixed code
        if feedback.get("fixed_code") and feedback.get("has_errors"):
            with st.expander("🔧 Corrected Code"):
                st.code(feedback["fixed_code"], language=lang.lower())

        # Encouragement
        if feedback.get("encouragement"):
            st.markdown(f"""
            <div class="success-box">
                💪 {feedback['encouragement']}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="info-box">Click 🔍 AI Analysis to get instant feedback on your code.</div>',
                    unsafe_allow_html=True)

    # Show solution after attempt
    if prob and feedback:
        with st.expander("📚 View Model Solution"):
            st.code(prob.get("solution", ""), language=lang.lower())
