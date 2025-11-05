"""
Agent API Routes for PM Document Intelligence.

This module provides endpoints for interacting with specialized agents.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models import UserInDB
from app.agents.orchestrator import get_orchestrator, TaskType
from app.database import execute_select
from app.utils.auth_helpers import get_current_active_user
from app.utils.exceptions import ValidationError, AIServiceError
from app.utils.logger import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])
limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# Request/Response Models
# ============================================================================


class AnalysisRequest(BaseModel):
    """Deep analysis request."""

    document_id: str
    document_type: Optional[str] = "general"
    include_risks: bool = True
    include_opportunities: bool = True


class ActionExtractionRequest(BaseModel):
    """Action item extraction request."""

    document_id: str
    track_dependencies: bool = True


class SummarizeRequest(BaseModel):
    """Summarization request."""

    document_id: str
    length: str = Field("medium", pattern="^(brief|medium|comprehensive)$")
    audience: str = Field("general", pattern="^(executive|technical|team|general)$")


class QuestionRequest(BaseModel):
    """Q&A request."""

    question: str = Field(..., min_length=3, max_length=500)
    document_id: Optional[str] = None
    conversation_id: Optional[str] = None
    use_context: bool = True


class MultiAgentRequest(BaseModel):
    """Multi-agent analysis request."""

    document_id: str
    tasks: List[str] = Field(..., min_items=1, max_items=5)
    parallel: bool = True


# ============================================================================
# Agent Endpoints
# ============================================================================


@router.post("/analyze", summary="Deep document analysis")
@limiter.limit("20/minute")
async def analyze_document(
    request: Request,
    analysis_request: AnalysisRequest,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Perform deep analysis on a document.

    **Features:**
    - Insight extraction
    - Pattern identification
    - Risk assessment
    - Recommendations

    **Rate Limit:** 20 requests/minute
    """
    try:
        # Get document
        documents = await execute_select(
            "documents",
            columns="extracted_text, document_type",
            match={"id": analysis_request.document_id, "user_id": current_user.id},
        )

        if not documents:
            raise ValidationError(
                message="Document not found",
                details={"document_id": analysis_request.document_id},
            )

        document = documents[0]

        # Analyze
        orchestrator = get_orchestrator()
        result = await orchestrator.analyze_document(
            document_id=analysis_request.document_id,
            document_text=document["extracted_text"],
            user_id=current_user.id,
            task="deep_analysis",
            options={
                "document_type": document["document_type"]
                or analysis_request.document_type,
                "include_risks": analysis_request.include_risks,
                "include_opportunities": analysis_request.include_opportunities,
            },
        )

        return result

    except (ValidationError, AIServiceError):
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise AIServiceError(message="Analysis failed", details={"error": str(e)})


@router.post("/extract-actions", summary="Extract action items")
@limiter.limit("30/minute")
async def extract_actions(
    request: Request,
    action_request: ActionExtractionRequest,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Extract action items from document.

    **Features:**
    - Action identification
    - Assignee extraction
    - Due date detection
    - Priority classification
    - Dependency tracking

    **Rate Limit:** 30 requests/minute
    """
    try:
        documents = await execute_select(
            "documents",
            columns="extracted_text",
            match={"id": action_request.document_id, "user_id": current_user.id},
        )

        if not documents:
            raise ValidationError(
                message="Document not found",
                details={"document_id": action_request.document_id},
            )

        orchestrator = get_orchestrator()
        result = await orchestrator.analyze_document(
            document_id=action_request.document_id,
            document_text=documents[0]["extracted_text"],
            user_id=current_user.id,
            task="extract_actions",
            options={"track_dependencies": action_request.track_dependencies},
        )

        return result

    except (ValidationError, AIServiceError):
        raise


@router.post("/summarize", summary="Generate summary")
@limiter.limit("30/minute")
async def summarize_document(
    request: Request,
    summarize_request: SummarizeRequest,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Generate document summary.

    **Lengths:**
    - brief: ~200 tokens
    - medium: ~500 tokens
    - comprehensive: ~1000 tokens

    **Audiences:**
    - executive: High-level, business-focused
    - technical: Technical details
    - team: Actionable items
    - general: Balanced

    **Rate Limit:** 30 requests/minute
    """
    try:
        documents = await execute_select(
            "documents",
            columns="extracted_text",
            match={"id": summarize_request.document_id, "user_id": current_user.id},
        )

        if not documents:
            raise ValidationError(
                message="Document not found",
                details={"document_id": summarize_request.document_id},
            )

        orchestrator = get_orchestrator()
        result = await orchestrator.analyze_document(
            document_id=summarize_request.document_id,
            document_text=documents[0]["extracted_text"],
            user_id=current_user.id,
            task="summarize",
            options={
                "length": summarize_request.length,
                "audience": summarize_request.audience,
            },
        )

        return result

    except (ValidationError, AIServiceError):
        raise


@router.post("/ask", summary="Ask questions about documents")
@limiter.limit("30/minute")
async def ask_question(
    request: Request,
    question_request: QuestionRequest,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Ask questions about documents using RAG.

    **Features:**
    - Semantic search for context
    - Citation of sources
    - Follow-up questions
    - Multi-hop reasoning

    **Rate Limit:** 30 requests/minute

    **Example:**
    ```json
    {
      "question": "What are the main risks in the project plan?",
      "document_id": "doc_123",
      "conversation_id": "conv_456"
    }
    ```
    """
    try:
        orchestrator = get_orchestrator()

        result = await orchestrator.ask_question(
            question=question_request.question,
            document_id=question_request.document_id,
            user_id=current_user.id,
            conversation_id=question_request.conversation_id,
            use_context=question_request.use_context,
        )

        return result

    except (ValidationError, AIServiceError):
        raise


@router.post("/multi-agent", summary="Run multiple agents")
@limiter.limit("10/minute")
async def multi_agent_analysis(
    request: Request,
    multi_request: MultiAgentRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Run multiple agents on a document.

    **Tasks:**
    - deep_analysis
    - extract_actions
    - summarize
    - extract_entities

    **Rate Limit:** 10 requests/minute

    **Example:**
    ```json
    {
      "document_id": "doc_123",
      "tasks": ["deep_analysis", "extract_actions", "summarize"],
      "parallel": true
    }
    ```
    """
    try:
        documents = await execute_select(
            "documents",
            columns="extracted_text",
            match={"id": multi_request.document_id, "user_id": current_user.id},
        )

        if not documents:
            raise ValidationError(
                message="Document not found",
                details={"document_id": multi_request.document_id},
            )

        orchestrator = get_orchestrator()
        result = await orchestrator.multi_agent_analysis(
            document_id=multi_request.document_id,
            document_text=documents[0]["extracted_text"],
            user_id=current_user.id,
            tasks=multi_request.tasks,
            parallel=multi_request.parallel,
        )

        return result

    except (ValidationError, AIServiceError):
        raise


# ============================================================================
# Agent Status & Management
# ============================================================================


@router.get("/status", summary="Get agent status")
async def get_agent_status(
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Get status of all agents.

    Returns health, metrics, and circuit breaker states.
    """
    orchestrator = get_orchestrator()

    return {
        "agents": orchestrator.get_all_agent_status(),
        "orchestrator": orchestrator.get_orchestrator_stats(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health", summary="Agent health check")
async def agent_health_check():
    """
    Check health of agent system.

    Returns overall health status and any issues.
    """
    orchestrator = get_orchestrator()
    health = await orchestrator.health_check()
    return health


@router.delete("/conversation/{conversation_id}", summary="Clear conversation")
async def clear_conversation(
    conversation_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Clear conversation history for Q&A follow-ups.
    """
    orchestrator = get_orchestrator()
    orchestrator.clear_conversation(conversation_id)

    return {
        "message": "Conversation cleared",
        "conversation_id": conversation_id,
    }
