import os
import json
import logging
import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool registry
# Each entry describes one MCP-compatible tool available to agents.
# "builtin" tools are executed locally; "remote" tools call an MCP server URL.
# ---------------------------------------------------------------------------
TOOL_REGISTRY: dict[str, dict] = {
    "web_fetch": {
        "description": "Fetch the raw text content of a URL.",
        "type": "builtin",
        "parameters": ["url"],
    },
    "json_parse": {
        "description": "Parse a JSON string and return a Python dict.",
        "type": "builtin",
        "parameters": ["json_string"],
    },
    "text_length": {
        "description": "Return the character count of a text string.",
        "type": "builtin",
        "parameters": ["text"],
    },
}


# ---------------------------------------------------------------------------
# Builtin tool implementations
# ---------------------------------------------------------------------------

def _tool_web_fetch(args: dict) -> dict:
    url = args.get("url", "").strip()
    if not url:
        return {"success": False, "result": "", "error": "No URL provided."}
    try:
        response = httpx.get(url, timeout=10, follow_redirects=True)
        text = response.text[:4000]  # Cap at 4000 chars for agent context
        return {"success": True, "result": text, "error": ""}
    except Exception as e:
        return {"success": False, "result": "", "error": str(e)}


def _tool_json_parse(args: dict) -> dict:
    raw = args.get("json_string", "")
    try:
        parsed = json.loads(raw)
        return {"success": True, "result": parsed, "error": ""}
    except json.JSONDecodeError as e:
        return {"success": False, "result": {}, "error": str(e)}


def _tool_text_length(args: dict) -> dict:
    text = args.get("text", "")
    return {"success": True, "result": len(text), "error": ""}


# Map tool names to their implementation functions
BUILTIN_HANDLERS = {
    "web_fetch": _tool_web_fetch,
    "json_parse": _tool_json_parse,
    "text_length": _tool_text_length,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_tools() -> list[dict]:
    """
    Return all registered MCP tools with their descriptions and parameters.
    Agents use this to discover what tools are available.
    """
    return [
        {
            "name": name,
            "description": meta["description"],
            "parameters": meta["parameters"],
            "type": meta["type"],
        }
        for name, meta in TOOL_REGISTRY.items()
    ]


def call_tool(tool_name: str, args: dict) -> dict:
    """
    Execute an MCP tool by name with the given arguments.

    Args:
        tool_name: Name of the tool to call (must exist in TOOL_REGISTRY).
        args:      Dict of arguments matching the tool's parameter list.

    Returns:
        dict with keys: success (bool), result (any), error (str)
    """
    if tool_name not in TOOL_REGISTRY:
        return {
            "success": False,
            "result": None,
            "error": f"Tool '{tool_name}' not found in registry.",
        }

    tool_meta = TOOL_REGISTRY[tool_name]

    # Validate required parameters
    missing = [p for p in tool_meta["parameters"] if p not in args]
    if missing:
        return {
            "success": False,
            "result": None,
            "error": f"Missing required parameters: {missing}",
        }

    tool_type = tool_meta.get("type", "builtin")

    if tool_type == "builtin":
        handler = BUILTIN_HANDLERS.get(tool_name)
        if not handler:
            return {
                "success": False,
                "result": None,
                "error": f"No handler registered for builtin tool '{tool_name}'.",
            }
        logger.info(f"MCP: executing builtin tool '{tool_name}'")
        return handler(args)

    elif tool_type == "remote":
        # Placeholder for real MCP server calls
        server_url = tool_meta.get("server_url", "")
        if not server_url:
            return {
                "success": False,
                "result": None,
                "error": f"Remote tool '{tool_name}' has no server_url configured.",
            }
        try:
            response = httpx.post(
                server_url,
                json={"tool": tool_name, "args": args},
                timeout=15,
            )
            data = response.json()
            return {
                "success": data.get("success", False),
                "result": data.get("result"),
                "error": data.get("error", ""),
            }
        except Exception as e:
            return {"success": False, "result": None, "error": str(e)}

    return {
        "success": False,
        "result": None,
        "error": f"Unknown tool type '{tool_type}'.",
    }


def register_tool(name: str, description: str, parameters: list[str], tool_type: str = "builtin", **kwargs) -> None:
    """
    Dynamically register a new MCP tool at runtime.
    Used when connecting to external MCP servers.
    """
    TOOL_REGISTRY[name] = {
        "description": description,
        "type": tool_type,
        "parameters": parameters,
        **kwargs,
    }
    logger.info(f"MCP: registered tool '{name}' (type={tool_type})")
