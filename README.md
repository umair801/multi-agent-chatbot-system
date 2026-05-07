# Multi-Agent AI Chatbot System — Datawebify

A production-ready multi-agent AI system that coordinates specialized agents,
integrates with external business APIs, retrieves domain-specific knowledge via
a full RAG pipeline, and delivers responses through a conversational chat interface.

**Live Demo:** [chatbot.datawebify.com](https://chatbot.datawebify.com)
**API Docs:** [chatbot.datawebify.com/docs](https://chatbot.datawebify.com/docs)
**Case Study:** [datawebify.com/projects/agai24-multi-agent-chatbot-system](https://datawebify.com/projects/agai24-multi-agent-chatbot-system)
**GitHub:** [github.com/umair801/multi-agent-chatbot-system](https://github.com/umair801/multi-agent-chatbot-system)

---

## What It Does

- Accepts natural language goals and chat messages
- Plans and executes multi-step workflows across specialist agents
- Connects to external business APIs and data sources with configurable auth
- Ingests documents (PDF, DOCX, URL) and answers questions with source citations
- Delivers responses through a turn-by-turn chat interface with session memory
- Streams live execution steps via WebSocket for full transparency

---

## Agent Architecture
User Message → Orchestrator (LangGraph)
├── Planner Agent           (GPT-4o — breaks goal into steps)
├── Web Search Agent        (Tavily — real-time search)
├── Code Execution Agent    (sandboxed Python)
├── Summarization Agent     (Claude API — executive summaries)
├── File Generation Agent   (PDF, DOCX, CSV output)
├── API Integration Agent   (external REST APIs, webhooks)
├── RAG Agent               (domain knowledge retrieval + citations)
└── Supervisor Agent        (quality validation on every step)
↓
Chat Interface + Live WebSocket Step Feed

---

## Three Core Capabilities

### 1. External API Integration (Gap 1)
Connects to any external business API with zero code changes.
Auth methods supported: Bearer token, API key, Basic auth, None.
All connector config is set via environment variables.
Includes inbound webhook receiver for event-driven data ingestion.

Live connectors included:
- wttr.in Weather API (no auth required, live weather data)
- RestCountries (open data, business intelligence demo)

### 2. Full RAG Pipeline (Gap 2)
End-to-end document ingestion to cited answer generation.
- Ingests PDF, DOCX, and URLs
- Semantic chunking with overlap
- OpenAI text-embedding-3-small embeddings
- Pinecone vector store with hybrid search and reranking
- Every answer includes source document and relevance score

### 3. Conversational Chat Interface (Gap 3)
Turn-by-turn chat UI replacing the goal-submission form.
- Message bubble layout (user and assistant)
- Session memory for multi-turn follow-up questions
- Chat history sidebar
- Live WebSocket execution feed as collapsible side panel

---

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (TypedDict state, total=False) |
| LLM Primary | GPT-4o |
| LLM Fallback | Claude API |
| Web Search | Tavily API |
| Embeddings | OpenAI text-embedding-3-small |
| Vector DB | Pinecone + pgvector (hybrid) |
| Backend | FastAPI + Python 3.12 |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS v3 |
| Real-time | WebSockets |
| Protocol | MCP (Model Context Protocol) |
| Database | Supabase (PostgreSQL) |
| Deployment | Railway (backend) + Vercel (frontend) |
| Containerization | Docker |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | System health check |
| POST | /api/execute | Submit a goal for agent execution |
| GET | /api/connectors/weather | Live weather via OpenWeatherMap |
| GET | /api/connectors/countries | Country data via RestCountries |
| POST | /api/webhook/{source} | Inbound webhook receiver |
| GET | /api/webhook/events | List received webhook events |
| POST | /api/v1/ingest/file | Upload PDF or DOCX for RAG ingestion |
| POST | /api/v1/ingest/url | Ingest URL for RAG ingestion |
| POST | /api/v1/chat | Chat endpoint with session memory |
| WebSocket | /ws/execute/{session_id} | Live execution step feed |

---

## Project Structure
AgAI_24_Multi_Agent_Chatbot_System/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── orchestrator.py           # LangGraph orchestration graph
│   │   │   ├── web_search_agent.py       # Tavily web search
│   │   │   ├── code_execution_agent.py   # Sandboxed Python execution
│   │   │   ├── summarization_agent.py    # Claude API summaries
│   │   │   ├── file_generation_agent.py  # PDF, DOCX, CSV generation
│   │   │   ├── supervisor_agent.py       # Output quality validation
│   │   │   ├── rag_agent.py              # RAG retrieval + cited answers
│   │   │   ├── api_integration_agent.py  # Base connector class + config
│   │   │   ├── api_agent.py              # API agent orchestrator node
│   │   │   ├── rest_connector.py         # Generic GET/POST with auth
│   │   │   ├── webhook_receiver.py       # Inbound webhook handler
│   │   │   └── connectors/
│   │   │       ├── weather_connector.py  # OpenWeatherMap connector
│   │   │       └── countries_connector.py # RestCountries connector
│   │   ├── schemas/
│   │   │   └── models.py                 # Pydantic models + LangGraph state
│   │   ├── tools/
│   │   │   ├── llm.py                    # LLM client factory
│   │   │   ├── model_router.py           # GPT-4o / Claude routing
│   │   │   ├── memory.py                 # Session memory management
│   │   │   ├── error_handler.py          # Centralized error handling
│   │   │   └── mcp_client.py             # MCP protocol client
│   │   └── main.py                       # FastAPI app + all routes
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── runtime.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── app/                          # Next.js app router
│       ├── components/                   # Chat UI components
│       └── hooks/                        # WebSocket hook
├── database/
│   ├── schema.sql
│   └── migrations/
├── .gitignore
└── README.md

---

## Getting Started

```powershell
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Fill in your API keys in .env
python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## Environment Variables

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
TAVILY_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
WEBHOOK_SECRET=

# External API connectors
CONNECTOR_WEATHER_NAME=OpenWeatherMap
CONNECTOR_WEATHER_BASE_URL=https://api.openweathermap.org/data/2.5
CONNECTOR_WEATHER_AUTH_METHOD=api_key
CONNECTOR_WEATHER_AUTH_TOKEN=
CONNECTOR_WEATHER_API_KEY_HEADER=appid

CONNECTOR_COUNTRIES_NAME=RestCountries
CONNECTOR_COUNTRIES_BASE_URL=https://restcountries.com/v3.1
CONNECTOR_COUNTRIES_AUTH_METHOD=none

# RAG Pipeline (added in Phase B)
PINECONE_API_KEY=
PINECONE_INDEX_NAME=
```

---

## Deployment

- Backend: Railway — auto-deploy from `backend/` on push to main
- Frontend: Vercel — auto-deploy from `frontend/` on push to main
- Live URL: [chatbot.datawebify.com](https://chatbot.datawebify.com)

---

## About

Built by Muhammad Umair — Agentic AI Specialist
[datawebify.com](https://datawebify.com) | [github.com/umair801](https://github.com/umair801)