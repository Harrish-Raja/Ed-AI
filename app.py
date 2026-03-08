import streamlit as st
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from database.db_manager import init_db, get_user, get_total_stats, get_performance_data
from utils.session_manager import init_session

# ── Page config ──────────────────────────────────────────
st.set_page_config(
    page_title="EdAI — AI Learning Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Init DB ───────────────────────────────────────────────
init_db()
init_session()

# ── Load CSS ──────────────────────────────────────────────
css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Redirect or show landing ────────────────────────────
# ── Demo mode entry point ─────────────────────────────────
if st.session_state.get("demo_mode"):
    # User already clicked "Preview" — show a redirect hint
    st.markdown("""
    <div style="text-align:center;padding:3rem 1rem;">
        <div style="font-size:2rem;margin-bottom:.75rem;">🎯</div>
        <div style="font-size:1rem;color:var(--text-muted,#7a7a98);">
            Redirecting to Sample Dashboard…
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.switch_page("pages/01_🏠_Dashboard.py")

elif not st.session_state.get("user_id"):
    # ── Landing hero ─────────────────────────────────────
    st.markdown("""
    <div class="landing-hero">
        <div class="hero-glow"></div>
        <div class="hero-content">
            <div class="hero-badge">✨ AI-Powered Learning</div>
            <h1 class="hero-title">
                Master Any Tech Skill<br>
                <span class="gradient-text">With Your Personal AI Mentor</span>
            </h1>
            <p class="hero-subtitle">
                Get a personalized roadmap, adaptive teaching, real-time code feedback,
                and interview prep — all in one beautiful platform.
            </p>
            <div class="hero-stats">
                <div class="stat-pill">📚 AI-Generated Roadmaps</div>
                <div class="stat-pill">💻 Live Code Execution</div>
                <div class="stat-pill">🧩 Smart Quizzes</div>
                <div class="stat-pill">📊 Growth Analytics</div>
                <div class="stat-pill">🎯 Interview Coach</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CTA buttons ───────────────────────────────────────
    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

    cta_l, cta_c1, cta_c2, cta_r = st.columns([1.5, 1, 1, 1.5])
    with cta_c1:
        if st.button("👀 Preview Sample Dashboard", use_container_width=True, type="primary"):
            st.session_state.demo_mode = True
            st.switch_page("pages/01_🏠_Dashboard.py")
    with cta_c2:
        if st.button("ℹ️ Read About EdAI", use_container_width=True):
            st.switch_page("pages/10_ℹ️_About.py")

    # ── Instructions ──────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🚀 Get Started")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div style="background:var(--bg-elevated,#18181f);border:1px solid var(--border,#28283c);
                    border-radius:12px;padding:1.25rem 1.5rem;">
            <div style="font-size:.8rem;font-weight:700;color:var(--accent,#7c6dfa);
                        text-transform:uppercase;letter-spacing:.5px;margin-bottom:.625rem;">
                New Here?
            </div>
            <ol style="color:var(--text-base,#c4c4d4);font-size:.9rem;
                       line-height:1.8;padding-left:1.25rem;margin:0;">
                <li>Go to <strong>⚙️ Settings</strong> (sidebar)</li>
                <li>Create your profile</li>
                <li>Add your Gemini API key <em>or</em> set up LM Studio</li>
                <li>Head to <strong>📚 Roadmap</strong> and generate your first plan</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style="background:var(--bg-elevated,#18181f);border:1px solid var(--border,#28283c);
                    border-radius:12px;padding:1.25rem 1.5rem;">
            <div style="font-size:.8rem;font-weight:700;color:var(--green,#34d399);
                        text-transform:uppercase;letter-spacing:.5px;margin-bottom:.625rem;">
                Returning User?
            </div>
            <ol style="color:var(--text-base,#c4c4d4);font-size:.9rem;
                       line-height:1.8;padding-left:1.25rem;margin:0;">
                <li>Go to <strong>⚙️ Settings</strong></li>
                <li>Pick your existing profile</li>
                <li>Navigate to <strong>🏠 Dashboard</strong></li>
                <li>Continue from where you left off</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    # ── Feature Cards ─────────────────────────────────────
    st.markdown("<div style='height:.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 🌟 Everything You Need to Master Tech")
    fc1, fc2, fc3 = st.columns(3)
    cards = [
        ("🗺️", "Smart Roadmaps",
         "AI generates a complete, dependency-aware learning plan tailored to your goals and timeline."),
        ("🧠", "Adaptive Teaching",
         "Content adjusts to your level — simple for beginners, deep dives for advanced learners."),
        ("🏆", "Interview Ready",
         "Practice with real interview questions, mock sessions, and get your job readiness score."),
    ]
    for col, (icon, title, desc) in zip([fc1, fc2, fc3], cards):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

else:
    # ── Logged in — show welcome redirect ─────────────────
    user = get_user(st.session_state.user_id)
    if user:
        st.markdown(f"""
        <div class="welcome-back">
            <span>👋 Welcome back, <strong>{user['name']}</strong>!</span>
        </div>
        """, unsafe_allow_html=True)
        st.info("👈 Navigate using the sidebar to access your Dashboard, Studies, and more!")
