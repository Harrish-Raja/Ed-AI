import subprocess
import sys
import tempfile
import os
from utils.llm_client import ask_llm_json, ask_llm


def analyze_code(code: str, problem_description: str, language: str = "Python",
                 level: str = "Beginner") -> dict:
    """
    Analyze user's code for errors, give feedback, and suggest improvements.
    """
    prompt = f"""
You are an expert {language} error tutor. A {level} student wrote this code for the problem:
"{problem_description}"

Code:
```{language.lower()}
{code}
```

Analyze thoroughly and return JSON:
{{
  "has_errors": true/false,
  "error_type": "syntax|logic|runtime|none",
  "errors": [
    {{
      "line": <line_number or null>,
      "code_snippet": "the problematic code",
      "issue": "what's wrong",
      "fix": "how to fix it",
      "concept": "underlying concept to understand"
    }}
  ],
  "correctness": "correct|partially_correct|incorrect",
  "logic_analysis": "Analysis of the overall logic approach",
  "optimizations": ["optimization 1", "optimization 2"],
  "best_practices": ["best practice suggestion 1"],
  "fixed_code": "corrected and optimized {language} code if needed, else same code",
  "explanation": "friendly mentor-style explanation of all issues",
  "score": <0-100 based on correctness + code quality>,
  "encouragement": "encouraging message for the student"
}}

Be specific, educational, and kind. Return ONLY valid JSON.
"""
    return ask_llm_json(prompt, temperature=0.3)


def run_code_safely(code: str, stdin_input: str = "", timeout: int = 10) -> dict:
    """Execute Python code in a subprocess and return output."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                     delete=False, encoding='utf-8') as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "⏱️ Time Limit Exceeded (10s)", "returncode": -1, "success": False}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "success": False}
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


def explain_error_message(error_msg: str, code: str, level: str = "Beginner") -> str:
    """Explain a Python error message in simple terms."""
    prompt = f"""
A {level} Python student got this error:
{error_msg}

Their code:
{code[:500]}

Explain this error in simple terms:
1. What went wrong (1-2 sentences)
2. Why it happens (1-2 sentences)  
3. How to fix it (specific steps)

Be friendly and educational. Use plain text, no markdown.
"""
    return ask_llm(prompt, temperature=0.4)


def get_code_review(code: str, topic: str, language: str = "Python") -> dict:
    """Full code review with style and best practice suggestions."""
    prompt = f"""
Review this {language} code for {topic}:
```python
{code}
```

Return JSON:
{{
  "overall_quality": "poor|fair|good|excellent",
  "score": <0-100>,
  "style_issues": ["issue 1"],
  "performance_issues": ["issue 1"],
  "security_issues": ["issue 1"],
  "readability_score": <0-10>,
  "suggestions": ["suggestion for improvement"],
  "refactored_code": "cleaner version of the code",
  "summary": "2-3 sentence overall assessment"
}}

Return ONLY valid JSON.
"""
    return ask_llm_json(prompt, temperature=0.3)
