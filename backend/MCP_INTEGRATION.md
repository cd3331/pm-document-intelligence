# MCP (Model Context Protocol) Integration

Comprehensive guide to the MCP integration for PM Document Intelligence, enabling extended AI agent capabilities through tools, resources, and prompt templates.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tools](#tools)
- [Resources](#resources)
- [Prompt Templates](#prompt-templates)
- [Context Management](#context-management)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Security](#security)
- [Best Practices](#best-practices)

---

## Overview

MCP (Model Context Protocol) extends Claude's capabilities by providing:

1. **Tools**: Callable functions that Claude can use to perform actions
2. **Resources**: URI-based access to documents and data
3. **Prompts**: Reusable templates for common tasks
4. **Context**: Conversation history and state management

### Key Features

- ✅ **5 Specialized Tools** for search, analysis, and data management
- ✅ **URI-based Resources** for documents and users
- ✅ **4 Prompt Templates** for common AI tasks
- ✅ **Conversation Context** with automatic management
- ✅ **Full Access Control** with user authentication
- ✅ **Audit Logging** for all tool executions
- ✅ **Cost Tracking** for AI operations
- ✅ **Tool Composability** for complex workflows

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              MCP API Endpoints                       │
│         POST /api/mcp/execute                        │
│         POST /api/mcp/chat                           │
│         GET  /api/mcp/tools                          │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │   PMIntelligenceMCP      │
        │      (MCP Server)        │
        └────────┬─────────────────┘
                 │
        ┌────────┼────────────┐
        │        │            │
        ▼        ▼            ▼
   ┌───────┐ ┌─────────┐ ┌────────┐
   │ Tools │ │Resources│ │Prompts │
   └───┬───┘ └────┬────┘ └───┬────┘
       │          │          │
       ▼          ▼          ▼
┌──────────────────────────────────┐
│      Backend Services             │
│  • VectorSearch                   │
│  • AgentOrchestrator              │
│  • Database                       │
│  • AWS Services                   │
└───────────────────────────────────┘
```

### Component Flow

```
User Request → MCP API → MCP Server → Tool Execution → Service Call → Result
                    ↓
              Context Manager (stores history)
                    ↓
              Audit Logger (tracks usage)
```

---

## Tools

MCP provides 5 specialized tools that Claude can use to perform actions.

### 1. search_documents

Search documents using semantic search with natural language queries.

**When to Use:**
- Finding relevant documents
- Discovering related content
- Answering questions about past documents

**Parameters:**

```python
{
    "query": str,           # Natural language search query
    "filters": dict,        # Optional filters (document_type, date_range)
    "limit": int,           # Max results (1-50, default: 10)
    "user_id": str          # User ID (auto-injected)
}
```

**Returns:**

```json
{
    "success": true,
    "query": "project risks",
    "total_results": 5,
    "results": [
        {
            "document_id": "doc_123",
            "filename": "Project Plan.pdf",
            "snippet": "The project faces several risks including...",
            "relevance_score": 0.89,
            "metadata": {
                "document_type": "project_plan",
                "created_at": "2024-12-01",
                "chunk_index": 2
            }
        }
    ]
}
```

**Example:**

```python
result = await mcp.call_tool("search_documents", {
    "query": "What are the budget concerns?",
    "filters": {"document_type": "financial_report"},
    "limit": 5,
    "user_id": "user_123"
})
```

---

### 2. analyze_metrics

Extract and analyze quantitative metrics from documents.

**When to Use:**
- Extracting numerical data
- Finding percentages and statistics
- Identifying dates and deadlines
- Analyzing financial data

**Parameters:**

```python
{
    "document_id": str,                          # Document to analyze
    "metric_types": List[str],                   # Types to extract
    "user_id": str                               # User ID (auto-injected)
}
```

**Metric Types:**
- `numerical`: Numbers with context
- `percentages`: Percentage values
- `dates`: Dates and deadlines
- `currency`: Monetary values

**Returns:**

```json
{
    "success": true,
    "document_id": "doc_123",
    "document_name": "Q4 Report.pdf",
    "metrics": {
        "numerical": [
            {
                "value": 15.5,
                "unit": "percent",
                "context": "budget overrun by 15.5%",
                "position": 342
            }
        ],
        "percentages": [
            {"value": 90, "context": "90% completion rate"}
        ],
        "dates": [
            {"date": "2024-12-31", "context": "deadline: Dec 31, 2024"}
        ],
        "currency": [
            {
                "amount": 50000,
                "currency_symbol": "$",
                "context": "$50,000 budget allocation"
            }
        ]
    },
    "summary": {
        "total_metrics_found": 15,
        "metric_types": ["numerical", "percentages", "dates", "currency"]
    }
}
```

**Example:**

```python
metrics = await mcp.call_tool("analyze_metrics", {
    "document_id": "doc_123",
    "metric_types": ["numerical", "percentages", "currency"],
    "user_id": "user_123"
})
```

---

### 3. query_database

Safe database queries for structured data retrieval.

**When to Use:**
- Listing documents or action items
- Filtering by status or priority
- Retrieving user data
- Finding specific records

**Parameters:**

```python
{
    "query_type": str,      # documents | action_items | analyses
    "filters": dict,        # Filter conditions
    "limit": int,           # Max results (1-100, default: 20)
    "user_id": str          # User ID (auto-injected)
}
```

**Supported Query Types:**
- `documents`: User's documents
- `action_items`: Action items and tasks
- `analyses`: Analysis results

**Returns:**

```json
{
    "success": true,
    "query_type": "action_items",
    "total_results": 3,
    "results": [
        {
            "id": "action_456",
            "title": "Complete security audit",
            "priority": "HIGH",
            "status": "TODO",
            "due_date": "2024-12-31"
        }
    ],
    "filters_applied": {
        "user_id": "user_123",
        "priority": "HIGH",
        "status": "TODO"
    }
}
```

**Example:**

```python
# Get high-priority TODO items
items = await mcp.call_tool("query_database", {
    "query_type": "action_items",
    "filters": {
        "priority": "HIGH",
        "status": "TODO"
    },
    "limit": 10,
    "user_id": "user_123"
})
```

**Security:**
- SQL injection prevention through parameterized queries
- User ID always enforced for access control
- Only allowed fields can be filtered

---

### 4. create_action_item

Create new action items in the system.

**When to Use:**
- Creating tasks from document analysis
- Recording action items from meetings
- Setting up follow-up tasks
- Assigning responsibilities

**Parameters:**

```python
{
    "title": str,              # Action item title (3-200 chars)
    "description": str,        # Detailed description (10-2000 chars)
    "assignee": str,           # Person responsible (optional)
    "due_date": str,           # ISO format date (optional)
    "priority": str,           # LOW | MEDIUM | HIGH | CRITICAL
    "document_id": str,        # Source document (optional)
    "user_id": str             # User creating (auto-injected)
}
```

**Returns:**

```json
{
    "success": true,
    "action_item_id": "action_789",
    "action_item": {
        "title": "Complete security audit",
        "description": "Review authentication system for vulnerabilities",
        "assignee": "Security Team",
        "due_date": "2024-12-31T23:59:59Z",
        "priority": "HIGH",
        "status": "TODO",
        "created_at": "2024-12-15T10:00:00Z"
    },
    "message": "Action item 'Complete security audit' created successfully"
}
```

**Example:**

```python
item = await mcp.call_tool("create_action_item", {
    "title": "Review project budget",
    "description": "Analyze Q4 budget and identify cost savings",
    "assignee": "Finance Team",
    "due_date": "2024-12-20T17:00:00Z",
    "priority": "HIGH",
    "document_id": "doc_123",
    "user_id": "user_123"
})
```

**Validation:**
- Due date must be in the future
- Title and description have length constraints
- Priority must be one of the allowed values

---

### 5. get_user_context

Retrieve user preferences and recent activity for personalization.

**When to Use:**
- Personalizing responses
- Understanding user preferences
- Tailoring recommendations
- Providing context-aware assistance

**Parameters:**

```python
{
    "user_id": str,                    # User ID to fetch
    "include_preferences": bool,       # Include preferences (default: true)
    "include_recent_activity": bool,   # Include activity (default: true)
    "activity_days": int               # Days of activity (1-90, default: 30)
}
```

**Returns:**

```json
{
    "success": true,
    "context": {
        "user_id": "user_123",
        "profile": {
            "id": "user_123",
            "email": "user@example.com",
            "username": "john_doe",
            "role": "project_manager",
            "created_at": "2024-01-15"
        },
        "preferences": {
            "default_document_type": "meeting_notes",
            "summary_length": "medium",
            "notification_enabled": true
        },
        "recent_activity": {
            "recent_documents": [
                {
                    "id": "doc_123",
                    "filename": "Project Plan.pdf",
                    "document_type": "project_plan",
                    "created_at": "2024-12-10"
                }
            ],
            "activity_period_days": 30
        }
    },
    "timestamp": "2024-12-15T10:00:00Z"
}
```

**Example:**

```python
context = await mcp.call_tool("get_user_context", {
    "user_id": "user_123",
    "include_preferences": True,
    "include_recent_activity": True,
    "activity_days": 30
})
```

---

## Resources

Resources provide URI-based access to documents and user data.

### Document Resources

**URI Format:** `doc://{document_id}`

**Access Control:** Users can only access their own documents

**Example:**

```python
resource = await mcp.get_resource("doc://doc_123", user_id="user_123")

# Returns:
{
    "uri": "doc://doc_123",
    "type": "document",
    "data": {
        "id": "doc_123",
        "filename": "Project Plan.pdf",
        "extracted_text": "...",
        "processing_status": "completed"
    },
    "metadata": {
        "document_type": "project_plan",
        "status": "completed",
        "created_at": "2024-12-01",
        "file_size": 1048576
    },
    "access_control": {
        "owner": "user_123",
        "permissions": ["read", "write", "delete"]
    }
}
```

### User Resources

**URI Format:** `user://{user_id}`

**Access Control:** Users can only access their own profile

**Privacy Controls:**
- Email visibility controlled by settings
- Activity visibility customizable

**Example:**

```python
resource = await mcp.get_resource("user://user_123", user_id="user_123")

# Returns:
{
    "uri": "user://user_123",
    "type": "user",
    "data": {
        "profile": {
            "id": "user_123",
            "username": "john_doe",
            "role": "project_manager"
        },
        "preferences": {...}
    },
    "metadata": {
        "role": "project_manager",
        "member_since": "2024-01-15"
    },
    "privacy": {
        "email_visible": false,
        "activity_visible": true
    }
}
```

---

## Prompt Templates

Reusable templates for common AI tasks with variable substitution.

### Available Templates

#### 1. document_analysis_prompt

For comprehensive document analysis.

**Variables:**
- `document_name`: Name of the document
- `document_type`: Type (e.g., meeting_notes, financial_report)
- `document_text`: Full document text

**Example:**

```python
prompt = mcp.get_prompt_template(
    "document_analysis_prompt",
    document_name="Q4 Meeting Notes.pdf",
    document_type="meeting_notes",
    document_text="[Full document text...]"
)
```

#### 2. action_item_extraction_prompt

For extracting action items from documents.

**Variables:**
- `document_name`: Document name
- `document_text`: Document content

#### 3. executive_summary_prompt

For creating executive summaries.

**Variables:**
- `document_name`: Document name
- `audience`: Target audience (executive, technical, team)
- `length`: Summary length (brief, medium, comprehensive)
- `document_text`: Document content

#### 4. qa_with_context_prompt

For question answering with document context.

**Variables:**
- `question`: User's question
- `context`: Retrieved document context
- `conversation_history`: Previous conversation

---

## Context Management

### MCPContext

Manages conversation history and agent state.

**Features:**
- Automatic message history (up to 20 exchanges)
- Agent state persistence
- Token limit management
- Tool usage tracking

**Usage:**

```python
from app.mcp import get_mcp_server

mcp = get_mcp_server()

# Add message
mcp.context.add_message(
    conversation_id="conv_123",
    role="user",
    content="What are the project risks?",
    metadata={"timestamp": "2024-12-15T10:00:00Z"}
)

# Get conversation history
history = mcp.context.get_conversation("conv_123")

# Clear conversation
mcp.context.clear_conversation("conv_123")

# Get statistics
stats = mcp.context.get_stats()
```

**Statistics:**

```json
{
    "total_conversations": 15,
    "total_messages": 150,
    "active_agents": 5,
    "tool_usage": {
        "search_documents": 45,
        "analyze_metrics": 20,
        "create_action_item": 10
    }
}
```

---

## API Reference

### POST /api/mcp/execute

Execute an MCP tool.

**Request:**

```json
{
    "tool_name": "search_documents",
    "parameters": {
        "query": "project risks",
        "limit": 5
    },
    "conversation_id": "conv_123",
    "track_cost": true
}
```

**Response:**

```json
{
    "success": true,
    "tool_name": "search_documents",
    "result": {...},
    "execution_time": 1.23,
    "cost": 0.002,
    "timestamp": "2024-12-15T10:00:00Z"
}
```

**Rate Limit:** 60 requests/minute

---

### GET /api/mcp/tools

List all available MCP tools.

**Response:**

```json
[
    {
        "name": "search_documents",
        "description": "Search documents using natural language",
        "parameters": {...},
        "example_usage": "Find all documents mentioning 'budget overrun'"
    }
]
```

---

### POST /api/mcp/chat

Chat with an MCP-enabled agent.

**Request:**

```json
{
    "message": "Search for project risks and create action items",
    "conversation_id": "conv_123",
    "allow_tools": true,
    "context": {
        "project_id": "proj_456"
    }
}
```

**Response:**

```json
{
    "conversation_id": "conv_123",
    "response": "I found 3 project risks and created action items for each...",
    "citations": [...],
    "tools_used": ["search_documents", "create_action_item"],
    "cost": 0.005,
    "execution_time": 2.5,
    "timestamp": "2024-12-15T10:00:00Z"
}
```

**Rate Limit:** 30 requests/minute

---

## Usage Examples

### Example 1: Search and Analyze

```python
from app.mcp import get_mcp_server

mcp = get_mcp_server()

# 1. Search for relevant documents
search_result = await mcp.call_tool("search_documents", {
    "query": "budget overruns",
    "filters": {"document_type": "financial_report"},
    "limit": 5,
    "user_id": "user_123"
})

# 2. Analyze metrics from top result
if search_result["success"] and search_result["results"]:
    top_doc = search_result["results"][0]

    metrics = await mcp.call_tool("analyze_metrics", {
        "document_id": top_doc["document_id"],
        "metric_types": ["numerical", "currency"],
        "user_id": "user_123"
    })

    print(f"Found {metrics['summary']['total_metrics_found']} metrics")
```

### Example 2: Create Action Items from Analysis

```python
# 1. Search for meeting notes
meetings = await mcp.call_tool("query_database", {
    "query_type": "documents",
    "filters": {"document_type": "meeting_notes"},
    "limit": 1,
    "user_id": "user_123"
})

# 2. Extract action items
for doc in meetings["results"]:
    # Use agent to analyze
    # Then create action items
    await mcp.call_tool("create_action_item", {
        "title": "Follow up on meeting decision",
        "description": "Review and implement decision from meeting",
        "priority": "HIGH",
        "document_id": doc["id"],
        "user_id": "user_123"
    })
```

### Example 3: Personalized Chat

```python
# 1. Get user context
context = await mcp.call_tool("get_user_context", {
    "user_id": "user_123",
    "include_preferences": True,
    "include_recent_activity": True
})

# 2. Use context for personalized response
preferences = context["context"]["preferences"]
summary_length = preferences.get("summary_length", "medium")

# 3. Generate summary with user preferences
prompt = mcp.get_prompt_template(
    "executive_summary_prompt",
    document_name="Project Update.pdf",
    audience="executive",
    length=summary_length,
    document_text="..."
)
```

---

## Security

### Authentication

All MCP endpoints require authentication:

```python
from app.utils.auth_helpers import get_current_active_user

@router.post("/execute")
async def execute_tool(
    current_user: UserInDB = Depends(get_current_active_user)
):
    # User ID automatically injected into tool parameters
    ...
```

### Authorization

**Access Control:**
- Users can only access their own documents
- User ID enforced on all database queries
- Resource access validated

**SQL Injection Prevention:**
- Parameterized queries
- Field whitelist
- Value sanitization

### Audit Logging

All tool executions are logged:

```python
{
    "user_id": "user_123",
    "action": "mcp_tool_search_documents",
    "details": {
        "tool_name": "search_documents",
        "parameters": {...},
        "success": true,
        "duration": 1.23
    },
    "timestamp": "2024-12-15T10:00:00Z"
}
```

### Rate Limiting

- Tool execution: 60/minute
- Chat: 30/minute
- Resource access: 100/minute

---

## Best Practices

### 1. Tool Selection

**Choose the right tool:**
- Use `search_documents` for finding content
- Use `analyze_metrics` for quantitative data
- Use `query_database` for structured queries
- Use `create_action_item` for task creation

### 2. Error Handling

```python
try:
    result = await mcp.call_tool("search_documents", {...})
    if result["success"]:
        # Process results
        pass
    else:
        # Handle tool-specific error
        print(f"Error: {result['error']}")
except ValidationError as e:
    # Handle validation errors
    print(f"Invalid parameters: {e}")
```

### 3. Conversation Management

```python
# Keep conversations organized
conversation_id = f"conv_{user_id}_{project_id}"

# Clear old conversations
if message_count > 100:
    mcp.context.clear_conversation(conversation_id)
```

### 4. Cost Tracking

```python
total_cost = 0.0

result = await mcp.call_tool("search_documents", {...})
total_cost += result.get("cost", 0)

# Monitor costs
if total_cost > budget_limit:
    # Alert or throttle
    pass
```

### 5. Tool Composition

Chain tools for complex workflows:

```python
# 1. Search
docs = await mcp.call_tool("search_documents", {...})

# 2. Analyze top results
for doc in docs["results"][:3]:
    metrics = await mcp.call_tool("analyze_metrics", {
        "document_id": doc["document_id"],
        ...
    })

# 3. Create action items based on findings
    if high_risk_detected:
        await mcp.call_tool("create_action_item", {...})
```

---

## Troubleshooting

### Common Issues

#### 1. Tool Not Found

**Error:** `Unknown tool: tool_name`

**Solution:** Check available tools with `GET /api/mcp/tools`

#### 2. Access Denied

**Error:** `Cannot access other user profiles`

**Solution:** Verify user_id matches authenticated user

#### 3. Invalid Parameters

**Error:** `Validation error: field required`

**Solution:** Check parameter schema in tool definition

#### 4. Rate Limit Exceeded

**Error:** `429 Too Many Requests`

**Solution:** Implement backoff, reduce request frequency

---

## Performance

### Optimization Tips

1. **Cache Results**: Cache frequently accessed resources
2. **Batch Operations**: Combine multiple operations when possible
3. **Limit Results**: Use appropriate limits for searches
4. **Context Cleanup**: Clear old conversations regularly

### Metrics

Monitor these metrics for optimal performance:

- Tool execution time
- Success rate per tool
- Cost per tool type
- Conversation length distribution

---

## Resources

### Documentation

- [Multi-Agent System](./MULTI_AGENT_SYSTEM.md)
- [Vector Search](./VECTOR_SEARCH.md)
- [Testing Guide](./TESTING.md)
- [Integration Summary](./INTEGRATION_SUMMARY.md)

### External Links

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Claude API Documentation](https://docs.anthropic.com/)

---

**MCP Integration Status**: ✅ **Fully Implemented and Production Ready**

Last Updated: 2024-12-15
