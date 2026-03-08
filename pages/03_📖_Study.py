import streamlit as st
import sys, os, time
from contextlib import nullcontext
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db_manager import (get_user, get_topics, get_latest_roadmap,
                                   update_topic_status, log_study_session,
                                   log_quiz_attempt, log_code_submission,
                                   save_study_content, get_study_content)
from core.adaptive_teacher import teach_topic, generate_practice_problem
from core.quiz_engine import generate_quiz, evaluate_quiz
from core.error_tutor import run_code_safely
from utils.session_manager import init_session, require_login, require_api_key

st.set_page_config(page_title="Study · EdAI", page_icon="📖", layout="wide")
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session()
require_login()
require_api_key()

uid   = st.session_state.user_id
user  = get_user(uid)
level = user.get("level", "Beginner")
roadmap = get_latest_roadmap(uid)
topics  = get_topics(uid, roadmap["id"] if roadmap else None) if roadmap else []

# ══════════════════════════════════════════════════════
# SMART TOPIC DETECTION
# Determines: is this a coding topic? what language?
# ══════════════════════════════════════════════════════
_CODING_KEYWORDS = {
    # Programming languages
    "python", "javascript", "typescript", "java", "c++", "c#", "golang", "go",
    "rust", "kotlin", "swift", "php", "ruby", "scala", "dart", "r ",
    # CS / coding topics
    "algorithm", "data structure", "array", "linked list", "tree", "graph",
    "stack", "queue", "heap", "hash", "sorting", "searching", "recursion",
    "dynamic programming", "dp", "backtracking", "greedy", "binary search",
    "string", "function", "class", "object", "oop", "inheritance", "polymorphism",
    "pointer", "memory", "loop", "iteration", "list", "dict", "tuple", "set",
    "api", "sql", "database", "query", "html", "css", "react", "django", "flask",
    "node", "express", "spring", "regex", "lambda", "closure", "async",
    "decorator", "generator", "iterator", "exception", "file i/o", "threading",
    "machine learning", "deep learning", "neural", "numpy", "pandas",
    "code", "program", "implement", "leetcode", "coding",
}

_LANG_PATTERNS = [
    (["python"],             "Python"),
    (["javascript", "js", "node", "react", "vue", "next"], "JavaScript"),
    (["typescript", "ts"],   "JavaScript"),  # TS runs as JS in browser context
    (["java", "spring"],     "Java"),
    (["c++", "cpp"],         "C++"),
    (["c#", "csharp", ".net"], "C#"),
    (["sql", "mysql", "postgres", "sqlite"], "SQL"),
    (["html", "css", "web"], "HTML"),
    (["rust"],               "Rust"),
    (["go", "golang"],       "Go"),
    (["kotlin"],             "Kotlin"),
    (["swift", "ios"],       "Swift"),
    (["r ", "rstudio"],      "R"),
]

def _detect_topic(topic_name: str, user_pref_lang: str) -> dict:
    """Return {is_coding, language, needs_lang_selector} for a topic name."""
    tl = topic_name.lower()
    # Language detection from topic name
    detected_lang = None
    for keywords, lang in _LANG_PATTERNS:
        if any(kw in tl for kw in keywords):
            detected_lang = lang
            break

    # Coding topic detection
    is_coding = detected_lang is not None or any(kw in tl for kw in _CODING_KEYWORDS)

    # Language to use: topic-name > user preference (only matters for coding topics)
    lang = detected_lang or (user_pref_lang if is_coding else "")

    return {"is_coding": is_coding, "language": lang}


# ── Header ─────────────────────────────────────────────────
st.markdown("# 📖 Study Session")

# ── Topic Selector ──────────────────────────────────────────
col_sel, col_info = st.columns([3, 1], gap="medium")
with col_sel:
    available = [t for t in topics if t["status"] in ("available", "in_progress", "completed")]
    if not available:
        available = topics

    topic_names = [t["topic_name"] for t in available]
    default_idx = 0
    if st.session_state.get("current_topic_name") in topic_names:
        default_idx = topic_names.index(st.session_state.current_topic_name)

    selected_name = st.selectbox("Topic", topic_names, index=default_idx,
                                  label_visibility="visible")
    selected_topic = next((t for t in available if t["topic_name"] == selected_name), None)

with col_info:
    if selected_topic:
        status  = selected_topic.get("status", "locked")
        mastery = selected_topic.get("mastery_pct", 0) or 0
        status_colors = {"completed": "var(--green)", "in_progress": "var(--accent)",
                         "available": "var(--cyan)", "locked": "var(--text-muted)"}
        sc = status_colors.get(status, "var(--text-muted)")
        st.markdown(f"""
        <div style="background:var(--bg-elevated);border:1px solid var(--border);
                    border-radius:var(--radius);padding:1rem;margin-top:1.6rem;">
            <div style="display:flex;justify-content:space-between;margin-bottom:0.5rem;">
                <span style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;">Status</span>
                <span style="font-size:0.8rem;font-weight:600;color:{sc};">
                    {'✅' if status=='completed' else '🔄' if status=='in_progress' else '📌'}
                    {status.replace('_',' ').title()}
                </span>
            </div>
            <div style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;">
                Mastery
            </div>
            <div style="background:var(--bg-overlay);border-radius:99px;height:5px;overflow:hidden;">
                <div style="height:100%;width:{mastery}%;background:linear-gradient(90deg,var(--accent),var(--cyan));border-radius:99px;transition:width .5s ease;"></div>
            </div>
            <div style="text-align:right;font-size:0.78rem;color:var(--accent);margin-top:3px;font-weight:600;">{mastery:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

if not selected_topic:
    st.markdown('<div class="warning-box">⚠️ Create a roadmap first to start studying!</div>',
                unsafe_allow_html=True)
    st.stop()

tid = selected_topic["id"]
st.session_state.current_topic_id   = tid
st.session_state.current_topic_name = selected_name
if selected_topic["status"] == "available":
    update_topic_status(tid, "in_progress")

# ── Detect topic type ───────────────────────────────────────
_topic_info = _detect_topic(selected_name, user.get("preferred_language", "Python"))
is_coding   = _topic_info["is_coding"]
lang        = _topic_info["language"]

# ── Dynamic Tabs ────────────────────────────────────────────
if is_coding:
    tab_learn, tab_practice, tab_quiz = st.tabs(["📖  Learn", "💻  Code Practice", "🧩  Quiz"])
else:
    tab_learn, tab_quiz = st.tabs(["📖  Learn", "🧩  Quiz"])
    tab_practice = nullcontext()  # no-op context: with tab_practice: does nothing for theory

# ══════════════════════════════════════════════════════════════
# TAB 1 — LEARN
# ══════════════════════════════════════════════════════════════
with tab_learn:
    col_h, col_btn = st.columns([4, 1])
    with col_h:
        st.markdown(f"### {selected_name}")
        if is_coding and lang:
            st.caption(f"Level: **{level}** · Language: **{lang}**")
        else:
            st.caption(f"Level: **{level}**")
    with col_btn:
        load_btn = st.button("🧠 Load Content", use_container_width=True)

    if load_btn or st.session_state.get(f"content_{tid}"):
        # ─ Check if we have cached content in DB first ─
        db_cached = get_study_content(uid, tid)

        force_reload = load_btn

        if not force_reload and db_cached and not st.session_state.get(f"content_{tid}"):
            # Restore from DB cache into session state
            st.session_state[f"content_{tid}"] = db_cached["content_dict"]
            st.session_state.study_start_time = time.time()

        if force_reload or not st.session_state.get(f"content_{tid}"):
            with st.spinner(f"🧠 AI is preparing **{selected_name}**… (this may take 15–30s)"):
                c = teach_topic(selected_name, level, lang)
                if c:
                    st.session_state[f"content_{tid}"] = c
                    st.session_state.study_start_time = time.time()
                    # ─ Save to DB so we don't regenerate next visit
                    save_study_content(uid, tid, selected_name, lang, level, c)

        c = st.session_state.get(f"content_{tid}")

        # Show cache badge if loaded from DB
        if db_cached and not force_reload:
            st.markdown(
                f'<div style="font-size:.72rem;color:var(--text-muted);margin-bottom:.5rem;">'  
                f'📅 Content loaded from cache · '
                f'<span style="color:var(--accent);">Regenerate</span> by clicking '
                f'<strong>Load Content</strong> again.</div>',
                unsafe_allow_html=True
            )

        if c:
            # ── Overview card ──────────────────────────────
            analogy = c.get("analogy", "")
            st.markdown(f"""
            <div class="content-panel" style="animation:fadeInUp 0.4s ease;">
                <div style="font-size:0.7rem;font-weight:700;letter-spacing:1px;
                            color:var(--text-muted);text-transform:uppercase;margin-bottom:0.75rem;">
                    Overview
                </div>
                <p style="color:var(--text-base);line-height:1.75;font-size:0.95rem;">
                    {c.get('overview','')}
                </p>
                {f'''<div style="margin-top:1rem;padding:0.875rem 1rem;
                              background:rgba(34,211,238,0.06);border-left:3px solid var(--cyan);
                              border-radius:0 var(--radius-sm) var(--radius-sm) 0;">
                    <span style="color:var(--cyan);font-weight:600;font-size:0.82rem;">
                        💡 Analogy</span>
                    <div style="color:var(--text-base);margin-top:0.25rem;">{analogy}</div>
                </div>''' if analogy else ''}
            </div>
            """, unsafe_allow_html=True)

            # ── Sections ───────────────────────────────────
            for i, section in enumerate(c.get("sections", [])):
                with st.expander(f"{'▸'} {section.get('title', f'Section {i+1}')}", expanded=(i == 0)):
                    st.markdown(section.get("content", ""))
                    if section.get("code_example"):
                        st.markdown("""
                        <div style="font-size:0.75rem;font-weight:600;color:var(--text-muted);
                                    text-transform:uppercase;letter-spacing:.5px;margin:0.875rem 0 0.375rem;">
                            Code Example
                        </div>
                        """, unsafe_allow_html=True)
                        st.code(section["code_example"], language=lang.lower())
                    if section.get("explanation"):
                        st.markdown(f'<div class="info-box" style="margin-top:.5rem;">📝 {section["explanation"]}</div>',
                                    unsafe_allow_html=True)

            # ── Key Points ─────────────────────────────────
            kps = c.get("key_points", [])
            mistakes = c.get("common_mistakes", [])
            tips = c.get("interview_tips", [])

            if kps or mistakes or tips:
                c1, c2, c3 = st.columns(3)
                with c1:
                    if kps:
                        st.markdown("""<div style="font-size:0.72rem;font-weight:700;color:var(--green);
                                        text-transform:uppercase;letter-spacing:.5px;margin-bottom:.5rem;">
                                        ✅ Key Takeaways</div>""", unsafe_allow_html=True)
                        for kp in kps:
                            st.markdown(f"""
                            <div style="padding:.4rem .75rem;margin-bottom:.3rem;
                                        border-left:2px solid var(--green);
                                        background:rgba(52,211,153,0.05);border-radius:0 6px 6px 0;
                                        color:var(--text-base);font-size:.875rem;">{kp}</div>
                            """, unsafe_allow_html=True)
                with c2:
                    if mistakes:
                        st.markdown("""<div style="font-size:0.72rem;font-weight:700;color:var(--amber);
                                        text-transform:uppercase;letter-spacing:.5px;margin-bottom:.5rem;">
                                        ⚠️ Common Mistakes</div>""", unsafe_allow_html=True)
                        for m in mistakes:
                            st.markdown(f"""
                            <div style="padding:.4rem .75rem;margin-bottom:.3rem;
                                        border-left:2px solid var(--amber);
                                        background:rgba(251,191,36,0.05);border-radius:0 6px 6px 0;
                                        color:var(--text-base);font-size:.875rem;">{m}</div>
                            """, unsafe_allow_html=True)
                with c3:
                    if tips:
                        st.markdown("""<div style="font-size:0.72rem;font-weight:700;color:var(--accent);
                                        text-transform:uppercase;letter-spacing:.5px;margin-bottom:.5rem;">
                                        🎯 Interview Tips</div>""", unsafe_allow_html=True)
                        for tip in tips:
                            st.markdown(f"""
                            <div style="padding:.4rem .75rem;margin-bottom:.3rem;
                                        border-left:2px solid var(--accent);
                                        background:rgba(124,109,250,0.06);border-radius:0 6px 6px 0;
                                        color:var(--text-base);font-size:.875rem;">{tip}</div>
                            """, unsafe_allow_html=True)

            # ── Mark Complete ──────────────────────────────
            st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)
            if st.button("✅ Mark as Studied — Earn XP", use_container_width=True, type="primary"):
                elapsed = time.time() - (st.session_state.study_start_time or time.time())
                mins = max(1, elapsed / 60)
                xp = log_study_session(uid, tid, selected_name, mins)
                update_topic_status(tid, "completed",
                                    min(100, selected_topic.get("mastery_pct", 0) + 30))
                st.balloons()
                st.success(f"🎉 Great work! +{xp} XP · {mins:.1f} min studied!")
    else:
        st.markdown("""
        <div style="text-align:center;padding:4rem 2rem;color:var(--text-muted);">
            <div style="font-size:3rem;margin-bottom:1rem;">🧠</div>
            <div style="font-size:1rem;margin-bottom:.5rem;color:var(--text-base);">Ready to learn?</div>
            <div style="font-size:.875rem;">Click <strong>Load Content</strong> to begin your AI-powered lesson.</div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TAB 2 — CODE PRACTICE  (coding topics only — nullcontext for theory)
# ══════════════════════════════════════════════════════════════
with tab_practice:

    # ── Problem generator controls ──────────────────────────
    ctrl_l, ctrl_r = st.columns([3, 1], gap="medium")
    with ctrl_l:
        diff = st.select_slider("Difficulty", ["Easy", "Medium", "Hard"], value="Medium",
                                 label_visibility="visible")
    with ctrl_r:
        gen_btn = st.button("🎲 New Problem", use_container_width=True)

    if gen_btn:
        with st.spinner("Generating challenge…"):
            prob = generate_practice_problem(selected_name, level, lang, diff.lower())
            st.session_state.current_problem   = prob
            st.session_state.practice_code     = prob.get("starter_code", f"# Your {lang} solution here\n")
            st.session_state.practice_output   = None
            st.session_state.show_hints        = False
            st.session_state.show_solution     = False

    prob = st.session_state.get("current_problem")

    if not prob:
        st.markdown("""
        <div style="text-align:center;padding:4rem 2rem;color:var(--text-muted);">
            <div style="font-size:3rem;margin-bottom:1rem;">💻</div>
            <div style="font-size:1rem;color:var(--text-base);margin-bottom:.5rem;">No problem loaded yet</div>
            <div style="font-size:.875rem;">Click <strong>🎲 New Problem</strong> to get a coding challenge.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ── Two-column split: problem | editor ─────────────
        left_col, right_col = st.columns([1, 1], gap="medium")

        # ── LEFT: Problem Statement ─────────────────────────
        with left_col:
            diff_colors = {"Easy": "var(--green)", "Medium": "var(--amber)", "Hard": "var(--rose)"}
            dc = diff_colors.get(diff, "var(--accent)")

            st.markdown(f"""
            <div class="practice-problem-col" style="animation:slideIn .3s ease;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1rem;">
                    <h4 style="color:var(--text-primary);font-size:1rem;font-weight:700;margin:0;line-height:1.4;">
                        {prob.get('title','')}
                    </h4>
                    <span style="font-size:0.75rem;font-weight:700;color:{dc};white-space:nowrap;
                                 background:rgba(0,0,0,0.3);padding:3px 10px;border-radius:99px;
                                 border:1px solid {dc};margin-left:.75rem;">
                        {diff}
                    </span>
                </div>
                <p style="color:var(--text-base);font-size:.9rem;line-height:1.75;margin-bottom:1.25rem;">
                    {prob.get('description','')}
                </p>
            """, unsafe_allow_html=True)

            # Examples
            exs = prob.get("examples", [])
            if exs:
                st.markdown("""
                <div style="font-size:.72rem;font-weight:700;color:var(--text-muted);
                            text-transform:uppercase;letter-spacing:.5px;margin-bottom:.5rem;">
                    Examples
                </div>
                """, unsafe_allow_html=True)
                for i, ex in enumerate(exs[:3]):
                    st.markdown(f"""
                    <div style="background:var(--bg-overlay);border:1px solid var(--border-muted);
                                border-radius:var(--radius-sm);padding:.75rem 1rem;margin-bottom:.5rem;
                                font-family:var(--font-mono);font-size:.8rem;line-height:1.6;">
                        <span style="color:var(--text-muted);">#{i+1}</span><br>
                        <span style="color:var(--green);">Input: </span>
                        <span style="color:var(--text-base);">{ex.get('input','')}</span><br>
                        <span style="color:var(--cyan);">Output: </span>
                        <span style="color:var(--text-base);">{ex.get('output','')}</span>
                        {f'<br><span style="color:var(--text-muted);font-style:italic;">{ex.get("explanation","")}</span>' if ex.get("explanation") else ''}
                    </div>
                    """, unsafe_allow_html=True)

            # Constraints
            consts = prob.get("constraints", [])
            if consts:
                st.markdown("""
                <div style="font-size:.72rem;font-weight:700;color:var(--text-muted);
                            text-transform:uppercase;letter-spacing:.5px;margin:.75rem 0 .4rem;">
                    Constraints
                </div>
                """, unsafe_allow_html=True)
                for c in consts:
                    st.markdown(f"""
                    <div style="font-size:.8rem;color:var(--text-muted);font-family:var(--font-mono);
                                padding:2px 0;">· {c}</div>
                    """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # ── Hints & Solution ───────────────────────────
            with st.expander("💡 Hints"):
                for h in prob.get("hints", []):
                    st.markdown(f"""
                    <div style="padding:.4rem .75rem;border-left:2px solid var(--amber);
                                background:rgba(251,191,36,0.06);border-radius:0 6px 6px 0;
                                margin-bottom:.4rem;color:var(--text-base);font-size:.875rem;">{h}</div>
                    """, unsafe_allow_html=True)

            with st.expander("✅ Official Solution"):
                st.code(prob.get("solution", ""), language=lang.lower())
                c_tc, c_sc = st.columns(2)
                c_tc.metric("⏱ Time", prob.get("time_complexity", "O(?)"))
                c_sc.metric("💾 Space", prob.get("space_complexity", "O(?)"))

        # ── RIGHT: Code Editor ──────────────────────────────
        with right_col:
            # Editor chrome
            st.markdown(f"""
            <div class="editor-toolbar">
                <div style="display:flex;gap:5px;align-items:center;">
                    <span class="editor-dot" style="background:#ff5f57;"></span>
                    <span class="editor-dot" style="background:#febc2e;"></span>
                    <span class="editor-dot" style="background:#28c840;"></span>
                </div>
                <span>solution.{lang.lower()[:2] if lang!='Python' else 'py'}</span>
                <span style="color:var(--accent);">{lang}</span>
            </div>
            """, unsafe_allow_html=True)

            # Ace editor (or textarea fallback)
            try:
                from streamlit_ace import st_ace
                code_val = st.session_state.get("practice_code",
                                                  prob.get("starter_code", f"# Write your {lang} solution\n"))
                user_code = st_ace(
                    value=code_val,
                    language="python",
                    theme="tomorrow_night",
                    font_size=13,
                    height=340,
                    key=f"practice_ace_{tid}",
                    auto_update=True,
                    wrap=False,
                    show_gutter=True,
                    show_print_margin=False,
                    keybinding="vscode",
                )
            except ImportError:
                user_code = st.text_area(
                    "Your Code",
                    value=st.session_state.get("practice_code",
                                                prob.get("starter_code", f"# Write your {lang} solution\n")),
                    height=340,
                    key=f"practice_textarea_{tid}",
                    label_visibility="collapsed",
                    placeholder=f"# Write your {lang} solution here…"
                )
            st.session_state.practice_code = user_code

            # ── Action buttons: Run | Submit | Reset ───────────
            btn_run_col, btn_submit_col, btn_clear_col = st.columns([2, 2, 1])
            with btn_run_col:
                run_btn = st.button("▶ Run Code", use_container_width=True, type="primary")
            with btn_submit_col:
                submit_btn = st.button("✅ Submit Answer", use_container_width=True)
            with btn_clear_col:
                if st.button("⟳", use_container_width=True, help="Reset to starter code"):
                    st.session_state.practice_code   = prob.get("starter_code", "")
                    st.session_state.practice_output = None
                    st.session_state.pop(f"submit_result_{tid}", None)
                    st.rerun()

            # ── Run ─────────────────────────────────────────────
            if run_btn and user_code:
                with st.spinner("Running…"):
                    result = run_code_safely(user_code)
                    st.session_state.practice_output = result
                    st.session_state.pop(f"submit_result_{tid}", None)

            out = st.session_state.get("practice_output")
            if out is not None:
                stdout = out.get("stdout", "").strip()
                stderr = out.get("stderr", "").strip()
                success = out.get("success", False)
                out_label = "✓ Output" if success else "✗ Error"
                out_color = "var(--green)" if success else "var(--rose)"
                out_class = "" if success else " error"
                st.markdown(f"""
                <div style="margin-top:.75rem;font-size:.72rem;font-weight:700;
                            color:{out_color};text-transform:uppercase;
                            letter-spacing:.5px;margin-bottom:.35rem;">
                    {out_label}
                </div>
                <div class="output-box{out_class}">
{stdout if success else stderr if stderr else '(no output)'}
                </div>
                """, unsafe_allow_html=True)

            # ── Submit & Check ───────────────────────────────────
            if submit_btn and user_code:
                with st.spinner("Checking your answer…"):
                    run_result = run_code_safely(user_code)
                    st.session_state.practice_output = run_result

                    stdout  = run_result.get("stdout", "").strip()
                    stderr  = run_result.get("stderr", "").strip()
                    ran_ok  = run_result.get("success", False)

                    # Compare against expected example outputs
                    examples = prob.get("examples", [])
                    verdict  = "incorrect"
                    if not ran_ok:
                        verdict = "error"
                    elif examples:
                        # Check if ANY example output appears in stdout
                        for ex in examples:
                            expected = str(ex.get("output", "")).strip()
                            if expected and expected in stdout:
                                verdict = "correct"
                                break
                        else:
                            verdict = "incorrect"
                    else:
                        # No examples to check against — treat as attempted
                        verdict = "attempted" if ran_ok else "error"

                    xp = log_code_submission(
                        uid, tid, selected_name,
                        prob.get("title", "Practice Problem"),
                        user_code, stdout or stderr,
                        {}, verdict
                    )
                    new_mastery = min(100, (selected_topic.get("mastery_pct") or 0)
                                     + (20 if verdict == "correct" else 5))
                    update_topic_status(tid, "in_progress", new_mastery)

                    st.session_state[f"submit_result_{tid}"] = {
                        "verdict": verdict, "xp": xp,
                        "stdout": stdout, "stderr": stderr,
                        "mastery": new_mastery,
                    }

            sub_res = st.session_state.get(f"submit_result_{tid}")
            if sub_res:
                v = sub_res["verdict"]
                v_configs = {
                    "correct":   ("var(--green)", "rgba(52,211,153,0.08)",
                                  "rgba(52,211,153,0.35)", "🎉 Correct!",
                                  "Your output matches the expected answer."),
                    "incorrect": ("var(--amber)", "rgba(251,191,36,0.08)",
                                  "rgba(251,191,36,0.3)",  "⚠️ Not Quite",
                                  "Output doesn't match expected. Check the examples."),
                    "attempted": ("var(--cyan)",  "rgba(34,211,238,0.08)",
                                  "rgba(34,211,238,0.3)",  "👍 Submitted",
                                  "No examples to auto-check. XP awarded for attempting!"),
                    "error":     ("var(--rose)",  "rgba(251,113,133,0.08)",
                                  "rgba(251,113,133,0.3)", "✗ Runtime Error",
                                  "Fix the error above and try again."),
                }
                fc, bg, border, label, msg = v_configs.get(v, v_configs["attempted"])
                st.markdown(f"""
                <div style="margin-top:.875rem;background:{bg};border:1px solid {border};
                            border-radius:var(--radius);padding:1rem 1.25rem;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:.95rem;font-weight:700;color:{fc};">{label}</span>
                        <span style="font-size:.82rem;font-weight:700;color:var(--amber);
                                     background:rgba(251,191,36,0.12);padding:3px 10px;
                                     border-radius:99px;border:1px solid rgba(251,191,36,0.25);"
                        >+{sub_res['xp']} XP</span>
                    </div>
                    <div style="font-size:.82rem;color:var(--text-muted);margin-top:.35rem;">
                        {msg} &nbsp;·&nbsp; Mastery now <strong style="color:{fc};">
                        {sub_res['mastery']:.0f}%</strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if v == "correct":
                    st.balloons()
                    if st.button("🎲 Next Problem", use_container_width=True):
                        st.session_state.pop(f"submit_result_{tid}", None)
                        st.session_state.practice_output = None
                        st.session_state.practice_code = ""
                        st.session_state.current_problem = None
                        st.rerun()


# ══════════════════════════════════════════════════════════════
# TAB 3 — QUIZ
# ══════════════════════════════════════════════════════════════
with tab_quiz:
    col_qh, col_qbtn = st.columns([3, 1])
    with col_qh:
        st.markdown(f"### Quiz — {selected_name}")
        num_q = st.slider("Number of questions", 3, 10, 5, label_visibility="visible")
    with col_qbtn:
        gen_quiz = st.button("🎯 Generate", use_container_width=True)

    if gen_quiz:
        with st.spinner("Generating questions…"):
            qs = generate_quiz(selected_name, level, num_q, lang)
            st.session_state.quiz_questions = qs
            st.session_state.quiz_answers   = {}
            st.session_state.quiz_start_time = time.time()
            st.session_state[f"quiz_submitted_{tid}"] = False

    qs        = st.session_state.get("quiz_questions", [])
    submitted = st.session_state.get(f"quiz_submitted_{tid}", False)

    if not qs:
        st.markdown("""
        <div style="text-align:center;padding:4rem 2rem;color:var(--text-muted);">
            <div style="font-size:3rem;margin-bottom:1rem;">🧩</div>
            <div style="font-size:1rem;color:var(--text-base);margin-bottom:.5rem;">No quiz yet</div>
            <div style="font-size:.875rem;">Click <strong>🎯 Generate</strong> to create a quiz from this topic.</div>
        </div>
        """, unsafe_allow_html=True)

    elif not submitted:
        with st.form("quiz_form"):
            for i, q in enumerate(qs):
                type_label = q.get("type", "").upper()
                st.markdown(f"""
                <div class="quiz-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.75rem;">
                        <span style="font-size:.7rem;font-weight:700;color:var(--text-muted);
                                     letter-spacing:.5px;">{type_label or f"Q{i+1}"}</span>
                    </div>
                    <div style="font-weight:600;color:var(--text-primary);font-size:.95rem;line-height:1.5;">
                        {i+1}. {q['question']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.radio("", q["options"], key=f"q_{i}", index=None,
                         label_visibility="collapsed")
                st.markdown("<div style='height:.25rem;'></div>", unsafe_allow_html=True)

            submitted_btn = st.form_submit_button("📝 Submit Quiz", use_container_width=True)

        if submitted_btn:
            answers = {str(i): st.session_state.get(f"q_{i}", "") for i in range(len(qs))}
            elapsed = time.time() - (st.session_state.quiz_start_time or time.time())
            result  = evaluate_quiz(qs, answers)
            score, total = result["score"], result["total"]
            pct, xp = log_quiz_attempt(uid, tid, selected_name, score, total,
                                        result["results"], int(elapsed))
            update_topic_status(tid, "in_progress",
                                min(100, selected_topic.get("mastery_pct", 0) + score * 5))
            st.session_state[f"quiz_result_{tid}"]    = result
            st.session_state[f"quiz_submitted_{tid}"] = True
            st.rerun()

    else:
        res = st.session_state.get(f"quiz_result_{tid}", {})
        pct = res.get("percentage", 0)
        grade_color = "var(--green)" if pct >= 75 else "var(--amber)" if pct >= 50 else "var(--rose)"
        grade_bg    = ("rgba(52,211,153,0.08)" if pct >= 75 else
                       "rgba(251,191,36,0.08)"   if pct >= 50 else
                       "rgba(251,113,133,0.08)")

        st.markdown(f"""
        <div style="text-align:center;padding:2.5rem;background:{grade_bg};
                    border:1px solid {grade_color};border-radius:var(--radius-lg);
                    margin-bottom:1.5rem;animation:fadeInUp .4s ease;">
            <div style="font-size:2.5rem;margin-bottom:.5rem;">{res.get('grade','').split()[0] if res.get('grade') else '📊'}</div>
            <div style="font-size:2.75rem;font-weight:800;color:{grade_color};letter-spacing:-1px;">{pct}%</div>
            <div style="color:var(--text-muted);font-size:.9rem;margin:.25rem 0;">
                {res.get('grade','')} — {res.get('score',0)}/{res.get('total',0)} correct
            </div>
            <div style="color:var(--text-base);font-size:.875rem;margin-top:.75rem;font-style:italic;">
                {res.get('feedback','')}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Answer Review")
        for r in res.get("results", []):
            ok = r["is_correct"]
            border = "rgba(52,211,153,0.4)" if ok else "rgba(251,113,133,0.4)"
            bg     = "rgba(52,211,153,0.04)" if ok else "rgba(251,113,133,0.04)"
            icon   = "✅" if ok else "❌"
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {border};
                        border-radius:var(--radius);padding:1.125rem 1.25rem;
                        margin-bottom:.625rem;animation:fadeIn .3s ease;">
                <div style="font-weight:600;color:var(--text-primary);font-size:.9rem;
                            margin-bottom:.5rem;">{r['question']}</div>
                <div style="font-size:.85rem;color:{'var(--green)' if ok else 'var(--rose)'};">
                    {icon} Your answer: {r.get('user_answer','(no answer)')}
                </div>
                {f'<div style="font-size:.85rem;color:var(--green);margin-top:.2rem;">✔ Correct: {r["correct_answer"]}</div>' if not ok else ''}
                <div style="font-size:.82rem;color:var(--text-muted);margin-top:.5rem;">💡 {r.get('explanation','')}</div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🔄 Retake Quiz", use_container_width=False):
            st.session_state[f"quiz_submitted_{tid}"] = False
            st.session_state.quiz_questions = []
            st.rerun()
