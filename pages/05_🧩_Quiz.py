import streamlit as st
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db_manager import (get_user, get_topics, get_latest_roadmap,
                                   log_quiz_attempt, get_quiz_attempts)
from core.quiz_engine import generate_quiz, evaluate_quiz, generate_flashcards
from utils.session_manager import init_session, require_login, require_api_key
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Quiz · EdAI", page_icon="🧩", layout="wide")
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
level = user.get("level", "Beginner")
lang  = user.get("preferred_language", "Python")

st.markdown("# 🧩 Quiz Engine")
st.markdown("Test your knowledge with AI-generated quizzes and flashcards.")

tab1, tab2, tab3 = st.tabs(["🎯 Quiz", "🃏 Flashcards", "📊 Quiz History"])

# ── Tab 1: Quiz ──────────────────────────────────
with tab1:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        topic_names = [t["topic_name"] for t in topics] if topics else ["Python Basics"]
        topic_sel = st.selectbox("📌 Select Topic", topic_names)
    with col2:
        num_q = st.selectbox("# Questions", [3, 5, 8, 10, 15], index=1)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        gen_btn = st.button("🎯 Start Quiz", use_container_width=True)

    selected_topic_obj = next((t for t in topics if t["topic_name"] == topic_sel), None)
    tid = selected_topic_obj["id"] if selected_topic_obj else 0

    if gen_btn:
        with st.spinner(f"Generating {num_q} questions on **{topic_sel}**..."):
            qs = generate_quiz(topic_sel, level, num_q, lang)
            st.session_state.quiz_questions = qs
            st.session_state.quiz_answers = {}
            st.session_state.quiz_start_time = time.time()
            st.session_state.quiz_submitted_main = False

    qs = st.session_state.get("quiz_questions", [])
    submitted = st.session_state.get("quiz_submitted_main", False)

    if qs and not submitted:
        elapsed = time.time() - (st.session_state.quiz_start_time or time.time())
        st.markdown(f"""
        <div style="display:flex;gap:1rem;align-items:center;margin-bottom:1rem;">
            <span class="badge badge-blue">📌 {topic_sel}</span>
            <span class="badge badge-purple">{level}</span>
            <span class="badge badge-yellow">⏱️ {int(elapsed)}s elapsed</span>
        </div>
        """, unsafe_allow_html=True)

        with st.form("main_quiz_form"):
            answers = {}
            for i, q in enumerate(qs):
                diff_color = {"easy": "badge-green", "medium": "badge-yellow", "hard": "badge-red"}
                dc = diff_color.get(q.get("difficulty","medium"), "badge-purple")
                st.markdown(f"""
                <div class="quiz-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;margin-bottom:0.75rem;">
                        <div style="font-weight:600;color:#e8e8f0;font-size:1rem;">
                            Q{i+1}. {q['question']}
                        </div>
                        <span class="badge {dc}" style="white-space:nowrap;">{q.get('difficulty','')}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                ans = st.radio("", q["options"], key=f"main_q_{i}", index=None,
                               label_visibility="collapsed")
                answers[str(i)] = ans or ""
                st.markdown("<br>", unsafe_allow_html=True)

            col_sub, col_clr = st.columns([2, 1])
            with col_sub:
                quiz_submit = st.form_submit_button("📝 Submit Quiz", use_container_width=True)
            with col_clr:
                st.form_submit_button("🔄 Clear", use_container_width=True)

        if quiz_submit:
            elapsed = time.time() - (st.session_state.quiz_start_time or time.time())
            result = evaluate_quiz(qs, answers)
            score = result["score"]
            total = result["total"]
            pct, xp = log_quiz_attempt(uid, tid, topic_sel, score, total,
                                        result["results"], int(elapsed))
            st.session_state.quiz_result_main = result
            st.session_state.quiz_submitted_main = True
            st.rerun()

    elif submitted and st.session_state.get("quiz_result_main"):
        res = st.session_state.quiz_result_main
        pct = res["percentage"]
        grade = res["grade"]

        # Score display
        score_color = "#00D4A8" if pct >= 75 else "#FFC400" if pct >= 50 else "#FF6B6B"
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">🎯</div>
                <div class="metric-value" style="color:{score_color};">{pct}%</div>
                <div class="metric-label">Score</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">✅</div>
                <div class="metric-value">{res['score']}/{res['total']}</div>
                <div class="metric-label">Correct</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">🏆</div>
                <div class="metric-value" style="font-size:1.5rem;">{grade.split()[0]}</div>
                <div class="metric-label">{grade.split(None,1)[-1]}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="report-card" style="margin-top:1rem;">
            <strong>💬 Feedback:</strong> {res['feedback']}
        </div>
        """, unsafe_allow_html=True)

        weak = res.get("weak_concepts", [])
        if weak:
            st.markdown(f"""
            <div class="warning-box" style="margin-top:0.75rem;">
                📚 <strong>Review these concepts:</strong> {", ".join(weak)}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### 📋 Detailed Review")
        for r in res["results"]:
            ic = r["is_correct"]
            with st.expander(f"{'✅' if ic else '❌'} Q: {r['question'][:60]}..."):
                st.markdown(f"**Your answer:** {r['user_answer']}")
                if not ic:
                    st.markdown(f"**✔ Correct answer:** {r['correct_answer']}")
                st.info(f"💡 {r['explanation']}")

        if st.button("🔄 Take Another Quiz", use_container_width=True):
            st.session_state.quiz_questions = []
            st.session_state.quiz_submitted_main = False
            st.session_state.quiz_result_main = None
            st.rerun()

# ── Tab 2: Flashcards ────────────────────────────
with tab2:
    st.markdown("### 🃏 Flashcards")
    topic_names_fc = [t["topic_name"] for t in topics] if topics else ["Python Basics"]
    fc_topic = st.selectbox("Topic", topic_names_fc, key="fc_topic")
    fc_num = st.slider("Number of Cards", 4, 20, 8)

    if st.button("🎴 Generate Flashcards"):
        with st.spinner("Creating flashcards..."):
            cards = generate_flashcards(fc_topic, level, fc_num)
            st.session_state.flashcards = cards
            st.session_state.fc_index = 0
            st.session_state.fc_flipped = False

    cards = st.session_state.get("flashcards", [])
    if cards:
        idx = st.session_state.get("fc_index", 0)
        flipped = st.session_state.get("fc_flipped", False)
        card = cards[idx]

        cat_colors = {"definition": "badge-blue", "code": "badge-purple",
                       "formula": "badge-yellow", "concept": "badge-green"}
        cat_cls = cat_colors.get(card.get("category","concept"), "badge-purple")

        st.markdown(f"""
        <div class="content-panel" style="min-height:200px;text-align:center;
                    cursor:pointer;transition:all 0.3s;">
            <div class="badge {cat_cls}" style="margin-bottom:1rem;">{card.get('category','').upper()}</div>
            <div style="font-size:0.8rem;color:#7070a0;margin-bottom:0.5rem;">
                Card {idx+1} of {len(cards)}
            </div>
            <div style="font-size:1.15rem;font-weight:600;color:#e8e8f0;margin-bottom:1rem;">
                {card['front']}
            </div>
            {f'<hr style="border-color:rgba(255,255,255,0.1);"><div style="color:#a09cf7;font-size:0.95rem;line-height:1.6;">{card["back"]}</div>' if flipped else '<div style="color:#5050a0;font-style:italic;">Click "Flip" to see the answer</div>'}
        </div>
        """, unsafe_allow_html=True)

        col_prev, col_flip, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("◀ Prev") and idx > 0:
                st.session_state.fc_index = idx - 1
                st.session_state.fc_flipped = False
                st.rerun()
        with col_flip:
            if st.button("🔄 Flip Card", use_container_width=True):
                st.session_state.fc_flipped = not flipped
                st.rerun()
        with col_next:
            if st.button("Next ▶") and idx < len(cards) - 1:
                st.session_state.fc_index = idx + 1
                st.session_state.fc_flipped = False
                st.rerun()

        # Progress dots
        dots = "".join([
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;margin:0 2px;background:{"#6C63FF" if i==idx else "#2a2a4a"};"></span>'
            for i in range(len(cards))
        ])
        st.markdown(f'<div style="text-align:center;margin-top:0.75rem;">{dots}</div>',
                    unsafe_allow_html=True)

# ── Tab 3: Quiz History ──────────────────────────
with tab3:
    st.markdown("### 📊 Your Quiz History")
    quiz_hist = get_quiz_attempts(uid, limit=50)
    if quiz_hist:
        df = pd.DataFrame(quiz_hist)
        df["created_at"] = pd.to_datetime(df["created_at"])
        df_display = df[["created_at", "topic_name", "score", "total", "percentage", "time_taken_secs"]].copy()
        df_display.columns = ["Date", "Topic", "Score", "Total", "Percentage", "Time (s)"]
        df_display["Percentage"] = df_display["Percentage"].apply(lambda x: f"{x:.1f}%")
        df_display["Date"] = df_display["Date"].dt.strftime("%Y-%m-%d %H:%M")

        # Chart
        import plotly.express as px
        fig = px.line(df.sort_values("created_at"), x="created_at", y="percentage",
                      color="topic_name", markers=True,
                      color_discrete_sequence=px.colors.qualitative.Vivid)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#9090b8"), height=250,
            xaxis=dict(showgrid=False, title=None),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Score %", range=[0,105]),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=0,r=0,t=10,b=0)
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="info-box">No quizzes taken yet. Start a quiz above! 🧩</div>',
                    unsafe_allow_html=True)
