import subprocess
import sys
import tempfile
import os
from openai import OpenAI


def _get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Blocklist: imports that are never allowed inside sandboxed code
BLOCKED_IMPORTS = [
    "os.system", "subprocess", "shutil.rmtree", "socket",
    "requests", "httpx", "urllib", "ftplib", "smtplib",
    "__import__", "eval(", "exec(", "open(",
]

SYSTEM_PROMPT = """You are a Python code writer. 
The user will give you a task. Write Python code to solve it.
Return ONLY the raw Python code. No markdown, no explanation, no backticks.
The code must print its final result using print().
Only use Python standard library modules (math, json, csv, statistics, datetime, itertools, collections, re, string).
Do NOT use requests, subprocess, os.system, socket, or any network/file-system-destructive calls."""


def _is_safe(code: str) -> tuple[bool, str]:
    """Check code against the blocklist before execution."""
    for blocked in BLOCKED_IMPORTS:
        if blocked in code:
            return False, f"Blocked pattern detected: '{blocked}'"
    return True, ""


def _generate_code(task: str) -> str:
    """Ask GPT-4o to write Python code for the given task."""
    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ],
        temperature=0,
        max_tokens=1000,
    )
    return response.choices[0].message.content.strip()


def _run_code(code: str, timeout: int = 10) -> dict:
    """Write code to a temp file and run it in a subprocess with timeout."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds.",
            "returncode": -1,
        }
    finally:
        os.unlink(tmp_path)


def run_code_execution_agent(task: str) -> dict:
    """
    Main entry point for the code execution agent.
    
    Args:
        task: Natural language description of what to compute or analyze.
    
    Returns:
        dict with keys: success (bool), output (str), code (str), error (str)
    """
    try:
        # Step 1: Generate code
        code = _generate_code(task)

        # Step 2: Safety check
        is_safe, reason = _is_safe(code)
        if not is_safe:
            return {
                "success": False,
                "output": "",
                "code": code,
                "error": f"Safety check failed: {reason}",
            }

        # Step 3: Execute
        result = _run_code(code)

        if result["returncode"] == 0:
            return {
                "success": True,
                "output": result["stdout"],
                "code": code,
                "error": "",
            }
        else:
            return {
                "success": False,
                "output": result["stdout"],
                "code": code,
                "error": result["stderr"] or "Unknown execution error.",
            }

    except Exception as e:
        return {
            "success": False,
            "output": "",
            "code": "",
            "error": str(e),
        }