# Multi-Agent Orchestration System

## Overview

The Multi-Agent System provides intelligent document analysis through specialized AI agents, each optimized for specific tasks. The system includes agent orchestration, task routing, failure handling, and result aggregation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  AnalysisAgent      ───▶  Deep analysis & insights              │
│  ActionItemAgent    ───▶  Extract action items                  │
│  SummaryAgent       ───▶  Generate summaries                    │
│  EntityAgent        ───▶  Extract entities                      │
│  QAAgent            ───▶  Answer questions (RAG)                │
│                                                                   │
│  ✓ Circuit Breakers ───▶  Prevent cascading failures           │
│  ✓ Rate Limiting    ───▶  Respect API limits                    │
│  ✓ Cost Tracking    ───▶  Monitor per-agent costs               │
│  ✓ Metrics          ───▶  Performance monitoring                │
│  ✓ Conversation     ───▶  Memory for follow-ups                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. BaseAgent (Abstract Class)

**File**: `backend/app/agents/base_agent.py`

**Features:**
- ✅ Agent lifecycle management
- ✅ Input/output validation
- ✅ Error handling framework
- ✅ Circuit breaker pattern
- ✅ Rate limiting (configurable RPM)
- ✅ Cost tracking per agent
- ✅ Performance metrics
- ✅ Status monitoring

**Key Classes:**
```python
class AgentStatus(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"

class AgentMetrics:
    # Tracks: requests, success rate, duration, cost, errors

class AgentCircuitBreaker:
    # States: closed, open, half-open
    # Auto-recovery after timeout

class BaseAgent(ABC):
    @abstractmethod
    async def process(self, input_data) -> Dict[str, Any]:
        pass
```

### 2. AgentOrchestrator

**File**: `backend/app/agents/orchestrator.py`

**Responsibilities:**
- Route tasks to appropriate agents
- Coordinate multi-agent workflows
- Manage agent lifecycle
- Handle failures and retries
- Aggregate results
- Maintain conversation memory

**Key Methods:**
```python
orchestrator = AgentOrchestrator()

# Register agents
orchestrator.register_agent(agent, [TaskType.DEEP_ANALYSIS])

# Route single task
result = await orchestrator.route_task(TaskType.DEEP_ANALYSIS, input_data)

# Multi-agent analysis
result = await orchestrator.multi_agent_analysis(
    document_id, text, user_id,
    tasks=["deep_analysis", "extract_actions"],
    parallel=True
)

# Q&A with conversation memory
result = await orchestrator.ask_question(
    question, document_id, user_id,
    conversation_id="conv_123"
)
```

### 3. Specialized Agents

#### AnalysisAgent

**File**: `backend/app/agents/analysis_agent.py`

**Specialization:** Deep document analysis with complex reasoning

**Output:**
- Executive summary
- Key insights
- Patterns identified
- Recommendations (with priority and rationale)
- Risks and concerns (with severity and mitigation)
- Opportunities
- Action priorities
- Confidence score

**Example:**
```python
result = await orchestrator.analyze_document(
    document_id="doc_123",
    document_text=text,
    user_id="user_456",
    task="deep_analysis"
)

# Result:
{
    "analysis": {
        "executive_summary": "Project shows good progress...",
        "key_insights": ["Insight 1", "Insight 2"],
        "patterns_identified": ["Pattern 1"],
        "recommendations": [
            {
                "recommendation": "Increase testing coverage",
                "priority": "HIGH",
                "rationale": "Current coverage is 45%, target is 80%"
            }
        ],
        "risks_and_concerns": [
            {
                "risk": "Timeline may slip by 2 weeks",
                "severity": "HIGH",
                "mitigation": "Add 2 contractors for critical path"
            }
        ],
        "confidence_score": 0.85
    },
    "cost": 0.0045
}
```

#### ActionItemAgent

**File**: `backend/app/agents/action_agent.py`

**Specialization:** Action item extraction with structured data

**Output:**
- Action description
- Assignee
- Due date
- Priority (HIGH/MEDIUM/LOW)
- Status (TODO/IN_PROGRESS/BLOCKED/DONE)
- Dependencies
- Confidence score

**Example:**
```python
result = await orchestrator.analyze_document(
    document_id="doc_123",
    document_text=text,
    user_id="user_456",
    task="extract_actions"
)

# Result:
{
    "action_items": [
        {
            "action": "Complete security review",
            "assignee": "Security Team",
            "due_date": "2024-02-15",
            "priority": "HIGH",
            "status": "TODO",
            "dependencies": ["Complete code review"],
            "confidence": 0.92
        }
    ],
    "total_actions": 5,
    "high_priority": 2,
    "cost": 0.0023
}
```

#### SummaryAgent

**File**: `backend/app/agents/summary_agent.py`

**Specialization:** Document summarization with configurable length and audience

**Lengths:**
- **brief**: ~200 tokens
- **medium**: ~500 tokens
- **comprehensive**: ~1000 tokens

**Audiences:**
- **executive**: High-level, business-focused
- **technical**: Technical details and implementation
- **team**: Actionable items and collaboration
- **general**: Balanced overview

**Example:**
```python
result = await orchestrator.analyze_document(
    document_id="doc_123",
    document_text=text,
    user_id="user_456",
    task="summarize",
    options={"length": "medium", "audience": "executive"}
)

# Result:
{
    "summary": {
        "executive_summary": "Q4 project on track for delivery...",
        "key_points": [
            "Backend development 90% complete",
            "Frontend integration ahead of schedule",
            "Testing phase starting next week"
        ],
        "decisions": [
            "Approved additional $15K for cloud infrastructure"
        ],
        "next_steps": [
            "Begin user acceptance testing",
            "Finalize deployment plan"
        ],
        "concerns": [
            "Potential delay in third-party API integration"
        ]
    },
    "length": "medium",
    "audience": "executive",
    "cost": 0.0018
}
```

#### EntityAgent

**File**: `backend/app/agents/entity_agent.py`

**Specialization:** Entity extraction combining AWS Comprehend + Claude

**Entities Extracted:**
- **Comprehend**: PERSON, ORGANIZATION, LOCATION, DATE, QUANTITY, etc.
- **Project-Specific**:
  - Projects (with status)
  - Stakeholders (with roles)
  - Milestones (with dates)
  - Budget items
  - Dependencies
  - Teams (with members and focus)

**Example:**
```python
result = await orchestrator.analyze_document(
    document_id="doc_123",
    document_text=text,
    user_id="user_456",
    task="extract_entities"
)

# Result:
{
    "comprehend_entities": [
        {"text": "John Doe", "type": "PERSON", "score": 0.98},
        {"text": "Q4 2024", "type": "DATE", "score": 0.95}
    ],
    "project_entities": {
        "projects": [
            {"name": "Project Phoenix", "status": "active"}
        ],
        "stakeholders": [
            {"name": "Jane Smith", "role": "Sponsor", "email": "jane@example.com"}
        ],
        "milestones": [
            {"name": "Beta Release", "date": "2024-04-01", "status": "pending"}
        ],
        "budget_items": [
            {"item": "Development", "amount": 50000, "currency": "USD"}
        ],
        "teams": [
            {"name": "Backend Team", "members": ["Alice", "Bob"], "focus": "API"}
        ]
    },
    "total_entities": 25,
    "cost": 0.0032
}
```

#### QAAgent (RAG)

**File**: `backend/app/agents/qa_agent.py`

**Specialization:** Question answering with Retrieval Augmented Generation

**Features:**
- ✅ Semantic search for relevant context
- ✅ Citation of sources
- ✅ Conversation memory for follow-ups
- ✅ Multi-hop reasoning
- ✅ Grounded answers only

**Example:**
```python
# First question
result = await orchestrator.ask_question(
    question="What are the main risks in the project?",
    document_id="doc_123",
    user_id="user_456",
    conversation_id="conv_789"
)

# Result:
{
    "question": "What are the main risks in the project?",
    "answer": "Based on the project plan [Document: project_plan.pdf, Chunk: 3], the main risks are:\n\n1. Resource constraints - The team is currently understaffed by 2 developers\n2. Timeline pressure - Deadline is aggressive with only 6 weeks remaining\n3. Third-party dependency - External API not yet stable",
    "citations": [
        {
            "document_id": "doc_123",
            "filename": "project_plan.pdf",
            "chunk_index": 3,
            "similarity_score": 0.89
        }
    ],
    "context_used": 3,
    "has_followup_context": false,
    "cost": 0.0028
}

# Follow-up question (uses conversation memory)
result = await orchestrator.ask_question(
    question="How can we mitigate the resource constraints?",
    document_id="doc_123",
    user_id="user_456",
    conversation_id="conv_789"
)

# Answer uses context from previous question
```

## API Endpoints

### POST /api/agents/analyze

Deep document analysis.

**Request:**
```json
{
  "document_id": "doc_123",
  "document_type": "project_plan",
  "include_risks": true,
  "include_opportunities": true
}
```

**Rate Limit:** 20 requests/minute

### POST /api/agents/extract-actions

Extract action items.

**Request:**
```json
{
  "document_id": "doc_123",
  "track_dependencies": true
}
```

**Rate Limit:** 30 requests/minute

### POST /api/agents/summarize

Generate summary.

**Request:**
```json
{
  "document_id": "doc_123",
  "length": "medium",
  "audience": "executive"
}
```

**Rate Limit:** 30 requests/minute

### POST /api/agents/ask

Ask questions (RAG).

**Request:**
```json
{
  "question": "What are the project risks?",
  "document_id": "doc_123",
  "conversation_id": "conv_456",
  "use_context": true
}
```

**Rate Limit:** 30 requests/minute

### POST /api/agents/multi-agent

Run multiple agents in parallel or sequential.

**Request:**
```json
{
  "document_id": "doc_123",
  "tasks": ["deep_analysis", "extract_actions", "summarize"],
  "parallel": true
}
```

**Response:**
```json
{
  "document_id": "doc_123",
  "results": {
    "deep_analysis": {...},
    "extract_actions": {...},
    "summarize": {...}
  },
  "total_tasks": 3,
  "successful_tasks": 3,
  "failed_tasks": 0,
  "total_cost_usd": 0.0089,
  "duration_seconds": 4.5,
  "execution_mode": "parallel"
}
```

**Rate Limit:** 10 requests/minute

### GET /api/agents/status

Get agent system status.

**Response:**
```json
{
  "agents": {
    "AnalysisAgent": {
      "status": "idle",
      "metrics": {
        "total_requests": 150,
        "success_rate": 0.97,
        "average_cost_usd": 0.0042
      },
      "circuit_breaker": {
        "state": "closed"
      }
    }
  },
  "orchestrator": {
    "total_agents": 5,
    "total_requests": 450,
    "total_cost_usd": 1.23
  }
}
```

### GET /api/agents/health

Health check for agent system.

## Cost Management

### Per-Agent Costs

Average costs per execution:

| Agent | Average Cost | Token Usage |
|-------|-------------|-------------|
| AnalysisAgent | $0.004-$0.006 | 2000-3000 |
| ActionItemAgent | $0.002-$0.003 | 1000-1500 |
| SummaryAgent | $0.002-$0.004 | 500-1500 |
| EntityAgent | $0.003-$0.005 | 1500-2000 |
| QAAgent | $0.003-$0.004 | 1000-1500 |

### Cost Tracking

Each agent tracks:
- Total requests
- Total tokens
- Total cost
- Average cost per request
- Cost by model

```python
# Get cost report
orchestrator = get_orchestrator()
stats = orchestrator.get_orchestrator_stats()

print(f"Total cost: ${stats['total_cost_usd']:.4f}")
```

## Circuit Breaker Pattern

**Purpose:** Prevent cascading failures when an agent is consistently failing.

**States:**
1. **Closed**: Normal operation
2. **Open**: Agent blocked after failures (threshold: 5)
3. **Half-Open**: Testing recovery

**Recovery:**
- After 60 seconds, circuit attempts recovery
- Requires 2 consecutive successes to close
- Automatically reopens on failure

**Example:**
```python
# Agent fails 5 times
agent.circuit_breaker.state  # "open"

# Wait 60 seconds
await asyncio.sleep(60)

# Next request tests recovery
result = await agent.execute(data)  # "half-open"

# If successful, circuit closes
agent.circuit_breaker.state  # "closed"
```

## Rate Limiting

Each agent has configurable rate limits:

| Agent | Max RPM |
|-------|---------|
| AnalysisAgent | 30 |
| ActionItemAgent | 40 |
| SummaryAgent | 50 |
| EntityAgent | 40 |
| QAAgent | 30 |

Automatically enforced with wait times.

## Performance Metrics

### Agent Metrics

Each agent tracks:
- **Total requests**: Count of all executions
- **Success rate**: Successful / Total
- **Average duration**: Mean execution time
- **Average cost**: Mean cost per execution
- **Error types**: Breakdown by error category

### Orchestrator Metrics

System-wide metrics:
- **Total agents**: Number of registered agents
- **Total requests**: Across all agents
- **Total cost**: Cumulative cost
- **Active conversations**: Number of Q&A sessions

## Error Handling

### Error Types

1. **ValidationError**: Invalid input/output
2. **AIServiceError**: AI API failures
3. **CircuitOpenError**: Circuit breaker open
4. **RateLimitError**: Rate limit exceeded

### Retry Strategy

- Automatic retries via circuit breaker
- Exponential backoff for transient failures
- Different handling per error type

## Conversation Memory

For Q&A agent:
- Stores last 10 exchanges per conversation
- Enables follow-up questions
- Context-aware responses
- Manual clearing via API

```python
# Ask with conversation
result = await orchestrator.ask_question(
    question="What's the timeline?",
    conversation_id="conv_123"
)

# Follow-up
result = await orchestrator.ask_question(
    question="Why is it delayed?",  # Understands "it" refers to timeline
    conversation_id="conv_123"
)

# Clear when done
orchestrator.clear_conversation("conv_123")
```

## Integration

### With Document Processing

```python
from app.services.document_processor import DocumentProcessor
from app.agents.orchestrator import get_orchestrator

# Process document
processor = DocumentProcessor()
doc_result = await processor.process_document(...)

# Then analyze with agents
orchestrator = get_orchestrator()
analysis = await orchestrator.multi_agent_analysis(
    document_id=doc_result["document_id"],
    document_text=doc_result["extracted_text"],
    user_id=user_id,
    tasks=["deep_analysis", "extract_actions", "summarize"],
    parallel=True
)
```

### With Vector Search

QAAgent automatically uses vector search for context retrieval:

```python
# Automatic semantic search in QAAgent
result = await orchestrator.ask_question(
    question="What are the risks?",
    user_id=user_id,
    use_context=True  # Triggers vector search
)

# Returns answer with citations from most relevant chunks
```

## Best Practices

### 1. Use Appropriate Agents

- **Deep analysis**: AnalysisAgent
- **Quick summaries**: SummaryAgent
- **Structured data**: ActionItemAgent, EntityAgent
- **Questions**: QAAgent

### 2. Leverage Multi-Agent

For comprehensive analysis:

```python
result = await orchestrator.multi_agent_analysis(
    document_id, text, user_id,
    tasks=["deep_analysis", "extract_actions", "extract_entities"],
    parallel=True  # Faster execution
)
```

### 3. Monitor Circuit Breakers

```python
status = await orchestrator.get_all_agent_status()

for agent_name, agent_status in status.items():
    if agent_status["circuit_breaker"]["state"] == "open":
        logger.warning(f"Agent {agent_name} circuit is open!")
```

### 4. Track Costs

```python
stats = orchestrator.get_orchestrator_stats()

if stats["total_cost_usd"] > budget_threshold:
    # Send alert
    notify_admin(f"Agent cost: ${stats['total_cost_usd']}")
```

## Troubleshooting

### Circuit Breaker Open

**Symptom:** Agent requests fail with "circuit breaker open"

**Solution:**
1. Check agent status: `GET /api/agents/status`
2. Review error logs
3. Wait for auto-recovery (60s)
4. Or reset metrics manually

### Rate Limit Exceeded

**Symptom:** Requests delayed with "rate limit" status

**Solution:**
- Reduce request frequency
- Increase agent's `max_requests_per_minute`
- Use batch operations

### High Costs

**Symptom:** Costs higher than expected

**Solution:**
1. Review per-agent costs
2. Optimize prompts to reduce tokens
3. Cache frequently requested analyses
4. Use smaller models where appropriate

## Future Enhancements

Planned features:
- [ ] Agent versioning and A/B testing
- [ ] Custom agent training
- [ ] Agent collaboration (agents working together)
- [ ] Streaming responses for real-time feedback
- [ ] Agent performance optimization
- [ ] Advanced multi-hop reasoning
- [ ] Cross-document analysis
- [ ] Automated agent selection based on query

## Summary

The multi-agent system provides:
- ✅ 5 specialized agents for different tasks
- ✅ Intelligent orchestration and routing
- ✅ Circuit breaker for resilience
- ✅ Cost tracking and metrics
- ✅ RAG for question answering
- ✅ Conversation memory
- ✅ Multi-agent workflows
- ✅ Production-ready error handling

All agents are production-ready with comprehensive monitoring, error handling, and cost optimization!
