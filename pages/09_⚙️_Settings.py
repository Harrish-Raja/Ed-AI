import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db_manager import (get_user, create_user, update_user,
                                   get_all_users, init_db)
from utils.session_manager import init_session
from utils.llm_client import reload_model

st.set_page_config(page_title="Settings · EdAI", page_icon="⚙️", layout="wide")
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding='utf-8') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_db()
init_session()

st.markdown("# ⚙️ Settings")

tab1, tab2, tab3 = st.tabs(["👤 Profile", "🤖 LLM Backend", "📁 Data"])

# ── Tab 1: Profile ───────────────────────────────
with tab1:
    st.markdown("### 👤 Your Profile")

    existing_users = get_all_users()
    user_options = {u["name"]: u["id"] for u in existing_users}

    if existing_users:
        st.markdown("**Switch Profile:**")
        selected_user_name = st.selectbox(
            "Existing Profiles",
            ["— Create New —"] + list(user_options.keys())
        )
        if selected_user_name != "— Create New —":
            uid = user_options[selected_user_name]
            if st.button(f"✅ Load Profile: {selected_user_name}", use_container_width=True):
                st.session_state.user_id = uid
                st.session_state.demo_mode = False
                st.success(f"✅ Logged in as **{selected_user_name}**!")
                st.rerun()

    st.markdown("---")
    st.markdown("**Create New Profile:**")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("👤 Your Name", placeholder="e.g., Jayachandiran")
            email = st.text_input("📧 Email (optional)", placeholder="you@example.com")
            level = st.selectbox("📊 Current Level",
                                  ["Beginner", "Intermediate", "Advanced"])
        with col2:
            daily_hours = st.slider("⏰ Daily Study Hours", 0.5, 8.0, 2.0, 0.5)
            target_goal = st.selectbox("🎯 Main Goal",
                                        ["Interview Preparation", "Job Ready", "Exam Preparation",
                                         "Skill Mastery", "Freelance Projects"])
            preferred_language = st.selectbox("💻 Primary Language",
                                               ["Python", "JavaScript", "Java", "C++", "Go"])

        submit = st.form_submit_button("🚀 Create / Update Profile", use_container_width=True)

    if submit and name:
        uid = create_user(name, email or f"{name.lower().replace(' ','_')}@edai.local",
                          level, daily_hours, target_goal, preferred_language)
        st.session_state.user_id = uid
        st.session_state.demo_mode = False
        st.success(f"✅ Profile created! Welcome, **{name}**!")
        st.balloons()
        st.rerun()
    elif submit:
        st.warning("Please enter your name.")

    # Edit current profile
    if st.session_state.get("user_id"):
        current = get_user(st.session_state.user_id)
        if current:
            st.markdown("---")
            st.markdown(f"**Currently logged in as: {current['name']}**")
            with st.form("edit_form"):
                e_level = st.selectbox("Update Level",
                                        ["Beginner", "Intermediate", "Advanced"],
                                        index=["Beginner","Intermediate","Advanced"].index(
                                            current.get("level","Beginner")))
                e_hours = st.slider("Update Daily Hours", 0.5, 8.0,
                                     float(current.get("daily_hours", 2.0)), 0.5)
                e_goal  = st.selectbox("Update Goal",
                                        ["Interview Preparation","Job Ready","Exam Preparation",
                                         "Skill Mastery","Freelance Projects"],
                                        index=["Interview Preparation","Job Ready","Exam Preparation",
                                               "Skill Mastery","Freelance Projects"].index(
                                            current.get("target_goal","Skill Mastery")))
                if st.form_submit_button("💾 Save Changes"):
                    update_user(st.session_state.user_id,
                                level=e_level, daily_hours=e_hours, target_goal=e_goal)
                    st.success("✅ Profile updated!")

# ── Tab 2: LLM Backend ───────────────────────────
with tab2:
    st.markdown("### 🤖 LLM Backend")

    # ── Current backend badge ──────────────────────
    current_backend = os.getenv("EDAI_BACKEND", st.session_state.get("llm_backend", "gemini"))
    badge_color = "#00D4A8" if current_backend == "lmstudio" else "#6C63FF"
    badge_icon  = "🖥️ LM Studio (Local)" if current_backend == "lmstudio" else "☁️ Google Gemini"
    st.markdown(f"""
    <div style="display:inline-flex;align-items:center;gap:0.6rem;
                padding:8px 18px;border-radius:50px;
                background:rgba(0,0,0,0.3);border:1px solid {badge_color};
                margin-bottom:1.25rem;">
        <span style="width:8px;height:8px;border-radius:50%;
                     background:{badge_color};display:inline-block;"></span>
        <span style="color:{badge_color};font-weight:700;">Active: {badge_icon}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Backend selector ───────────────────────────
    backend_choice = st.radio(
        "Choose your AI backend",
        ["☁️ Google Gemini (Cloud)", "🖥️ LM Studio (Local / Offline)"],
        index=1 if current_backend == "lmstudio" else 0,
        help="Switch between Google Gemini (needs API key) and your local LM Studio server."
    )
    chosen = "lmstudio" if "LM Studio" in backend_choice else "gemini"

    st.markdown("---")

    # ══════════════════════════════════════════════
    # LM Studio section
    # ══════════════════════════════════════════════
    if chosen == "lmstudio":
        st.markdown("### 🖥️ LM Studio — Local Configuration")
        st.markdown("""
        <div class="info-box">
            LM Studio runs a local OpenAI-compatible API server. No internet or API key needed!<br>
            <strong>Make sure LM Studio is open and a model is loaded before testing.</strong>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**How to set up LM Studio:**")
        st.markdown("""
        1. Download **[LM Studio](https://lmstudio.ai/)** and install it
        2. Load any model (e.g. `Llama 3`, `Mistral`, `Phi-3`, `Qwen`)
        3. Go to the **Local Server** tab (⚡ icon on the left)
        4. Click **Start Server** — default port is `1234`
        5. Come back here and click **Test Connection**
        """)

        col_url, col_model = st.columns(2)
        with col_url:
            lm_url = st.text_input(
                "🌐 LM Studio Server URL",
                value=st.session_state.get("lm_studio_url",
                                            os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")),
                placeholder="http://localhost:1234/v1",
                help="Default is http://localhost:1234/v1 — don't change unless you changed the port."
            )
        with col_model:
            lm_model = st.text_input(
                "🧠 Model identifier",
                value=st.session_state.get("lm_studio_model",
                                            os.getenv("LM_STUDIO_MODEL", "local-model")),
                placeholder="local-model  (or leave as-is — LM Studio ignores this)",
                help="LM Studio uses whatever model is loaded. You can leave this as 'local-model'."
            )

        col_save_lm, col_test_lm = st.columns(2)
        with col_save_lm:
            if st.button("💾 Save & Use LM Studio", use_container_width=True):
                st.session_state.lm_studio_url   = lm_url
                st.session_state.lm_studio_model  = lm_model
                st.session_state.llm_backend      = "lmstudio"
                os.environ["EDAI_BACKEND"]        = "lmstudio"
                os.environ["LM_STUDIO_URL"]       = lm_url
                os.environ["LM_STUDIO_MODEL"]     = lm_model
                from utils.llm_client import reload_model
                reload_model()
                st.success("✅ LM Studio backend activated!")
                st.rerun()

        with col_test_lm:
            if st.button("🧪 Test LM Studio", use_container_width=True):
                os.environ["EDAI_BACKEND"]    = "lmstudio"
                os.environ["LM_STUDIO_URL"]   = lm_url
                os.environ["LM_STUDIO_MODEL"] = lm_model
                from utils.llm_client import reload_model, ask_llm
                reload_model()
                try:
                    result = ask_llm(
                        "Respond with exactly two words: 'EdAI connected'",
                        temperature=0.1
                    )
                    st.success(f"✅ LM Studio connected! Response: **{result}**")
                except ImportError:
                    st.error("❌ `openai` package missing. Run: `pip install openai`")
                except Exception as e:
                    st.error(f"❌ Connection failed: {e}\n\n"
                             f"Make sure LM Studio server is **running** on `{lm_url}`")

        # Install helper
        st.markdown("---")
        st.markdown("**Missing the openai package?**")
        st.code("pip install openai", language="bash")
        st.markdown("""
        <div class="warning-box">
            ⚠️ The <code>openai</code> Python package is only needed for LM Studio integration.
            It communicates with LM Studio's local API, not OpenAI's servers.
        </div>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # Gemini section
    # ══════════════════════════════════════════════
    else:
        st.markdown("### ☁️ Google Gemini API Key")
        st.markdown("""
        <div class="info-box">
            Uses <strong>Google Gemini 2.0 Flash</strong> — fast, high-quality, with a generous free tier.
            Your key is stored in the session and never sent anywhere except Google's API.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**How to get your Gemini API Key:**")
        st.markdown("""
        1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
        2. Sign in with your Google account
        3. Click **"Create API Key"**
        4. Copy and paste it below
        """)

        current_key = st.session_state.get("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
        if current_key and len(current_key) > 12:
            masked = f"{current_key[:8]}...{current_key[-4:]}"
            st.markdown(f'<div class="success-box">✅ Key configured: <code>{masked}</code></div>',
                        unsafe_allow_html=True)

        new_key = st.text_input(
            "🔑 Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Stored in session only."
        )

        col_save_g, col_test_g = st.columns(2)
        with col_save_g:
            if st.button("💾 Save & Use Gemini", use_container_width=True):
                if new_key:
                    st.session_state.gemini_api_key = new_key
                    st.session_state.llm_backend    = "gemini"
                    os.environ["GEMINI_API_KEY"]    = new_key
                    os.environ["EDAI_BACKEND"]      = "gemini"
                    from utils.llm_client import reload_model
                    reload_model()
                    st.success("✅ Gemini backend activated!")
                    st.rerun()
                else:
                    st.warning("Please enter your API key first.")

        with col_test_g:
            if st.button("🧪 Test Gemini", use_container_width=True):
                test_key = new_key or st.session_state.get("gemini_api_key", "")
                if test_key:
                    os.environ["GEMINI_API_KEY"] = test_key
                    os.environ["EDAI_BACKEND"]   = "gemini"
                    from utils.llm_client import reload_model, ask_llm
                    reload_model()
                    try:
                        result = ask_llm(
                            "Respond with exactly two words: 'EdAI connected'",
                            temperature=0
                        )
                        st.success(f"✅ Gemini connected! Response: **{result}**")
                    except Exception as e:
                        st.error(f"❌ Connection failed: {e}")
                else:
                    st.warning("Please enter an API key first.")

        st.markdown("---")
        st.markdown("### 📁 .env File Alternative")
        st.markdown("You can also set your key via a `.env` file in the project root:")
        st.code("GEMINI_API_KEY=your_key_here\nEDAI_BACKEND=gemini", language="bash")



# ── Tab 3: Data ──────────────────────────────────
with tab3:
    st.markdown("### 📁 Data Management")

    if st.session_state.get("user_id"):
        from database.db_manager import get_performance_data, get_quiz_attempts, get_study_sessions
        import pandas as pd
        import json

        uid = st.session_state.user_id

        st.markdown("**Export Your Data:**")
        col_e1, col_e2, col_e3 = st.columns(3)

        with col_e1:
            quiz_data = get_quiz_attempts(uid)
            if quiz_data:
                df_quiz = pd.DataFrame(quiz_data)
                csv = df_quiz.to_csv(index=False)
                st.download_button("📥 Quiz History (CSV)", csv,
                                   "edai_quiz_history.csv", "text/csv",
                                   use_container_width=True)

        with col_e2:
            study_data = get_study_sessions(uid)
            if study_data:
                df_study = pd.DataFrame(study_data)
                csv2 = df_study.to_csv(index=False)
                st.download_button("📥 Study Sessions (CSV)", csv2,
                                   "edai_study_sessions.csv", "text/csv",
                                   use_container_width=True)

        with col_e3:
            perf_data = get_performance_data(uid, 365)
            if perf_data:
                df_perf = pd.DataFrame(perf_data)
                csv3 = df_perf.to_csv(index=False)
                st.download_button("📥 Performance (CSV)", csv3,
                                   "edai_performance.csv", "text/csv",
                                   use_container_width=True)

        st.markdown("---")
        st.markdown("**App Info:**")
        from database.db_manager import DB_PATH
        st.markdown(f"""
        <div class="content-panel">
            <div style="color:#9090b8;font-size:0.85rem;">Database Path</div>
            <code style="color:#a09cf7;">{DB_PATH}</code>
            <div style="color:#9090b8;font-size:0.85rem;margin-top:1rem;">Version</div>
            <div style="color:#e8e8f0;">EdAI v2.0 · Google Gemini 2.0 Flash</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-box">⚠️ Please create a profile first to access data options.</div>',
                    unsafe_allow_html=True)
