# ✨ EdAI: AI-Powered Learning Platform

Welcome to **EdAI**, your personalized AI Coding Study Planner & Error Tutor. EdAI brings the future of learning directly to your browser, offering dynamic roadmaps, adaptive explanations, interactive quizzes, local code execution, and mock interviews — all in one modern, gamified ecosystem. 

Whether you're prepping for exams, brushing up for technical interviews, or mastering a new language, EdAI curates a learning path just for you.

---

## 🌟 Key Features

### 🗺️ AI-Generated Smart Roadmaps
Input any technical topic (e.g., "Data Structures in Python" or "React for Beginners"), and EdAI will generate a personalized, day-by-day learning schedule. 
- **Duolingo-Style Visualization:** Visualize your progress down an interactive, curvy timeline, marking node completions until you unlock the treasure chest at the bottom!
- **Milestone Tracking:** Break large topics down into digestible weekly chunks and manageable daily tasks.

### 📖 Adaptive Teaching & Code Lab
Don't just read about topics — interact with them. 
- **In-Platform Editor:** A split-screen Code Lab powered by `streamlit-ace` lets you write, run, and test Python code natively in your browser. 
- **Error Tutor:** Built-in AI error tracking automatically identifies traceback logs, analyzes exactly *why* your code failed, and coaches you toward the solution without just giving away the answer.

### 🏆 Interactive Interview Prep
Switch to Interview Mode and simulate a technical or behavioral interview. 
- **Real-Time Feedback:** Get an instant score on your responses alongside constructive feedback from the AI.
- **Dynamic Question Types:** Face technical coding problems, conceptual questions, or scenario-based behavioral challenges.

### 📊 Growth Analytics Dashboard
A beautifully designed dashboard to track your XP, learning streak, quiz accuracy, and total study hours with animated charts and UI components. 

### ☁️ Flexible AI Backends
- **Google Gemini 2.0:** Securely use your Google API key for blazingly fast cloud generation using Gemini 2.0 Flash. 
- **LM Studio (100% Local):** For the privacy-conscious, seamlessly swap the backend to point to a local LM Studio server running LLaMA, Mistral, or Phi-3. **No internet required.**

---

## 🚀 Quick Setup & Deployment

### 1. Prerequisites 
Ensure you have Python 3.10+ installed on your system.
This project uses SQLite out of the box, so no external database setup is necessary!

### 2. Installation
Clone this repository and install the dependencies:
```bash
git clone https://github.com/yourusername/edai.git
cd edai
pip install -r requirements.txt
```

### 3. Running Locally
Simply spin up the Streamlit server!
```bash
streamlit run app.py
```
This will open the app locally on `http://localhost:8501`.

### 4. Setup Your Backend (In-App)
Navigate to **⚙️ Settings -> LLM Backend** on the sidebar:
- Provide your free Google Gemini API Key.
- OR flip the switch to LM Studio and provide your local inference URL (e.g., `http://localhost:1234/v1`).

---

## 🔒 Security & Deployment Notes

**Is this safe to deploy to Streamlit Community Cloud?**
Yes! This application was explicitly built with safety and ease of deployment in mind:
1. **API Keys:** API keys are never hard-coded. They are processed securely via Streamlit's `st.session_state` (stored only for the duration of the user browser session) or can be read natively from the `.env` / Streamlit Secrets configuration if provided by an administrator.
2. **Database:** The database (`database/edai.db`) utilizes local SQLite. **Note for Streamlit Cloud:** Streamlit Cloud ephemeral instances reset local storage on reboot. Therefore, your database will be reset if the application spins down. For permanent data retention on cloud providers, mount an external volume, or easily point the `sqlite3.connect()` string to a persistent storage path.
3. **Local Code Execution:** The code execution engine currently utilizes Python's built-in `eval()` and `exec()`. While captured and redirected via `contextlib`, this poses a security risk if hosted on a public cloud since users can run arbitrary backend scripts. **For wide-scale public deployment, it is highly recommended to wrap `execute_python_code` (in `utils/code_executor.py`) within an isolated Docker container or restrict the execution environment.**

---

## 🛠 Tech Stack
- **Frontend / Fullstack:** Streamlit (Python)
- **Database:** SQLite3
- **Visualization:** CSS Grid, SVG Animations, Plotly
- **AI Integration:** `google-generativeai` (Gemini SDK), `openai` module (for LM Studio OpenAI-compatible local APIs)
- **Local Code Editor:** `streamlit-ace`

---

*Made with ❤️ for aspirants, students, and engineers everywhere.*
