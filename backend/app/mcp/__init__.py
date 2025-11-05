"""
MCP (Model Context Protocol) Module for PM Document Intelligence.

This package provides extended AI agent capabilities through:
- Tools: Callable functions for Claude to use
- Resources: URI-based access to documents and data
- Prompts: Reusable templates for common tasks
- Context: Conversation history and state management

Usage:
    from app.mcp import get_mcp_server, initialize_mcp

    # Get MCP server
    mcp = get_mcp_server()

    # Execute a tool
    result = await mcp.call_tool("search_documents", {
        "query": "project risks",
        "user_id": "user_123"
    })

    # Access a resource
    doc = await mcp.get_resource("doc://123", user_id="user_123")

    # Get a prompt
    prompt = mcp.get_prompt_template(
        "document_analysis_prompt",
        document_name="Report.pdf",
        document_text="..."
    )
"""

from app.mcp.mcp_server import (
    MCPContext,
    PMIntelligenceMCP,
    get_mcp_server,
    initialize_mcp,
)

__all__ = [
    "PMIntelligenceMCP",
    "MCPContext",
    "get_mcp_server",
    "initialize_mcp",
]
