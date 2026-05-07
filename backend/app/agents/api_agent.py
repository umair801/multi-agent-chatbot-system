import os
import logging
import asyncio
from typing import Any
from dotenv import load_dotenv
from app.agents.api_integration_agent import APIConnectorConfig, AuthMethod, APIIntegrationError
from app.agents.rest_connector import RESTConnector

load_dotenv()
logger = logging.getLogger(__name__)


def _load_connector(prefix: str) -> RESTConnector:
    """
    Load a REST connector from environment variables using prefix.
    Initialized inside function — never at module level.
    """
    config = APIConnectorConfig.from_env(prefix)
    return RESTConnector(config)


async def run_api_agent(task: str, connector_prefix: str = "CONNECTOR_CRM") -> dict:
    """
    Execute an API task using the configured connector.

    The planner passes a natural language task string.
    This agent parses the intent (GET vs POST) and calls the connector.

    Args:
        task:             Natural language instruction from the planner
        connector_prefix: .env prefix for the connector to use

    Returns:
        dict with keys: success, output, raw_data, connector
    """
    logger.info(f"API agent task: '{task}' using connector: {connector_prefix}")

    connector = _load_connector(connector_prefix)

    validation = connector.validate_config()
    if not validation["valid"]:
        return {
            "success": False,
            "output": f"Connector '{connector_prefix}' is not configured: {validation['issues']}",
            "raw_data": {},
            "connector": connector_prefix,
        }

    # Determine method and endpoint from task string
    task_lower = task.lower()
    method = "GET"
    if any(w in task_lower for w in ["create", "post", "send", "submit", "add", "insert"]):
        method = "POST"

    # Extract endpoint hint from task — default to root
    endpoint = "/"
    for segment in ["/users", "/leads", "/contacts", "/tasks", "/data", "/records", "/weather"]:
        if segment.replace("/", "") in task_lower:
            endpoint = segment
            break

    try:
        if method == "GET":
            result = await connector.get(endpoint)
        else:
            result = await connector.post(endpoint, payload={"task": task})

        raw = result.get("data", {})

        # Format output as readable summary
        if isinstance(raw, dict):
            output = f"API call to {connector.config.name} succeeded.\n"
            output += f"Endpoint: {endpoint}\n"
            output += f"Status: {result.get('status_code')}\n"
            output += f"Response keys: {list(raw.keys())[:10]}"
        elif isinstance(raw, list):
            output = f"API call to {connector.config.name} returned {len(raw)} records."
        else:
            output = f"API call to {connector.config.name} succeeded: {str(raw)[:300]}"

        return {
            "success": True,
            "output": output,
            "raw_data": raw,
            "connector": connector.config.name,
        }

    except APIIntegrationError as e:
        logger.error(f"API agent error: {e}")
        return {
            "success": False,
            "output": f"API call failed: {str(e)}",
            "raw_data": {},
            "connector": connector_prefix,
        }
    except Exception as e:
        logger.error(f"API agent unexpected error: {e}")
        return {
            "success": False,
            "output": f"Unexpected error: {str(e)}",
            "raw_data": {},
            "connector": connector_prefix,
        }