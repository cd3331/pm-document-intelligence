# MCP Quick Reference

Fast reference for using MCP (Model Context Protocol) in PM Document Intelligence.

## 🚀 Quick Start

### Import and Initialize

```python
from app.mcp import get_mcp_server

# Get MCP server instance
mcp = get_mcp_server()
```

---

## 🛠️ Tools - Quick Reference

### 1. search_documents

**Find documents using natural language:**

```python
result = await mcp.call_tool("search_documents", {
    "query": "What are the budget concerns?",
    "filters": {"document_type": "financial_report"},
    "limit": 5,
    "user_id": "user_123"
})

# Access results
for doc in result["results"]:
    print(f"{doc['filename']}: {doc['snippet']}")
```

---

### 2. analyze_metrics

**Extract numbers, dates, percentages from documents:**

```python
metrics = await mcp.call_tool("analyze_metrics", {
    "document_id": "doc_123",
    "metric_types": ["numerical", "percentages", "currency"],
    "user_id": "user_123"
})

# Access metrics
for num in metrics["metrics"]["numerical"]:
    print(f"{num['value']} {num['unit']}: {num['context']}")
```

---

### 3. query_database

**Query action items, documents, or analyses:**

```python
# Get high-priority action items
items = await mcp.call_tool("query_database", {
    "query_type": "action_items",
    "filters": {"priority": "HIGH", "status": "TODO"},
    "limit": 10,
    "user_id": "user_123"
})

# Access results
for item in items["results"]:
    print(f"{item['title']} - Due: {item['due_date']}")
```

---

### 4. create_action_item

**Create new action items:**

```python
item = await mcp.call_tool("create_action_item", {
    "title": "Review security audit",
    "description": "Complete security review by end of month",
    "assignee": "Security Team",
    "due_date": "2024-12-31T23:59:59Z",
    "priority": "HIGH",
    "user_id": "user_123"
})

# Get created item ID
action_id = item["action_item_id"]
```

---

### 5. get_user_context

**Retrieve user preferences and activity:**

```python
context = await mcp.call_tool("get_user_context", {
    "user_id": "user_123",
    "include_preferences": True,
    "include_recent_activity": True,
    "activity_days": 30
})

# Access preferences
prefs = context["context"]["preferences"]
summary_length = prefs.get("summary_length", "medium")
```

---

## 🔗 Resources - Quick Reference

### Access Document Resource

```python
doc = await mcp.get_resource("doc://doc_123", user_id="user_123")

# Access document data
document_text = doc["data"]["extracted_text"]
filename = doc["data"]["filename"]
```

### Access User Resource

```python
user = await mcp.get_resource("user://user_123", user_id="user_123")

# Access user data
profile = user["data"]["profile"]
preferences = user["data"]["preferences"]
```

---

## 📝 Prompt Templates - Quick Reference

### Get Formatted Prompt

```python
prompt = mcp.get_prompt_template(
    "document_analysis_prompt",
    document_name="Q4 Report.pdf",
    document_type="financial_report",
    document_text="[Full document text...]"
)

# Use prompt with Claude
response = await bedrock.invoke_claude(prompt)
```

**Available Templates:**
- `document_analysis_prompt`
- `action_item_extraction_prompt`
- `executive_summary_prompt`
- `qa_with_context_prompt`

---

## 🌐 API Endpoints - Quick Reference

### Execute Tool (POST /api/mcp/execute)

```bash
curl -X POST http://localhost:8000/api/v1/mcp/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "search_documents",
    "parameters": {
      "query": "project risks",
      "limit": 5
    }
  }'
```

### List Tools (GET /api/mcp/tools)

```bash
curl http://localhost:8000/api/v1/mcp/tools \
  -H "Authorization: Bearer $TOKEN"
```

### Chat (POST /api/mcp/chat)

```bash
curl -X POST http://localhost:8000/api/v1/mcp/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Search for budget concerns and create action items",
    "conversation_id": "conv_123",
    "allow_tools": true
  }'
```

---

## 🧠 Context Management - Quick Reference

### Add Message to Conversation

```python
mcp.context.add_message(
    conversation_id="conv_123",
    role="user",
    content="What are the project risks?",
    metadata={"source": "web_ui"}
)
```

### Get Conversation History

```python
history = mcp.context.get_conversation("conv_123")

# Last 5 messages
recent = history[-5:]
```

### Clear Conversation

```python
mcp.context.clear_conversation("conv_123")
```

### Get Statistics

```python
stats = mcp.context.get_stats()

print(f"Total conversations: {stats['total_conversations']}")
print(f"Tool usage: {stats['tool_usage']}")
```

---

## 🔄 Common Workflows

### Workflow 1: Search → Analyze → Create Actions

```python
# 1. Search for documents
search = await mcp.call_tool("search_documents", {
    "query": "security vulnerabilities",
    "limit": 3,
    "user_id": user_id
})

# 2. Analyze metrics in each
for doc in search["results"]:
    metrics = await mcp.call_tool("analyze_metrics", {
        "document_id": doc["document_id"],
        "metric_types": ["numerical"],
        "user_id": user_id
    })

    # 3. Create action items for high-value metrics
    await mcp.call_tool("create_action_item", {
        "title": f"Address findings in {doc['filename']}",
        "description": doc['snippet'],
        "priority": "HIGH",
        "user_id": user_id
    })
```

---

### Workflow 2: Personalized Analysis

```python
# 1. Get user context
context = await mcp.call_tool("get_user_context", {
    "user_id": user_id,
    "include_preferences": True
})

prefs = context["context"]["preferences"]

# 2. Use preferences for customized prompt
prompt = mcp.get_prompt_template(
    "executive_summary_prompt",
    document_name="Report.pdf",
    audience=prefs.get("default_audience", "executive"),
    length=prefs.get("summary_length", "medium"),
    document_text=document_text
)
```

---

### Workflow 3: Query and Update

```python
# 1. Get all TODO items
todos = await mcp.call_tool("query_database", {
    "query_type": "action_items",
    "filters": {"status": "TODO"},
    "user_id": user_id
})

# 2. Process each item
# (Would use other services to update status, etc.)
```

---

## ⚡ Performance Tips

### 1. Batch Operations

```python
# Instead of multiple individual calls
for doc_id in document_ids:
    await mcp.call_tool("analyze_metrics", {...})

# Use query_database to get all at once
docs = await mcp.call_tool("query_database", {
    "query_type": "documents",
    "filters": {"id": {"in": document_ids}},  # If supported
    "user_id": user_id
})
```

### 2. Cache Conversations

```python
# Reuse conversation_id for related queries
conversation_id = f"analysis_{project_id}"

# All related messages in same conversation
await mcp.call_tool("search_documents", {
    ...,
    "conversation_id": conversation_id
})
```

### 3. Limit Results

```python
# Don't fetch more than needed
result = await mcp.call_tool("search_documents", {
    "query": "...",
    "limit": 5,  # ← Not 50!
    "user_id": user_id
})
```

---

## 🔐 Security Checklist

- ✅ Always pass user_id from authenticated user
- ✅ Never hardcode credentials
- ✅ Validate all user inputs
- ✅ Use HTTPS in production
- ✅ Monitor rate limits
- ✅ Log tool usage for audit

---

## ❌ Common Mistakes

### ❌ Don't: Hardcode user_id

```python
# BAD
result = await mcp.call_tool("search_documents", {
    "user_id": "hardcoded_user"  # ❌
})
```

### ✅ Do: Use authenticated user

```python
# GOOD
@router.post("/search")
async def search(
    current_user: UserInDB = Depends(get_current_active_user)
):
    result = await mcp.call_tool("search_documents", {
        "user_id": current_user.id  # ✅
    })
```

---

### ❌ Don't: Ignore errors

```python
# BAD
result = await mcp.call_tool("search_documents", {...})
# Use result without checking success ❌
```

### ✅ Do: Check success

```python
# GOOD
result = await mcp.call_tool("search_documents", {...})

if result["success"]:
    # Process results ✅
    process(result["results"])
else:
    # Handle error ✅
    logger.error(f"Tool failed: {result['error']}")
```

---

### ❌ Don't: Create too many conversations

```python
# BAD
for i in range(100):
    conv_id = f"conv_{i}"  # ❌ Creates 100 conversations
    await mcp.call_tool(..., conversation_id=conv_id)
```

### ✅ Do: Reuse conversations

```python
# GOOD
conv_id = f"session_{user_id}"  # ✅ One per session
for query in queries:
    await mcp.call_tool(..., conversation_id=conv_id)
```

---

## 📊 Monitoring

### Track Tool Usage

```python
stats = mcp.context.get_stats()

print("Tool Usage:")
for tool, count in stats["tool_usage"].items():
    print(f"  {tool}: {count} calls")
```

### Track Costs

```python
total_cost = 0.0

result = await mcp.call_tool("search_documents", {...})
total_cost += result.get("cost", 0)

print(f"Total cost: ${total_cost:.4f}")
```

---

## 🐛 Debugging

### Enable Debug Logging

```python
import logging

logging.getLogger("app.mcp").setLevel(logging.DEBUG)
```

### Check Tool Availability

```python
from app.mcp import get_mcp_server

mcp = get_mcp_server()
tools = mcp.list_tools()

print("Available tools:")
for tool in tools:
    print(f"  - {tool['name']}: {tool['description']}")
```

### Test Tool Execution

```python
# Minimal test
try:
    result = await mcp.call_tool("search_documents", {
        "query": "test",
        "limit": 1,
        "user_id": "test_user"
    })
    print(f"Success: {result['success']}")
except Exception as e:
    print(f"Error: {e}")
```

---

## 📚 Additional Resources

- **Full Documentation**: [MCP_INTEGRATION.md](./MCP_INTEGRATION.md)
- **Implementation Details**: [MCP_IMPLEMENTATION_SUMMARY.md](./MCP_IMPLEMENTATION_SUMMARY.md)
- **Agent System**: [MULTI_AGENT_SYSTEM.md](./MULTI_AGENT_SYSTEM.md)
- **Vector Search**: [VECTOR_SEARCH.md](./VECTOR_SEARCH.md)

---

## 🆘 Getting Help

1. Check error message carefully
2. Review tool parameter schema
3. Check authentication token
4. Verify user has access to resource
5. Review logs for detailed errors
6. Check rate limit status

---

**Quick Reference Version**: 1.0
**Last Updated**: 2024-12-15
