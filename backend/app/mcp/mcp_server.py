"""
MCP (Model Context Protocol) Server for PM Document Intelligence.

This module implements a FastMCP server that provides extended AI agent capabilities
through tools, resources, and prompt templates. Enables Claude to:
- Search and analyze documents
- Extract metrics and data
- Create action items
- Access user context
- Use structured prompts

Architecture:
- Tools: Callable functions that agents can use
- Resources: URI-based access to documents and user data
- Prompts: Reusable templates for common tasks
- Context: Conversation history and state management

Usage:
    from app.mcp.mcp_server import mcp_server, get_mcp_server

    server = get_mcp_server()
    result = await server.call_tool("search_documents", {
        "query": "project risks",
        "limit": 5
    })
"""

import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from fastmcp import FastMCP
from pydantic import BaseModel, Field, validator

from app.agents.orchestrator import get_orchestrator
from app.database import execute_insert, execute_select
from app.services.vector_search import VectorSearch
from app.utils.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Pydantic Models for Tool Parameters
# ============================================================================


class SearchDocumentsParams(BaseModel):
    """Parameters for search_documents tool."""

    query: str = Field(..., description="Natural language search query", min_length=3)
    filters: dict[str, Any] | None = Field(
        default=None, description="Optional filters (document_type, date_range, etc.)"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results to return")
    user_id: str = Field(..., description="User ID for access control")


class AnalyzeMetricsParams(BaseModel):
    """Parameters for analyze_metrics tool."""

    document_id: str = Field(..., description="Document to analyze")
    metric_types: list[str] = Field(
        default=["numerical", "dates", "percentages"],
        description="Types of metrics to extract",
    )
    user_id: str = Field(..., description="User ID for access control")


class QueryDatabaseParams(BaseModel):
    """Parameters for query_database tool."""

    query_type: str = Field(
        ...,
        description="Type of query: documents, action_items, analyses",
        pattern="^(documents|action_items|analyses|users)$",
    )
    filters: dict[str, Any] = Field(default_factory=dict, description="Filter conditions")
    limit: int = Field(default=20, ge=1, le=100)
    user_id: str = Field(..., description="User ID for access control")


class CreateActionItemParams(BaseModel):
    """Parameters for create_action_item tool."""

    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    assignee: str | None = Field(None, max_length=100)
    due_date: str | None = Field(None, description="ISO format date")
    priority: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    document_id: str | None = None
    user_id: str = Field(..., description="User ID creating the action")

    @validator("due_date")
    def validate_due_date(cls, v):
        """Validate due date is in future."""
        if v:
            try:
                date = datetime.fromisoformat(v.replace("Z", "+00:00"))
                if date < datetime.utcnow():
                    raise ValueError("Due date must be in the future")
            except ValueError as e:
                raise ValueError(f"Invalid date format: {e}")
        return v


class GetUserContextParams(BaseModel):
    """Parameters for get_user_context tool."""

    user_id: str = Field(..., description="User ID to fetch context for")
    include_preferences: bool = Field(default=True)
    include_recent_activity: bool = Field(default=True)
    activity_days: int = Field(default=30, ge=1, le=90)


# ============================================================================
# Context Management
# ============================================================================


class MCPContext:
    """Manages conversation history and agent state."""

    def __init__(self, max_history: int = 20, max_tokens: int = 100000):
        """
        Initialize context manager.

        Args:
            max_history: Maximum conversation exchanges to retain
            max_tokens: Maximum total tokens before compression
        """
        self.conversations: dict[str, list[dict[str, Any]]] = {}
        self.agent_state: dict[str, dict[str, Any]] = {}
        self.max_history = max_history
        self.max_tokens = max_tokens
        self.tool_usage_stats: dict[str, int] = {}

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add message to conversation history.

        Args:
            conversation_id: Unique conversation identifier
            role: Message role (user, assistant, tool)
            content: Message content
            metadata: Optional metadata (tool calls, etc.)
        """
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        self.conversations[conversation_id].append(message)

        # Trim if exceeds max history
        if len(self.conversations[conversation_id]) > self.max_history:
            # Keep first message (usually contains important context)
            # and most recent messages
            first_msg = self.conversations[conversation_id][0]
            recent_msgs = self.conversations[conversation_id][-(self.max_history - 1) :]
            self.conversations[conversation_id] = [first_msg] + recent_msgs

        logger.debug(f"Added message to conversation {conversation_id}")

    def get_conversation(self, conversation_id: str) -> list[dict[str, Any]]:
        """Get conversation history."""
        return self.conversations.get(conversation_id, [])

    def clear_conversation(self, conversation_id: str) -> None:
        """Clear conversation history."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
        logger.info(f"Cleared conversation {conversation_id}")

    def set_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Set agent state."""
        self.agent_state[agent_id] = {
            **state,
            "updated_at": datetime.utcnow().isoformat(),
        }

    def get_agent_state(self, agent_id: str) -> dict[str, Any]:
        """Get agent state."""
        return self.agent_state.get(agent_id, {})

    def record_tool_usage(self, tool_name: str) -> None:
        """Record tool usage for analytics."""
        self.tool_usage_stats[tool_name] = self.tool_usage_stats.get(tool_name, 0) + 1

    def get_stats(self) -> dict[str, Any]:
        """Get context manager statistics."""
        total_conversations = len(self.conversations)
        total_messages = sum(len(conv) for conv in self.conversations.values())

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "active_agents": len(self.agent_state),
            "tool_usage": self.tool_usage_stats,
        }


# ============================================================================
# MCP Server Implementation
# ============================================================================


class PMIntelligenceMCP:
    """MCP Server for PM Document Intelligence."""

    def __init__(self):
        """Initialize MCP server."""
        self.server = FastMCP("PM Document Intelligence MCP Server")
        self.context = MCPContext()
        self.vector_search = VectorSearch()
        self.orchestrator = get_orchestrator()

        # Register all components
        self._register_tools()
        self._register_resources()
        self._register_prompts()

        logger.info("MCP Server initialized with tools, resources, and prompts")

    # ========================================================================
    # Tool Implementations
    # ========================================================================

    async def search_documents(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        user_id: str = None,
    ) -> dict[str, Any]:
        """
        Search documents using semantic search.

        This tool enables Claude to find relevant documents based on natural
        language queries. Uses vector embeddings for semantic understanding.

        Args:
            query: Natural language search query
            filters: Optional filters (document_type, date_range)
            limit: Maximum results (1-50)
            user_id: User ID for access control

        Returns:
            Dict with search results including snippets and metadata

        Example:
            result = await search_documents(
                query="What are the project risks?",
                filters={"document_type": "meeting_notes"},
                limit=5,
                user_id="user_123"
            )
        """
        try:
            # Validate parameters
            params = SearchDocumentsParams(
                query=query, filters=filters, limit=limit, user_id=user_id
            )

            logger.info(f"MCP Tool: search_documents - query='{query[:50]}...'")

            # Perform semantic search
            search_results = await self.vector_search.semantic_search(
                query=params.query,
                user_id=params.user_id,
                limit=params.limit,
                similarity_threshold=0.7,
                use_cache=True,
            )

            # Apply additional filters if provided
            filtered_results = search_results["results"]
            if params.filters:
                filtered_results = self._apply_filters(filtered_results, params.filters)

            # Format for Claude
            formatted_results = []
            for result in filtered_results[: params.limit]:
                formatted_results.append(
                    {
                        "document_id": result["document_id"],
                        "filename": result["filename"],
                        "snippet": result["matched_chunk"]["text"][:500],
                        "relevance_score": result["similarity_score"],
                        "metadata": {
                            "document_type": result.get("document_type"),
                            "created_at": result.get("created_at"),
                            "chunk_index": result["matched_chunk"]["chunk_index"],
                        },
                    }
                )

            self.context.record_tool_usage("search_documents")

            return {
                "success": True,
                "query": params.query,
                "total_results": len(formatted_results),
                "results": formatted_results,
                "search_metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "filters_applied": params.filters or {},
                },
            }

        except Exception as e:
            logger.error(f"search_documents failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "tool": "search_documents"}

    async def analyze_metrics(
        self, document_id: str, metric_types: list[str] = None, user_id: str = None
    ) -> dict[str, Any]:
        """
        Extract and analyze quantitative metrics from documents.

        Identifies numerical data, percentages, dates, and other measurable
        values in documents. Useful for executive summaries and dashboards.

        Args:
            document_id: Document to analyze
            metric_types: Types to extract (numerical, dates, percentages, etc.)
            user_id: User ID for access control

        Returns:
            Structured metric data with context

        Example:
            metrics = await analyze_metrics(
                document_id="doc_123",
                metric_types=["numerical", "percentages"],
                user_id="user_123"
            )
        """
        try:
            params = AnalyzeMetricsParams(
                document_id=document_id,
                metric_types=metric_types or ["numerical", "dates", "percentages"],
                user_id=user_id,
            )

            logger.info(f"MCP Tool: analyze_metrics - doc={document_id}")

            # Get document text
            documents = await execute_select(
                "documents",
                columns="extracted_text, filename, document_type",
                match={"id": params.document_id, "user_id": params.user_id},
            )

            if not documents:
                raise NotFoundError(f"Document {document_id} not found")

            text = documents[0]["extracted_text"]

            # Extract metrics using regex patterns
            metrics = {}

            if "numerical" in params.metric_types:
                # Extract numbers with context
                metrics["numerical"] = self._extract_numerical_metrics(text)

            if "percentages" in params.metric_types:
                # Extract percentages
                metrics["percentages"] = self._extract_percentages(text)

            if "dates" in params.metric_types:
                # Extract dates and deadlines
                metrics["dates"] = self._extract_dates(text)

            if "currency" in params.metric_types:
                # Extract monetary values
                metrics["currency"] = self._extract_currency(text)

            self.context.record_tool_usage("analyze_metrics")

            return {
                "success": True,
                "document_id": params.document_id,
                "document_name": documents[0]["filename"],
                "metrics": metrics,
                "summary": {
                    "total_metrics_found": sum(len(v) for v in metrics.values()),
                    "metric_types": list(metrics.keys()),
                },
            }

        except Exception as e:
            logger.error(f"analyze_metrics failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "tool": "analyze_metrics"}

    async def query_database(
        self,
        query_type: str,
        filters: dict[str, Any] = None,
        limit: int = 20,
        user_id: str = None,
    ) -> dict[str, Any]:
        """
        Safe database queries for data retrieval.

        Provides structured access to database entities with built-in
        access control and SQL injection prevention.

        Args:
            query_type: Type of query (documents, action_items, analyses)
            filters: Filter conditions
            limit: Maximum results
            user_id: User ID for access control

        Returns:
            Filtered database results

        Example:
            items = await query_database(
                query_type="action_items",
                filters={"priority": "HIGH", "status": "TODO"},
                limit=10,
                user_id="user_123"
            )
        """
        try:
            params = QueryDatabaseParams(
                query_type=query_type,
                filters=filters or {},
                limit=limit,
                user_id=user_id,
            )

            logger.info(f"MCP Tool: query_database - type={query_type}")

            # Map query types to tables
            table_map = {
                "documents": "documents",
                "action_items": "action_items",
                "analyses": "analyses",
            }

            if params.query_type not in table_map:
                raise ValidationError(f"Invalid query_type: {params.query_type}")

            table = table_map[params.query_type]

            # Build safe filter (user_id always enforced)
            safe_filters = {
                "user_id": params.user_id,
                **self._sanitize_filters(params.filters),
            }

            # Execute query
            results = await execute_select(table, match=safe_filters, limit=params.limit)

            self.context.record_tool_usage("query_database")

            return {
                "success": True,
                "query_type": params.query_type,
                "total_results": len(results),
                "results": results,
                "filters_applied": safe_filters,
            }

        except Exception as e:
            logger.error(f"query_database failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "tool": "query_database"}

    async def create_action_item(
        self,
        title: str,
        description: str,
        assignee: str | None = None,
        due_date: str | None = None,
        priority: str = "MEDIUM",
        document_id: str | None = None,
        user_id: str = None,
    ) -> dict[str, Any]:
        """
        Create new action items in the system.

        Allows Claude to create actionable tasks based on document analysis
        or conversation context.

        Args:
            title: Action item title
            description: Detailed description
            assignee: Person responsible
            due_date: Due date (ISO format)
            priority: Priority level (LOW, MEDIUM, HIGH, CRITICAL)
            document_id: Optional source document
            user_id: User creating the action

        Returns:
            Created action item with ID

        Example:
            item = await create_action_item(
                title="Complete security audit",
                description="Review authentication system for vulnerabilities",
                assignee="Security Team",
                due_date="2024-12-31T23:59:59Z",
                priority="HIGH",
                user_id="user_123"
            )
        """
        try:
            params = CreateActionItemParams(
                title=title,
                description=description,
                assignee=assignee,
                due_date=due_date,
                priority=priority,
                document_id=document_id,
                user_id=user_id,
            )

            logger.info(f"MCP Tool: create_action_item - title='{title}'")

            # Create action item
            action_item = {
                "title": params.title,
                "description": params.description,
                "assignee": params.assignee,
                "due_date": params.due_date,
                "priority": params.priority,
                "status": "TODO",
                "document_id": params.document_id,
                "user_id": params.user_id,
                "created_at": datetime.utcnow().isoformat(),
                "created_via": "mcp_tool",
            }

            # Insert into database
            result = await execute_insert("action_items", action_item)

            self.context.record_tool_usage("create_action_item")

            return {
                "success": True,
                "action_item_id": result.get("id"),
                "action_item": action_item,
                "message": f"Action item '{title}' created successfully",
            }

        except Exception as e:
            logger.error(f"create_action_item failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "tool": "create_action_item"}

    async def get_user_context(
        self,
        user_id: str,
        include_preferences: bool = True,
        include_recent_activity: bool = True,
        activity_days: int = 30,
    ) -> dict[str, Any]:
        """
        Retrieve user preferences and history for personalization.

        Provides Claude with context about user preferences, recent activity,
        and interaction patterns for personalized responses.

        Args:
            user_id: User ID to fetch context for
            include_preferences: Include user preferences
            include_recent_activity: Include recent activity
            activity_days: Days of activity to fetch (1-90)

        Returns:
            User context including preferences and activity

        Example:
            context = await get_user_context(
                user_id="user_123",
                include_preferences=True,
                include_recent_activity=True,
                activity_days=30
            )
        """
        try:
            params = GetUserContextParams(
                user_id=user_id,
                include_preferences=include_preferences,
                include_recent_activity=include_recent_activity,
                activity_days=activity_days,
            )

            logger.info(f"MCP Tool: get_user_context - user={user_id}")

            context = {"user_id": params.user_id}

            # Get user profile
            users = await execute_select(
                "users",
                columns="id, email, username, role, created_at",
                match={"id": params.user_id},
            )

            if not users:
                raise NotFoundError(f"User {user_id} not found")

            context["profile"] = users[0]

            # Get preferences
            if params.include_preferences:
                preferences = await execute_select(
                    "user_preferences", match={"user_id": params.user_id}
                )
                context["preferences"] = preferences[0] if preferences else {}

            # Get recent activity
            if params.include_recent_activity:
                datetime.utcnow() - timedelta(days=params.activity_days)

                # Recent documents
                recent_docs = await execute_select(
                    "documents",
                    columns="id, filename, document_type, created_at",
                    match={"user_id": params.user_id},
                    limit=10,
                )

                # Recent searches (from audit log if available)
                # This would query an audit_log table

                context["recent_activity"] = {
                    "recent_documents": recent_docs,
                    "activity_period_days": params.activity_days,
                }

            self.context.record_tool_usage("get_user_context")

            return {
                "success": True,
                "context": context,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"get_user_context failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "tool": "get_user_context"}

    # ========================================================================
    # Resource Handlers
    # ========================================================================

    async def get_document_resource(self, uri: str, user_id: str) -> dict[str, Any]:
        """
        Get document resource by URI.

        URI scheme: doc://{document_id}

        Args:
            uri: Resource URI
            user_id: User ID for access control

        Returns:
            Document resource with metadata
        """
        try:
            # Parse URI
            parsed = urlparse(uri)
            if parsed.scheme != "doc":
                raise ValidationError(f"Invalid URI scheme: {parsed.scheme}")

            document_id = parsed.netloc or parsed.path.lstrip("/")

            logger.info(f"MCP Resource: document - {document_id}")

            # Get document with access control
            documents = await execute_select(
                "documents", match={"id": document_id, "user_id": user_id}
            )

            if not documents:
                raise NotFoundError(f"Document {document_id} not found")

            document = documents[0]

            return {
                "uri": uri,
                "type": "document",
                "data": document,
                "metadata": {
                    "document_type": document.get("document_type"),
                    "status": document.get("processing_status"),
                    "created_at": document.get("created_at"),
                    "file_size": document.get("file_size"),
                },
                "access_control": {
                    "owner": user_id,
                    "permissions": ["read", "write", "delete"],
                },
            }

        except Exception as e:
            logger.error(f"get_document_resource failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "uri": uri}

    async def get_user_resource(self, uri: str, requesting_user_id: str) -> dict[str, Any]:
        """
        Get user resource by URI.

        URI scheme: user://{user_id}

        Args:
            uri: Resource URI
            requesting_user_id: User making the request

        Returns:
            User resource with privacy controls
        """
        try:
            parsed = urlparse(uri)
            if parsed.scheme != "user":
                raise ValidationError(f"Invalid URI scheme: {parsed.scheme}")

            user_id = parsed.netloc or parsed.path.lstrip("/")

            logger.info(f"MCP Resource: user - {user_id}")

            # Check access (users can only access their own profile via MCP)
            if user_id != requesting_user_id:
                raise AuthorizationError("Cannot access other user profiles")

            # Get user data
            users = await execute_select(
                "users",
                columns="id, email, username, role, created_at",
                match={"id": user_id},
            )

            if not users:
                raise NotFoundError(f"User {user_id} not found")

            user = users[0]

            # Get preferences
            preferences = await execute_select("user_preferences", match={"user_id": user_id})

            return {
                "uri": uri,
                "type": "user",
                "data": {
                    "profile": user,
                    "preferences": preferences[0] if preferences else {},
                },
                "metadata": {
                    "role": user.get("role"),
                    "member_since": user.get("created_at"),
                },
                "privacy": {
                    "email_visible": False,  # Controlled by privacy settings
                    "activity_visible": True,
                },
            }

        except Exception as e:
            logger.error(f"get_user_resource failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "uri": uri}

    # ========================================================================
    # Prompt Templates
    # ========================================================================

    def get_prompt_template(self, template_name: str, **variables) -> str:
        """
        Get prompt template with variable substitution.

        Args:
            template_name: Template name
            **variables: Variables to substitute

        Returns:
            Formatted prompt
        """
        templates = {
            "document_analysis_prompt": """Analyze the following document and provide comprehensive insights:

Document: {document_name}
Type: {document_type}

Content:
{document_text}

Please provide:
1. Executive Summary (2-3 sentences)
2. Key Insights (3-5 bullet points)
3. Patterns and Trends Identified
4. Recommendations (with priority levels)
5. Risks and Concerns
6. Opportunities

Be specific and reference exact details from the document. Focus on actionable insights for project managers.""",
            "action_item_extraction_prompt": """Extract action items from this document:

Document: {document_name}

Content:
{document_text}

For each action item, identify:
- Action: What needs to be done
- Assignee: Who is responsible (if mentioned)
- Due Date: When it should be completed (if mentioned)
- Priority: Urgency level (HIGH/MEDIUM/LOW)
- Status: Current state (TODO/IN_PROGRESS/DONE)
- Dependencies: Other items that must be completed first

Return a structured list of all action items found.""",
            "executive_summary_prompt": """Create an executive summary for this document:

Document: {document_name}
Intended Audience: {audience}
Desired Length: {length}

Content:
{document_text}

Create a {length} summary suitable for {audience}. Focus on:
- Key decisions made
- Critical issues requiring attention
- Next steps
- Budget or timeline implications

Use clear, concise language appropriate for busy executives.""",
            "qa_with_context_prompt": """Answer the following question using the provided document context.

Question: {question}

Relevant Context:
{context}

Previous Conversation:
{conversation_history}

Please answer the question based on the context provided. If the information isn't available in the context, clearly state that. Cite specific parts of the documents when possible using [Document: filename] format.

Be concise but thorough. If the question relates to previous conversation, maintain context continuity.""",
        }

        template = templates.get(template_name)
        if not template:
            raise ValidationError(f"Unknown template: {template_name}")

        try:
            return template.format(**variables)
        except KeyError as e:
            raise ValidationError(f"Missing template variable: {e}")

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _apply_filters(
        self, results: list[dict[str, Any]], filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Apply additional filters to search results."""
        filtered = results

        if "document_type" in filters:
            filtered = [r for r in filtered if r.get("document_type") == filters["document_type"]]

        if "date_range" in filters:
            start = filters["date_range"].get("start")
            end = filters["date_range"].get("end")
            # Filter by date range
            filtered = [r for r in filtered if self._in_date_range(r.get("created_at"), start, end)]

        return filtered

    def _in_date_range(
        self, date_str: str | None, start: str | None, end: str | None
    ) -> bool:
        """Check if date is in range."""
        if not date_str:
            return False

        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if start:
                start_date = datetime.fromisoformat(start.replace("Z", "+00:00"))
                if date < start_date:
                    return False
            if end:
                end_date = datetime.fromisoformat(end.replace("Z", "+00:00"))
                if date > end_date:
                    return False
            return True
        except:
            return False

    def _sanitize_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Sanitize filter values to prevent SQL injection."""
        safe_filters = {}

        allowed_fields = {
            "document_type",
            "status",
            "priority",
            "processing_status",
            "created_at",
            "updated_at",
        }

        for key, value in filters.items():
            if key in allowed_fields:
                # Sanitize value
                if isinstance(value, str):
                    # Remove potential SQL injection attempts
                    safe_value = re.sub(r"[;'\"]", "", value)
                    safe_filters[key] = safe_value
                else:
                    safe_filters[key] = value

        return safe_filters

    def _extract_numerical_metrics(self, text: str) -> list[dict[str, Any]]:
        """Extract numerical metrics with context."""
        pattern = r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*([A-Za-z%]*)"
        matches = re.finditer(pattern, text)

        metrics = []
        for match in matches:
            number = match.group(1).replace(",", "")
            unit = match.group(2)

            # Get context (surrounding text)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end]

            try:
                value = float(number)
                metrics.append(
                    {
                        "value": value,
                        "unit": unit or "count",
                        "context": context.strip(),
                        "position": match.start(),
                    }
                )
            except ValueError:
                continue

        return metrics[:20]  # Limit to top 20

    def _extract_percentages(self, text: str) -> list[dict[str, Any]]:
        """Extract percentage values."""
        pattern = r"(\d+(?:\.\d+)?)\s*%"
        matches = re.finditer(pattern, text)

        percentages = []
        for match in matches:
            value = float(match.group(1))
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end]

            percentages.append(
                {"value": value, "context": context.strip(), "position": match.start()}
            )

        return percentages

    def _extract_dates(self, text: str) -> list[dict[str, Any]]:
        """Extract dates and deadlines."""
        # Match various date formats
        patterns = [
            r"\d{4}-\d{2}-\d{2}",  # ISO format
            r"\d{1,2}/\d{1,2}/\d{4}",  # MM/DD/YYYY
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}",  # Month DD, YYYY
        ]

        dates = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]

                dates.append(
                    {
                        "date": match.group(0),
                        "context": context.strip(),
                        "position": match.start(),
                    }
                )

        return dates

    def _extract_currency(self, text: str) -> list[dict[str, Any]]:
        """Extract monetary values."""
        pattern = r"[$€£¥]\s*(\d+(?:,\d{3})*(?:\.\d{2})?)"
        matches = re.finditer(pattern, text)

        currency = []
        for match in matches:
            amount = match.group(1).replace(",", "")
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end]

            try:
                value = float(amount)
                currency.append(
                    {
                        "amount": value,
                        "currency_symbol": match.group(0)[0],
                        "context": context.strip(),
                        "position": match.start(),
                    }
                )
            except ValueError:
                continue

        return currency

    # ========================================================================
    # Registration Methods
    # ========================================================================

    def _register_tools(self) -> None:
        """Register all MCP tools."""
        tools = [
            {
                "name": "search_documents",
                "description": "Search documents using natural language queries. Returns relevant documents with snippets.",
                "parameters": SearchDocumentsParams.schema(),
                "handler": self.search_documents,
            },
            {
                "name": "analyze_metrics",
                "description": "Extract and analyze quantitative metrics (numbers, percentages, dates) from documents.",
                "parameters": AnalyzeMetricsParams.schema(),
                "handler": self.analyze_metrics,
            },
            {
                "name": "query_database",
                "description": "Query database for documents, action items, or analyses with filters.",
                "parameters": QueryDatabaseParams.schema(),
                "handler": self.query_database,
            },
            {
                "name": "create_action_item",
                "description": "Create a new action item with title, description, assignee, and due date.",
                "parameters": CreateActionItemParams.schema(),
                "handler": self.create_action_item,
            },
            {
                "name": "get_user_context",
                "description": "Retrieve user preferences and recent activity for personalized responses.",
                "parameters": GetUserContextParams.schema(),
                "handler": self.get_user_context,
            },
        ]

        for tool in tools:
            logger.info(f"Registered MCP tool: {tool['name']}")

        self.tools = {tool["name"]: tool for tool in tools}

    def _register_resources(self) -> None:
        """Register resource handlers."""
        self.resource_handlers = {
            "doc": self.get_document_resource,
            "user": self.get_user_resource,
        }

        logger.info("Registered MCP resource handlers: doc://, user://")

    def _register_prompts(self) -> None:
        """Register prompt templates."""
        prompt_names = [
            "document_analysis_prompt",
            "action_item_extraction_prompt",
            "executive_summary_prompt",
            "qa_with_context_prompt",
        ]

        self.prompts = {name: name for name in prompt_names}
        logger.info(f"Registered {len(prompt_names)} MCP prompt templates")

    # ========================================================================
    # Public API
    # ========================================================================

    async def call_tool(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """
        Call an MCP tool.

        Args:
            tool_name: Name of tool to call
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            raise ValidationError(f"Unknown tool: {tool_name}")

        tool = self.tools[tool_name]
        handler = tool["handler"]

        start_time = datetime.utcnow()

        try:
            result = await handler(**parameters)

            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"MCP tool '{tool_name}' completed",
                extra={"duration": duration, "success": result.get("success", True)},
            )

            return result

        except Exception as e:
            logger.error(f"MCP tool '{tool_name}' failed: {e}", exc_info=True)
            raise

    async def get_resource(self, uri: str, user_id: str) -> dict[str, Any]:
        """
        Get resource by URI.

        Args:
            uri: Resource URI (e.g., doc://123, user://456)
            user_id: User ID for access control

        Returns:
            Resource data
        """
        parsed = urlparse(uri)
        scheme = parsed.scheme

        if scheme not in self.resource_handlers:
            raise ValidationError(f"Unknown resource scheme: {scheme}")

        handler = self.resource_handlers[scheme]
        return await handler(uri, user_id)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools."""
        return [
            {
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
            for name, tool in self.tools.items()
        ]

    def list_resources(self) -> list[dict[str, str]]:
        """List available resource schemes."""
        return [
            {
                "scheme": scheme,
                "description": f"Access {scheme} resources",
                "uri_format": f"{scheme}://{{id}}",
            }
            for scheme in self.resource_handlers.keys()
        ]

    def list_prompts(self) -> list[str]:
        """List available prompt templates."""
        return list(self.prompts.keys())


# ============================================================================
# Global MCP Server Instance
# ============================================================================

_mcp_server: PMIntelligenceMCP | None = None


def get_mcp_server() -> PMIntelligenceMCP:
    """
    Get global MCP server instance.

    Returns:
        PMIntelligenceMCP instance
    """
    global _mcp_server

    if _mcp_server is None:
        _mcp_server = PMIntelligenceMCP()

    return _mcp_server


def initialize_mcp() -> PMIntelligenceMCP:
    """
    Initialize MCP server (called during app startup).

    Returns:
        Configured MCP server
    """
    server = get_mcp_server()
    logger.info("MCP Server initialized successfully")
    return server
