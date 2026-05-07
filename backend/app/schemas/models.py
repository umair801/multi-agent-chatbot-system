from pydantic import BaseModel
from typing import Optional, List, Any
from typing_extensions import TypedDict

# Request/Response Models
class GoalRequest(BaseModel):
    goal: str
    context: Optional[str] = None

class ExecutionStep(BaseModel):
    step_id: str
    step_number: int
    agent_type: str
    action: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    tokens_used: Optional[int] = None

class ExecutionResult(BaseModel):
    goal: str
    status: str
    steps: List[ExecutionStep]
    final_output: Optional[Any] = None
    total_tokens: Optional[int] = None

# LangGraph State (TypedDict with total=False for flexible state)
class OrchestratorState(TypedDict, total=False):
    """
    Shared state across all agents in the execution graph
    total=False allows agents to add/read keys dynamically
    """
    # Core execution metadata
    session_id: str
    goal: str
    user_context: str
    
    # Planning
    plan: List[dict]  # List of planned steps
    current_step_index: int
    
    # Execution tracking
    steps: List[dict]  # Completed steps
    current_step: dict  # Step currently being executed
    
    # Shared data
    web_search_results: List[dict]  # Results from web search
    browser_state: dict  # State from browser automation
    code_output: str  # Output from code execution
    generated_files: List[dict]  # Generated PDFs, CSVs, etc.
    
    # RAG
    knowledge_base_context: str  # Retrieved context from uploaded docs
    
    # Error handling
    errors: List[str]
    retry_count: int
    
    # Tokens & cost
    total_tokens: int
    model_used: str
    
    # Accumulated agent outputs for downstream context passing
    accumulated_output: str

    # WebSocket callback for live step broadcasting
    ws_callback: Any

    # Final output
    final_output: Any
    execution_status: str  # 'pending', 'running', 'completed', 'failed'
