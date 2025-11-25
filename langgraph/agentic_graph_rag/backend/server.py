"""
FastAPI server for Synthea chatbot application.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from agent import create_agent, query_agent

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Synthea Chatbot API",
    description="AI-powered chatbot for querying Synthea patient database",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent
agent = None
conversation_histories = {}
executed_queries_storage = {}  # Store executed queries per session


# Pydantic models for request/response
class ChatMessage(BaseModel):
    """Chat message model."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: Optional[str] = "default"


class QueryInfo(BaseModel):
    """Information about an executed query."""
    query: str
    params: dict
    source: str
    timestamp: str
    tool_args: Optional[dict] = None
    question: Optional[str] = None


class LatencyLog(BaseModel):
    """Information about LLM or tool latency."""
    name: str  # e.g., "LLM: Validation", "Tool: get_patient_procedures"
    duration_ms: int  # Duration in milliseconds
    model: Optional[str] = None  # Model name for LLM calls (e.g., "gpt-oss-120b")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    session_id: str
    executed_queries: List[QueryInfo] = []
    latency_logs: List[LatencyLog] = []


@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup."""
    global agent
    print("Initializing LangGraph agent...")

    # Check for required environment variables
    if not os.getenv("SAMBANOVA_API_KEY"):
        print("WARNING: SAMBANOVA_API_KEY not found in environment variables!")
        print("Please set SAMBANOVA_API_KEY in .env file or environment")

    try:
        agent = create_agent()
        print("Agent initialized successfully!")
    except Exception as e:
        print(f"Error initializing agent: {e}")
        print("Agent will be initialized on first request")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Synthea Chatbot API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_initialized": agent is not None
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for querying the agent.

    Args:
        request: ChatRequest containing user message and session_id

    Returns:
        ChatResponse with agent's response
    """
    global agent

    # Initialize agent if not already done
    if agent is None:
        try:
            agent = create_agent()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize agent: {str(e)}"
            )

    try:
        # Get or create conversation history and query storage for this session
        if request.session_id not in conversation_histories:
            conversation_histories[request.session_id] = []
            executed_queries_storage[request.session_id] = []

        # Query the agent
        response, updated_history, executed_queries, latency_logs = query_agent(
            agent,
            request.message,
            conversation_histories[request.session_id],
            executed_queries_storage[request.session_id]
        )

        # Update conversation history and queries
        conversation_histories[request.session_id] = updated_history
        executed_queries_storage[request.session_id] = executed_queries

        # Convert executed_queries to QueryInfo models
        query_infos = [QueryInfo(**q) for q in executed_queries] if executed_queries else []

        # Convert latency_logs to LatencyLog models
        latency_log_models = [LatencyLog(**log) for log in latency_logs] if latency_logs else []

        return ChatResponse(
            response=response,
            session_id=request.session_id,
            executed_queries=query_infos,
            latency_logs=latency_log_models
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )


@app.post("/chat/reset")
async def reset_chat(session_id: str = "default"):
    """
    Reset conversation history for a session.

    Args:
        session_id: Session ID to reset

    Returns:
        Success message
    """
    if session_id in conversation_histories:
        conversation_histories[session_id] = []
    if session_id in executed_queries_storage:
        executed_queries_storage[session_id] = []

    return {
        "message": f"Conversation history reset for session: {session_id}",
        "session_id": session_id
    }


@app.get("/sessions")
async def list_sessions():
    """
    List all active sessions.

    Returns:
        List of session IDs
    """
    return {
        "sessions": list(conversation_histories.keys()),
        "count": len(conversation_histories)
    }


class ProviderRequest(BaseModel):
    """Provider switch request model."""
    provider: str


@app.get("/provider")
async def get_provider():
    """
    Get the current provider configuration.

    Returns:
        Current provider and model configuration
    """
    from llm_factory import get_provider, get_main_agent_model, get_validation_model, get_cypher_agent_model, get_synthesis_model

    current_provider = get_provider()

    return {
        "provider": current_provider,
        "models": {
            "main_agent": get_main_agent_model(),
            "validation": get_validation_model(),
            "cypher_agent": get_cypher_agent_model(),
            "synthesis": get_synthesis_model()
        }
    }


@app.post("/provider")
async def switch_provider(request: ProviderRequest):
    """
    Switch the LLM provider (Anthropic or SambaNova).

    This updates the PROVIDER environment variable and recreates the agent.

    Args:
        request: Provider request with provider name

    Returns:
        Updated provider configuration
    """
    global agent

    provider = request.provider.lower()

    if provider not in ["anthropic", "sambanova"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {provider}. Must be 'anthropic' or 'sambanova'"
        )

    # Update the environment variable
    os.environ["PROVIDER"] = provider

    # Recreate the agent with new provider
    try:
        agent = create_agent()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating agent with provider {provider}: {str(e)}"
        )

    # Get updated model configuration
    from llm_factory import get_main_agent_model, get_validation_model, get_cypher_agent_model, get_synthesis_model

    return {
        "provider": provider,
        "message": f"Switched to {provider} provider",
        "models": {
            "main_agent": get_main_agent_model(),
            "validation": get_validation_model(),
            "cypher_agent": get_cypher_agent_model(),
            "synthesis": get_synthesis_model()
        }
    }


# Mount static files (frontend)
# This serves the frontend HTML/JS files
# Determine the correct frontend directory path
import pathlib
backend_dir = pathlib.Path(__file__).parent
frontend_dir = backend_dir.parent / "frontend"

try:
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/app")
    async def serve_app():
        """Serve the main application page."""
        return FileResponse(str(frontend_dir / "index.html"))

    @app.get("/graph")
    async def serve_graph():
        """Serve the LangGraph visualization page."""
        return FileResponse(str(frontend_dir / "graph.html"))
except Exception as e:
    print(f"Note: Frontend files not mounted - {e}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))

    print(f"""
    ╔══════════════════════════════════════════════════╗
    ║     Synthea Chatbot Server Starting...          ║
    ╚══════════════════════════════════════════════════╝

    Server will be available at: http://localhost:{port}
    API Documentation: http://localhost:{port}/docs
    Health Check: http://localhost:{port}/health
    Chat Interface: http://localhost:{port}/app

    Press Ctrl+C to stop the server
    """)

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
