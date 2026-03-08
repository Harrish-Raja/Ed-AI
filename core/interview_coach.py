from utils.llm_client import ask_llm_json, ask_llm


def generate_interview_questions(topic: str, job_role: str, level: str,
                                  num_questions: int = 10) -> list:
    """Generate interview questions for a topic and job role."""
    prompt = f"""
Generate {num_questions} interview questions for "{topic}" for a "{job_role}" position.
Candidate level: {level}

Return JSON array:
[
  {{
    "question": "Interview question",
    "type": "conceptual|coding|behavioral|system_design",
    "difficulty": "easy|medium|hard",
    "expected_answer": "Key points expected in the answer",
    "follow_up": "Possible follow-up question",
    "category": "{topic}",
    "why_asked": "Why interviewers ask this"
  }}
]

Mix types: 40% conceptual, 40% coding, 10% behavioral, 10% system design.
Return ONLY valid JSON.
"""
    return ask_llm_json(prompt, temperature=0.4)


def evaluate_interview_answer(question: str, answer: str, expected: str,
                               level: str) -> dict:
    """Evaluate a candidate's answer to an interview question."""
    prompt = f"""
Evaluate this interview answer:

Question: {question}
Candidate's Answer: {answer}
Expected key points: {expected}
Level: {level}

Return JSON:
{{
  "score": <0-10>,
  "coverage": "How well they covered the expected points",
  "strengths": ["what they got right"],
  "gaps": ["what was missing"],
  "improved_answer": "A model answer that combines their answer with missing points",
  "tips": "Specific advice to improve this answer",
  "verdict": "strong|adequate|needs_improvement"
}}

Be encouraging but honest. Return ONLY valid JSON.
"""
    return ask_llm_json(prompt, temperature=0.4)


def get_job_readiness_report(topic: str, quiz_scores: list, code_scores: list,
                              interview_scores: list, level: str) -> dict:
    """Generate a job readiness report."""
    avg_quiz = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
    avg_code = sum(code_scores) / len(code_scores) if code_scores else 0
    avg_interview = sum(interview_scores) / len(interview_scores) if interview_scores else 0
    overall = (avg_quiz * 0.3 + avg_code * 0.4 + avg_interview * 0.3)

    prompt = f"""
A student is learning {topic} at {level} level. Their performance:
- Quiz average: {avg_quiz:.1f}%
- Code challenge average: {avg_code:.1f}%
- Interview practice average: {avg_interview:.1f}/10
- Overall readiness: {overall:.1f}%

Assess their job readiness and return JSON:
{{
  "readiness_score": {overall:.1f},
  "readiness_level": "Not Ready|Learning|Developing|Job Ready|Senior Ready",
  "suitable_roles": [
    {{"role": "Job Title", "match_pct": 75, "company_examples": ["Company1"]}}
  ],
  "strengths": ["identified strength 1"],
  "improvement_areas": ["area to improve"],
  "action_plan": ["specific action 1", "specific action 2"],
  "estimated_ready_in": "time estimate to be job ready",
  "salary_range": "estimated salary range for junior/mid roles",
  "message": "encouraging personalized message"
}}

Return ONLY valid JSON.
"""
    return ask_llm_json(prompt, temperature=0.4)


def get_mock_interview_response(question: str, answer: str, conversation_history: list,
                                 topic: str) -> str:
    """Simulate an interviewer response in a mock interview."""
    history_text = "\n".join([
        f"Interviewer: {h['q']}\nCandidate: {h['a']}"
        for h in conversation_history[-3:]
    ])

    prompt = f"""
You are a friendly but professional technical interviewer conducting a mock interview about {topic}.

Previous conversation:
{history_text}

You just asked: {question}
Candidate answered: {answer}

Respond as the interviewer would:
- Acknowledge their answer briefly
- Ask a natural follow-up OR transition to the next topic
- Keep it conversational
- If the answer was wrong, guide them without directly giving the answer
- 2-4 sentences maximum

Just write the interviewer's response text, nothing else.
"""
    return ask_llm(prompt, temperature=0.7)
