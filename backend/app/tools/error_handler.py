import time
import logging
import traceback
from typing import Callable, Any

logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 2.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0


def safe_execute(fn: Callable, *args, context: str = "", **kwargs) -> dict:
    """
    Execute a callable and catch all exceptions.
    Always returns a structured dict, never raises.

    Args:
        fn:      The function to call.
        *args:   Positional arguments for fn.
        context: Human-readable label for logging (e.g. 'web_search_agent').
        **kwargs: Keyword arguments for fn.

    Returns:
        dict with keys: success (bool), result (any), error (str)
    """
    label = context or fn.__name__
    try:
        result = fn(*args, **kwargs)
        return {"success": True, "result": result, "error": ""}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{label}] Unhandled exception: {error_msg}")
        logger.debug(traceback.format_exc())
        return {"success": False, "result": None, "error": error_msg}


def with_retry(
    fn: Callable,
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    context: str = "",
    **kwargs,
) -> dict:
    """
    Execute a callable with automatic retries and exponential backoff.
    Returns on first success. After all retries exhausted, returns the last error.

    Args:
        fn:                 The function to call.
        *args:              Positional arguments for fn.
        max_retries:        Maximum number of attempts (including first try).
        backoff_seconds:    Initial wait time between retries in seconds.
        backoff_multiplier: Multiply backoff by this value after each retry.
        context:            Human-readable label for logging.
        **kwargs:           Keyword arguments for fn.

    Returns:
        dict with keys: success (bool), result (any), error (str), attempts (int)
    """
    label = context or fn.__name__
    last_error = ""
    wait = backoff_seconds

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[{label}] Attempt {attempt}/{max_retries}")
            result = fn(*args, **kwargs)

            # If the function itself returns a dict with success=False, treat as failure
            if isinstance(result, dict) and result.get("success") is False:
                last_error = result.get("error", "Agent returned success=False")
                logger.warning(f"[{label}] Attempt {attempt} returned failure: {last_error}")
                if attempt < max_retries:
                    logger.info(f"[{label}] Retrying in {wait:.1f}s...")
                    time.sleep(wait)
                    wait *= backoff_multiplier
                continue

            logger.info(f"[{label}] Succeeded on attempt {attempt}")
            return {"success": True, "result": result, "error": "", "attempts": attempt}

        except Exception as e:
            last_error = str(e)
            logger.warning(f"[{label}] Attempt {attempt} raised exception: {last_error}")
            logger.debug(traceback.format_exc())
            if attempt < max_retries:
                logger.info(f"[{label}] Retrying in {wait:.1f}s...")
                time.sleep(wait)
                wait *= backoff_multiplier

    logger.error(f"[{label}] All {max_retries} attempts failed. Last error: {last_error}")
    return {
        "success": False,
        "result": None,
        "error": last_error,
        "attempts": max_retries,
    }


def format_error(agent: str, step: int, error: str, recoverable: bool = True) -> dict:
    """
    Return a standardized error record for the orchestrator step log.

    Args:
        agent:       Name of the agent that failed.
        step:        Step number in the execution plan.
        error:       Error message string.
        recoverable: Whether the orchestrator should retry this step.

    Returns:
        Structured error dict.
    """
    return {
        "agent": agent,
        "step": step,
        "error": error,
        "recoverable": recoverable,
    }
