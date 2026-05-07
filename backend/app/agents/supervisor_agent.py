import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Confidence threshold: below this score the supervisor requests a retry
CONFIDENCE_THRESHOLD = 0.65

SUPERVISOR_SYSTEM_PROMPT = """You are a strict quality supervisor for an autonomous AI agent system.
You will receive:
1. The agent type that produced the output
2. The original task given to that agent
3. The output the agent produced

Your job is to evaluate the output and return a JSON object with exactly these keys:
{
  "score": <float between 0.0 and 1.0>,
  "verdict": <"approved" | "retry" | "escalate">,
  "reason": <one sentence explaining your verdict>,
  "suggestions": <one sentence on how to improve, or empty string if approved>
}

Scoring guide:
- 0.9 - 1.0: Output fully answers the task, no gaps
- 0.7 - 0.89: Output mostly answers the task, minor gaps
- 0.5 - 0.69: Output partially answers the task, significant gaps
- 0.0 - 0.49: Output fails to answer the task or is empty/irrelevant

Verdict rules:
- score >= 0.65: verdict = "approved"
- 0.35 <= score < 0.65: verdict = "retry"
- score < 0.35: verdict = "escalate"

Return ONLY the JSON object. No markdown, no explanation, no backticks."""


def _build_evaluation_prompt(agent_type: str, task: str, output: str) -> str:
    return (
        f"Agent type: {agent_type}\n\n"
        f"Original task:\n{task}\n\n"
        f"Agent output:\n{output}"
    )


def _parse_verdict(raw: str) -> dict:
    """Parse GPT-4o's JSON verdict safely."""
    try:
        # Strip any accidental markdown fences
        cleaned = raw.strip().strip("```json").strip("```").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse supervisor verdict JSON: {e}")
        return {
            "score": 0.0,
            "verdict": "escalate",
            "reason": "Supervisor could not parse evaluation response.",
            "suggestions": "Check supervisor prompt and model output format.",
        }


def run_supervisor_agent(
    agent_type: str,
    task: str,
    output: str,
) -> dict:
    """
    Evaluate the output of a specialist agent.

    Args:
        agent_type: Name of the agent that produced the output (e.g. 'web_search').
        task:       The original task string given to that agent.
        output:     The string output produced by that agent.

    Returns:
        dict with keys:
            success (bool)
            verdict (str): 'approved' | 'retry' | 'escalate'
            score (float): 0.0 to 1.0
            reason (str)
            suggestions (str)
            error (str)
    """
    if not output or not output.strip():
        return {
            "success": False,
            "verdict": "escalate",
            "score": 0.0,
            "reason": "Agent produced empty output.",
            "suggestions": "Check agent configuration and inputs.",
            "error": "Empty output received.",
        }

    try:
        prompt = _build_evaluation_prompt(agent_type, task, output)

        response = _get_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=300,
        )

        raw = response.choices[0].message.content
        verdict_data = _parse_verdict(raw)

        score = float(verdict_data.get("score", 0.0))
        verdict = verdict_data.get("verdict", "escalate")
        reason = verdict_data.get("reason", "")
        suggestions = verdict_data.get("suggestions", "")

        logger.info(
            f"Supervisor verdict for '{agent_type}': {verdict} "
            f"(score={score:.2f})"
        )

        return {
            "success": True,
            "verdict": verdict,
            "score": score,
            "reason": reason,
            "suggestions": suggestions,
            "error": "",
        }

    except Exception as e:
        logger.error(f"Supervisor agent failed: {str(e)}")
        return {
            "success": False,
            "verdict": "escalate",
            "score": 0.0,
            "reason": "Supervisor encountered an internal error.",
            "suggestions": "",
            "error": str(e),
        }