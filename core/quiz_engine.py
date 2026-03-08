from utils.llm_client import ask_llm_json, ask_llm


def generate_quiz(topic: str, level: str, num_questions: int = 5,
                  language: str = "Python") -> list:
    """Generate MCQ quiz questions for a topic."""
    prompt = f"""
Generate {num_questions} multiple-choice quiz questions on "{topic}" for a {level} {language} learner.

Return JSON array:
[
  {{
    "question": "Question text",
    "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
    "correct_answer": "A",
    "explanation": "Why this is correct and others are wrong",
    "difficulty": "easy|medium|hard",
    "concept_tested": "specific concept being tested"
  }}
]

Rules:
- Mix difficulty levels ({"mostly easy" if level == "Beginner" else "mixed" if level == "Intermediate" else "mostly hard"})
- Include code-based questions where appropriate
- Make distractors plausible but clearly wrong on reflection
- Explanations should teach, not just state the answer

Return ONLY valid JSON array.
"""
    return ask_llm_json(prompt, temperature=0.5)


def evaluate_quiz(questions: list, user_answers: dict) -> dict:
    """Evaluate quiz answers and provide feedback."""
    results = []
    score = 0
    for i, q in enumerate(questions):
        user_ans = user_answers.get(str(i), "")
        is_correct = user_ans.strip().upper().startswith(q["correct_answer"].upper())
        if is_correct:
            score += 1
        results.append({
            "question": q["question"],
            "user_answer": user_ans,
            "correct_answer": q["correct_answer"],
            "is_correct": is_correct,
            "explanation": q["explanation"],
            "concept": q.get("concept_tested", "")
        })

    wrong_concepts = [r["concept"] for r in results if not r["is_correct"]]
    percentage = round(score / len(questions) * 100, 1) if questions else 0

    feedback = _get_quiz_feedback(percentage, wrong_concepts)

    return {
        "score": score,
        "total": len(questions),
        "percentage": percentage,
        "results": results,
        "weak_concepts": wrong_concepts,
        "feedback": feedback,
        "grade": _get_grade(percentage)
    }


def _get_grade(pct):
    if pct >= 90: return "🏆 Excellent"
    if pct >= 75: return "⭐ Good"
    if pct >= 60: return "✅ Pass"
    if pct >= 40: return "📖 Needs Review"
    return "🔄 Re-study Required"


def _get_quiz_feedback(pct, weak_concepts):
    if not weak_concepts:
        return "Outstanding! You've mastered this topic. Ready to move on!"
    prompt = f"""
A student scored {pct}% on a quiz. They struggled with: {", ".join(weak_concepts)}.
Give 2-3 sentences of encouraging, specific feedback on what to focus on next.
Be motivating. No markdown.
"""
    return ask_llm(prompt, temperature=0.6)


def generate_flashcards(topic: str, level: str, num: int = 8) -> list:
    """Generate flashcard-style Q&A pairs."""
    prompt = f"""
Generate {num} flashcard Q&A pairs for "{topic}" at {level} level.

Return JSON:
[
  {{"front": "Question or concept", "back": "Answer or explanation", "category": "definition|code|formula|concept"}}
]

Return ONLY valid JSON.
"""
    return ask_llm_json(prompt, temperature=0.4)
