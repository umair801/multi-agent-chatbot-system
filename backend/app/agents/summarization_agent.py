import os
import logging
import anthropic

logger = logging.getLogger(__name__)

# Summary mode prompts
SUMMARY_MODES = {
    "executive": (
        "You are an expert analyst. Produce a concise executive summary in 3-5 sentences. "
        "Focus on the key finding, its significance, and any recommended action. "
        "Write in clear, professional prose. No bullet points."
    ),
    "bullet": (
        "You are an expert analyst. Summarize the content as a structured bullet list. "
        "Use 5-8 bullets. Each bullet must be a single clear sentence. "
        "Start each bullet with a strong action or finding word."
    ),
    "detailed": (
        "You are an expert analyst. Write a detailed summary with the following sections: "
        "Overview, Key Findings, Supporting Details, and Conclusion. "
        "Use clear headings. Be thorough but avoid redundancy."
    ),
    "technical": (
        "You are a senior engineer. Summarize the content with a focus on technical details, "
        "methods, tools, and implementation specifics. Use precise terminology. "
        "Suitable for a technical audience."
    ),
}

DEFAULT_MODE = "executive"


def run_summarization_agent(
    content: str,
    instruction: str = "",
    mode: str = DEFAULT_MODE,
    max_tokens: int = 1024,
) -> dict:
    """
    Summarize content using the Claude API.

    Args:
        content:     Raw text to summarize.
        instruction: Optional extra instruction appended to the system prompt.
        mode:        One of 'executive', 'bullet', 'detailed', 'technical'.
        max_tokens:  Max tokens for the Claude response.

    Returns:
        dict with keys: success (bool), summary (str), mode (str), error (str)
    """
    if not content or not content.strip():
        return {
            "success": False,
            "summary": "",
            "mode": mode,
            "error": "No content provided for summarization.",
        }

    # Resolve mode
    if mode not in SUMMARY_MODES:
        logger.warning(f"Unknown mode '{mode}', falling back to '{DEFAULT_MODE}'")
        mode = DEFAULT_MODE

    system_prompt = SUMMARY_MODES[mode]
    if instruction:
        system_prompt += f"\n\nAdditional instruction: {instruction}"

    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set in environment.")

        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Please summarize the following content:\n\n{content}",
                }
            ],
        )

        summary = message.content[0].text.strip()
        logger.info(f"Summarization complete. Mode: {mode}, chars: {len(summary)}")

        return {
            "success": True,
            "summary": summary,
            "mode": mode,
            "error": "",
        }

    except Exception as e:
        logger.error(f"Summarization agent failed: {str(e)}")
        return {
            "success": False,
            "summary": "",
            "mode": mode,
            "error": str(e),
        }