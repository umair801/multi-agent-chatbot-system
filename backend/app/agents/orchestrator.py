import os
import json
import logging
from typing import Any
from openai import OpenAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.constants import START
from app.schemas.models import OrchestratorState
from app.tools.memory import get_or_create_session, cleanup_session, MemoryKeys
from app.agents.web_search_agent import web_search_agent
from app.agents.file_generation_agent import file_generation_agent
from app.agents.code_execution_agent import run_code_execution_agent
from app.agents.summarization_agent import run_summarization_agent
from app.agents.supervisor_agent import run_supervisor_agent
from app.agents.api_agent import run_api_agent
from app.agents.rag_agent import run_rag_query

load_dotenv()
logger = logging.getLogger(__name__)


def _get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Maps plan step agent names to internal agent keys
AGENT_ALIASES = {
    "web_search": "web_search",
    "search": "web_search",
    "file_generation": "file_generation",
    "file": "file_generation",
    "code_execution": "code_execution",
    "code": "code_execution",
    "summarization": "summarization",
    "summarize": "summarization",
    "summary": "summarization",
    "api_integration": "api_integration",
    "api": "api_integration",
    "external_api": "api_integration",
    "crm": "api_integration",
    "data_source": "api_integration",
    "rag": "rag",
    "knowledge_base": "rag",
    "knowledge": "rag",
    "document": "rag",
    "retrieval": "rag",
}

PLANNER_SYSTEM_PROMPT = """You are a planning agent for an autonomous AI system.
The user will give you a goal. Break it into a step-by-step execution plan.

Return a JSON array of steps. Each step must have:
{
  "step_number": <int starting at 1>,
  "agent": <"web_search" | "code_execution" | "file_generation" | "summarization" | "api_integration" | "rag">,
  "task": <specific instruction for that agent, one sentence>
}

Rules:
- Use only the agent names listed above.
- Order steps logically. Search before summarizing. Compute before generating files.
- Maximum 6 steps per plan.
- Return ONLY the JSON array. No markdown, no explanation, no backticks."""


async def goal_intake(state: OrchestratorState) -> OrchestratorState:
    logger.info(f"Goal intake: {state.get('goal')}")
    state["execution_status"] = "running"
    state["current_step_index"] = 0
    state["steps"] = []
    state["errors"] = []
    state["total_tokens"] = 0
    state["retry_count"] = 0
    return state


async def plan_execution(state: OrchestratorState) -> OrchestratorState:
    goal = state.get("goal", "")
    user_context = state.get("user_context", "")

    prompt = f"Goal: {goal}"
    if user_context:
        prompt += f"\nAdditional context: {user_context}"

    logger.info("Generating execution plan...")

    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()
        cleaned = raw.strip("```json").strip("```").strip()
        plan = json.loads(cleaned)
        state["plan"] = plan
        logger.info(f"Plan generated: {len(plan)} steps")
    except Exception as e:
        logger.error(f"Planning failed: {e}")
        state["plan"] = []
        state["errors"] = state.get("errors", []) + [f"Planning error: {str(e)}"]

    return state


async def execute_step(state: OrchestratorState) -> OrchestratorState:
    plan = state.get("plan", [])
    index = state.get("current_step_index", 0)

    if index >= len(plan):
        state["execution_status"] = "completed"
        return state

    step = plan[index]
    agent_key = AGENT_ALIASES.get(step.get("agent", "").lower(), "summarization")
    task = step.get("task", "")
    step_number = step.get("step_number", index + 1)

    logger.info(f"Executing step {step_number}: agent={agent_key}, task={task}")

    output = ""
    agent_result = {}

    try:
        if agent_key == "web_search":
            agent_result = await web_search_agent.search(task)
            results = agent_result.get("results", [])
            output = "\n\n".join(
                f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}"
                for r in results[:5]
            )
            if not output:
                output = agent_result.get("answer", "No results found.")

        elif agent_key == "code_execution":
            agent_result = run_code_execution_agent(task)
            output = agent_result.get("output", "") or agent_result.get("error", "")

        elif agent_key == "file_generation":
            agent_result = await file_generation_agent.generate(
                output_type="pdf",
                content=state.get("accumulated_output", task),
                filename="output",
                title="Agent Output",
            )
            output = (
                f"File generated: {agent_result.get('file_path', 'unknown')}"
                if agent_result.get("status") == "success"
                else agent_result.get("error", "File generation failed.")
            )

        elif agent_key == "rag":
            rag_result = run_rag_query(task)
            output = rag_result.get("answer", "No answer generated.")
            sources = rag_result.get("sources", [])
            if sources:
                output += f"\n\nSources: {', '.join(sources)}"

        elif agent_key == "api_integration":
            connector_prefix = step.get("connector_prefix", "CONNECTOR_CRM")
            agent_result = await run_api_agent(task, connector_prefix=connector_prefix)
            output = agent_result.get("output", "No output returned from API agent.")

        elif agent_key == "summarization":
            accumulated = state.get("accumulated_output", "").strip()
            content = accumulated if accumulated else task
            agent_result = run_summarization_agent(
                content=content,
                instruction=f"The user's original goal was: {state.get('goal', '')}",
                mode="executive",
            )
            output = agent_result.get("summary", "")

    except Exception as e:
        logger.error(f"Step {step_number} execution error: {e}")
        output = f"Error: {str(e)}"
        agent_result = {"success": False, "error": str(e)}

    supervisor_result = run_supervisor_agent(
        agent_type=agent_key,
        task=task,
        output=output,
    )

    step_record = {
        "step_number": step_number,
        "agent": agent_key,
        "task": task,
        "output": output,
        "supervisor_verdict": supervisor_result.get("verdict", "unknown"),
        "supervisor_score": supervisor_result.get("score", 0.0),
    }

    steps = state.get("steps", [])
    steps.append(step_record)
    state["steps"] = steps

    # Broadcast step via WebSocket callback if available
    ws_callback = state.get("ws_callback")
    if ws_callback:
        try:
            await ws_callback(step_record)
        except Exception as e:
            logger.warning(f"WebSocket broadcast failed: {e}")

    accumulated = state.get("accumulated_output", "")
    if output:
        state["accumulated_output"] = f"{accumulated}\n\n{output}".strip()

    state["current_step_index"] = index + 1

    return state


def should_continue(state: OrchestratorState) -> str:
    plan = state.get("plan", [])
    index = state.get("current_step_index", 0)
    status = state.get("execution_status", "")

    if status == "completed" or index >= len(plan):
        return "validate"
    return "execute"


async def validate_output(state: OrchestratorState) -> OrchestratorState:
    steps = state.get("steps", [])
    accumulated = state.get("accumulated_output", "")

    last_summary = ""
    for s in reversed(steps):
        if s.get("agent") == "summarization" and s.get("output"):
            last_summary = s["output"]
            break

    # Use last successful non-error step output if no summarization exists
    if not last_summary:
        for s in reversed(steps):
            output = s.get("output", "")
            if output and not output.startswith("cannot load") and not output.startswith("Error:") and not output.startswith("File generation"):
                last_summary = output
                break

    state["final_output"] = {
        "summary": last_summary or accumulated.strip(),
        "steps_completed": len(steps),
        "steps": steps,
    }
    state["execution_status"] = "completed"
    logger.info(f"Execution complete. Steps: {len(steps)}")
    return state


async def handle_error(state: OrchestratorState) -> OrchestratorState:
    errors = state.get("errors", [])
    logger.error(f"Error handler triggered. Errors: {errors}")
    state["execution_status"] = "failed"
    state["final_output"] = {"error": errors}
    return state


def build_orchestrator_graph() -> StateGraph:
    workflow = StateGraph(OrchestratorState)

    workflow.add_node("goal_intake", goal_intake)
    workflow.add_node("plan_execution", plan_execution)
    workflow.add_node("execute_step", execute_step)
    workflow.add_node("validate_output", validate_output)
    workflow.add_node("handle_error", handle_error)

    workflow.add_edge(START, "goal_intake")
    workflow.add_edge("goal_intake", "plan_execution")
    workflow.add_edge("plan_execution", "execute_step")
    workflow.add_conditional_edges(
        "execute_step",
        should_continue,
        {"execute": "execute_step", "validate": "validate_output"},
    )
    workflow.add_edge("validate_output", END)

    return workflow


def get_orchestrator():
    graph = build_orchestrator_graph()
    compiled = graph.compile()
    logger.info("Orchestrator graph compiled")
    return compiled