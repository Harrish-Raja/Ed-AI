import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db_manager import (get_user, save_roadmap, get_all_roadmaps,
                                   get_latest_roadmap, save_topics, get_topics,
                                   update_topic_status)
from core.roadmap_generator import generate_roadmap
from utils.session_manager import init_session, require_login, require_api_key

st.set_page_config(page_title="Roadmap · EdAI", page_icon="📚", layout="wide")
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session()
require_login()
require_api_key()

uid = st.session_state.user_id
user = get_user(uid)

st.markdown("# 📚 Learning Roadmap Builder")
st.markdown("Generate your personalized, AI-powered learning roadmap in seconds.")

tab1, tab2 = st.tabs(["🆕 Create New Roadmap", "📂 My Roadmaps"])

with tab1:
    with st.form("roadmap_form"):
        st.markdown("### Configure Your Learning Path")
        col1, col2 = st.columns(2)
        with col1:
            topic = st.text_input("📌 Topic to Learn",
                                   placeholder="e.g., Data Structures & Algorithms, Machine Learning, Python")
            goal = st.selectbox("🎯 Target Goal",
                                 ["Interview Preparation", "Job Ready", "Exam Preparation",
                                  "Skill Mastery", "Freelance Projects", "Research"])
            level = st.selectbox("📊 Your Level",
                                  ["Beginner", "Intermediate", "Advanced"],
                                  index=["Beginner", "Intermediate", "Advanced"].index(
                                      user.get("level", "Beginner")))
        with col2:
            daily_hours = st.slider("⏰ Daily Study Hours", 0.5, 8.0,
                                     float(user.get("daily_hours", 2.0)), 0.5)
            duration_weeks = st.slider("📅 Duration (Weeks)", 1, 24, 8, 1)
            language = st.selectbox("💻 Programming Language",
                                     ["Python", "JavaScript", "Java", "C++", "Go", "Rust"],
                                     index=0)

        submit = st.form_submit_button("🚀 Generate My Roadmap", use_container_width=True)

    if submit and topic:
        with st.spinner(
            "🧠 AI is building your roadmap — this may take 15-30 seconds for longer plans…"
        ):
            try:
                roadmap_data = generate_roadmap(topic, goal, level, daily_hours,
                                                 duration_weeks, language)
                rid = save_roadmap(uid, topic, goal, level, duration_weeks, roadmap_data)
                st.session_state.current_roadmap_id = rid

                # Flatten topics for DB
                flat_topics = []
                for week in roadmap_data.get("weeks", []):
                    for day in week.get("days", []):
                        for top in day.get("topics", []):
                            flat_topics.append({
                                "name": top.get("name", "Topic"),
                                "parent": top.get("parent"),
                                "week": week.get("week", 1),
                                "day": day.get("day", 1),
                                "hours": top.get("estimated_hours", 1.0)
                            })
                save_topics(rid, uid, flat_topics)

                # Was it a fallback roadmap?
                desc = roadmap_data.get("description", "")
                if "Auto-generated" in desc:
                    st.warning(
                        "⚠️ The AI returned an invalid response — a **fallback roadmap** was "
                        "generated instead. Try again with a shorter duration or simpler topic."
                    )
                else:
                    st.success(
                        f"✅ Roadmap generated! **{len(flat_topics)} topics** across "
                        f"{duration_weeks} weeks. Scroll down to start studying!"
                    )
            except Exception as e:
                err_str = str(e)
                # Give a clear, non-technical error
                if "JSON" in err_str or "json" in err_str or "char" in err_str:
                    st.markdown("""
                    <div class="warning-box">
                        ⚠️ <strong>The AI returned malformed data</strong> — this can happen with
                        very long roadmaps or a slow connection.<br><br>
                        <strong>Try one of these:</strong>
                        <ul style="margin:.5rem 0 0 1rem;">
                            <li>Reduce the <strong>Duration</strong> (try 4–6 weeks instead)</li>
                            <li>Click <strong>Generate</strong> again — the AI response varies</li>
                            <li>Make the topic more specific (e.g., "Python lists" not "Python")</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"❌ Unexpected error: {err_str[:200]}")

    # Display current/latest roadmap
    roadmap = get_latest_roadmap(uid)
    if roadmap and roadmap.get("roadmap_json"):
        rj = roadmap["roadmap_json"]
        st.markdown("---")
        st.markdown(f"## 🗺️ {rj.get('title', roadmap['topic'])}")
        st.markdown(f"> {rj.get('description', '')}")

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("📌 Topic", roadmap["topic"])
        with col_b:
            st.metric("🎯 Goal", roadmap["goal"])
        with col_c:
            st.metric("📊 Level", roadmap["level"])
        with col_d:
            st.metric("📅 Duration", f"{roadmap['duration_weeks']} weeks")

        # Skills & Interview topics
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            skills = rj.get("skills_gained", [])
            if skills:
                st.markdown("**🎓 Skills You'll Gain:**")
                st.markdown(" ".join([f'<span class="badge badge-blue">{s}</span>' for s in skills]),
                            unsafe_allow_html=True)
        with col_s2:
            itopics = rj.get("interview_topics", [])
            if itopics:
                st.markdown("**🎯 Key Interview Topics:**")
                st.markdown(" ".join([f'<span class="badge badge-purple">{t}</span>' for t in itopics[:6]]),
                            unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Milestones
        milestones = rj.get("milestones", [])
        if milestones:
            st.markdown("### 🏆 Milestones")
            cols = st.columns(min(len(milestones), 4))
            for i, m in enumerate(milestones):
                with cols[i % len(cols)]:
                    st.markdown(f"""
                    <div class="metric-card" style="text-align:left;">
                        <div class="badge badge-yellow">Week {m.get('week')}</div>
                        <div style="margin-top:0.75rem;color:#e8e8f0;font-size:0.9rem;">{m.get('milestone')}</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("### 📅 Full Roadmap")

        # Get all topics from DB to show status
        db_topics = get_topics(uid, roadmap["id"])
        topic_status_map = {t["topic_name"]: t for t in db_topics}

        # ── Duolingo-Style Vertical S-Path Visual ───────────────────────
        _weekly_nodes = []
        first_uncompleted = False
        active_index = 0

        weeks = rj.get("weeks", [])
        for idx, _wk in enumerate(weeks):
            week_num = _wk.get("week", idx + 1)
            theme = _wk.get("theme", f"Week {week_num}")
            
            completed_count = 0
            in_progress_count = 0
            total_topics = 0
            
            # Use db_topics mapped earlier
            for _day in _wk.get("days", []):
                for _top in _day.get("topics", []):
                    total_topics += 1
                    _tname = _top.get("name", "")
                    _dbt = topic_status_map.get(_tname, {})
                    status = _dbt.get("status", "locked")
                    if status == "completed": completed_count += 1
                    if status == "in_progress": in_progress_count += 1

            total_topics = max(total_topics, 1)

            if completed_count == total_topics:
                status = "completed"
                active_index = idx + 1
            elif not first_uncompleted:
                status = "in_progress" if (completed_count > 0 or in_progress_count > 0) else "available"
                first_uncompleted = True
                active_index = idx
            else:
                status = "locked"
                
            _weekly_nodes.append({
                "week": week_num,
                "theme": theme,
                "status": status,
                "total": total_topics,
                "completed": completed_count
            })

        active_index = min(active_index, len(_weekly_nodes) - 1)

        points = []
        for i in range(len(_weekly_nodes)):
            offset = [0, 50, 80, 50, 0, -50, -80, -50][i % 8]
            cx = 150 + offset
            cy = 40 + i * 110
            points.append((cx, cy))

        # Add the final treasure chest point
        if points:
            chest_x, chest_y = 150, points[-1][1] + 110
            points.append((chest_x, chest_y))
        else:
            points.append((150, 100))

        def make_path(pts):
            if not pts: return ""
            d = f"M {pts[0][0]} {pts[0][1]} "
            for i in range(len(pts)-1):
                x1, y1 = pts[i]
                x2, y2 = pts[i+1]
                d += f"C {x1} {y1+55}, {x2} {y2-55}, {x2} {y2} "
            return d

        bg_path = make_path(points)
        if len(_weekly_nodes) > 0 and _weekly_nodes[-1]["status"] == "completed":
            fg_path = make_path(points)
        else:
            fg_path = make_path(points[:active_index+1])

        html_nodes = ""
        for i, node in enumerate(_weekly_nodes):
            x, y = points[i]
            is_completed = node["status"] == "completed"
            is_active = node["status"] in ["in_progress", "available"]
            
            if is_completed:
                bg = "#58cc02"
                icon = "✔"
                border = "#46a302"
            elif is_active:
                bg = "#ce82ff"
                icon = "★"
                border = "#a568cc"
            else:
                bg = "#2c2c3c"
                icon = "🔒"
                border = "#1e1e2c"
                
            glow = "box-shadow: 0 0 0 8px rgba(206, 130, 255, 0.2);" if is_active else ""
            bounce = "animation: duo-bounce 2s infinite;" if is_active else ""
            
            html_nodes += f"""
<div style="position:absolute; top:{y - 35}px; left:calc(50% - 150px + {x - 35}px); z-index:2; display:flex; flex-direction:column; align-items:center; width:70px; {bounce}">
<div style="width:70px; height:70px; border-radius:50%; background:{bg}; border-bottom: 6px solid {border}; display:flex; align-items:center; justify-content:center; color:white; font-size:1.8rem; font-weight:900; {glow} cursor:pointer;" title="{node['theme']} ({node['completed']}/{node['total']})">
{icon}
</div>
<div style="margin-top:8px; font-weight:700; font-size:0.75rem; color:var(--text-primary); background:var(--bg-elevated); padding:3px 10px; border-radius:12px; border:1px solid var(--border); white-space:nowrap; box-shadow:0 2px 4px rgba(0,0,0,0.3);">
Week {node['week']}
</div>
</div>
"""

        chest_x, chest_y = points[-1]
        is_chest_open = len(_weekly_nodes) > 0 and _weekly_nodes[-1]["status"] == "completed"
        chest_icon = "🏆" if is_chest_open else "🎁"
        chest_glow = "filter: drop-shadow(0 0 20px rgba(255, 215, 0, 0.6));" if is_chest_open else "filter: drop-shadow(0 10px 10px rgba(0,0,0,0.5));"
        
        html_nodes += f"""
<div style="position:absolute; top:{chest_y - 45}px; left:calc(50% - 45px); z-index:2; width:90px; height:90px; display:flex; align-items:center; justify-content:center; font-size:3.5rem; {chest_glow}">
{chest_icon}
</div>
"""

        total_height = chest_y + 80

        st.markdown(f"""
<style>
@keyframes duo-bounce {{
    0%, 100% {{ transform: translateY(0); }}
    50% {{ transform: translateY(-8px); }}
}}
.duo-path-wrap {{
    position: relative;
    width: 100%;
    height: {total_height}px;
    background: linear-gradient(180deg, var(--bg-surface) 0%, rgba(18,18,28,0.4) 100%);
    border: 1px solid var(--border-muted);
    border-radius: 20px;
    margin: 1rem 0 2rem;
    overflow: hidden;
}}
</style>
<div class="duo-path-wrap">
<svg width="300" height="{total_height}" style="position:absolute; top:0; left:50%; transform:translateX(-50%); z-index:0;" overflow="visible">
<path d="{bg_path}" fill="none" stroke="#2c2c3c" stroke-width="32" stroke-linecap="round" stroke-linejoin="round"/>
<path d="{bg_path}" fill="none" stroke="#222230" stroke-width="20" stroke-linecap="round" stroke-linejoin="round"/>
<path d="{fg_path}" fill="none" stroke="#58cc02" stroke-width="32" stroke-linecap="round" stroke-linejoin="round"/>
<path d="{fg_path}" fill="none" stroke="#78e02b" stroke-width="20" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
{html_nodes}
</div>
""", unsafe_allow_html=True)

        type_icons = {
            "concept": "📖", "practice": "✏️", "project": "🛠️",
            "revision": "🔄", "quiz": "🧩"
        }
        relevance_colors = {"high": "badge-red", "medium": "badge-yellow", "low": "badge-green"}

        for week in rj.get("weeks", []):
            with st.expander(f"📅 Week {week['week']}: {week.get('theme', '')} — {week.get('goal', '')}", expanded=week['week'] == 1):
                for day in week.get("days", []):
                    st.markdown(f"**Day {day['day']}**")
                    for top in day.get("topics", []):
                        tname = top.get("name", "")
                        db_t = topic_status_map.get(tname, {})
                        status = db_t.get("status", "locked")
                        mastery = db_t.get("mastery_pct", 0)
                        tid = db_t.get("id")

                        status_icon = {"completed": "✅", "in_progress": "🔄",
                                       "available": "📌", "locked": "🔒"}.get(status, "📌")
                        rel_class = relevance_colors.get(top.get("interview_relevance", "low"), "badge-green")

                        col_t1, col_t2, col_t3 = st.columns([3, 1, 1])
                        with col_t1:
                            st.markdown(f"""
                            <div class="roadmap-day-item">
                                <span style="font-size:1rem;">{status_icon}</span>
                                <span style="font-size:1.1rem;">{type_icons.get(top.get('type','concept'), '📖')}</span>
                                <div>
                                    <span style="font-weight:600;color:#e8e8f0;">{tname}</span>
                                    <span class="badge {rel_class}" style="margin-left:0.5rem;">
                                        {top.get('interview_relevance','')}</span>
                                    <br>
                                    <span style="color:#7070a0;font-size:0.8rem;">{top.get('description','')[:80]}...</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_t2:
                            st.caption(f"⏱️ {top.get('estimated_hours', 1)}h")
                        with col_t3:
                            if tid and status == "available":
                                if st.button("Study →", key=f"study_{tid}_{tname[:10]}"):
                                    st.session_state.current_topic_id = tid
                                    st.session_state.current_topic_name = tname
                                    st.switch_page("pages/03_📖_Study.py")

        # Projects
        projects = rj.get("project_ideas", [])
        if projects:
            st.markdown("### 🛠️ Project Ideas")
            pc = st.columns(len(projects))
            icons = ["🌱", "🚀", "🏆"]
            labels = ["Beginner Project", "Intermediate Project", "Capstone Project"]
            for i, (col, proj) in enumerate(zip(pc, projects)):
                with col:
                    st.markdown(f"""
                    <div class="content-panel" style="text-align:center;">
                        <div style="font-size:2rem;">{icons[i]}</div>
                        <div class="badge badge-purple">{labels[i]}</div>
                        <div style="margin-top:1rem;color:#e8e8f0;font-weight:500;">{proj}</div>
                    </div>
                    """, unsafe_allow_html=True)

with tab2:
    all_roadmaps = get_all_roadmaps(uid)
    if all_roadmaps:
        for rm in all_roadmaps:
            rj = rm.get("roadmap_json", {})
            total = len(get_topics(uid, rm["id"]))
            completed = len([t for t in get_topics(uid, rm["id"]) if t["status"] == "completed"])
            pct = round(completed / total * 100) if total else 0

            with st.expander(f"📚 {rm['topic']} — {rm['goal']} ({rm['created_at'][:10]})"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Level", rm["level"])
                col2.metric("Duration", f"{rm['duration_weeks']} weeks")
                col3.metric("Progress", f"{pct}% ({completed}/{total})")

                st.progress(pct / 100)
                if st.button("Load This Roadmap", key=f"load_{rm['id']}"):
                    st.session_state.current_roadmap_id = rm["id"]
                    st.success("✅ Roadmap loaded!")
    else:
        st.markdown('<div class="info-box">No roadmaps yet. Create one above! 🚀</div>',
                    unsafe_allow_html=True)
