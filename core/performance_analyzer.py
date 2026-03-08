from utils.llm_client import ask_llm
import pandas as pd
from datetime import datetime, timedelta


def generate_growth_report(user: dict, perf_data: list, quiz_data: list,
                            code_data: list, topics: list,
                            period: str = "weekly") -> str:
    """Generate an AI-written growth report."""
    # Compute stats
    total_study = sum(p.get("study_mins", 0) for p in perf_data)
    avg_quiz = sum(p.get("quiz_accuracy", 0) for p in perf_data) / max(len(perf_data), 1)
    total_xp = sum(p.get("xp_earned", 0) for p in perf_data)
    completed = [t for t in topics if t.get("status") == "completed"]
    
    prompt = f"""
You are a supportive AI mentor writing a {period} growth report for a student.

Student: {user.get('name', 'Student')}
Topic: {user.get('target_goal', 'Programming')}
Level: {user.get('level', 'Beginner')}

{period.title()} Stats:
- Total study time: {total_study:.0f} minutes
- Topics completed: {len(completed)} / {len(topics)}
- Average quiz score: {avg_quiz:.1f}%
- XP earned: {total_xp}
- Study sessions: {len(perf_data)} days

Write a warm, specific, and motivating {period} growth report (200-300 words) that:
1. Celebrates their progress and effort
2. Highlights 2-3 specific strengths based on their data
3. Identifies 1-2 areas to focus on
4. Gives 3 actionable next steps
5. Ends with an inspiring message

Use second-person ("you", "your"). Be specific, not generic.
Format with clear sections using ** for bold headers.
"""
    return ask_llm(prompt, temperature=0.7)


def compute_skill_radar(topics: list, quiz_data: list) -> dict:
    """Compute skill mastery scores for radar chart."""
    skill_map = {}
    for t in topics:
        name = t.get("topic_name", "")
        mastery = t.get("mastery_pct", 0)
        if name:
            skill_map[name] = mastery

    # Boost from quiz performance
    for q in quiz_data:
        tname = q.get("topic_name", "")
        if tname in skill_map:
            skill_map[tname] = min(100, skill_map[tname] + q.get("percentage", 0) * 0.2)

    return skill_map


def identify_weak_areas(topics: list, quiz_data: list) -> list:
    """Identify topics that need more attention."""
    weak = []
    for t in topics:
        mastery = t.get("mastery_pct", 0)
        if mastery < 50 and t.get("status") in ["available", "in_progress", "completed"]:
            weak.append({
                "topic": t.get("topic_name"),
                "mastery": mastery,
                "status": t.get("status")
            })

    # Add from quiz failures
    topic_quiz_scores = {}
    for q in quiz_data:
        tn = q.get("topic_name", "")
        scores = topic_quiz_scores.get(tn, [])
        scores.append(q.get("percentage", 0))
        topic_quiz_scores[tn] = scores

    for tn, scores in topic_quiz_scores.items():
        avg = sum(scores) / len(scores)
        if avg < 60:
            exists = any(w["topic"] == tn for w in weak)
            if not exists:
                weak.append({"topic": tn, "mastery": avg, "status": "needs_review"})

    return sorted(weak, key=lambda x: x["mastery"])[:10]


def compute_learning_streak(perf_data: list) -> int:
    """Compute current learning streak in days."""
    if not perf_data:
        return 0
    dates = sorted([p.get("date", "") for p in perf_data], reverse=True)
    today = datetime.now().date()
    streak = 0
    for i, d in enumerate(dates):
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            expected = today - timedelta(days=i)
            if dt == expected:
                streak += 1
            else:
                break
        except:
            break
    return streak


def compute_xp_level(total_xp: int) -> tuple:
    """Compute student level title and progress to next level from XP."""
    levels = [
        (0, "🌱 Seedling"),
        (100, "📚 Explorer"),
        (300, "⚡ Learner"),
        (600, "🔥 Practitioner"),
        (1000, "💎 Developer"),
        (1500, "🚀 Engineer"),
        (2500, "🏆 Expert"),
        (5000, "👑 Master"),
    ]
    current_level = levels[0]
    next_level = levels[1] if len(levels) > 1 else None
    for i, (xp_req, title) in enumerate(levels):
        if total_xp >= xp_req:
            current_level = (xp_req, title)
            next_level = levels[i + 1] if i + 1 < len(levels) else None

    if next_level:
        progress = (total_xp - current_level[0]) / (next_level[0] - current_level[0]) * 100
    else:
        progress = 100

    return current_level[1], min(100, progress), next_level[1] if next_level else "MAX"
