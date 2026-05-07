import os
import logging
import anthropic
from openai import OpenAI

logger = logging.getLogger(__name__)

# Available model identifiers
MODEL_GPT4O = "gpt4o"
MODEL_CLAUDE = "claude"
MODEL_AUTO = "auto"  # Uses GPT-4o, falls back to Claude on failure

# Actual model strings
GPT4O_MODEL = "gpt-4o"
CLAUDE_MODEL = "claude-opus-4-5"


def _call_gpt4o(system: str, user: str, max_tokens: int, temperature: float) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=GPT4O_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _call_claude(system: str, user: str, max_tokens: int, temperature: float) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text.strip()


def chat_completion(
    system: str,
    user: str,
    model: str = MODEL_AUTO,
    max_tokens: int = 1024,
    temperature: float = 0.0,
) -> dict:
    """
    Unified chat completion interface for all agents.

    Args:
        system:      System prompt.
        user:        User message.
        model:       'gpt4o', 'claude', or 'auto' (GPT-4o with Claude fallback).
        max_tokens:  Max tokens for the response.
        temperature: Sampling temperature.

    Returns:
        dict with keys: success (bool), text (str), model_used (str), error (str)
    """
    if model == MODEL_GPT4O:
        try:
            text = _call_gpt4o(system, user, max_tokens, temperature)
            return {"success": True, "text": text, "model_used": GPT4O_MODEL, "error": ""}
        except Exception as e:
            logger.error(f"GPT-4o call failed: {e}")
            return {"success": False, "text": "", "model_used": GPT4O_MODEL, "error": str(e)}

    elif model == MODEL_CLAUDE:
        try:
            text = _call_claude(system, user, max_tokens, temperature)
            return {"success": True, "text": text, "model_used": CLAUDE_MODEL, "error": ""}
        except Exception as e:
            logger.error(f"Claude call failed: {e}")
            return {"success": False, "text": "", "model_used": CLAUDE_MODEL, "error": str(e)}

    else:
        # AUTO: try GPT-4o first, fall back to Claude
        try:
            text = _call_gpt4o(system, user, max_tokens, temperature)
            logger.info("Auto mode: GPT-4o succeeded.")
            return {"success": True, "text": text, "model_used": GPT4O_MODEL, "error": ""}
        except Exception as e:
            logger.warning(f"Auto mode: GPT-4o failed ({e}), falling back to Claude.")
            try:
                text = _call_claude(system, user, max_tokens, temperature)
                logger.info("Auto mode: Claude fallback succeeded.")
                return {"success": True, "text": text, "model_used": CLAUDE_MODEL, "error": ""}
            except Exception as e2:
                logger.error(f"Auto mode: Claude fallback also failed: {e2}")
                return {
                    "success": False,
                    "text": "",
                    "model_used": "none",
                    "error": f"GPT-4o: {e} | Claude: {e2}",
                }
