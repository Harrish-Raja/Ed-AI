import json
from utils.llm_client import ask_llm_json, ask_llm


def generate_roadmap(topic: str, goal: str, level: str, daily_hours: float,
                     duration_weeks: int, language: str = "Python") -> dict:
    """
    Generate a complete learning roadmap in two passes:
    Pass 1 — compact skeleton (always fast, always fits token window)
    Pass 2 — enrich with descriptions/resources on the Roadmap page on demand
    Falls back to a minimal stub if the LLM still fails.
    """
    # ── Compute a realistic number of topics to avoid token explosion ──────
    # ~daily_hours * 1.5 topics/day, max 4 topics/day regardless of hours
    topics_per_day = min(4, max(1, round(daily_hours * 1.5)))
    total_days     = duration_weeks * 5  # Mon-Fri only
    approx_total   = total_days * topics_per_day

    prompt = f"""You are an expert curriculum designer.
Generate a structured learning roadmap as a SINGLE valid JSON object.

STRICT RULES:
- Return ONLY the JSON object. No markdown, no code fences, no comments.
- All strings use double quotes.
- No trailing commas.
- Keep descriptions SHORT (max 10 words each) to stay within token limits.
- Generate exactly {duration_weeks} weeks, 5 days per week.
- Each day has {topics_per_day} topic(s) at most.

INPUT:
Topic: {topic}
Goal: {goal}
Level: {level}
Daily hours: {daily_hours}
Duration: {duration_weeks} weeks
Language: {language}

OUTPUT SCHEMA (fill in the real data):
{{
  "title": "string",
  "description": "string (1 sentence)",
  "total_topics": {approx_total},
  "prerequisites": ["string"],
  "skills_gained": ["string"],
  "weeks": [
    {{
      "week": 1,
      "theme": "string",
      "goal": "string (1 sentence)",
      "days": [
        {{
          "day": 1,
          "topics": [
            {{
              "name": "string",
              "description": "string (max 10 words)",
              "type": "concept",
              "estimated_hours": 1.5,
              "interview_relevance": "high"
            }}
          ]
        }}
      ]
    }}
  ],
  "milestones": [
    {{"week": 2, "milestone": "string"}}
  ],
  "interview_topics": ["string"],
  "project_ideas": ["string", "string", "string"]
}}

Level guidance: {
    "Start from absolute basics with simple names." if level == "Beginner"
    else "Balance theory and practical exercises."   if level == "Intermediate"
    else "Focus on advanced patterns and architecture."
}

NOW generate the roadmap JSON for: {topic}
"""

    try:
        result = ask_llm_json(prompt, temperature=0.2, retry_on_fail=True)
        # Ensure required keys exist
        result.setdefault("title",        f"{topic} Learning Roadmap")
        result.setdefault("description",  f"Master {topic} in {duration_weeks} weeks")
        result.setdefault("total_topics", approx_total)
        result.setdefault("prerequisites",   [])
        result.setdefault("skills_gained",   [topic])
        result.setdefault("milestones",      [])
        result.setdefault("interview_topics",[topic])
        result.setdefault("project_ideas",   [f"Build a {topic} project"])
        result.setdefault("weeks",           [])
        return result

    except Exception as e:
        # ── Ultimate fallback: return a minimal stub so the UI doesn't crash ─
        return _build_fallback_roadmap(topic, goal, level, daily_hours,
                                       duration_weeks, language, str(e))


def _build_fallback_roadmap(topic, goal, level, daily_hours,
                             duration_weeks, language, error_msg) -> dict:
    """Return a minimal but functional roadmap when the LLM fails entirely."""
    weeks = []
    base_topics = [
        f"{topic} Introduction",
        f"{topic} Core Concepts",
        f"{topic} Intermediate Techniques",
        f"{topic} Advanced Patterns",
        f"{topic} Project & Practice",
        f"{topic} Review & Quiz",
    ]
    for w in range(1, duration_weeks + 1):
        days = []
        for d in range(1, 6):
            idx = ((w - 1) * 5 + (d - 1)) % len(base_topics)
            days.append({
                "day": d,
                "topics": [{
                    "name": f"{base_topics[idx]} (Week {w})",
                    "description": f"Study {base_topics[idx]}",
                    "type": "concept",
                    "estimated_hours": daily_hours,
                    "interview_relevance": "medium"
                }]
            })
        weeks.append({
            "week": w,
            "theme": f"Week {w}: {base_topics[(w-1) % len(base_topics)]}",
            "goal": f"Complete week {w} of {topic}",
            "days": days
        })

    return {
        "title": f"{topic} — {duration_weeks}-Week Roadmap",
        "description": (
            f"A structured {duration_weeks}-week plan to learn {topic} "
            f"for {goal}. (Auto-generated — AI returned invalid JSON: {error_msg[:80]})"
        ),
        "total_topics": duration_weeks * 5,
        "prerequisites": [],
        "skills_gained": [topic, language],
        "weeks": weeks,
        "milestones": [
            {"week": max(1, duration_weeks // 2), "milestone": f"Midpoint review of {topic}"},
            {"week": duration_weeks, "milestone": f"Complete {topic} roadmap"},
        ],
        "interview_topics": [f"{topic} core concepts", "Problem solving", "Code review"],
        "project_ideas": [
            f"Simple {topic} demo",
            f"Intermediate {topic} application",
            f"Full {topic} capstone project",
        ],
    }


def get_topic_summary(topic: str, level: str) -> str:
    """Get a brief summary/overview of a topic."""
    prompt = (
        f'In 3-4 sentences, explain what "{topic}" is and why it matters '
        f"for a {level} learner. Be encouraging and clear. No markdown."
    )
    return ask_llm(prompt, temperature=0.5)


def get_daily_plan(roadmap: dict, current_week: int, current_day: int) -> dict:
    """Extract today's plan from a saved roadmap dict."""
    for w in roadmap.get("weeks", []):
        if w.get("week") == current_week:
            for d in w.get("days", []):
                if d.get("day") == current_day:
                    return d
    return {}
