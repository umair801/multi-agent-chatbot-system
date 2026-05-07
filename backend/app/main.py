from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Header, UploadFile, File
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import json
from datetime import datetime
import uuid
from app.schemas.models import GoalRequest, OrchestratorState
from app.agents.orchestrator import get_orchestrator
from app.tools.memory import cleanup_session
from app.agents.webhook_receiver import verify_webhook_signature, parse_webhook_payload

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'info').upper()
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# Initialize FastAPI app (no on_startup parameter - use lifespan instead in v0.104+)
app = FastAPI(
    title='Datawebify Autonomous Agent Platform',
    description='A Manus-style autonomous AI agent platform',
    version='1.0.0'
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Store active WebSocket connections
active_connections = {}

@app.get('/health')
async def health_check():
    env = os.getenv('ENVIRONMENT', 'development')
    return {'status': 'ok', 'environment': env}

@app.websocket('/ws/execute/{session_id}')
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time execution step visibility
    """
    await websocket.accept()
    active_connections[session_id] = websocket
    logger.info(f'WebSocket connected: {session_id}')
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f'Received from {session_id}: {data}')
    except WebSocketDisconnect:
        if session_id in active_connections:
            del active_connections[session_id]
        logger.info(f'WebSocket disconnected: {session_id}')
    except Exception as e:
        logger.error(f'WebSocket error for {session_id}: {str(e)}')
        if session_id in active_connections:
            del active_connections[session_id]

async def broadcast_step(session_id: str, step_data: dict):
    """
    Broadcast a step update to the connected frontend via WebSocket
    """
    if session_id in active_connections:
        try:
            message = {
                'type': 'step_update',
                'timestamp': datetime.now().isoformat(),
                'step': step_data
            }
            await active_connections[session_id].send_json(message)
            logger.info(f'Broadcasted step to {session_id}: {step_data.get("step_number")}')
        except Exception as e:
            logger.error(f'Failed to broadcast to {session_id}: {str(e)}')

@app.post('/api/execute')
async def execute_goal(request: GoalRequest):
    session_id = str(uuid.uuid4())
    logger.info(f'Starting execution for goal: {request.goal}, session: {session_id}')

    try:
        orchestrator = get_orchestrator()

        async def ws_broadcast(step_data: dict):
            await broadcast_step(session_id, step_data)

        initial_state: OrchestratorState = {
            'session_id': session_id,
            'goal': request.goal,
            'user_context': request.context or '',
            'execution_status': 'pending',
            'ws_callback': ws_broadcast,
        }

        result = await orchestrator.ainvoke(initial_state)

        logger.info(f'Execution completed for session {session_id}')

        return {
            'session_id': session_id,
            'status': result.get('execution_status'),
            'steps': result.get('steps', []),
            'final_output': result.get('final_output'),
            'total_tokens': result.get('total_tokens', 0),
        }

    except Exception as e:
        logger.error(f'Orchestrator error: {str(e)}')
        return {
            'session_id': session_id,
            'status': 'failed',
            'error': str(e),
        }

    finally:
        cleanup_session(session_id)


# ---------------------------------------------------------------------------
# RAG endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/ingest/url")
async def ingest_url(request: Request):
    """Ingest a URL into the RAG knowledge base."""
    from app.agents.rag_agent import run_rag_ingest
    body = await request.json()
    url = body.get("url", "")
    if not url:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="url is required")
    result = run_rag_ingest(url, "url")
    return result


@app.post("/api/v1/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    """Ingest a PDF or DOCX file into the RAG knowledge base."""
    import shutil
    import tempfile
    from app.agents.rag_agent import run_rag_ingest
    suffix = os.path.splitext(file.filename)[-1].lower()
    source_type = "pdf" if suffix == ".pdf" else "docx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    result = run_rag_ingest(tmp_path, source_type)
    os.unlink(tmp_path)
    return result


@app.post("/api/v1/chat")
async def rag_chat(request: Request):
    """Answer a question using the RAG knowledge base."""
    from app.agents.rag_agent import run_rag_query
    body = await request.json()
    query = body.get("query", "")
    top_k = body.get("top_k", 5)
    if not query:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="query is required")
    result = run_rag_query(query, top_k=top_k)
    return result


# ---------------------------------------------------------------------------
# Live connector endpoints
# ---------------------------------------------------------------------------

@app.get("/api/connectors/weather")
async def weather_endpoint(city: str = "London"):
    """Fetch live weather data via OpenWeatherMap connector."""
    from app.agents.connectors.weather_connector import get_weather
    result = await get_weather(city)
    return result


@app.get("/api/connectors/countries")
async def countries_endpoint(country: str = "Germany"):
    """Fetch country business data via RestCountries connector."""
    from app.agents.connectors.countries_connector import get_country_info
    result = await get_country_info(country)
    return result


# ---------------------------------------------------------------------------
# Webhook receiver endpoints
# ---------------------------------------------------------------------------

# In-memory store for received webhooks (keyed by source)
# In production this would persist to Supabase agent_webhooks table
webhook_store: list = []


@app.post("/api/webhook/{source}")
async def receive_webhook(
    source: str,
    request: Request,
    x_webhook_signature: Optional[str] = Header(default=None),
):
    """
    Generic inbound webhook receiver.
    Accepts POST from any external system at /api/webhook/<source_name>.
    Verifies HMAC signature if WEBHOOK_SECRET is set in .env.
    """
    raw_bytes = await request.body()

    secret = os.getenv("WEBHOOK_SECRET")
    if not verify_webhook_signature(raw_bytes, x_webhook_signature, secret):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        raw_payload = await request.json()
    except Exception:
        raw_payload = {"raw_body": raw_bytes.decode(errors="replace")}

    raw_payload["source"] = source
    envelope = parse_webhook_payload(raw_payload)

    webhook_store.append(envelope)
    logger.info(f"Webhook received from '{source}': event={envelope['event_type']}")

    return {
        "status": "received",
        "source": source,
        "event_type": envelope["event_type"],
        "received_at": envelope["received_at"],
    }


@app.get("/api/webhook/events")
async def list_webhook_events(source: Optional[str] = None):
    """
    List received webhook events.
    Optional ?source= filter to narrow by sender.
    """
    events = webhook_store
    if source:
        events = [e for e in webhook_store if e.get("source") == source]
    return {"count": len(events), "events": events}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)

