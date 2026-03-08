import streamlit as st
import sys, os, json, tempfile, time as _time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db_manager import (get_user, get_topics, get_latest_roadmap,
                                   get_quiz_attempts, get_code_submissions,
                                   log_interview_session)
from core.interview_coach import (generate_interview_questions, evaluate_interview_answer,
                                   get_job_readiness_report, get_mock_interview_response)
from utils.session_manager import init_session, require_login, require_api_key
from utils.llm_client import ask_llm_json, ask_llm
import plotly.graph_objects as go

st.set_page_config(page_title="Interview Prep · EdAI", page_icon="🎯", layout="wide")
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session()
require_login()
require_api_key()

uid   = st.session_state.user_id
user  = get_user(uid)
roadmap = get_latest_roadmap(uid)
topics  = get_topics(uid, roadmap["id"] if roadmap else None) if roadmap else []
quiz_data = get_quiz_attempts(uid, limit=100)
code_data = get_code_submissions(uid, limit=100)
level = (user or {}).get("level", "Beginner")

# Studied topics — only completed/in_progress ones
studied_topics = [t for t in topics if t.get("status") in ("completed", "in_progress")]

st.markdown("# 🎯 Interview Preparation Coach")
st.markdown("Practice with AI questions, realistic AI interviews, and track your job readiness.")

tab1, tab2, tab3 = st.tabs(["📋 Question Bank", "🎙️ Interview Session", "💼 Job Readiness"])

# ──────────────────────────────────────────────────────────────
# TAB 1 — QUESTION BANK
# ──────────────────────────────────────────────────────────────
with tab1:
    col1, col2, col3 = st.columns(3)
    with col1:
        topic_names = [t["topic_name"] for t in topics] if topics else ["Python", "Data Structures"]
        topic_sel = st.selectbox("📌 Topic", topic_names)
    with col2:
        job_roles = ["Software Engineer", "Data Scientist", "ML Engineer", "Backend Developer",
                     "Full Stack Developer", "Data Analyst", "DevOps Engineer"]
        job_role = st.selectbox("💼 Job Role", job_roles)
    with col3:
        num_q = st.select_slider("# Questions", [5, 8, 10, 15, 20], value=10)

    if st.button("🚀 Generate Interview Questions", use_container_width=True):
        with st.spinner(f"Preparing {num_q} interview questions..."):
            qs = generate_interview_questions(topic_sel, job_role, level, num_q)
            st.session_state.qbank_questions = qs
            st.session_state.qbank_topic     = topic_sel
            st.session_state.interview_evaluations = {}

    qs = st.session_state.get("qbank_questions", [])
    if qs:
        st.markdown(f"### 📋 {len(qs)} Questions — {st.session_state.get('qbank_topic', '')}")
        for i, q in enumerate(qs):
            if isinstance(q, dict):
                q_text = q.get("question", str(q))
                q_type = q.get("type", "")
                if isinstance(q_type, list):
                    q_type = ", ".join(q_type)
                q_diff = q.get("difficulty", "")
                q_follow = q.get("follow_up", "")
            else:
                q_text, q_type, q_diff, q_follow = str(q), "", "", ""

            diff_color = {"Easy": "#34d399", "Medium": "#fbbf24", "Hard": "#fb7185"}.get(q_diff, "#7a7a98")

            with st.expander(f"Q{i+1}: {q_text[:80]}{'…' if len(q_text)>80 else ''}"):
                st.markdown(f"""
                <div style="background:rgba(124,109,250,0.05);border-left:3px solid var(--accent);
                            padding:1rem 1.25rem;border-radius:0 8px 8px 0;margin-bottom:.75rem;">
                    <div style="display:flex;gap:.5rem;align-items:center;margin-bottom:.5rem;flex-wrap:wrap;">
                        {'<span style="font-size:.7rem;background:rgba(124,109,250,.18);color:#a09cf7;padding:2px 8px;border-radius:4px;">'+q_type+'</span>' if q_type else ''}
                        {'<span style="font-size:.7rem;background:rgba(0,0,0,.25);color:'+diff_color+';padding:2px 8px;border-radius:4px;border:1px solid '+diff_color+'">'+q_diff+'</span>' if q_diff else ''}
                    </div>
                    <div style="color:var(--text-primary);font-size:1rem;font-weight:600;">{q_text}</div>
                    {('<div style="color:var(--text-muted);font-size:.82rem;margin-top:.5rem;">🔄 Follow-up: '+q_follow+'</div>') if q_follow else ''}
                </div>
                """, unsafe_allow_html=True)

                ans = st.text_area("✍️ Your Answer:", key=f"qb_ans_{i}", height=90,
                                   placeholder="Type your answer here to get AI feedback...")
                if st.button("🤖 Evaluate", key=f"qb_eval_{i}") and ans.strip():
                    with st.spinner("Evaluating..."):
                        ev = evaluate_interview_answer(
                            q_text, ans,
                            q.get("expected_answer", "") if isinstance(q, dict) else "",
                            level
                        )
                        st.session_state.setdefault("interview_evaluations", {})[i] = ev

                ev = st.session_state.get("interview_evaluations", {}).get(i)
                if ev:
                    score = ev.get("score", 0)
                    verdict = ev.get("verdict", "")
                    vc = {"strong": "#00D4A8", "adequate": "#FFC400", "needs_improvement": "#FF6B6B"}.get(verdict, "#9090b8")
                    vl = {"strong": "💪 Strong", "adequate": "👍 Adequate", "needs_improvement": "📚 Needs Work"}.get(verdict, "")
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.03);border-radius:10px;padding:.875rem 1rem;
                                border:1px solid rgba(255,255,255,0.07);margin-top:.5rem;">
                        <div style="display:flex;gap:1rem;align-items:center;margin-bottom:.5rem;">
                            <span style="font-size:1.4rem;font-weight:800;color:{vc};">{score}/10</span>
                            <span style="color:{vc};font-weight:600;">{vl}</span>
                        </div>
                        <div style="color:#c0c0d8;font-size:.83rem;">
                            <strong>Coverage:</strong> {ev.get('coverage','')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    cs, gs = st.columns(2)
                    with cs:
                        st.markdown("**✅ Strengths:**")
                        for s in ev.get("strengths", []):
                            st.markdown(f"- {s}")
                    with gs:
                        st.markdown("**📌 To Improve:**")
                        for g in ev.get("gaps", []):
                            st.markdown(f"- {g}")
                    with st.expander("🌟 Model Answer"):
                        st.markdown(ev.get("improved_answer", ""))
                    if ev.get("tips"):
                        st.markdown(f'<div class="info-box">💡 {ev["tips"]}</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# TAB 2 — UNIFIED INTERVIEW SESSION
# ──────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 🎙️ Interview Session")

    # ── Mode selector ─────────────────────────────────────────
    mode = st.radio(
        "Choose Interview Mode:",
        ["🧠 Mock Interview — Conversational AI", "📖 Study Q&A — Spoken Viva"],
        horizontal=True,
        key="interview_mode"
    )
    st.markdown("---")

    # ────────────────────────────────────────────────────────────
    # MODE A — MOCK INTERVIEW (Live Conversational)
    # ────────────────────────────────────────────────────────────
    if mode == "🧠 Mock Interview — Conversational AI":
        st.markdown("""
        <div style="background:rgba(124,109,250,0.06);border:1px solid rgba(124,109,250,0.2);
                    border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;font-size:.875rem;
                    color:var(--text-base);">
            🤵 <strong>How it works:</strong> The AI interviewer asks questions one at a time.
            You speak or type your answer. The AI responds naturally and asks the next question —
            just like a real interview. Set a time limit or max rounds before starting.
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state.get("mock_active"):
            # ── Setup form ────────────────────────────────────
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                mock_topic_opts = [t["topic_name"] for t in topics] if topics else ["Python", "Data Structures", "System Design"]
                mock_topic = st.selectbox("📌 Topic(s)", mock_topic_opts, key="mock_topic_sel")
            with mc2:
                mock_role = st.selectbox("💼 Role", ["Software Engineer", "Data Scientist", "ML Engineer",
                                                      "Backend Developer", "Full Stack Developer"], key="mock_role_sel")
            with mc3:
                mock_duration = st.select_slider("⏱️ Duration", ["10 min", "20 min", "30 min", "Open-ended"], value="20 min", key="mock_dur")

            if st.button("🎙️ Start Mock Interview", use_container_width=True, type="primary"):
                with st.spinner("🤵 Your AI interviewer is getting ready…"):
                    # Generate a rich opening question to kick off
                    opening_prompt = f"""
You are a professional {mock_role} interviewer conducting a {mock_duration} interview on "{mock_topic}" with a {level}-level candidate.

Start the interview with a warm opening and your FIRST question. Keep it conversational and natural — like a real interview.

Return ONLY JSON:
{{
  "opening": "Brief warm opening (1-2 sentences, don't say 'certainly' or 'of course')",
  "first_question": "Your opening interview question (natural spoken language)",
  "topic_focus": "{mock_topic}",
  "interview_context": "Brief 1-sentence description of what kind of interview this is"
}}
Return ONLY valid JSON.
"""
                    opening_data = ask_llm_json(opening_prompt, temperature=0.6)
                    if not opening_data:
                        opening_data = {
                            "opening": f"Welcome! Let's have a {mock_duration} conversation about {mock_topic}.",
                            "first_question": f"Can you start by telling me about your experience with {mock_topic}?",
                            "topic_focus": mock_topic,
                            "interview_context": f"{mock_duration} conversational interview"
                        }

                st.session_state.mock_active     = True
                st.session_state.mock_history    = []
                st.session_state.mock_start_time = _time.time()
                st.session_state.mock_duration   = mock_duration
                st.session_state.mock_topic_s    = mock_topic
                st.session_state.mock_role_s     = mock_role
                st.session_state.mock_opening    = opening_data
                st.session_state.mock_round      = 0
                st.session_state.mock_ended      = False
                st.rerun()

        else:
            # ── Active interview ──────────────────────────────
            mock_history    = st.session_state.get("mock_history", [])
            mock_opening    = st.session_state.get("mock_opening", {})
            mock_topic_s    = st.session_state.get("mock_topic_s", "")
            mock_role_s     = st.session_state.get("mock_role_s", "")
            mock_start_time = st.session_state.get("mock_start_time", _time.time())
            mock_duration   = st.session_state.get("mock_duration", "20 min")
            mock_round      = st.session_state.get("mock_round", 0)

            # Calculate elapsed time
            elapsed_secs = _time.time() - mock_start_time
            elapsed_min  = elapsed_secs / 60
            dur_mins     = int(mock_duration.split()[0]) if mock_duration != "Open-ended" else 999

            # Time-up detection
            if mock_duration != "Open-ended" and elapsed_min >= dur_mins:
                st.session_state.mock_ended = True

            if st.session_state.get("mock_ended"):
                # ── Interview ended summary ─────────────────
                n_answered = len(mock_history)
                st.markdown(f"""
                <div style="text-align:center;padding:2rem;background:rgba(255,255,255,.02);
                            border-radius:16px;border:1px solid rgba(255,255,255,.07);">
                    <div style="font-size:3rem;">🎉</div>
                    <h3 style="color:var(--text-primary);">Interview Complete!</h3>
                    <div style="color:var(--text-muted);">
                        {n_answered} exchanges · {int(elapsed_min)} min {int(elapsed_secs % 60)}s
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if mock_history:
                    st.markdown("### 📋 Interview Recap")
                    for i, turn in enumerate(mock_history):
                        with st.expander(f"Exchange {i+1}: {turn.get('q','')[:60]}…"):
                            st.markdown(f"**🤵 Interviewer:** {turn.get('q','')}")
                            st.markdown(f"**👤 You:** {turn.get('a','')}")
                            if turn.get("ir"):
                                st.markdown(f"**🤵 Response:** {turn.get('ir','')}")

                if st.button("🔄 Start New Interview", use_container_width=True, type="primary"):
                    for k in ["mock_active", "mock_history", "mock_opening", "mock_round",
                              "mock_start_time", "mock_ended", "mock_topic_s", "mock_role_s",
                              "mock_duration"]:
                        st.session_state.pop(k, None)
                    st.rerun()
            else:
                # ── Time bar (only if not open-ended) ────────
                if mock_duration != "Open-ended":
                    time_pct = min(elapsed_min / dur_mins, 1.0)
                    remaining = max(dur_mins - elapsed_min, 0)
                    bar_color = "#34d399" if time_pct < 0.6 else "#fbbf24" if time_pct < 0.85 else "#fb7185"
                    st.markdown(f"""
                    <div style="background:var(--bg-elevated);border:1px solid var(--border);
                                border-radius:var(--radius);padding:.75rem 1.25rem;margin-bottom:1rem;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:.35rem;">
                            <span style="font-size:.72rem;color:var(--text-muted);">⏱️ {mock_duration} Session</span>
                            <span style="font-size:.78rem;font-weight:700;color:{bar_color};">
                                {int(remaining)}m {int((remaining % 1)*60)}s remaining
                            </span>
                        </div>
                        <div style="background:var(--bg-overlay);border-radius:99px;height:5px;overflow:hidden;">
                            <div style="height:100%;width:{time_pct*100:.0f}%;
                                        background:linear-gradient(90deg,{bar_color},{bar_color});
                                        border-radius:99px;transition:width 1s ease;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # ── Chat history ──────────────────────────────
                if not mock_history:
                    # Show opening
                    opening_text = mock_opening.get("opening", "")
                    first_q      = mock_opening.get("first_question", "")
                    st.markdown(f"""
                    <div style="padding:.875rem 1.125rem;border-radius:12px;margin-bottom:.5rem;
                                background:rgba(108,99,255,0.08);border:1px solid rgba(108,99,255,0.2);">
                        <span style="color:#a09cf7;font-size:.8rem;font-weight:700;">🤵 Interviewer</span>
                        <div style="color:#e8e8f0;margin-top:.4rem;line-height:1.6;">
                            {opening_text}<br><br><strong>{first_q}</strong>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    # Store the first question
                    st.session_state._current_mock_q = first_q
                else:
                    # Show last 6 exchanges
                    for turn in mock_history[-5:]:
                        st.markdown(f"""
                        <div style="padding:.75rem 1rem;border-radius:10px;margin-bottom:.4rem;
                                    background:rgba(108,99,255,0.08);border:1px solid rgba(108,99,255,0.18);">
                            <span style="color:#a09cf7;font-size:.78rem;font-weight:700;">🤵 Interviewer</span>
                            <div style="color:#e8e8f0;margin-top:.25rem;">{turn.get('q','')}</div>
                        </div>
                        <div style="padding:.75rem 1rem;border-radius:10px;margin-bottom:.75rem;
                                    background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.13);">
                            <span style="color:#00D4FF;font-size:.78rem;font-weight:700;">👤 You</span>
                            <div style="color:#c0c0d8;margin-top:.25rem;">{turn.get('a','')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if turn.get("ir"):
                            # The interviewer's follow-up / next question is stored in next turn
                            pass

                # ── Current question + answer input ──────────
                current_q = st.session_state.get("_current_mock_q",
                    mock_opening.get("first_question", f"Tell me about your experience with {mock_topic_s}."))

                if mock_history:
                    current_q = mock_history[-1].get("next_q", current_q)

                # Show current question boldly
                st.markdown(f"""
                <div style="background:rgba(124,109,250,0.1);border:1px solid rgba(124,109,250,.35);
                            border-radius:12px;padding:1.25rem 1.5rem;margin:.5rem 0 1rem;">
                    <span style="color:#a09cf7;font-size:.78rem;font-weight:700;">🤵 Current Question</span>
                    <div style="font-size:1.05rem;font-weight:600;color:#e8e8f0;margin-top:.4rem;line-height:1.55;">
                        {current_q}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ── Voice input ───────────────────────────────
                transcribed = ""
                try:
                    audio = st.audio_input("🎙️ Speak your answer", key=f"mock_audio_{mock_round}")
                    if audio is not None:
                        try:
                            import speech_recognition as sr
                            recognizer = sr.Recognizer()
                            audio_bytes = audio.read()
                            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                                tmp.write(audio_bytes); tmp_path = tmp.name
                            with sr.AudioFile(tmp_path) as src:
                                audio_content = recognizer.record(src)
                            try:
                                transcribed = recognizer.recognize_google(audio_content)
                                os.unlink(tmp_path)
                                st.markdown(f"""
                                <div style="background:rgba(52,211,153,.06);border:1px solid rgba(52,211,153,.25);
                                            border-radius:8px;padding:.75rem 1rem;margin-bottom:.5rem;">
                                    <span style="font-size:.7rem;font-weight:700;color:#34d399;text-transform:uppercase;">
                                        ✓ Transcribed
                                    </span>
                                    <div style="color:var(--text-base);font-size:.9rem;margin-top:.25rem;">
                                        "{transcribed}"
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            except Exception:
                                os.unlink(tmp_path)
                                st.warning("⚠️ Couldn't transcribe — type below")
                        except ImportError:
                            st.info("💡 Install SpeechRecognition for voice: `pip install SpeechRecognition`")
                except AttributeError:
                    pass  # old Streamlit, skip audio

                user_reply = st.text_area(
                    "📝 Your answer (type or override transcription):",
                    value=transcribed, height=100,
                    key=f"mock_ans_{mock_round}",
                    placeholder="Speak or type your response…"
                )

                col_send, col_end = st.columns([3, 1])
                with col_send:
                    send_btn = st.button("✅ Send Reply", use_container_width=True,
                                         type="primary", key=f"mock_send_{mock_round}")
                with col_end:
                    if st.button("🏁 End Interview", use_container_width=True, key="mock_end_btn"):
                        st.session_state.mock_ended = True
                        st.rerun()

                if send_btn and (user_reply or transcribed).strip():
                    reply_text = (user_reply or transcribed).strip()
                    with st.spinner("🤵 Interviewer is thinking…"):
                        # Build context from history for natural conversation
                        history_ctx = "\n".join([
                            f"Q: {t['q']}\nA: {t['a']}" for t in mock_history[-4:]
                        ])
                        next_q_prompt = f"""
You are a professional {mock_role_s} interviewer. You have been interviewing a {level}-level candidate on "{mock_topic_s}".

INTERVIEW CONTEXT:
{history_ctx}

LATEST EXCHANGE:
Interviewer: {current_q}
Candidate: "{reply_text}"

Respond naturally as an interviewer would:
1. Give a brief, genuine reaction to their answer (1-2 sentences — acknowledge, probe, or comment)
2. Ask your NEXT interview question (keep it relevant, building on what was discussed)

Keep it conversational and natural — like a real interview. No "Great answer!" filler.
Return ONLY JSON:
{{
  "reaction": "Your brief reaction to their answer (1-2 sentences)",
  "next_question": "Your next interview question"
}}
Return ONLY valid JSON.
"""
                        resp = ask_llm_json(next_q_prompt, temperature=0.65)
                        if not resp:
                            resp = {"reaction": "I see, interesting perspective.",
                                    "next_question": f"Can you tell me more about how you've applied {mock_topic_s} in practice?"}

                    # Store exchange
                    turn_data = {
                        "q": current_q,
                        "a": reply_text,
                        "ir": resp.get("reaction", ""),
                        "next_q": resp.get("next_question", "")
                    }
                    mock_history.append(turn_data)
                    st.session_state.mock_history = mock_history
                    st.session_state.mock_round   = mock_round + 1
                    st.session_state._current_mock_q = resp.get("next_question", "")

                    # Show interviewer reaction before rerun
                    st.markdown(f"""
                    <div style="padding:1rem;background:rgba(108,99,255,0.1);border-radius:10px;
                                border:1px solid rgba(108,99,255,0.2);margin:.5rem 0;">
                        <span style="color:#a09cf7;font-weight:700;">🤵 Interviewer</span>
                        <div style="color:#e8e8f0;margin-top:.25rem;">{resp.get('reaction','')} <br><br>
                            <strong>{resp.get('next_question','')}</strong>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    _time.sleep(0.5)
                    st.rerun()

    # ────────────────────────────────────────────────────────────
    # MODE B — STUDY Q&A SPOKEN VIVA
    # ────────────────────────────────────────────────────────────
    else:
        st.markdown("""
        <div style="background:rgba(34,211,238,0.06);border:1px solid rgba(34,211,238,0.2);
                    border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;font-size:.875rem;
                    color:var(--text-base);">
            📖 <strong>How it works:</strong> Based on what you have studied in your roadmap,
            the AI generates questions. Speak your answer — it transcribes and compares with the
            model answer, giving detailed feedback on what you covered and missed.
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state.get("viva_active"):
            # ── Setup ─────────────────────────────────────────
            vc1, vc2, vc3 = st.columns(3)
            with vc1:
                viva_topic_opts = [t["topic_name"] for t in studied_topics] if studied_topics else \
                                  [t["topic_name"] for t in topics] if topics else ["Python"]
                viva_topic = st.selectbox("📖 Studied Topic", viva_topic_opts, key="viva_topic_sel",
                                           help="Only topics you've started/completed appear here")
            with vc2:
                viva_role = st.selectbox("💼 Context Role", ["Software Engineer", "Data Scientist",
                                                              "ML Engineer", "Backend Developer"], key="viva_role_sel")
            with vc3:
                viva_n = st.select_slider("# Questions", [3, 5, 8, 10], value=5, key="viva_n_sel")

            if studied_topics:
                st.info(f"📚 You have {len(studied_topics)} studied topic(s) available for Q&A")
            else:
                st.warning("⚠️ No studied topics yet. Go to Study and start learning first! Any topic will work for now.")

            if st.button("📖 Start Study Q&A", use_container_width=True, type="primary"):
                with st.spinner("🧠 Generating questions based on your studies…"):
                    viva_prompt = f"""
You are a {viva_role} interviewer quizzing a {level}-level student on what they have studied about "{viva_topic}".

Generate {viva_n} questions that test deep understanding — not just surface recall.
Questions should be spoken-exam style: clear, concise, 1-2 sentences each.

Return ONLY JSON:
{{
  "questions": [
    {{
      "question": "Clear spoken question suitable for a viva exam",
      "model_answer": "Complete ideal answer in plain spoken language (150-200 words)",
      "key_points": ["key point 1", "key point 2", "key point 3"],
      "difficulty": "Easy|Medium|Hard"
    }}
  ]
}}
Return ONLY valid JSON. No markdown fences.
"""
                    viva_data = ask_llm_json(viva_prompt, temperature=0.4)
                    if viva_data and viva_data.get("questions"):
                        qs = viva_data["questions"]
                    else:
                        qs = [{"question": f"Explain the core concepts of {viva_topic} in your own words.",
                               "model_answer": "A comprehensive understanding of the topic fundamentals.",
                               "key_points": ["Core concepts", "Practical application", "Common use cases"],
                               "difficulty": "Medium"}]

                st.session_state.viva_active  = True
                st.session_state.viva_qs      = qs
                st.session_state.viva_idx     = 0
                st.session_state.viva_results = []
                st.session_state.viva_topic_s = viva_topic
                st.session_state.viva_role_s  = viva_role
                st.rerun()
        else:
            viva_qs     = st.session_state.get("viva_qs", [])
            viva_idx    = st.session_state.get("viva_idx", 0)
            viva_results = st.session_state.get("viva_results", [])
            viva_topic_s = st.session_state.get("viva_topic_s", "")
            viva_role_s  = st.session_state.get("viva_role_s", "")

            # ── Progress bar ──────────────────────────────────
            pct = viva_idx / max(len(viva_qs), 1)
            st.markdown(f"""
            <div style="background:var(--bg-elevated);border:1px solid var(--border);
                        border-radius:var(--radius);padding:.875rem 1.25rem;margin-bottom:1rem;">
                <div style="display:flex;justify-content:space-between;margin-bottom:.4rem;">
                    <span style="font-size:.72rem;color:var(--text-muted);">📖 {viva_topic_s} · Q&A Progress</span>
                    <span style="font-size:.78rem;font-weight:700;color:var(--accent);">{viva_idx}/{len(viva_qs)}</span>
                </div>
                <div style="background:var(--bg-overlay);border-radius:99px;height:6px;overflow:hidden;">
                    <div style="height:100%;width:{pct*100:.0f}%;background:linear-gradient(90deg,var(--cyan),var(--accent));
                                border-radius:99px;transition:width .5s ease;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if viva_idx < len(viva_qs):
                cq = viva_qs[viva_idx]
                diff_c = {"Easy": "#34d399", "Medium": "#fbbf24", "Hard": "#fb7185"}.get(cq.get("difficulty","Medium"), "#fbbf24")

                st.markdown(f"""
                <div style="background:rgba(34,211,238,0.07);border:1px solid rgba(34,211,238,0.25);
                            border-radius:12px;padding:1.5rem 1.75rem;margin-bottom:1.25rem;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem;">
                        <span style="font-size:.72rem;font-weight:700;color:#22d3ee;
                                     text-transform:uppercase;letter-spacing:.5px;">
                            Question {viva_idx+1} of {len(viva_qs)}
                        </span>
                        <span style="font-size:.72rem;font-weight:700;color:{diff_c};
                                     background:rgba(0,0,0,.25);padding:2px 10px;
                                     border-radius:99px;border:1px solid {diff_c};">
                            {cq.get('difficulty','Medium')}
                        </span>
                    </div>
                    <div style="font-size:1.1rem;font-weight:700;color:var(--text-primary);line-height:1.55;">
                        📖 {cq.get('question','')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ── Voice input ───────────────────────────────
                transcribed_v = ""
                try:
                    audio_v = st.audio_input("🎙️ Speak your answer", key=f"viva_audio_{viva_idx}")
                    if audio_v is not None:
                        try:
                            import speech_recognition as sr
                            recognizer = sr.Recognizer()
                            audio_bytes = audio_v.read()
                            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                                tmp.write(audio_bytes); tmp_path = tmp.name
                            with sr.AudioFile(tmp_path) as src:
                                audio_content = recognizer.record(src)
                            try:
                                transcribed_v = recognizer.recognize_google(audio_content)
                                os.unlink(tmp_path)
                                st.markdown(f"""
                                <div style="background:rgba(52,211,153,.06);border:1px solid rgba(52,211,153,.25);
                                            border-radius:8px;padding:.75rem 1rem;margin:.5rem 0;">
                                    <span style="font-size:.7rem;font-weight:700;color:#34d399;text-transform:uppercase;">✓ Transcribed</span>
                                    <div style="color:var(--text-base);font-size:.9rem;margin-top:.25rem;">"{transcribed_v}"</div>
                                </div>
                                """, unsafe_allow_html=True)
                            except Exception:
                                os.unlink(tmp_path)
                                st.warning("⚠️ Couldn't transcribe — type below")
                        except ImportError:
                            pass
                except AttributeError:
                    pass

                manual_v = st.text_area(
                    "📝 Your answer:", value=transcribed_v, height=110,
                    key=f"viva_text_{viva_idx}",
                    placeholder="Speak into the mic above, or type your answer here…"
                )
                final_ans = (manual_v or transcribed_v).strip()

                col_sub, col_skip, col_rst = st.columns([3, 2, 2])
                with col_sub:
                    sub_btn = st.button("✅ Submit Answer", use_container_width=True,
                                        type="primary", key=f"viva_sub_{viva_idx}")
                with col_skip:
                    skip_btn = st.button("⏭ Skip", use_container_width=True, key=f"viva_skip_{viva_idx}")
                with col_rst:
                    if st.button("🔄 Restart", use_container_width=True, key="viva_rst"):
                        for k in ["viva_active","viva_qs","viva_idx","viva_results","viva_topic_s","viva_role_s"]:
                            st.session_state.pop(k, None)
                        st.rerun()

                if sub_btn and final_ans:
                    with st.spinner("🤖 Comparing with model answer…"):
                        eval_p = f"""
Evaluate this viva answer from a {level} student.

QUESTION: {cq.get('question','')}
MODEL ANSWER: {cq.get('model_answer','')}
KEY POINTS: {json.dumps(cq.get('key_points', []))}
STUDENT'S ANSWER: "{final_ans}"

Return ONLY JSON:
{{
  "score": <1-10>,
  "verdict": "excellent|good|adequate|needs_improvement",
  "coverage_pct": <0-100>,
  "feedback": "2-3 sentence specific feedback on their answer",
  "strengths": ["specific things they got right"],
  "missed": ["specific concepts they missed"],
  "ideal_phrasing": "How the core idea should have been expressed (1-2 sentences)"
}}
Return ONLY valid JSON.
"""
                        ev = ask_llm_json(eval_p, temperature=0.3) or {
                            "score": 5, "verdict": "adequate", "coverage_pct": 50,
                            "feedback": "Could not evaluate. Check LLM connection.",
                            "strengths": [], "missed": [],
                            "ideal_phrasing": cq.get("model_answer","")[:200]
                        }

                    viva_results.append({"q": cq.get("question",""), "a": final_ans,
                                         "ev": ev, "model": cq.get("model_answer","")})
                    st.session_state.viva_results = viva_results
                    st.session_state.viva_idx = viva_idx + 1

                    sc = ev.get("score", 5)
                    vc = "#34d399" if sc >= 7 else "#fbbf24" if sc >= 5 else "#fb7185"
                    vl = {"excellent":"🌟 Excellent!","good":"👍 Good","adequate":"✅ Adequate","needs_improvement":"📚 Needs Work"}.get(ev.get("verdict",""), "✅ Done")
                    st.markdown(f"""
                    <div style="background:rgba(0,0,0,.15);border:1px solid {vc};border-radius:12px;
                                padding:1.25rem 1.5rem;margin-top:.75rem;">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem;">
                            <span style="font-size:1rem;font-weight:700;color:{vc};">{vl}</span>
                            <span style="font-size:1.5rem;font-weight:800;color:{vc};">{sc}/10</span>
                        </div>
                        <div style="font-size:.875rem;color:var(--text-base);line-height:1.6;">
                            {ev.get('feedback','')}
                        </div>
                        <div style="font-size:.72rem;color:var(--text-muted);margin-top:.5rem;">
                            Coverage: {ev.get('coverage_pct',0)}%
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    with st.expander("💡 Model Answer"):
                        st.markdown(cq.get("model_answer",""))
                        if ev.get("ideal_phrasing"):
                            st.markdown(f"""
                            <div style="border-left:2px solid var(--accent);padding:.75rem 1rem;
                                        border-radius:0 8px 8px 0;margin-top:.5rem;font-size:.875rem;
                                        background:rgba(124,109,250,.06);color:var(--text-base);">
                                💬 <strong>Better phrasing:</strong> {ev['ideal_phrasing']}
                            </div>
                            """, unsafe_allow_html=True)
                    _time.sleep(0.3)
                    st.rerun()

                if skip_btn:
                    viva_results.append({"q": cq.get("question",""), "a": "(skipped)",
                                         "ev": {"score":0,"verdict":"needs_improvement","feedback":"Skipped."},
                                         "model": cq.get("model_answer","")})
                    st.session_state.viva_results = viva_results
                    st.session_state.viva_idx = viva_idx + 1
                    st.rerun()

            else:
                # ── Session complete ──────────────────────────
                answered = [r for r in viva_results if r["a"] != "(skipped)"]
                scores   = [r["ev"].get("score", 0) for r in answered]
                avg      = sum(scores) / max(len(scores), 1)
                pc       = "#34d399" if avg >= 7 else "#fbbf24" if avg >= 5 else "#fb7185"
                pl       = "Excellent" if avg >= 8 else "Good" if avg >= 6 else "Fair" if avg >= 4 else "Needs Practice"

                st.markdown(f"""
                <div style="text-align:center;background:var(--bg-elevated);border:1px solid var(--border);
                            border-radius:16px;padding:2rem;margin-bottom:1.5rem;">
                    <div style="font-size:2.5rem;">📖</div>
                    <h3 style="color:var(--text-primary);">Study Q&A Complete!</h3>
                    <div style="font-size:3rem;font-weight:800;color:{pc};">{avg:.1f}<span style="font-size:1.25rem;">/10</span></div>
                    <div style="color:var(--text-muted);">{pl} · {len(answered)}/{len(viva_qs)} answered</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("### 📋 Review")
                for i, r in enumerate(viva_results):
                    sc = r["ev"].get("score", 0)
                    scc = "#34d399" if sc >= 7 else "#fbbf24" if sc >= 5 else "#fb7185"
                    with st.expander(f"Q{i+1} — {r['q'][:60]}… · {sc}/10"):
                        ca, cb = st.columns(2)
                        with ca:
                            st.markdown("**Your Answer:**")
                            st.markdown(f"*{r['a']}*")
                        with cb:
                            st.markdown("**Model (excerpt):**")
                            st.markdown(f"*{r['model'][:180]}…*")
                        st.markdown(f"**💬 Feedback:** {r['ev'].get('feedback','')}")

                if st.button("🔄 New Study Q&A", use_container_width=True, type="primary"):
                    for k in ["viva_active","viva_qs","viva_idx","viva_results","viva_topic_s","viva_role_s"]:
                        st.session_state.pop(k, None)
                    st.rerun()


# ──────────────────────────────────────────────────────────────
# TAB 3 — JOB READINESS
# ──────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 💼 Job Readiness Assessment")

    topic_sel_jr = st.selectbox("Topic", [t["topic_name"] for t in topics] if topics else ["Python"],
                                 key="jr_topic")

    if st.button("🎯 Assess My Job Readiness", use_container_width=True):
        quiz_scores = [q.get("percentage", 0) for q in quiz_data if q.get("topic_name") == topic_sel_jr]
        code_scores_raw = [c.get("xp_earned", 0) for c in code_data if c.get("topic_name") == topic_sel_jr]
        code_scores = [(s / 20) * 100 for s in code_scores_raw]
        iv_scores = [r["ev"].get("score",5)*10 for r in st.session_state.get("viva_results",[]) if "ev" in r]

        with st.spinner("Analyzing your readiness..."):
            report = get_job_readiness_report(
                topic_sel_jr, quiz_scores or [50], code_scores or [50],
                iv_scores or [5], level
            )
            st.session_state.job_readiness = report

    jr = st.session_state.get("job_readiness")
    if jr:
        readiness = jr.get("readiness_score", 0)
        readiness_level = jr.get("readiness_level", "Learning")
        rcolor = "#FF6B6B" if readiness < 40 else "#FFC400" if readiness < 65 else "#00D4A8"

        fig_jr = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=readiness,
            number={"suffix": "%", "font": {"color": rcolor, "size": 40}},
            title={"text": readiness_level, "font": {"color": "#9090b8", "size": 14}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": rcolor},
                "bgcolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0,40], "color": "rgba(255,107,107,0.1)"},
                    {"range": [40,65], "color": "rgba(255,196,0,0.1)"},
                    {"range": [65,80], "color": "rgba(0,212,168,0.1)"},
                    {"range": [80,100], "color": "rgba(108,99,255,0.15)"},
                ]
            }
        ))
        fig_jr.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#9090b8"),
            height=220, margin=dict(l=30,r=30,t=30,b=0)
        )
        col_gauge, col_info = st.columns([1, 2])
        with col_gauge:
            st.plotly_chart(fig_jr, use_container_width=True)
        with col_info:
            st.markdown(f"""
            <div style="padding:1rem;">
                <div style="color:#9090b8;font-size:.8rem;">Estimated Ready In</div>
                <div style="font-size:1.2rem;font-weight:700;color:#e8e8f0;">{jr.get('estimated_ready_in','')}</div>
                <div style="color:#9090b8;font-size:.8rem;margin-top:.75rem;">Salary Range (Junior–Mid)</div>
                <div style="font-size:1rem;font-weight:600;color:#00D4A8;">{jr.get('salary_range','')}</div>
            </div>
            """, unsafe_allow_html=True)

        roles = jr.get("suitable_roles", [])
        if roles:
            st.markdown("#### 💼 Suitable Job Roles")
            r_cols = st.columns(min(len(roles), 3))
            for i, role in enumerate(roles):
                with r_cols[i % len(r_cols)]:
                    match = role.get("match_pct", 0)
                    mc = "#00D4A8" if match >= 70 else "#FFC400" if match >= 50 else "#FF6B6B"
                    companies = ", ".join(role.get("company_examples", [])[:2])
                    st.markdown(f"""
                    <div class="metric-card" style="text-align:left;">
                        <div style="font-weight:700;color:#e8e8f0;">{role.get('role','')}</div>
                        <div style="font-size:1.5rem;font-weight:800;color:{mc};margin:.5rem 0;">{match}%</div>
                        <div style="color:#7070a0;font-size:.8rem;">match</div>
                        {('<div style="color:#5050a0;font-size:.75rem;margin-top:.25rem;">e.g. '+companies+'</div>') if companies else ''}
                    </div>
                    """, unsafe_allow_html=True)

        col_s, col_a = st.columns(2)
        with col_s:
            st.markdown("**💪 Strengths:**")
            for s in jr.get("strengths", []):
                st.markdown(f'<div class="success-box" style="margin-bottom:.4rem;">{s}</div>',
                            unsafe_allow_html=True)
        with col_a:
            st.markdown("**📚 Action Plan:**")
            for step in jr.get("action_plan", []):
                st.markdown(f"""
                <div style="padding:.4rem .75rem;border-left:3px solid #6C63FF;
                            background:rgba(108,99,255,0.07);border-radius:0 8px 8px 0;
                            margin-bottom:.4rem;color:#c0c0d8;font-size:.85rem;">{step}</div>
                """, unsafe_allow_html=True)

        if jr.get("message"):
            st.markdown(f'<div class="report-card" style="margin-top:1rem;text-align:center;">{jr["message"]}</div>',
                        unsafe_allow_html=True)
    else:
        st.markdown('<div class="info-box">Click the button above to get your personalized job readiness assessment.</div>',
                    unsafe_allow_html=True)
