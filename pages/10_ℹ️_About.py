import streamlit as st
import os

st.set_page_config(
    page_title="About EdAI",
    page_icon="ℹ️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Load CSS ──────────────────────────────────────────────
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("ℹ️ About EdAI")
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    ### 🌟 Welcome to the Future of Learning
    **EdAI** is an AI-powered personalized coding study planner and error tutor designed to help you master new technical skills with ease. By combining dynamic roadmaps, adaptive teaching, and real-time coding playgrounds, EdAI bridges the gap between passive reading and active execution.

    ### 🚀 Our Goal
    Our goal is simple: **Make learning any technical skill accessible, structured, and interactive.** 
    Whether you are an aspirant looking to crack their first technical interview, a student trying to grasp Data Structures, or a seasoned developer picking up a new language, EdAI adapts to your pace and proficiency.
    """)

with col2:
    st.markdown("""
    <div style="background:var(--bg-elevated); padding:2rem; border-radius:12px; border:1px solid var(--border); text-align:center;">
        <h1 style="font-size:3.5rem; margin:0; padding:0;">🧠</h1>
        <h3 style="margin-top:0.5rem; color:var(--accent);">EdAI Platform</h3>
        <p style="color:var(--text-muted); font-size:0.9rem;">Version 2.0</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

st.markdown("### 💡 Why Use EdAI?")
benefits = [
    ("🗺️ Structured Roadmaps", "No more tutorial hell. EdAI generates a day-by-day learning checklist specific to your desired overarching goal, visualizing it down a satisfying, interactive path."),
    ("💻 Real-Time Code Execution", "You don't need to juggle a dozen terminal windows. Practice writing scripts directly inside the web browser and get immediate output."),
    ("🐛 The 'Error Tutor'", "Errors are learning opportunities. Rather than just giving you the answer verbatim, our AI tutor breaks down your stack traces and gives you coaching hints."),
    ("🎯 Interview Readiness", "Mock technical coding and behavioral interview environments track your job-readiness by providing instant feedback on your answers."),
    ("🔒 Local AI Support", "Don't want to send data to the cloud? Toggle on 'LM Studio' in the settings and use open-source Large Language Models completely offline.")
]

for icon, title in benefits:
    st.markdown(f"""
    <div style="background:var(--bg-elevated); border:1px solid var(--border-muted); border-radius:8px; padding:1.25rem; margin-bottom:1rem;">
        <h4 style="margin:0 0 0.5rem 0; color:var(--text-primary);">{icon}</h4>
        <p style="margin:0; color:var(--text-base); font-size:0.95rem;">{title}</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("""
### 🔐 Security & Privacy
EdAI is designed to be user-first. 
1. **API Keys** are stored ephemerally in your browser session using `st.session_state`. They are **not** logged natively into our database.
2. **Local Workspaces** allow you to keep your data close.
3. **Local AI** options mean you can utilize the platform without requiring an internet connection if configured with a local inference server.
""")
