import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class SessionMemory:
    """
    In-memory session store for agent context and intermediate results
    Persists during a single execution session
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.data: Dict[str, Any] = {}
        self.created_at = datetime.now()
        logger.info(f'SessionMemory created for session: {session_id}')
    
    def set(self, key: str, value: Any) -> None:
        """Store a value in memory"""
        self.data[key] = {
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        logger.debug(f'Memory set: {key}')
    
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from memory"""
        if key in self.data:
            return self.data[key]['value']
        logger.debug(f'Memory get: {key} (not found, returning default)')
        return default
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in memory"""
        return key in self.data
    
    def delete(self, key: str) -> bool:
        """Delete a key from memory"""
        if key in self.data:
            del self.data[key]
            logger.debug(f'Memory deleted: {key}')
            return True
        return False
    
    def clear(self) -> None:
        """Clear all memory"""
        self.data.clear()
        logger.info(f'Memory cleared for session: {self.session_id}')
    
    def list_keys(self, prefix: str = '') -> List[str]:
        """List all keys, optionally filtered by prefix"""
        if prefix:
            return [k for k in self.data.keys() if k.startswith(prefix)]
        return list(self.data.keys())
    
    def dump(self) -> Dict[str, Any]:
        """Return entire memory state (for debugging)"""
        return {k: v['value'] for k, v in self.data.items()}

# Global session memory store
sessions: Dict[str, SessionMemory] = {}

def get_or_create_session(session_id: str) -> SessionMemory:
    """Get or create a session memory"""
    if session_id not in sessions:
        sessions[session_id] = SessionMemory(session_id)
    return sessions[session_id]

def cleanup_session(session_id: str) -> None:
    """Clean up a session after execution completes"""
    if session_id in sessions:
        del sessions[session_id]
        logger.info(f'Session memory cleaned up: {session_id}')

# Common memory keys (conventions for all agents)
class MemoryKeys:
    # Planning
    GOAL = 'goal'
    PLAN = 'plan'
    PLAN_REASONING = 'plan_reasoning'
    
    # Web Search
    WEB_SEARCH_RESULTS = 'web_search_results'
    WEB_SEARCH_QUERY = 'web_search_query'
    
    # Browser Automation
    BROWSER_STATE = 'browser_state'
    BROWSER_EXTRACTED_DATA = 'browser_extracted_data'
    
    # Code Execution
    CODE_OUTPUT = 'code_output'
    CODE_ERRORS = 'code_errors'
    
    # File Generation
    GENERATED_FILES = 'generated_files'
    
    # RAG
    RAG_CONTEXT = 'rag_context'
    RAG_SOURCES = 'rag_sources'
    
    # Summarization
    SUMMARY = 'summary'
    
    # Execution metadata
    TOTAL_TOKENS = 'total_tokens'
    EXECUTION_TIME = 'execution_time'
    ERRORS = 'errors'
