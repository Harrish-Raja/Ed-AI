import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db_manager import (get_user, get_total_stats, get_performance_data,
                                   get_latest_roadmap, get_topics, get_quiz_attempts,
                                   get_study_sessions)
from core.performance_analyzer import (compute_xp_level, compute_learning_streak,
                                        identify_weak_areas)
from utils.session_manager import init_session, require_login
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import random

st.set_page_config(page_title="Dashboard · EdAI", page_icon="🏠", layout="wide")
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session()

# ── Check demo mode (no login required) ──────────────────
demo_mode = st.session_state.get("demo_mode", False)

if not demo_mode:
    require_login()

# ═══════════════════════════════════════════════════════════
# DEMO DATA  — realistic mock for a "sample" student
# ═══════════════════════════════════════════════════════════
def _make_demo_data():
    today = datetime.now().date()
    # 30 days of performance
    random.seed(42)
    perf = []
    for i in range(28, -1, -1):
        d = today - timedelta(days=i)
        if random.random() > 0.2:          # ~80% active days
            xp = random.randint(30, 150)
            mins = random.randint(20, 90)
            acc = random.uniform(55, 98)
            perf.append({"date": str(d), "xp_earned": xp,
                         "study_mins": mins, "quiz_accuracy": acc})

    topics_demo = [
        {"id": 1, "topic_name": "Python Basics",       "status": "completed",   "mastery_pct": 95, "week_number": 1, "day_number": 1},
        {"id": 2, "topic_name": "Lists & Tuples",      "status": "completed",   "mastery_pct": 88, "week_number": 1, "day_number": 2},
        {"id": 3, "topic_name": "Dictionaries",        "status": "completed",   "mastery_pct": 82, "week_number": 1, "day_number": 3},
        {"id": 4, "topic_name": "Functions & Scope",   "status": "completed",   "mastery_pct": 76, "week_number": 2, "day_number": 1},
        {"id": 5, "topic_name": "OOP Principles",      "status": "in_progress", "mastery_pct": 54, "week_number": 2, "day_number": 2},
        {"id": 6, "topic_name": "File I/O",            "status": "in_progress", "mastery_pct": 35, "week_number": 2, "day_number": 3},
        {"id": 7, "topic_name": "Recursion",           "status": "available",   "mastery_pct": 20, "week_number": 3, "day_number": 1},
        {"id": 8, "topic_name": "Sorting Algorithms",  "status": "available",   "mastery_pct": 0,  "week_number": 3, "day_number": 2},
        {"id": 9, "topic_name": "Binary Search",       "status": "locked",      "mastery_pct": 0,  "week_number": 3, "day_number": 3},
        {"id": 10,"topic_name": "Dynamic Programming", "status": "locked",      "mastery_pct": 0,  "week_number": 4, "day_number": 1},
    ]

    quiz_demo = []
    quiz_topics = ["Python Basics", "Lists & Tuples", "Dictionaries",
                   "Functions & Scope", "OOP Principles"]
    for i in range(20):
        d = today - timedelta(days=random.randint(0, 28))
        quiz_demo.append({
            "topic_name": random.choice(quiz_topics),
            "percentage": random.uniform(50, 100),
            "score": random.randint(3, 10), "total": 10,
            "created_at": str(d),
        })

    study_demo = []
    for i in range(15):
        d = today - timedelta(days=random.randint(0, 28))
        study_demo.append({
            "topic_name": random.choice(quiz_topics),
            "duration_mins": random.uniform(15, 90),
            "created_at": str(d),
        })

    stats_demo = {
        "total_xp": 2840,
        "total_study_mins": sum(p["study_mins"] for p in perf),
        "quizzes_taken": len(quiz_demo),
        "code_solved": 31,
        "max_streak": 9,
    }

    return perf, topics_demo, quiz_demo, study_demo, stats_demo


# ═══════════════════════════════════════════════════════════
# Load real or demo data
# ═══════════════════════════════════════════════════════════
if demo_mode:
    perf, topics, quiz_data, study_data, stats = _make_demo_data()
    demo_user = {"name": "Alex Chen", "level": "Intermediate",
                 "preferred_language": "Python", "target_goal": "Interview Preparation"}
    user = demo_user
    level_title, level_progress, next_level = "🏅 Level 6", 64.0, "Level 7"
    streak = 7
else:
    uid   = st.session_state.user_id
    user  = get_user(uid) or {"name": "Student", "level": "Beginner"}
    stats = {"total_xp": 0, "total_study_mins": 0, "quizzes_taken": 0,
             "code_solved": 0, "max_streak": 0}  # safe defaults
    try:
        stats = get_total_stats(uid)
    except Exception:
        pass
    perf       = get_performance_data(uid, days=30)
    quiz_data  = get_quiz_attempts(uid, limit=100)
    study_data = get_study_sessions(uid, limit=100)
    roadmap    = get_latest_roadmap(uid)
    topics     = get_topics(uid, roadmap["id"] if roadmap else None) if roadmap else []
    try:
        level_title, level_progress, next_level = compute_xp_level(stats["total_xp"])
    except Exception:
        level_title, level_progress, next_level = "🌱 Beginner", 0.0, "Level 2"
    streak = compute_learning_streak(perf)

# ─── Helper: Plotly base layout ───────────────────────────
def _chart(height=260):
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#7a7a98", family="Inter", size=11),
        xaxis=dict(showgrid=False, color="#28283c", tickcolor="#28283c"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", color="#28283c"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=0, r=0, t=8, b=0), height=height,
    )

# ═══════════════════════════════════════════════════════════
# DEMO BANNER
# ═══════════════════════════════════════════════════════════
if demo_mode:
    banner_col, dismiss_col = st.columns([5, 1])
    with banner_col:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:0.75rem;padding:0.625rem 1.125rem;
                    background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.3);
                    border-radius:var(--radius);margin-bottom:0.5rem;">
            <span style="font-size:1rem;">👁️</span>
            <div>
                <span style="color:var(--amber);font-weight:700;font-size:0.875rem;">Sample Dashboard</span>
                <span style="color:var(--text-muted);font-size:0.82rem;margin-left:0.5rem;">
                    — This is a demo with realistic mock data. Your real dashboard will show your own progress.
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with dismiss_col:
        if st.button("✕ Exit Demo", use_container_width=True):
            st.session_state.demo_mode = False
            st.rerun()

# ═══════════════════════════════════════════════════════════
# HERO BANNER
# ═══════════════════════════════════════════════════════════
hour    = datetime.now().hour
greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
name = user.get("name", "Student") if isinstance(user, dict) else "Student"

_demo_badge_html = '<span style="background:#fbbf24;color:#09090b;font-size:.7rem;font-weight:700;padding:2px 8px;border-radius:4px;margin-left:.25rem;">DEMO</span>' if demo_mode else ''
_lp = float(level_progress) if level_progress else 0.0
_nt = str(next_level) if next_level else 'MAX'
_xp_val = int(stats.get('total_xp', 0) or 0)

hero_left, hero_right = st.columns([3, 1])

with hero_left:
    _hero_left_html = f"""<div style="background:#18181f;border:1px solid #28283c;border-radius:16px;padding:1.5rem 1.75rem;"><div style="font-size:0.78rem;color:#7a7a98;margin-bottom:0.25rem;">{greeting} 👋</div><h2 style="margin:0;font-size:1.75rem;font-weight:800;color:#f0f0f5;letter-spacing:-0.5px;">{name}</h2><div style="margin-top:0.625rem;display:flex;gap:0.5rem;flex-wrap:wrap;align-items:center;"><span style="background:rgba(124,109,250,.15);border:1px solid rgba(124,109,250,.4);color:#a09cf7;font-size:.78rem;font-weight:700;padding:3px 10px;border-radius:99px;">⚡ {_xp_val:,} XP</span><span style="background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.35);color:#fbbf24;font-size:.78rem;font-weight:700;padding:3px 10px;border-radius:99px;">🔥 {streak}-day streak</span><span style="background:rgba(124,109,250,.12);border:1px solid rgba(124,109,250,.3);color:#a09cf7;font-size:.78rem;font-weight:600;padding:3px 10px;border-radius:99px;">{level_title}</span>{_demo_badge_html}</div></div>"""
    st.markdown(_hero_left_html, unsafe_allow_html=True)

with hero_right:
    _hero_right_html = f"""<div style="background:#18181f;border:1px solid #28283c;border-radius:16px;padding:1.5rem 1.25rem;text-align:right;"><div style="font-size:0.72rem;color:#7a7a98;text-transform:uppercase;letter-spacing:.4px;margin-bottom:0.35rem;">Next: {_nt}</div><div style="background:#1f1f2e;border-radius:99px;height:7px;overflow:hidden;width:100%;"><div style="height:100%;width:{_lp:.0f}%;background:linear-gradient(90deg,#7c6dfa,#22d3ee);border-radius:99px;transition:width .5s ease;"></div></div><div style="color:#7c6dfa;font-size:0.78rem;margin-top:0.3rem;font-weight:600;">{_lp:.0f}% to next level</div></div>"""
    st.markdown(_hero_right_html, unsafe_allow_html=True)



# ═══════════════════════════════════════════════════════════
# METRIC CARDS
# ═══════════════════════════════════════════════════════════
c1, c2, c3, c4, c5 = st.columns(5)
metric_rows = [
    (c1, "⚡", f"{stats['total_xp']:,}", "Total XP"),
    (c2, "⏱️", f"{stats['total_study_mins']:.0f}m", "Study Time"),
    (c3, "🧩", stats["quizzes_taken"], "Quizzes"),
    (c4, "💻", stats["code_solved"], "Problems"),
    (c5, "🔥", stats["max_streak"], "Best Streak"),
]
for col, icon, val, label in metric_rows:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height:1.25rem;'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# CHARTS + SIDEBAR PANELS
# ═══════════════════════════════════════════════════════════
col_main, col_side = st.columns([5, 2], gap="large")

with col_main:

    # ── XP Chart ──────────────────────────────────────────
    st.markdown("""<div style="font-size:.72rem;font-weight:700;color:var(--text-muted);
                    text-transform:uppercase;letter-spacing:.7px;margin-bottom:.5rem;">
                    XP Earned — Last 30 Days</div>""", unsafe_allow_html=True)

    if perf:
        df = pd.DataFrame(perf)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["xp_earned"].cumsum(),
            fill="tozeroy", name="Cumulative XP",
            line=dict(color="#7c6dfa", width=2),
            fillcolor="rgba(124,109,250,0.1)",
            hovertemplate="<b>%{x|%b %d}</b><br>XP: %{y}<extra></extra>"
        ))
        fig.add_trace(go.Bar(
            x=df["date"], y=df["xp_earned"],
            marker_color="rgba(34,211,238,0.45)",
            name="Daily XP",
            hovertemplate="<b>%{x|%b %d}</b><br>Daily: %{y} XP<extra></extra>"
        ))
        fig.update_layout(**_chart(260))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown('<div class="info-box">No activity yet — start studying to see your XP chart! 🚀</div>',
                    unsafe_allow_html=True)

    # ── Study Minutes ──────────────────────────────────────
    if perf:
        st.markdown("""<div style="font-size:.72rem;font-weight:700;color:var(--text-muted);
                        text-transform:uppercase;letter-spacing:.7px;margin:.75rem 0 .4rem;">
                        Daily Study Minutes</div>""", unsafe_allow_html=True)
        df2 = pd.DataFrame(perf)
        df2["date"] = pd.to_datetime(df2["date"])
        df2 = df2.sort_values("date")
        fig2 = px.bar(df2, x="date", y="study_mins",
                      color_discrete_sequence=["#22d3ee"])
        fig2.update_traces(
            marker_line_width=0,
            hovertemplate="<b>%{x|%b %d}</b><br>%{y:.0f} mins<extra></extra>"
        )
        fig2.update_layout(**_chart(190), xaxis_title=None, yaxis_title="mins")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Topic Mastery Bars ─────────────────────────────────
    done_topics = [t for t in topics if t.get("mastery_pct", 0) > 0]
    if done_topics:
        st.markdown("""<div style="font-size:.72rem;font-weight:700;color:var(--text-muted);
                        text-transform:uppercase;letter-spacing:.7px;margin:.75rem 0 .75rem;">
                        Topic Mastery</div>""", unsafe_allow_html=True)
        for t in sorted(done_topics, key=lambda x: x.get("mastery_pct", 0), reverse=True)[:8]:
            m = t.get("mastery_pct", 0) or 0
            col_c = "var(--green)" if m >= 75 else "var(--amber)" if m >= 40 else "var(--rose)"
            status_icon = "✅" if t["status"] == "completed" else "🔄" if t["status"] == "in_progress" else "📌"
            tl, tr = st.columns([4, 1])
            with tl:
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:2px;">
                    <span style="font-size:.8rem;">{status_icon}</span>
                    <span style="font-size:.875rem;color:var(--text-base);">{t['topic_name']}</span>
                </div>
                <div style="background:var(--bg-overlay);border-radius:99px;height:5px;overflow:hidden;
                            margin-bottom:.625rem;">
                    <div style="height:100%;width:{m}%;background:{col_c};border-radius:99px;
                                transition:width .5s ease;"></div>
                </div>
                """, unsafe_allow_html=True)
            with tr:
                st.markdown(f'<div style="color:{col_c};font-weight:700;font-size:.82rem;'
                            f'text-align:right;padding-top:2px;">{m:.0f}%</div>',
                            unsafe_allow_html=True)

with col_side:

    # ── Quiz Accuracy Gauge ────────────────────────────────
    if quiz_data:
        avg_acc = sum(q.get("percentage", 0) for q in quiz_data) / len(quiz_data)
        st.markdown("""<div style="font-size:.72rem;font-weight:700;color:var(--text-muted);
                        text-transform:uppercase;letter-spacing:.7px;margin-bottom:.4rem;">
                        Quiz Accuracy</div>""", unsafe_allow_html=True)
        gauge_color = "#34d399" if avg_acc >= 75 else "#fbbf24" if avg_acc >= 50 else "#fb7185"
        fig3 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=avg_acc,
            number={"suffix": "%", "font": {"color": gauge_color, "size": 28, "family": "Inter"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#28283c", "tickfont": {"size": 9}},
                "bar": {"color": gauge_color, "thickness": 0.3},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0,  50], "color": "rgba(251,113,133,0.08)"},
                    {"range": [50, 75], "color": "rgba(251,191,36,0.08)"},
                    {"range": [75,100], "color": "rgba(52,211,153,0.08)"},
                ],
                "threshold": {"line": {"color": gauge_color, "width": 2}, "value": 75},
            }
        ))
        fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                           font=dict(color="#7a7a98", family="Inter"),
                           height=170, margin=dict(l=10,r=10,t=10,b=0))
        st.plotly_chart(fig3, use_container_width=True)

    # ── Today's Focus ──────────────────────────────────────
    today_topics = [t for t in topics if t.get("status") in ("available", "in_progress")][:3]
    st.markdown("""<div style="font-size:.72rem;font-weight:700;color:var(--text-muted);
                    text-transform:uppercase;letter-spacing:.7px;margin:.5rem 0 .6rem;">
                    Today's Focus</div>""", unsafe_allow_html=True)

    if today_topics:
        for t in today_topics:
            m = t.get("mastery_pct", 0) or 0
            icon = "🔄" if t["status"] == "in_progress" else "📌"
            border_c = "var(--accent)" if t["status"] == "in_progress" else "var(--border)"
            st.markdown(f"""
            <div style="background:var(--bg-elevated);border:1px solid {border_c};
                        border-radius:var(--radius);padding:.75rem 1rem;margin-bottom:.4rem;">
                <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.35rem;">
                    <span>{icon}</span>
                    <span style="font-weight:600;font-size:.875rem;color:var(--text-primary);">
                        {t['topic_name']}
                    </span>
                </div>
                <div style="font-size:.72rem;color:var(--text-muted);margin-bottom:.3rem;">
                    Week {t.get('week_number',1)} · Day {t.get('day_number',1)}
                </div>
                <div style="background:var(--bg-overlay);border-radius:99px;height:4px;overflow:hidden;">
                    <div style="height:100%;width:{m}%;
                                background:linear-gradient(90deg,var(--accent),var(--cyan));
                                border-radius:99px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="success-box" style="font-size:.875rem;">🎉 All current topics complete!</div>',
                    unsafe_allow_html=True)

    # ── Weak Areas ─────────────────────────────────────────
    weak = identify_weak_areas(topics, quiz_data)
    if weak:
        st.markdown("""<div style="font-size:.72rem;font-weight:700;color:var(--text-muted);
                        text-transform:uppercase;letter-spacing:.7px;margin:.75rem 0 .6rem;">
                        Needs Attention</div>""", unsafe_allow_html=True)
        for w in weak[:4]:
            m = w["mastery"]
            col_c = "var(--rose)" if m < 30 else "var(--amber)" if m < 60 else "var(--green)"
            st.markdown(f"""
            <div style="margin-bottom:.5rem;">
                <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                    <span style="font-size:.82rem;color:var(--text-base);">
                        {w['topic']}</span>
                    <span style="font-size:.78rem;font-weight:700;color:{col_c};">
                        {m:.0f}%</span>
                </div>
                <div style="background:var(--bg-overlay);border-radius:99px;height:4px;overflow:hidden;">
                    <div style="height:100%;width:{m}%;background:{col_c};border-radius:99px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# RECENT ACTIVITY
# ═══════════════════════════════════════════════════════════
st.markdown("<div style='height:.75rem;'></div>", unsafe_allow_html=True)
st.markdown("""<div style="height:1px;background:var(--border-muted);margin:.75rem 0 1.25rem;"></div>""",
            unsafe_allow_html=True)
st.markdown("""<div style="font-size:.72rem;font-weight:700;color:var(--text-muted);
                text-transform:uppercase;letter-spacing:.7px;margin-bottom:.75rem;">
                Recent Activity</div>""", unsafe_allow_html=True)

activity = []
for s in study_data[:6]:
    activity.append({"type": "Study",  "icon": "📖", "color": "var(--accent)",
                     "topic": s.get("topic_name",""),
                     "detail": f"{s.get('duration_mins',0):.0f} min",
                     "time": s.get("created_at","")})
for q in quiz_data[:6]:
    pct = q.get("percentage", 0)
    c = "var(--green)" if pct >= 75 else "var(--amber)" if pct >= 50 else "var(--rose)"
    activity.append({"type": "Quiz", "icon": "🧩", "color": c,
                     "topic": q.get("topic_name",""),
                     "detail": f"{pct:.0f}%",
                     "time": q.get("created_at","")})

activity.sort(key=lambda x: x["time"], reverse=True)

if activity:
    cols_act = st.columns(2)
    for i, a in enumerate(activity[:8]):
        with cols_act[i % 2]:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:.75rem;
                        padding:.625rem .875rem;border-radius:var(--radius-sm);
                        background:var(--bg-elevated);border:1px solid var(--border-muted);
                        margin-bottom:.375rem;">
                <span style="font-size:1.1rem;">{a['icon']}</span>
                <div style="flex:1;min-width:0;">
                    <div style="font-size:.82rem;font-weight:600;color:var(--text-base);
                                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        {a['topic']}
                    </div>
                    <div style="font-size:.72rem;color:var(--text-muted);">
                        {a['type']} · {a['time'][:10] if a['time'] else ''}
                    </div>
                </div>
                <span style="font-size:.8rem;font-weight:700;color:{a['color']};white-space:nowrap;">
                    {a['detail']}
                </span>
            </div>
            """, unsafe_allow_html=True)
else:
    st.markdown('<div class="info-box">No activity yet. Let\'s start your learning journey! 🚀</div>',
                unsafe_allow_html=True)

# ── Demo CTA at bottom ─────────────────────────────────────
if demo_mode:
    st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center;padding:2rem;background:var(--bg-elevated);
                border:1px solid var(--border);border-radius:var(--radius-lg);">
        <div style="font-size:1.5rem;margin-bottom:.5rem;">🚀</div>
        <div style="font-size:1.1rem;font-weight:700;color:var(--text-primary);margin-bottom:.5rem;">
            Ready to start your own journey?
        </div>
        <div style="font-size:.875rem;color:var(--text-muted);">
            Go to <strong style="color:var(--accent);">⚙️ Settings</strong>
            to create your profile and unlock all features.
        </div>
    </div>
    """, unsafe_allow_html=True)
