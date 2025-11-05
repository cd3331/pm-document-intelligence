"""
MCP API Routes for PM Document Intelligence.

This module provides HTTP endpoints for MCP (Model Context Protocol) interactions:
- Tool execution
- Resource access
- Chat with MCP-enabled agents
- Tool and resource discovery

Features:
- Authentication and authorization
- Rate limiting
- Audit logging
- Tool cost tracking
- Conversation management
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status, Request, BackgroundTasks
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models import UserInDB
from app.mcp.mcp_server import get_mcp_server, PMIntelligenceMCP
from app.utils.auth_helpers import get_current_active_user
from app.utils.exceptions import ValidationError, AIServiceError, AuthorizationError
from app.utils.logger import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["mcp"])
limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# Request/Response Models
# ============================================================================

class ToolExecutionRequest(BaseModel):
    """Request to execute an MCP tool."""
    tool_name: str = Field(..., description="Name of tool to execute")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation ID for context"
    )
    track_cost: bool = Field(default=True, description="Track execution cost")


class ToolExecutionResponse(BaseModel):
    """Response from tool execution."""
    success: bool
    tool_name: str
    result: Dict[str, Any]
    execution_time: float
    cost: Optional[float] = None
    timestamp: str


class ResourceAccessRequest(BaseModel):
    """Request to access an MCP resource."""
    uri: str = Field(..., description="Resource URI (e.g., doc://123)")


class ChatMessage(BaseModel):
    """Chat message."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=10000)


class MCPChatRequest(BaseModel):
    """Request for MCP-enabled chat."""
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None
    allow_tools: bool = Field(default=True, description="Allow tool use")
    allowed_tools: Optional[List[str]] = Field(
        None,
        description="Specific tools to allow (null = all)"
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context"
    )


class ToolInfo(BaseModel):
    """Information about an MCP tool."""
    name: str
    description: str
    parameters: Dict[str, Any]
    example_usage: Optional[str] = None


# ============================================================================
# Audit Logging
# ============================================================================

async def log_tool_execution(
    user_id: str,
    tool_name: str,
    parameters: Dict[str, Any],
    result: Dict[str, Any],
    duration: float,
    success: bool
) -> None:
    """
    Log tool execution for audit trail.

    Args:
        user_id: User who executed the tool
        tool_name: Tool name
        parameters: Tool parameters
        result: Execution result
        duration: Execution duration
        success: Whether execution succeeded
    """
    from app.database import execute_insert

    try:
        await execute_insert(
            "audit_logs",
            {
                "user_id": user_id,
                "action": f"mcp_tool_{tool_name}",
                "details": {
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "success": success,
                    "duration": duration,
                    "result_summary": {
                        "success": result.get("success"),
                        "total_results": result.get("total_results"),
                        "error": result.get("error")
                    }
                },
                "timestamp": datetime.utcnow().isoformat(),
                "ip_address": None,  # Would be set from request
                "user_agent": None
            }
        )

        logger.info(
            f"Logged MCP tool execution: {tool_name}",
            extra={
                "user_id": user_id,
                "tool": tool_name,
                "success": success,
                "duration": duration
            }
        )

    except Exception as e:
        # Don't fail the request if audit logging fails
        logger.error(f"Failed to log tool execution: {e}", exc_info=True)


# ============================================================================
# MCP Endpoints
# ============================================================================

@router.post("/execute", summary="Execute MCP tool")
@limiter.limit("60/minute")
async def execute_tool(
    request: Request,
    tool_request: ToolExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_active_user),
) -> ToolExecutionResponse:
    """
    Execute an MCP tool with parameters.

    **Tool Execution Flow:**
    1. Validate user authentication
    2. Check tool availability
    3. Validate parameters
    4. Execute tool
    5. Track cost (if applicable)
    6. Log execution for audit

    **Available Tools:**
    - search_documents: Semantic search across documents
    - analyze_metrics: Extract quantitative metrics
    - query_database: Safe database queries
    - create_action_item: Create new action items
    - get_user_context: Retrieve user preferences

    **Rate Limit:** 60 requests/minute

    **Example:**
    ```json
    {
      "tool_name": "search_documents",
      "parameters": {
        "query": "project risks",
        "limit": 5,
        "user_id": "user_123"
      },
      "conversation_id": "conv_456"
    }
    ```
    """
    start_time = datetime.utcnow()

    try:
        mcp_server = get_mcp_server()

        # Inject user_id into parameters for access control
        parameters = {
            **tool_request.parameters,
            "user_id": current_user.id
        }

        logger.info(
            f"Executing MCP tool: {tool_request.tool_name}",
            extra={
                "user_id": current_user.id,
                "tool": tool_request.tool_name,
                "conversation_id": tool_request.conversation_id
            }
        )

        # Execute tool
        result = await mcp_server.call_tool(
            tool_name=tool_request.tool_name,
            parameters=parameters
        )

        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        # Add to conversation context if provided
        if tool_request.conversation_id:
            mcp_server.context.add_message(
                conversation_id=tool_request.conversation_id,
                role="tool",
                content=f"Executed {tool_request.tool_name}",
                metadata={
                    "tool_name": tool_request.tool_name,
                    "parameters": tool_request.parameters,
                    "result_success": result.get("success", True)
                }
            )

        # Extract cost if available
        cost = result.get("cost") or result.get("summary", {}).get("cost")

        # Background task: log execution
        background_tasks.add_task(
            log_tool_execution,
            user_id=current_user.id,
            tool_name=tool_request.tool_name,
            parameters=tool_request.parameters,
            result=result,
            duration=execution_time,
            success=result.get("success", True)
        )

        return ToolExecutionResponse(
            success=result.get("success", True),
            tool_name=tool_request.tool_name,
            result=result,
            execution_time=execution_time,
            cost=cost,
            timestamp=datetime.utcnow().isoformat()
        )

    except ValidationError as e:
        logger.warning(f"Tool execution validation error: {e}")
        raise

    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        raise AIServiceError(
            message=f"Failed to execute tool: {tool_request.tool_name}",
            details={"error": str(e)}
        )


@router.get("/tools", summary="List available MCP tools")
async def list_tools(
    current_user: UserInDB = Depends(get_current_active_user),
) -> List[ToolInfo]:
    """
    List all available MCP tools.

    Returns tool information including:
    - Name and description
    - Parameter schema
    - Usage examples

    **Example Response:**
    ```json
    [
      {
        "name": "search_documents",
        "description": "Search documents using natural language",
        "parameters": {...},
        "example_usage": "Search for project risks"
      }
    ]
    ```
    """
    mcp_server = get_mcp_server()
    tools = mcp_server.list_tools()

    # Add example usage for each tool
    examples = {
        "search_documents": "Find all documents mentioning 'budget overrun'",
        "analyze_metrics": "Extract all numerical metrics from quarterly report",
        "query_database": "Get all high-priority action items due this week",
        "create_action_item": "Create action item to review security audit",
        "get_user_context": "Retrieve user preferences for personalization"
    }

    return [
        ToolInfo(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["parameters"],
            example_usage=examples.get(tool["name"])
        )
        for tool in tools
    ]


@router.get("/resources", summary="List available MCP resources")
async def list_resources(
    current_user: UserInDB = Depends(get_current_active_user),
) -> List[Dict[str, str]]:
    """
    List available MCP resource schemes.

    Resources provide URI-based access to documents and user data.

    **Resource Schemes:**
    - `doc://{document_id}` - Access documents
    - `user://{user_id}` - Access user profiles

    **Example Response:**
    ```json
    [
      {
        "scheme": "doc",
        "description": "Access doc resources",
        "uri_format": "doc://{id}"
      }
    ]
    ```
    """
    mcp_server = get_mcp_server()
    return mcp_server.list_resources()


@router.post("/resource", summary="Access MCP resource")
@limiter.limit("100/minute")
async def get_resource(
    request: Request,
    resource_request: ResourceAccessRequest,
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Access an MCP resource by URI.

    **Supported URIs:**
    - `doc://{document_id}` - Get document with metadata
    - `user://{user_id}` - Get user profile (own profile only)

    **Access Control:**
    - Users can only access their own documents
    - Users can only access their own profile

    **Rate Limit:** 100 requests/minute

    **Example:**
    ```json
    {
      "uri": "doc://doc_123"
    }
    ```
    """
    try:
        mcp_server = get_mcp_server()

        logger.info(
            f"Accessing MCP resource: {resource_request.uri}",
            extra={"user_id": current_user.id}
        )

        resource = await mcp_server.get_resource(
            uri=resource_request.uri,
            user_id=current_user.id
        )

        return resource

    except AuthorizationError as e:
        logger.warning(f"Unauthorized resource access: {e}")
        raise

    except Exception as e:
        logger.error(f"Resource access failed: {e}", exc_info=True)
        raise AIServiceError(
            message="Failed to access resource",
            details={"uri": resource_request.uri, "error": str(e)}
        )


@router.get("/prompts", summary="List available prompt templates")
async def list_prompts(
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, List[str]]:
    """
    List available MCP prompt templates.

    Prompt templates provide reusable structures for common tasks.

    **Available Templates:**
    - document_analysis_prompt
    - action_item_extraction_prompt
    - executive_summary_prompt
    - qa_with_context_prompt
    """
    mcp_server = get_mcp_server()
    prompts = mcp_server.list_prompts()

    return {
        "prompts": prompts,
        "total": len(prompts)
    }


@router.post("/prompt", summary="Get prompt template")
async def get_prompt(
    template_name: str,
    variables: Dict[str, str],
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, str]:
    """
    Get a formatted prompt template.

    **Example:**
    ```json
    POST /api/mcp/prompt?template_name=document_analysis_prompt
    {
      "variables": {
        "document_name": "Q4 Report.pdf",
        "document_type": "financial_report",
        "document_text": "..."
      }
    }
    ```
    """
    try:
        mcp_server = get_mcp_server()

        prompt = mcp_server.get_prompt_template(
            template_name=template_name,
            **variables
        )

        return {
            "template_name": template_name,
            "prompt": prompt
        }

    except ValidationError as e:
        logger.warning(f"Invalid prompt template request: {e}")
        raise

    except Exception as e:
        logger.error(f"Prompt template generation failed: {e}", exc_info=True)
        raise AIServiceError(
            message="Failed to generate prompt",
            details={"template": template_name, "error": str(e)}
        )


@router.post("/chat", summary="Chat with MCP-enabled agent")
@limiter.limit("30/minute")
async def mcp_chat(
    request: Request,
    chat_request: MCPChatRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Chat with an MCP-enabled AI agent.

    The agent can use tools, access resources, and maintain conversation
    context across multiple messages.

    **Features:**
    - Tool use (if allowed)
    - Conversation context
    - Resource access
    - Cost tracking

    **Rate Limit:** 30 requests/minute

    **Example:**
    ```json
    {
      "message": "Search for documents about project risks and create action items for the top 3 risks",
      "conversation_id": "conv_123",
      "allow_tools": true,
      "context": {
        "project_id": "proj_456"
      }
    }
    ```
    """
    start_time = datetime.utcnow()

    try:
        from app.agents.orchestrator import get_orchestrator

        mcp_server = get_mcp_server()
        orchestrator = get_orchestrator()

        # Generate or use provided conversation ID
        conversation_id = chat_request.conversation_id or f"conv_{current_user.id}_{int(datetime.utcnow().timestamp())}"

        logger.info(
            f"MCP Chat request",
            extra={
                "user_id": current_user.id,
                "conversation_id": conversation_id,
                "message_length": len(chat_request.message)
            }
        )

        # Add user message to context
        mcp_server.context.add_message(
            conversation_id=conversation_id,
            role="user",
            content=chat_request.message
        )

        # Get conversation history
        history = mcp_server.context.get_conversation(conversation_id)

        # Build context for agent
        conversation_context = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in history[-5:]  # Last 5 messages
        ])

        # Use Q&A agent with MCP tools available
        result = await orchestrator.ask_question(
            question=chat_request.message,
            user_id=current_user.id,
            conversation_id=conversation_id,
            use_context=True
        )

        # Add assistant response to context
        mcp_server.context.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=result.get("answer", ""),
            metadata={
                "cost": result.get("cost"),
                "citations": result.get("citations", [])
            }
        )

        execution_time = (datetime.utcnow() - start_time).total_seconds()

        # Background task: log chat
        background_tasks.add_task(
            log_tool_execution,
            user_id=current_user.id,
            tool_name="mcp_chat",
            parameters={"message": chat_request.message[:100]},
            result=result,
            duration=execution_time,
            success=True
        )

        return {
            "conversation_id": conversation_id,
            "response": result.get("answer"),
            "citations": result.get("citations", []),
            "tools_used": [],  # Would be populated if tools were called
            "cost": result.get("cost"),
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"MCP chat failed: {e}", exc_info=True)
        raise AIServiceError(
            message="Chat request failed",
            details={"error": str(e)}
        )


@router.delete("/conversation/{conversation_id}", summary="Clear conversation")
async def clear_conversation(
    conversation_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, str]:
    """
    Clear conversation history.

    Removes all messages from the specified conversation while preserving
    the conversation ID for future use.

    **Example:**
    ```
    DELETE /api/mcp/conversation/conv_123
    ```
    """
    try:
        mcp_server = get_mcp_server()

        mcp_server.context.clear_conversation(conversation_id)

        logger.info(
            f"Cleared conversation {conversation_id}",
            extra={"user_id": current_user.id}
        )

        return {
            "message": "Conversation cleared successfully",
            "conversation_id": conversation_id
        }

    except Exception as e:
        logger.error(f"Failed to clear conversation: {e}", exc_info=True)
        raise AIServiceError(
            message="Failed to clear conversation",
            details={"conversation_id": conversation_id, "error": str(e)}
        )


@router.get("/stats", summary="Get MCP statistics")
async def get_mcp_stats(
    current_user: UserInDB = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get MCP server statistics.

    Returns information about:
    - Tool usage
    - Active conversations
    - Resource access patterns

    **Requires:** User authentication
    """
    mcp_server = get_mcp_server()

    stats = mcp_server.context.get_stats()

    return {
        "statistics": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health", summary="MCP health check")
async def mcp_health_check() -> Dict[str, Any]:
    """
    Check MCP server health.

    Returns health status and availability of tools/resources.
    """
    try:
        mcp_server = get_mcp_server()

        tools = mcp_server.list_tools()
        resources = mcp_server.list_resources()
        prompts = mcp_server.list_prompts()

        return {
            "status": "healthy",
            "tools_available": len(tools),
            "resources_available": len(resources),
            "prompts_available": len(prompts),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"MCP health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
