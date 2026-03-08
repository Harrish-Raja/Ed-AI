import os
import re
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ── Cached clients ─────────────────────────────────────────
_gemini_model = None
_lm_client = None


# ── Backend detection ──────────────────────────────────────
def _get_backend() -> str:
    return os.getenv("EDAI_BACKEND", "gemini").lower()


# ══════════════════════════════════════════════════════════
# JSON REPAIR  — handles all common LLM JSON quirks
# ══════════════════════════════════════════════════════════
def _repair_and_parse_json(raw: str) -> dict | list:
    """
    Attempt to coerce LLM output into valid JSON using a series of
    progressively more aggressive repair steps.
    Raises json.JSONDecodeError only if every step fails.
    """
    text = raw.strip()

    # Step 1 — strip leading/trailing markdown fences
    # ```json ... ``` or ``` ... ```
    text = re.sub(r'^```[a-zA-Z]*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    text = text.strip()

    # Also strip single-backtick wrapping
    if text.startswith("`") and text.endswith("`"):
        text = text[1:-1].strip()

    # Step 2 — try direct parse first (fast path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 3 — remove JS-style single-line and block comments
    text = re.sub(r'//[^\n]*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 4 — fix trailing commas before ] or }
    text = re.sub(r',\s*([\]}])', r'\1', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 5 — replace Python literals with JSON literals
    text = re.sub(r'\bNone\b', 'null', text)
    text = re.sub(r'\bTrue\b', 'true', text)
    text = re.sub(r'\bFalse\b', 'false', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 6 — fix single-quoted strings → double-quoted
    # Only replace quotes that are actually string delimiters, not apostrophes
    text = re.sub(r"(?<![\\])'", '"', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 7 — truncated JSON: find the last valid closing brace/bracket
    # and append missing closers
    for end_char, close in [('}', '}'), (']', ']')]:
        idx = text.rfind(end_char)
        if idx != -1:
            candidate = text[:idx + 1]
            # Count open vs closed braces/brackets
            open_b   = candidate.count('{') - candidate.count('}')
            open_sq  = candidate.count('[') - candidate.count(']')
            candidate += ']' * max(0, open_sq) + '}' * max(0, open_b)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    # Step 8 — extract first JSON object or array from mixed text
    for pattern in (r'\{.*\}', r'\[.*\]'):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass

    # All steps exhausted — re-raise with the cleaned text for debugging
    raise json.JSONDecodeError(
        f"Could not repair LLM JSON output (first 300 chars): {text[:300]}",
        text, 0
    )


# ══════════════════════════════════════════════════════════
# Gemini backend
# ══════════════════════════════════════════════════════════
def _get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set. Configure it in ⚙️ Settings.")
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel("gemini-2.0-flash")
    return _gemini_model


def _ask_gemini(prompt: str, temperature: float = 0.7, json_mode: bool = False) -> str:
    model = _get_gemini_model()
    cfg = genai.types.GenerationConfig(
        temperature=temperature,
        **({"response_mime_type": "application/json"} if json_mode else {})
    )
    response = model.generate_content(prompt, generation_config=cfg)
    return response.text.strip()


# ══════════════════════════════════════════════════════════
# LM Studio backend (OpenAI-compatible local API)
# ══════════════════════════════════════════════════════════
def _get_lm_client():
    global _lm_client
    if _lm_client is None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
        base_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        _lm_client = OpenAI(base_url=base_url, api_key="lm-studio")
    return _lm_client


def _ask_lmstudio(prompt: str, temperature: float = 0.7,
                  json_mode: bool = False, max_tokens: int = 8192) -> str:
    client = _get_lm_client()
    model_name = os.getenv("LM_STUDIO_MODEL", "local-model")

    messages = (
        [
            {"role": "system",
             "content": "You are a helpful assistant. Respond ONLY with valid JSON. "
                        "No markdown fences, no commentary, just the raw JSON object."},
            {"role": "user", "content": prompt},
        ]
        if json_mode
        else [{"role": "user", "content": prompt}]
    )

    response = _get_lm_client().chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════
# Public interface
# ══════════════════════════════════════════════════════════
def ask_llm(prompt: str, temperature: float = 0.7, json_mode: bool = False) -> str:
    """Send a prompt to the active backend and return raw text."""
    if _get_backend() == "lmstudio":
        return _ask_lmstudio(prompt, temperature, json_mode)
    return _ask_gemini(prompt, temperature, json_mode)


def ask_llm_json(prompt: str, temperature: float = 0.4,
                 retry_on_fail: bool = True) -> dict | list:
    """
    Ask LLM for JSON, repair common LLM JSON output issues, then parse.
    On failure, optionally retries once with a stricter minimal prompt.
    """
    raw = ask_llm(prompt, temperature=temperature, json_mode=True)

    try:
        return _repair_and_parse_json(raw)
    except (json.JSONDecodeError, ValueError) as first_err:
        if not retry_on_fail:
            raise

        # ── Retry: ask again with a much stricter, compact instruction ──────
        retry_prompt = (
            "Your previous response was not valid JSON. "
            "Return ONLY a valid JSON object — no markdown, no comments, no trailing commas. "
            "Here is the original task:\n\n" + prompt
        )
        raw2 = ask_llm(retry_prompt, temperature=0.1, json_mode=True)
        try:
            return _repair_and_parse_json(raw2)
        except (json.JSONDecodeError, ValueError):
            # Both attempts failed — re-raise the original error with context
            raise json.JSONDecodeError(
                f"LLM returned invalid JSON after 2 attempts. "
                f"First 200 chars of last response: {raw2[:200]}",
                raw2, 0
            ) from first_err


def reload_model():
    """Clear cached clients so the next call re-initialises."""
    global _gemini_model, _lm_client
    _gemini_model = None
    _lm_client = None
