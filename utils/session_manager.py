import streamlit as st
import os


def init_session():
    """Initialize all session state variables."""
    defaults = {
        "user_id": None,
        "current_roadmap_id": None,
        "current_topic_id": None,
        "current_topic_name": "",
        "quiz_questions": [],
        "quiz_answers": {},
        "quiz_start_time": None,
        "study_start_time": None,
        "interview_history": [],
        "current_problem": None,
        "code_output": "",
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        # LLM backend
        "llm_backend": os.getenv("EDAI_BACKEND", "gemini"),
        "lm_studio_url": os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1"),
        "lm_studio_model": os.getenv("LM_STUDIO_MODEL", "local-model"),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v



def require_login():
    """Show error and stop if user is not logged in."""
    if not st.session_state.get("user_id"):
        st.error("⚠️ Please set up your profile first in **⚙️ Settings**.")
        st.stop()


def require_api_key():
    """Show error and stop if no valid LLM backend is configured."""
    backend = os.getenv("EDAI_BACKEND",
                        st.session_state.get("llm_backend", "gemini")).lower()

    if backend == "lmstudio":
        # Apply saved LM Studio settings to env
        if st.session_state.get("lm_studio_url"):
            os.environ["LM_STUDIO_URL"] = st.session_state.lm_studio_url
        if st.session_state.get("lm_studio_model"):
            os.environ["LM_STUDIO_MODEL"] = st.session_state.lm_studio_model
        os.environ["EDAI_BACKEND"] = "lmstudio"
        return  # No API key needed for local LM Studio

    # Gemini path — needs a key
    key = st.session_state.get("gemini_api_key", "") or os.getenv("GEMINI_API_KEY", "")
    if not key:
        st.error("🔑 Please add your Gemini API key in **⚙️ Settings → LLM Backend**.")
        st.stop()
    os.environ["GEMINI_API_KEY"] = key
    os.environ["EDAI_BACKEND"] = "gemini"

