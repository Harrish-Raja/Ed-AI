@echo off
echo Starting EdAI - AI Coding Study Planner...
cd /d "%~dp0"
python -m streamlit run app.py --server.port 8505
