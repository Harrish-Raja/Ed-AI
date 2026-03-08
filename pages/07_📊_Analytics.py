import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db_manager import (get_user, get_performance_data, get_quiz_attempts,
                                   get_study_sessions, get_topics, get_latest_roadmap,
                                   get_total_stats, get_code_submissions)
from core.performance_analyzer import (generate_growth_report, compute_skill_radar,
                                        identify_weak_areas, compute_learning_streak,
                                        compute_xp_level)
from utils.session_manager import init_session, require_login, require_api_key
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta


def _chart_layout(height=300):
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#9090b8", family="Inter"),
        xaxis=dict(showgrid=False, color="#3a3a5e"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", color="#3a3a5e"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#9090b8")),
        margin=dict(l=0, r=0, t=10, b=0),
        height=height,
    )

st.set_page_config(page_title="Analytics · EdAI", page_icon="📊", layout="wide")
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session()
require_login()
require_api_key()

uid = st.session_state.user_id
user = get_user(uid)
stats = get_total_stats(uid)

# ── Period Selector ──────────────────────────────
st.markdown("# 📊 Analytics & Growth Dashboard")

col_period, col_gen = st.columns([3, 1])
with col_period:
    period = st.radio("📅 View Period", ["Today", "Week", "Month", "3 Months", "Year", "Custom"],
                      horizontal=True, index=2)

days_map = {"Today": 1, "Week": 7, "Month": 30, "3 Months": 90, "Year": 365}
if period == "Custom":
    with col_period:
        date_range = st.date_input("Select Range", value=(
            datetime.now().date() - timedelta(days=30), datetime.now().date()
        ))
    num_days = (date_range[1] - date_range[0]).days + 1 if len(date_range) == 2 else 30
else:
    num_days = days_map.get(period, 30)

with col_gen:
    gen_report = st.button("📝 Generate Growth Report", use_container_width=True)

# Load data
perf = get_performance_data(uid, days=num_days)
quiz_data = get_quiz_attempts(uid, limit=200)
study_data = get_study_sessions(uid, limit=200)
code_data = get_code_submissions(uid, limit=100)
roadmap = get_latest_roadmap(uid)
topics = get_topics(uid, roadmap["id"] if roadmap else None) if roadmap else []

streak = compute_learning_streak(perf)
level_title, level_progress, next_level = compute_xp_level(stats["total_xp"])

# ── Top KPIs ──────────────────────────────────────
st.markdown("### 📈 Key Metrics")
c1, c2, c3, c4, c5, c6 = st.columns(6)
period_xp = sum(p.get("xp_earned", 0) for p in perf)
period_study = sum(p.get("study_mins", 0) for p in perf)
avg_quiz = sum(p.get("quiz_accuracy", 0) for p in perf) / max(len(perf), 1)
topics_done = len([t for t in topics if t.get("status") == "completed"])
total_topics = len(topics)

for col, icon, val, label, badge in [
    (c1, "⚡", f"{period_xp}", f"XP ({period})", "badge-purple"),
    (c2, "⏱️", f"{period_study:.0f}m", "Study Time", "badge-blue"),
    (c3, "🎯", f"{avg_quiz:.1f}%", "Quiz Avg", "badge-green"),
    (c4, "✅", f"{topics_done}/{total_topics}", "Topics Done", "badge-yellow"),
    (c5, "🔥", f"{streak}", "Day Streak", "badge-red"),
    (c6, "🏆", level_title.split()[1] if " " in level_title else level_title, "Level", "badge-purple"),
]:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts Row 1 ─────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("#### 📈 XP Over Time")
    if perf:
        df_p = pd.DataFrame(perf)
        df_p["date"] = pd.to_datetime(df_p["date"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_p["date"], y=df_p["xp_earned"].cumsum(),
            fill="tozeroy", name="Cumulative XP",
            line=dict(color="#6C63FF", width=2),
            fillcolor="rgba(108,99,255,0.12)"
        ))
        fig.add_trace(go.Bar(
            x=df_p["date"], y=df_p["xp_earned"],
            name="Daily XP", marker_color="rgba(0,212,255,0.5)"
        ))
        fig.update_layout(_chart_layout(height=250))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown('<div class="info-box">No data for this period.</div>', unsafe_allow_html=True)

with col_b:
    st.markdown("#### ⏱️ Study Minutes per Day")
    if perf:
        df_s = pd.DataFrame(perf)
        df_s["date"] = pd.to_datetime(df_s["date"])
        fig2 = px.bar(df_s, x="date", y="study_mins",
                      color_discrete_sequence=["#00D4FF"])
        fig2.update_layout(_chart_layout(height=250))
        fig2.update_traces(marker_line_width=0)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.markdown('<div class="info-box">No study sessions recorded.</div>', unsafe_allow_html=True)

# ── Charts Row 2 ─────────────────────────────────
col_c, col_d = st.columns(2)

with col_c:
    st.markdown("#### 🎯 Quiz Accuracy Trend")
    if quiz_data:
        df_q = pd.DataFrame(quiz_data[-50:])
        df_q["created_at"] = pd.to_datetime(df_q["created_at"])
        fig3 = go.Figure()
        for topic_name in df_q["topic_name"].unique()[:6]:
            sub = df_q[df_q["topic_name"] == topic_name]
            fig3.add_trace(go.Scatter(
                x=sub["created_at"], y=sub["percentage"],
                mode="lines+markers", name=topic_name[:20],
                line=dict(width=2)
            ))
        fig3.add_hline(y=75, line_dash="dash", line_color="rgba(0,212,168,0.5)",
                      annotation_text="75% threshold")
        fig3.update_layout(_chart_layout(height=250))
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.markdown('<div class="info-box">No quizzes taken yet.</div>', unsafe_allow_html=True)

with col_d:
    st.markdown("#### 🕸️ Skill Mastery Radar")
    skill_map = compute_skill_radar(topics, quiz_data)
    if skill_map:
        top_skills = dict(sorted(skill_map.items(), key=lambda x: x[1], reverse=True)[:8])
        names = list(top_skills.keys())
        values = list(top_skills.values())
        names.append(names[0])
        values.append(values[0])
        fig4 = go.Figure(go.Scatterpolar(
            r=values, theta=[n[:20] for n in names],
            fill="toself",
            line_color="#6C63FF",
            fillcolor="rgba(108,99,255,0.2)"
        ))
        fig4.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 100],
                               gridcolor="rgba(255,255,255,0.1)",
                               tickcolor="#5050a0", color="#5050a0"),
                angularaxis=dict(gridcolor="rgba(255,255,255,0.1)",
                                tickcolor="#5050a0", color="#9090b8")
            ),
            **_chart_layout(height=280)
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.markdown('<div class="info-box">Complete some topics to see your skill radar.</div>',
                    unsafe_allow_html=True)

# ── Topic Mastery Heatmap ─────────────────────────
st.markdown("### 📋 Topic Mastery Overview")
if topics:
    topic_df = pd.DataFrame(topics)[["topic_name", "mastery_pct", "status", "week_number"]].copy()
    topic_df["mastery_pct"] = topic_df["mastery_pct"].fillna(0)
    topic_df["status_label"] = topic_df["status"].map({
        "completed": "✅ Done", "in_progress": "🔄 In Progress",
        "available": "📌 Pending", "locked": "🔒 Locked"
    })

    fig5 = px.bar(
        topic_df.head(20), x="topic_name", y="mastery_pct",
        color="mastery_pct",
        color_continuous_scale=[[0, "#FF6B6B"], [0.4, "#FFC400"], [0.7, "#00D4A8"], [1, "#6C63FF"]],
        labels={"mastery_pct": "Mastery %", "topic_name": "Topic"},
    )
    fig5.update_layout(
        _chart_layout(height=280),
        xaxis=dict(tickangle=-45, title=None),
        coloraxis_showscale=True,
    )
    fig5.update_traces(marker_line_width=0)
    st.plotly_chart(fig5, use_container_width=True)

# ── Weak Areas ────────────────────────────────────
st.markdown("### 🎯 Areas Needing Attention")
weak = identify_weak_areas(topics, quiz_data)
if weak:
    for w in weak[:6]:
        mastery = w["mastery"]
        color = "#FF6B6B" if mastery < 30 else "#FFC400" if mastery < 60 else "#00D4A8"
        c_l, c_r = st.columns([4, 1])
        with c_l:
            st.markdown(f"""
            <div style="margin-bottom:0.4rem;">
                <span style="color:#c0c0d8;font-size:0.9rem;">{w['topic']}</span>
            </div>
            <div class="progress-bar-wrapper">
                <div style="height:100%;width:{mastery}%;background:{color};border-radius:50px;"></div>
            </div>
            """, unsafe_allow_html=True)
        with c_r:
            st.markdown(f'<div style="color:{color};font-weight:700;text-align:right;">{mastery:.0f}%</div>',
                        unsafe_allow_html=True)
else:
    st.markdown('<div class="success-box">🎉 All topics are on track!</div>', unsafe_allow_html=True)

# ── Growth Report ─────────────────────────────────
st.markdown("---")
st.markdown("### 📝 AI Growth Report")

if gen_report:
    with st.spinner("🤖 Generating your personalized growth report..."):
        report = generate_growth_report(user, perf, quiz_data, code_data, topics, period.lower())
        st.session_state.growth_report = report

report = st.session_state.get("growth_report")
if report:
    st.markdown(f"""
    <div class="report-card">
        {report.replace(chr(10), '<br>')}
    </div>
    """, unsafe_allow_html=True)
elif not gen_report:
    st.markdown('<div class="info-box">Click 📝 Generate Growth Report to get your personalized AI analysis.</div>',
                unsafe_allow_html=True)

# ── Consistency Calendar ──────────────────────────
if perf:
    st.markdown("### 📅 Learning Consistency")
    df_cal = pd.DataFrame(perf)
    df_cal["date"] = pd.to_datetime(df_cal["date"])
    df_cal["week"] = df_cal["date"].dt.isocalendar().week
    df_cal["day"] = df_cal["date"].dt.day_name()
    df_cal["day_num"] = df_cal["date"].dt.dayofweek

    fig6 = go.Figure(go.Scatter(
        x=df_cal["date"], y=df_cal["xp_earned"],
        mode="markers",
        marker=dict(
            size=df_cal["xp_earned"].apply(lambda x: max(8, min(30, x / 2))),
            color=df_cal["xp_earned"],
            colorscale=[[0, "#1a1a3e"], [0.3, "#6C63FF"], [1, "#00D4FF"]],
            showscale=True,
            colorbar=dict(title="XP", tickcolor="#5050a0")
        ),
        text=df_cal.apply(lambda r: f"{r['date'].strftime('%b %d')}: {r['xp_earned']} XP", axis=1),
        hovertemplate="%{text}<extra></extra>"
    ))
    fig6.update_layout(_chart_layout(height=200))
    st.plotly_chart(fig6, use_container_width=True)

