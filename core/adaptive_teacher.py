from utils.llm_client import ask_llm, ask_llm_json


def teach_topic(topic_name: str, level: str, language: str = "",
                context: str = "") -> dict:
    """
    Generate adaptive teaching content for a topic.
    Returns structured content with explanation, examples, and key points.
    """
    level_instructions = {
        "Beginner": """
- Use very simple language, avoid jargon
- Always start with a clear real-world analogy
- For coding topics: provide 4–6 detailed code examples with step-by-step explanation
- For theory topics: use diagrams described in text, bullet lists, and simple comparisons
- Use encouraging tone  ("Great job!", "You're on the right track!")
- Include common mistakes beginners make with explanations of WHY each is wrong
- Include at least 5 sections: Introduction, Core Concept, Detailed Explanation, 
  Practice Examples, Common Pitfalls, Summary
""",
        "Intermediate": """
- Assume basic concept knowledge, skip trivial definitions
- Focus on HOW and WHY: internals, tradeoffs, use-cases
- For coding topics: provide 3–4 examples ranging from basic to real-world practical
- Include performance considerations and when NOT to use this
- Mention 3–4 related concepts and how they connect
- Include at least 5 sections: Recap, Deep Dive, Implementation Details,
  Real-World Use Cases, Optimization Tips, Common Interview Points
""",
        "Advanced": """
- Skip basics completely; go straight to depth
- Focus on edge cases, language internals, memory/performance, production patterns
- For coding topics: provide 2–3 production-level examples with complexity analysis
- Include advanced patterns, anti-patterns, and tradeoffs
- Cover interview-level depth (system design angle if relevant)
- Include at least 6 sections: Expert Overview, Internal Mechanics, Edge Cases,
  Performance Analysis, Production Patterns, Interview Scenarios
"""
    }

    is_coding_topic = bool(language)  # empty string = theory topic
    code_field = f'"code_example": "complete runnable {language} code (minimum 15 lines, well commented)",' if is_coding_topic else '"code_example": null,'

    prompt = f"""
You are a world-class {language or "subject"} mentor teaching "{topic_name}" to a {level} student.

TEACHING STYLE RULES (STRICTLY FOLLOW):
{level_instructions.get(level, level_instructions["Intermediate"])}

ADDITIONAL CONTEXT:
{f"Context: {context}" if context else "No additional context."}

CRITICAL REQUIREMENTS:
- Each section MUST have at least 200 words of detailed content in markdown
- "overview" MUST be 4–6 sentences (not a summary — give real depth)
- Generate EXACTLY 5–7 sections covering the topic comprehensively
- Do NOT use placeholder text or generic descriptions
- Content must be educational, accurate, and specific to "{topic_name}"

Return ONLY this JSON structure (no markdown fences, no comments):
{{
  "topic": "{topic_name}",
  "level": "{level}",
  "language": "{language}",
  "estimated_read_mins": <5–20>,
  "overview": "4–6 sentence rich overview of {topic_name} — what it is, why it matters, how it fits",
  "analogy": "A clear, memorable real-world analogy that makes the concept click immediately",
  "sections": [
    {{
      "title": "Section Title",
      "content": "## Section Title\\n\\nDetailed markdown content (minimum 200 words). Use **bold**, bullet lists, numbered steps, and sub-headers where appropriate. Be thorough and educational.",
      {code_field}
      "explanation": "Detailed explanation of the code example above (what each part does, why it's written that way)"
    }}
  ],
  "key_points": [
    "Key takeaway 1 — specific and actionable",
    "Key takeaway 2",
    "Key takeaway 3",
    "Key takeaway 4",
    "Key takeaway 5"
  ],
  "common_mistakes": [
    "Mistake 1: description of mistake — and WHY it happens and how to avoid it",
    "Mistake 2",
    "Mistake 3"
  ],
  "interview_tips": [
    "Interview tip 1 — specific question or scenario",
    "Interview tip 2",
    "Interview tip 3"
  ],
  "next_topics": ["recommended topic 1", "recommended topic 2", "recommended topic 3"],
  "further_reading": [
    {{"title": "Resource name", "description": "What this covers and why it's valuable"}}
  ]
}}

Return ONLY valid JSON. No markdown fences. No trailing commas.
"""
    return ask_llm_json(prompt, temperature=0.4)



def get_quick_explanation(concept: str, level: str, language: str = "Python") -> str:
    """Get a quick 2-3 line explanation of a concept."""
    prompt = f"""
Explain "{concept}" in {language} in 2-3 simple sentences for a {level} learner.
Be direct and clear. No markdown.
"""
    return ask_llm(prompt, temperature=0.3)


def generate_practice_problem(topic: str, level: str, language: str = "Python",
                               difficulty: str = "medium") -> dict:
    """Generate a coding practice problem."""
    prompt = f"""
Create a {difficulty} difficulty coding problem for "{topic}" in {language}
suitable for a {level} learner.

Return JSON:
{{
  "title": "Problem Title",
  "description": "Full problem description",
  "examples": [
    {{"input": "example input", "output": "expected output", "explanation": "why"}}
  ],
  "constraints": ["constraint 1", "constraint 2"],
  "hints": ["hint 1", "hint 2"],
  "starter_code": "# starter code template in {language}",
  "solution": "# complete solution with comments",
  "time_complexity": "O(?)",
  "space_complexity": "O(?)",
  "tags": ["tag1", "tag2"]
}}

Return ONLY valid JSON.
"""
    return ask_llm_json(prompt, temperature=0.4)
