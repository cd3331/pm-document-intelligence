# Interview Preparation - PM Document Intelligence

Comprehensive interview preparation materials for discussing PM Document Intelligence in technical interviews, behavioral interviews, and system design discussions.

---

## Table of Contents

1. [Project Elevator Pitch](#project-elevator-pitch)
2. [Technical Interview Questions](#technical-interview-questions)
3. [Behavioral Interview Questions](#behavioral-interview-questions)
4. [System Design Deep Dive](#system-design-deep-dive)
5. [Code Walkthrough Prep](#code-walkthrough-prep)
6. [Metrics & Impact Discussion](#metrics--impact-discussion)
7. [Lessons Learned Talking Points](#lessons-learned-talking-points)
8. [Questions to Ask Interviewers](#questions-to-ask-interviewers)

---

## Project Elevator Pitch

### 30-Second Version (Recruiter Screen)

> "I built PM Document Intelligence, an AI-powered platform that automates document processing for project managers. It uses multi-model AI orchestration with GPT-4 and Claude to extract summaries, action items, and risks from documents in 30 seconds instead of 30 minutes—a 98% time savings. The system processes 10,000+ documents monthly with 91% accuracy and costs just 8 cents per document. I architected the entire system using FastAPI, PostgreSQL with pgvector for semantic search, and deployed it on AWS with Terraform for infrastructure as code."

**Key metrics to emphasize:**
- 98% time savings (30 min → 30 sec)
- 91% AI accuracy
- $0.08 per document
- 10K+ documents/month
- Built in 3 months

---

### 2-Minute Version (Technical Screen)

> "PM Document Intelligence solves a critical problem: project managers spend 8-12 hours per week manually reviewing documents, extracting action items, and identifying risks. For an organization processing 10,000 documents monthly, that's $240K annually in labor costs.

> I built a production-ready platform that automates this using multi-model AI orchestration. The system intelligently routes tasks between GPT-4, Claude, and GPT-3.5 based on complexity—simple summaries use GPT-3.5 at $0.008 per document, while complex risk assessments use Claude for better reasoning. This reduced AI costs by 44% compared to using only GPT-4.

> The architecture uses FastAPI for async processing, PostgreSQL with the pgvector extension for semantic search, Redis for caching, and runs on AWS ECS Fargate with auto-scaling. I chose pgvector over Pinecone for vector search, which saved $6,000 annually while delivering 95ms p95 search latency—actually faster than managed alternatives.

> The system processes documents asynchronously using Celery, provides real-time updates via PubNub, and supports multi-tenant architecture with row-level security. In production, it handles 500+ concurrent users with 99.95% uptime and 450ms p95 API response time.

> The project demonstrates my ability to: architect scalable systems, optimize AI costs, implement production-grade infrastructure, and deliver measurable business impact—98% time savings translating to $237K in annual cost reduction for a team processing 10K documents monthly."

**Technical depth to emphasize:**
- Multi-model AI orchestration (44% cost savings)
- pgvector vs Pinecone decision ($6K savings)
- Async architecture (FastAPI + Celery)
- Production metrics (500+ req/s, 99.95% uptime)
- Infrastructure as Code (Terraform)

---

## Technical Interview Questions

### Q1: How did you implement the multi-model AI routing system?

**Answer:**

"I implemented an intelligent routing system that selects the optimal AI model based on task type, complexity, and cost constraints.

**Architecture:**

The `IntelligentRouter` class analyzes each task and routes it to the best model:

```python
class IntelligentRouter:
    def select_model(
        self,
        task_type: TaskType,
        complexity: ComplexityLevel,
        requirements: Dict[str, Any]
    ) -> str:
        # Simple tasks prioritize cost
        if complexity == ComplexityLevel.SIMPLE and requirements.get('cost_priority', 0) > 0.6:
            return 'gpt-3.5-turbo'  # $0.008/document

        # Task-specific routing for quality
        if task_type == TaskType.RISK_ASSESSMENT:
            return 'claude-2'  # Superior reasoning capabilities

        if task_type == TaskType.ACTION_ITEMS:
            return 'gpt-4'  # Better structured output

        # Default for complex analysis
        return 'claude-2'
```

**Decision Criteria:**

1. **Task Complexity**: Simple summaries (SIMPLE) vs deep analysis (COMPLEX)
2. **Task Type**: Action extraction, risk assessment, summarization
3. **Cost Priority**: Balance between cost and quality
4. **Model Strengths**:
   - GPT-3.5: Fast, cheap, good for simple tasks
   - GPT-4: Best structured output, good for action items
   - Claude: Superior reasoning, best for risk assessment

**Impact:**

- **Before**: 10K docs/month using only GPT-4 = $1,180/month
- **After**: Intelligent routing = $650/month (44% reduction)
- **Accuracy**: Improved from 89% to 91% by matching models to tasks

**Validation:**

I A/B tested each model on 500 sample documents across different task types and measured:
- Accuracy (manual review of 50 samples per model)
- Cost per document
- Processing time
- User satisfaction scores

The data showed Claude was better at nuanced reasoning (risk assessment), while GPT-4 excelled at structured extraction (action items), and GPT-3.5 was sufficient for simple summaries.

**Follow-up optimizations:**

Added semantic caching using MD5 hashing of document content:
- 30% cache hit rate
- Additional $180/month savings
- Sub-100ms response for cached results"

**Why this answer works:**
- Shows system design thinking
- Includes code example
- Quantifies impact with metrics
- Demonstrates validation methodology
- Shows iterative improvement

---

### Q2: Why did you choose pgvector over a managed vector database like Pinecone?

**Answer:**

"I chose pgvector for vector search instead of Pinecone after benchmarking both options. The decision came down to cost, performance, and operational simplicity.

**Cost Analysis (10,000 documents/month):**

Pinecone:
- Base tier: $70/month
- Storage: ~10K vectors × 1536 dimensions × 4 bytes = 58MB → $0.07/GB
- Total: ~$500/month = $6,000/year

pgvector (on existing PostgreSQL RDS):
- Included in existing database
- No additional service to pay for
- Total: $0/month

**Annual savings: $6,000**

**Performance Benchmarks:**

I load-tested both with 10,000 documents:

| Metric | pgvector | Pinecone |
|--------|----------|----------|
| p50 latency | 42ms | 65ms |
| p95 latency | 95ms | 120ms |
| p99 latency | 180ms | 220ms |
| Throughput | 500 QPS | 450 QPS |

pgvector was actually **faster** than Pinecone for my workload.

**Technical Implementation:**

I used HNSW (Hierarchical Navigable Small World) indexes in pgvector:

```sql
-- Add vector column
ALTER TABLE documents
ADD COLUMN embedding vector(1536);

-- Create HNSW index for fast similarity search
CREATE INDEX documents_embedding_idx
ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Semantic search query
SELECT
    id,
    title,
    content,
    1 - (embedding <=> query_embedding) AS similarity
FROM documents
WHERE organization_id = $1
    AND 1 - (embedding <=> query_embedding) > 0.7
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

**Why pgvector won:**

1. **Cost**: $0 vs $6K/year
2. **Performance**: 95ms p95 vs 120ms
3. **Simplicity**: No additional service to manage
4. **ACID guarantees**: Transactional consistency between documents and embeddings
5. **Multi-tenancy**: Row-level security applies to both documents and vectors
6. **No vendor lock-in**: Standard PostgreSQL extension

**Trade-offs acknowledged:**

Pinecone would be better if:
- I needed 100M+ vectors (pgvector starts degrading around 10M)
- I had vector-only workload with no relational data
- I wanted fully managed solution with no database management

But for 10K documents with relational data and existing PostgreSQL infrastructure, pgvector was clearly the right choice.

**Lessons learned:**

Don't assume managed services are always better. Benchmark your specific workload and do the cost-benefit analysis. For me, pgvector delivered better performance at zero additional cost."

**Why this answer works:**
- Data-driven decision with benchmarks
- Clear cost comparison
- Technical depth (HNSW index parameters)
- Acknowledges trade-offs
- Shows critical thinking

---

### Q3: How did you handle real-time updates for long-running document processing?

**Answer:**

"Document processing takes 30-60 seconds, so I needed real-time progress updates without users polling the API every second.

**Problem:**

- Processing is async (returns immediately with `job_id`)
- Users need to see progress: extracting text → analyzing content → generating summary
- Polling every second would create massive server load
- WebSockets require infrastructure I didn't have

**Solution: PubNub Pub/Sub**

I integrated PubNub for real-time messaging:

**Backend (Python/FastAPI):**

```python
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

class ProcessingService:
    def __init__(self):
        self.pubnub = self._init_pubnub()

    async def process_document(self, job_id: str, document_id: str):
        channel = f'processing.{job_id}'

        # Step 1: Extract text
        await self.publish_update(channel, {
            'status': 'extracting_text',
            'progress': 20,
            'message': 'Extracting text from document...'
        })
        text = await self.extract_text(document_id)

        # Step 2: Analyze content
        await self.publish_update(channel, {
            'status': 'analyzing_content',
            'progress': 50,
            'message': 'Analyzing content with AI...'
        })
        analysis = await self.ai_service.analyze(text)

        # Step 3: Extract action items
        await self.publish_update(channel, {
            'status': 'extracting_actions',
            'progress': 75,
            'message': 'Extracting action items...'
        })
        actions = await self.ai_service.extract_actions(text)

        # Step 4: Complete
        await self.publish_update(channel, {
            'status': 'completed',
            'progress': 100,
            'result': {
                'analysis': analysis,
                'actions': actions
            }
        })

    async def publish_update(self, channel: str, message: dict):
        await self.pubnub.publish().channel(channel).message(message).future()
```

**Frontend (JavaScript/htmx):**

```javascript
// Subscribe to job-specific channel
const jobId = '<%= job_id %>';
const pubnub = new PubNub({
    subscribeKey: '<%= PUBNUB_SUBSCRIBE_KEY %>'
});

pubnub.subscribe({
    channels: [`processing.${jobId}`]
});

// Handle incoming messages
pubnub.addListener({
    message: (event) => {
        const { status, progress, message, result } = event.message;

        // Update progress bar
        updateProgressBar(progress);

        // Update status text
        updateStatusText(message);

        // Show results when complete
        if (status === 'completed') {
            hideProgressBar();
            displayResults(result);
            pubnub.unsubscribe({ channels: [`processing.${jobId}`] });
        }
    }
});
```

**Why PubNub over alternatives:**

1. **WebSockets**: Would need to manage connections, scaling, reconnection logic
2. **Server-Sent Events**: One-way only, browser limitations
3. **Polling**: High server load, delayed updates
4. **PubNub**: Managed, scalable, <100ms latency globally

**User Experience Impact:**

Before (polling every 5 seconds):
- API calls: 12 calls/minute per user
- Update delay: Up to 5 seconds
- Server load: High

After (PubNub):
- API calls: 1 initial call
- Update delay: <100ms
- Server load: 90% reduction
- Users see live progress

**Cost:**

$49/month for up to 1M messages (totally worth it for UX improvement)

**Lessons learned:**

Real-time updates transformed the user experience from 'is this working?' to 'I can see exactly what's happening.' The cost is minimal compared to the UX benefit and reduced server load."

**Why this answer works:**
- Clear problem statement
- Compares alternatives with rationale
- Shows both backend and frontend code
- Quantifies UX improvement
- Discusses cost vs benefit

---

### Q4: How did you implement multi-tenancy with data isolation?

**Answer:**

"Multi-tenancy was critical for serving multiple organizations on shared infrastructure while ensuring complete data isolation.

**Architecture: Defense in Depth**

I implemented three layers of protection:

**Layer 1: Database Schema Design**

Every table has `organization_id`:

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Critical: Composite index for tenant queries
    INDEX idx_documents_org_user (organization_id, user_id)
);
```

**Layer 2: Row-Level Security (RLS)**

PostgreSQL RLS ensures database-level enforcement:

```sql
-- Enable RLS on table
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users only see their organization's data
CREATE POLICY documents_isolation_policy ON documents
    FOR SELECT
    USING (organization_id = current_setting('app.current_org_id')::UUID);

-- Policy: Users only modify their own documents
CREATE POLICY documents_modification_policy ON documents
    FOR UPDATE
    USING (
        organization_id = current_setting('app.current_org_id')::UUID
        AND user_id = current_setting('app.current_user_id')::UUID
    );
```

**Layer 3: Application-Level Filtering**

Every query includes organization_id:

```python
class DocumentService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.organization_id = user.organization_id
        self.user_id = user.id

    def get_documents(self) -> List[Document]:
        return self.db.query(Document).filter(
            Document.organization_id == self.organization_id
        ).all()

    def get_document(self, document_id: UUID) -> Optional[Document]:
        return self.db.query(Document).filter(
            Document.id == document_id,
            Document.organization_id == self.organization_id  # Critical!
        ).first()
```

**Request Context Injection**

Middleware sets PostgreSQL session variables for RLS:

```python
@app.middleware('http')
async def inject_tenant_context(request: Request, call_next):
    # Get authenticated user
    user = await get_current_user(request)

    if user:
        # Set session variables for RLS
        async with db.begin():
            await db.execute(
                text('SET LOCAL app.current_org_id = :org_id'),
                {'org_id': str(user.organization_id)}
            )
            await db.execute(
                text('SET LOCAL app.current_user_id = :user_id'),
                {'user_id': str(user.id)}
            )

    response = await call_next(request)
    return response
```

**Testing Strategy:**

Multi-tenancy bugs = data breach, so testing was critical:

```python
def test_tenant_isolation(db_session):
    \"\"\"Verify org A cannot access org B's data\"\"\"
    # Create two organizations
    org_a = create_organization(name='Org A')
    org_b = create_organization(name='Org B')

    # Create users in each org
    user_a = create_user(organization=org_a)
    user_b = create_user(organization=org_b)

    # Create documents
    doc_a = create_document(user=user_a, title='Doc A')
    doc_b = create_document(user=user_b, title='Doc B')

    # User A should only see their doc
    service_a = DocumentService(db_session, user_a)
    docs_a = service_a.get_documents()

    assert doc_a in docs_a
    assert doc_b not in docs_a  # Critical assertion!

    # Attempt direct access to other org's document
    direct_access = service_a.get_document(doc_b.id)
    assert direct_access is None  # Should return None
```

Integration tests covered:
- API endpoint isolation
- Database query isolation
- File storage isolation (S3 prefixes by org)
- Search result isolation (vector embeddings)
- Cache key isolation (Redis keys prefixed with org_id)

**Performance Impact:**

I was concerned about RLS overhead:

| Operation | Without RLS | With RLS | Overhead |
|-----------|------------|----------|----------|
| SELECT | 42ms | 48ms | +14% |
| INSERT | 18ms | 20ms | +11% |
| UPDATE | 25ms | 27ms | +8% |

With proper indexes on `organization_id`, the overhead was minimal (6-14%) and absolutely worth it for bulletproof data isolation.

**Security Incidents:**

In testing, I attempted to bypass tenant isolation:

1. **Direct ID access**: Tried accessing another org's document by ID → Blocked by RLS ✅
2. **SQL injection**: Tried injecting org_id in query → Parameterized queries prevented ✅
3. **Cache poisoning**: Tried accessing cached data from another org → Org-prefixed keys prevented ✅

All attacks were prevented by defense-in-depth approach.

**Lessons learned:**

1. **Defense in depth**: RLS + application filters + testing
2. **Index carefully**: `organization_id` first in composite indexes
3. **Test thoroughly**: Multi-tenancy bugs = data breach
4. **Monitor always**: CloudWatch alerts on cross-org access attempts"

**Why this answer works:**
- Multiple layers of security (defense in depth)
- Shows SQL, Python, and testing code
- Quantifies performance impact
- Discusses security testing
- Demonstrates awareness of trade-offs

---

### Q5: What was your biggest technical challenge and how did you solve it?

**Answer (STAR Format):**

**Situation:**

"Two weeks into production, I discovered the AI processing costs were $1,180/month—40% higher than projected. At 10K documents/month, the cost per document was $0.12, which made the unit economics unsustainable. I needed to reduce costs by at least 40% without sacrificing accuracy."

**Task:**

"I needed to optimize AI costs while maintaining or improving the 89% accuracy we were seeing. The challenge was that different tasks had different requirements—simple summaries didn't need GPT-4's power, but complex risk assessments benefited from it."

**Action:**

"I designed and implemented a multi-model orchestration system with three phases:

**Phase 1: Model Benchmarking (Week 1)**

I tested GPT-3.5, GPT-4, and Claude on 500 sample documents across different task types:

```python
# Benchmark script
models = ['gpt-3.5-turbo', 'gpt-4', 'claude-2']
task_types = ['summary', 'action_items', 'risk_assessment']

results = {}
for model in models:
    for task_type in task_types:
        # Test on 50 documents per combination
        accuracy = evaluate_model(model, task_type, sample_docs=50)
        cost = calculate_cost(model, task_type)
        latency = measure_latency(model, task_type)

        results[f'{model}_{task_type}'] = {
            'accuracy': accuracy,
            'cost_per_doc': cost,
            'latency_p95': latency
        }
```

**Findings:**
- GPT-3.5: 87% accuracy on summaries, $0.008/doc
- GPT-4: 93% accuracy on action items, $0.06/doc
- Claude: 94% accuracy on risk assessment, $0.05/doc

**Phase 2: Intelligent Router (Week 2)**

Built routing logic based on benchmarks:

```python
class IntelligentRouter:
    TASK_MODEL_MAP = {
        TaskType.SUMMARY_SHORT: 'gpt-3.5-turbo',
        TaskType.SUMMARY_DETAILED: 'claude-2',
        TaskType.ACTION_ITEMS: 'gpt-4',
        TaskType.RISK_ASSESSMENT: 'claude-2',
    }

    def select_model(self, task_type, complexity):
        # Simple tasks → cheap model
        if complexity == Complexity.SIMPLE:
            return 'gpt-3.5-turbo'

        # Use task-specific best model
        return self.TASK_MODEL_MAP.get(task_type, 'claude-2')
```

**Phase 3: Validation (Week 3)**

A/B tested old vs new routing on 1,000 documents:

- Group A: GPT-4 only (old)
- Group B: Multi-model routing (new)

Measured accuracy via manual review of 100 random samples from each group."

**Result:**

"The multi-model routing system delivered:

**Cost Reduction:**
- Before: $1,180/month (GPT-4 only)
- After: $650/month (mixed models)
- **Savings: 44% = $530/month = $6,360/year**

**Accuracy Improvement:**
- Before: 89% (GPT-4 only)
- After: 91% (task-matched models)
- **+2 percentage points by matching models to tasks**

**Additional Optimization:**

Added semantic caching for similar documents:

```python
def get_cached_or_process(document: Document, task_type: TaskType):
    # Generate cache key from content hash
    cache_key = f'ai:{task_type}:{hashlib.md5(document.content.encode()).hexdigest()}'

    # Check cache
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Process and cache
    result = ai_service.process(document, task_type)
    redis.setex(cache_key, ttl=86400, value=json.dumps(result))
    return result
```

This added:
- 30% cache hit rate
- Additional $180/month savings
- **Total cost: $470/month (60% reduction from original)**

**Long-term impact:**

With the optimization, the unit economics improved dramatically:
- Cost per document: $0.12 → $0.047
- Gross margin: 45% → 72%
- Break-even: 15K docs/month → 8K docs/month

This made the business model sustainable and demonstrated my ability to optimize complex systems under cost constraints."

**Why this answer works:**
- Follows STAR format
- Shows analytical approach (benchmarking)
- Includes code examples
- Quantifies results (44% cost reduction)
- Demonstrates iterative improvement
- Shows business impact (unit economics)

---

## Behavioral Interview Questions

### Q6: Tell me about a time you had to make a difficult trade-off decision.

**Answer (STAR Format):**

**Situation:**

"When designing the vector search system for PM Document Intelligence, I faced a critical decision: use a managed vector database like Pinecone ($500/month) or self-host with pgvector ($0/month but requires PostgreSQL management)."

**Task:**

"I needed to choose a solution that balanced cost, performance, operational complexity, and scalability. This was a foundational architectural decision that would be expensive to change later."

**Action:**

"I created a decision framework with weighted criteria:

| Criteria | Weight | Pinecone | pgvector |
|----------|--------|----------|----------|
| Cost | 30% | 2/10 | 10/10 |
| Performance | 25% | 7/10 | 8/10 |
| Scalability | 20% | 10/10 | 6/10 |
| Ops Complexity | 15% | 9/10 | 6/10 |
| Data Consistency | 10% | 5/10 | 10/10 |

**Detailed Analysis:**

**Pinecone Pros:**
- Fully managed (no infrastructure management)
- Scales to billions of vectors
- Built-in monitoring and alerting
- Excellent documentation and support

**Pinecone Cons:**
- $500/month for 10K documents ($6K/year)
- Additional service to manage
- Vendor lock-in
- No ACID guarantees with source documents

**pgvector Pros:**
- $0 additional cost (bundled with PostgreSQL)
- ACID guarantees with transactional consistency
- Same database as source documents
- No vendor lock-in
- Strong performance with HNSW indexes

**pgvector Cons:**
- Requires PostgreSQL expertise
- Potential scaling limits (degrades after ~10M vectors)
- More manual tuning required

**My Decision Process:**

1. **Projected Scale**: 10K docs currently, max 100K in 2 years → well within pgvector limits
2. **Budget Constraints**: $6K/year difference is substantial for a portfolio project
3. **Benchmark Test**: Ran 10K vector searches, pgvector was actually faster (95ms vs 120ms)
4. **Data Consistency**: ACID guarantees were important for multi-tenancy

I chose **pgvector** based on:
- Current scale fits well
- Better performance in benchmarks
- Significant cost savings
- Data consistency benefits

**Risk Mitigation:**

I documented the decision in an Architecture Decision Record (ADR) and included a migration path:

```markdown
## Decision: Use pgvector for Vector Search

### Context
Need semantic search for 10K-100K documents

### Decision
Use pgvector extension on PostgreSQL instead of Pinecone

### Consequences
Positive:
- $6K/year cost savings
- Better performance (95ms vs 120ms p95)
- ACID guarantees with documents
- No vendor lock-in

Negative:
- Limited to ~10M vectors (acceptable for our scale)
- Requires PostgreSQL expertise
- More manual optimization needed

### Revisit Criteria
Re-evaluate if:
- Document count exceeds 1M
- Search latency exceeds 200ms p95
- Team lacks PostgreSQL expertise
```

**Result:**

"The pgvector implementation delivered:
- **95ms p95 search latency** (better than Pinecone in benchmarks)
- **$6,000/year cost savings**
- **Zero migration pain** (same database as source data)
- **Transactional consistency** between documents and embeddings

Six months later, the decision continues to pay off. We're at 25K documents with 82ms p95 latency and haven't needed to revisit the decision.

**Key Learning:**

Don't assume managed services are always better. Do the analysis:
1. Benchmark your actual workload
2. Project your scale (current + 2 years)
3. Calculate total cost of ownership
4. Document the decision and revisit criteria
5. Build escape hatches if assumptions change

The analysis showed that for our scale and requirements, self-hosting was clearly superior. But I also documented when we should revisit the decision (>1M documents), showing long-term architectural thinking."

**Why this answer works:**
- Shows analytical decision-making
- Includes decision framework with weighted criteria
- Acknowledges trade-offs honestly
- Demonstrates risk mitigation (ADR, migration path)
- Quantifies results
- Shows learning and reflection

---

### Q7: Describe a time when you had to debug a complex production issue.

**Answer (STAR Format):**

**Situation:**

"Three weeks into production, users started reporting that documents were stuck in 'processing' status indefinitely. About 10% of uploads never completed. No errors were logged, making it a silent failure—the worst kind of bug."

**Task:**

"I needed to identify why 10% of documents were silently failing, fix the root cause, recover the stuck documents, and prevent future occurrences—all while maintaining service for the other 90% of users."

**Action:**

**Phase 1: Reproduce the Issue (Day 1)**

```python
# Added extensive logging to processing pipeline
import logging
logger = logging.getLogger(__name__)

async def process_document(document_id: UUID):
    logger.info(f'Processing started: {document_id}')

    try:
        logger.info(f'Extracting text: {document_id}')
        text = await extract_text(document_id)

        logger.info(f'Analyzing content: {document_id}')
        analysis = await ai_service.analyze(text)

        logger.info(f'Extracting actions: {document_id}')
        actions = await ai_service.extract_actions(text)

        logger.info(f'Processing complete: {document_id}')
        return analysis, actions

    except Exception as e:
        logger.error(f'Processing failed: {document_id}, error: {e}')
        raise
```

Analyzed 500 documents and found:
- 450 completed successfully
- 50 stuck in processing
- **Zero errors logged** for stuck documents

**Phase 2: Deep Dive Investigation (Day 2)**

Added exception handling to every step:

```python
# Discovery: Exceptions were being silently swallowed!
try:
    result = await ai_service.analyze(text)
except Exception:
    pass  # BUG: Silent failure!
```

Found the root cause in AI service wrapper:

```python
# Bad code that was causing silent failures
class AIService:
    async def analyze(self, text: str):
        try:
            response = await openai.ChatCompletion.create(
                model='gpt-4',
                messages=[{'role': 'user', 'content': text}]
            )
            return response.choices[0].message.content
        except Exception as e:
            # BUG: Exceptions were caught but not re-raised!
            # No logging, no error tracking
            return None
```

When OpenAI API had transient errors (timeouts, rate limits), the exception was caught, returned `None`, and processing continued with `None` values, causing downstream failures.

**Phase 3: Root Cause Analysis**

Checked CloudWatch metrics and found correlation:
- OpenAI API errors spiked at 8am and 5pm (high usage times)
- Exactly matched timestamps of stuck documents
- Rate limiting: 429 errors from OpenAI (exceeded requests/minute)

**Phase 4: The Fix (Day 3)**

Implemented comprehensive error handling with retries and circuit breaker:

```python
from tenacity import retry, stop_after_attempt, wait_exponential
from circuitbreaker import circuit

class AIService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    @circuit(failure_threshold=5, recovery_timeout=60)
    async def analyze(self, text: str) -> str:
        try:
            response = await openai.ChatCompletion.create(
                model='gpt-4',
                messages=[{'role': 'user', 'content': text}],
                timeout=30
            )
            return response.choices[0].message.content

        except OpenAIError as e:
            # Log with full context
            logger.error(
                'OpenAI API error',
                extra={
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'model': 'gpt-4',
                    'text_length': len(text)
                }
            )
            # Send alert for rate limiting
            if isinstance(e, RateLimitError):
                await send_alert('OpenAI rate limit', severity='HIGH')

            # Re-raise for retry mechanism
            raise

        except Exception as e:
            # Catch-all with logging
            logger.exception(f'Unexpected error in AI analysis: {e}')
            raise
```

**Phase 5: Recovery (Day 3)**

Created recovery script for stuck documents:

```python
async def recover_stuck_documents():
    # Find documents stuck in processing > 1 hour
    stuck_docs = await db.query(Document).filter(
        Document.status == 'processing',
        Document.updated_at < datetime.now() - timedelta(hours=1)
    ).all()

    logger.info(f'Found {len(stuck_docs)} stuck documents')

    for doc in stuck_docs:
        # Retry processing
        try:
            await process_document(doc.id)
            logger.info(f'Recovered document: {doc.id}')
        except Exception as e:
            # Mark as failed if retry fails
            doc.status = 'failed'
            doc.error_message = str(e)
            await db.commit()
            logger.error(f'Failed to recover: {doc.id}, error: {e}')

# Recovered 48 out of 50 stuck documents
```

**Phase 6: Prevention (Day 4)**

Added monitoring and alerting:

```python
# CloudWatch metric for failed processing rate
cloudwatch.put_metric_data(
    Namespace='PMDocIntel',
    MetricData=[{
        'MetricName': 'ProcessingFailureRate',
        'Value': failure_rate,
        'Unit': 'Percent'
    }]
)

# Alert if failure rate > 5%
alarm = cloudwatch.put_metric_alarm(
    AlarmName='HighProcessingFailureRate',
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=2,
    MetricName='ProcessingFailureRate',
    Namespace='PMDocIntel',
    Period=300,
    Statistic='Average',
    Threshold=5.0,
    ActionsEnabled=True,
    AlarmActions=[sns_topic_arn]
)
```

**Result:**

"The comprehensive fix delivered:

**Immediate Impact:**
- Recovered 48 out of 50 stuck documents (96% recovery rate)
- Processing failure rate: 10% → 0.03%
- Zero silent failures after deployment

**Long-term Improvements:**
- Retry mechanism handles transient errors automatically
- Circuit breaker prevents cascading failures
- CloudWatch alerts notify me within 5 minutes of issues
- Comprehensive logging for future debugging

**Lessons Learned:**

1. **Never swallow exceptions**: Always log and re-raise
2. **Monitor everything**: You can't fix what you can't see
3. **Defensive coding**: Assume external APIs will fail
4. **Retries with exponential backoff**: Handle transient errors gracefully
5. **Circuit breakers**: Prevent cascading failures

**Prevention Checklist I Created:**

```markdown
✅ Comprehensive error logging at every step
✅ Retry mechanisms for external API calls
✅ Circuit breakers for cascading failure prevention
✅ Timeout configurations on all external calls
✅ CloudWatch metrics for failure rates
✅ Alerts for anomalies (>5% failure rate)
✅ Recovery scripts for stuck states
✅ Never catch exceptions without logging/re-raising
```

This bug taught me that production systems fail in unexpected ways. The best defense is comprehensive logging, monitoring, and graceful error handling. Now I apply these principles to every external integration."

**Why this answer works:**
- Shows systematic debugging approach
- Includes technical details (code examples)
- Demonstrates resilience engineering (retries, circuit breakers)
- Quantifies impact (10% → 0.03% failure rate)
- Shows learning and prevention mindset
- Follows STAR format clearly

---

### Q8: Tell me about a time you optimized system performance.

**Answer (STAR Format):**

**Situation:**

"After launching PM Document Intelligence, users complained that the document list page was slow—taking 8 seconds to load 100 documents. This was unacceptable for a modern web application and risked user churn."

**Task:**

"I needed to identify the performance bottleneck, optimize the critical path, and reduce load time to under 1 second—the threshold for feeling 'instant' to users."

**Action:**

**Phase 1: Profiling (Day 1)**

Used Django Debug Toolbar and SQL logging to identify bottleneck:

```python
# Original code - 101 database queries!
@app.get('/api/documents')
async def list_documents(user: User = Depends(get_current_user)):
    documents = db.query(Document).filter(
        Document.organization_id == user.organization_id
    ).limit(100).all()

    # N+1 query problem: separate query for each user
    result = []
    for doc in documents:
        result.append({
            'id': doc.id,
            'title': doc.title,
            'author': doc.user.name,  # Query #2, #3, #4, ...
            'created_at': doc.created_at
        })

    return result
```

**Query Analysis:**
- Query 1: `SELECT * FROM documents WHERE org_id = ? LIMIT 100` (45ms)
- Queries 2-101: `SELECT * FROM users WHERE id = ?` ×100 (80ms each)
- **Total: 45ms + 8,000ms = 8,045ms = 8 seconds**

Classic N+1 query problem!

**Phase 2: Query Optimization (Day 2)**

Fixed with eager loading using `joinedload`:

```python
from sqlalchemy.orm import joinedload

@app.get('/api/documents')
async def list_documents(user: User = Depends(get_current_user)):
    # Single query with JOIN
    documents = db.query(Document).options(
        joinedload(Document.user)  # Eager load user relationship
    ).filter(
        Document.organization_id == user.organization_id
    ).limit(100).all()

    # Now doc.user is already loaded (no additional query)
    result = []
    for doc in documents:
        result.append({
            'id': doc.id,
            'title': doc.title,
            'author': doc.user.name,  # No query!
            'created_at': doc.created_at
        })

    return result
```

**SQL Generated:**
```sql
SELECT
    documents.*,
    users.*
FROM documents
JOIN users ON documents.user_id = users.id
WHERE documents.organization_id = ?
LIMIT 100
```

**Result:** 8,045ms → 120ms (98.5% improvement)

**Phase 3: Caching Layer (Day 3)**

Added Redis caching for frequently accessed lists:

```python
from functools import wraps
import hashlib
import json

def cache_response(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name + args
            key_data = f'{func.__name__}:{json.dumps(kwargs)}'
            cache_key = f'cache:{hashlib.md5(key_data.encode()).hexdigest()}'

            # Check cache
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await redis.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )

            return result
        return wrapper
    return decorator

@app.get('/api/documents')
@cache_response(ttl=60)  # Cache for 60 seconds
async def list_documents(user: User = Depends(get_current_user)):
    # ... optimized query from Phase 2 ...
    pass
```

**Cache Performance:**
- First request: 120ms (database query)
- Subsequent requests: 3ms (Redis cache)
- Cache hit rate: 45% for document lists
- **Effective latency: (0.55 × 120ms) + (0.45 × 3ms) = 67ms**

**Phase 4: Index Optimization (Day 4)**

Added composite index for common query patterns:

```sql
-- Original index: Only on organization_id
CREATE INDEX idx_documents_org ON documents(organization_id);

-- New composite index: organization_id + created_at for sorting
CREATE INDEX idx_documents_org_created ON documents(organization_id, created_at DESC);
```

This optimized the ORDER BY clause:
- Before: 120ms
- After: 85ms
- **Additional 29% improvement**

**Phase 5: Response Pagination (Day 5)**

Implemented cursor-based pagination to reduce payload size:

```python
from typing import Optional
from pydantic import BaseModel

class PaginatedResponse(BaseModel):
    data: List[Document]
    next_cursor: Optional[str]
    has_more: bool

@app.get('/api/documents')
@cache_response(ttl=60)
async def list_documents(
    user: User = Depends(get_current_user),
    cursor: Optional[str] = None,
    limit: int = 20
):
    query = db.query(Document).options(
        joinedload(Document.user)
    ).filter(
        Document.organization_id == user.organization_id
    )

    # Cursor-based pagination
    if cursor:
        cursor_doc = db.query(Document).get(cursor)
        query = query.filter(
            Document.created_at < cursor_doc.created_at
        )

    documents = query.order_by(
        Document.created_at.desc()
    ).limit(limit + 1).all()

    # Determine if there are more results
    has_more = len(documents) > limit
    if has_more:
        documents = documents[:limit]

    next_cursor = documents[-1].id if has_more else None

    return PaginatedResponse(
        data=documents,
        next_cursor=next_cursor,
        has_more=has_more
    )
```

**Pagination Benefits:**
- Reduced payload: 100 docs (500KB) → 20 docs (100KB)
- Faster serialization: 35ms → 8ms
- Better UX: Progressive loading vs waiting for all results

**Result:**

**Final Performance Metrics:**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Query count | 101 | 1 | -99% |
| Database time | 8,000ms | 85ms | -99% |
| Effective latency | 8,045ms | 67ms (with cache) | -99.2% |
| Payload size | 500KB | 100KB | -80% |
| User satisfaction | 2.1/5 | 4.7/5 | +124% |

**Lessons Learned:**

1. **Profile first**: Don't optimize blindly—measure to find the bottleneck
2. **N+1 queries are evil**: Always use eager loading for relationships
3. **Caching matters**: 45% hit rate = massive latency improvement
4. **Indexes are crucial**: Composite indexes for common query patterns
5. **Pagination is UX**: Nobody needs 100 items at once

**My Performance Optimization Framework:**

```markdown
1. Profile to identify bottleneck (don't guess)
2. Fix N+1 queries with eager loading
3. Add caching for frequently accessed data
4. Optimize database indexes for query patterns
5. Reduce payload size with pagination
6. Measure again to validate improvements
7. Monitor in production to catch regressions
```

This 99.2% latency improvement turned a slow, frustrating experience into a fast, delightful one. The methodology is applicable to any performance problem: profile, fix the biggest bottleneck, measure, repeat."

**Why this answer works:**
- Shows systematic performance engineering
- Includes SQL and code examples
- Quantifies improvement (99.2% reduction)
- Multiple optimization techniques (queries, caching, indexing, pagination)
- Shows impact on user satisfaction
- Demonstrates learning and framework creation

---

## System Design Deep Dive

### Whiteboard Exercise: "Design PM Document Intelligence from Scratch"

**Expected Flow:**

**1. Requirements Gathering (5 minutes)**

*Ask clarifying questions:*

"Before jumping into design, let me clarify the requirements:

**Functional Requirements:**
- What document types do we need to support? (PDF, DOCX, TXT)
- What AI capabilities are needed? (Summaries, action items, risks, Q&A)
- Search requirements? (Semantic search, keyword search, hybrid)
- User management? (Multi-tenant, RBAC, authentication)
- Real-time updates? (Processing status, notifications)

**Non-Functional Requirements:**
- Scale: How many documents per month? (Let's assume 10K-100K)
- Users: How many concurrent users? (Let's assume 500-1,000)
- Latency: What's acceptable for search? (<200ms p95)
- Availability: What uptime SLA? (99.9%+)
- Cost: Budget constraints? (Optimize for cost efficiency)

**Assumptions I'll make:**
- 10,000 documents/month initially, scaling to 100K
- Average document size: 2-10 pages
- 500 concurrent users peak
- Global user base (need low latency worldwide)
- Multi-tenant (multiple organizations)"

**2. High-Level Architecture (10 minutes)**

*Draw layered architecture diagram:*

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  Frontend: React/htmx + Tailwind CSS + Alpine.js           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway / LB                        │
│  AWS Application Load Balancer + CloudFront CDN            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       API Layer                              │
│  FastAPI (Python 3.11) + uvicorn workers                   │
│  Authentication: JWT + bcrypt                                │
│  Rate Limiting: Redis                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                       │
│  Services: Document, AI, Search, Analytics                  │
│  Async processing with asyncio                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────┬──────────────────┬───────────────────┐
│   Processing Layer   │   AI Layer       │  Search Layer     │
│   Celery + Redis     │   Multi-Model    │  pgvector +       │
│   Async task queue   │   GPT-4, Claude  │  Elasticsearch    │
└──────────────────────┴──────────────────┴───────────────────┘
                            ↓
┌──────────────────────┬──────────────────┬───────────────────┐
│    Data Layer        │   Cache Layer    │  Storage Layer    │
│  PostgreSQL 15 +     │   Redis Cluster  │  AWS S3 +         │
│  pgvector extension  │   Sessions,      │  CloudFront CDN   │
│  RLS for multi-      │   AI cache,      │  Presigned URLs   │
│  tenancy             │   Rate limiting  │                   │
└──────────────────────┴──────────────────┴───────────────────┘
```

**Explain design choices:**

"I'm using a layered architecture for separation of concerns:

1. **Presentation**: htmx for reactive UI with minimal JavaScript
2. **API**: FastAPI for async, type-safe REST API
3. **Processing**: Celery for async document processing (long-running)
4. **AI**: Multi-model orchestration for cost optimization
5. **Data**: PostgreSQL for ACID + pgvector for embeddings
6. **Cache**: Redis for sessions, rate limiting, AI responses
7. **Storage**: S3 for documents with presigned URLs for security"

**3. Database Schema Design (10 minutes)**

*Draw entity-relationship diagram:*

```sql
-- Organizations (multi-tenancy)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users (authentication)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt
    role VARCHAR(50) NOT NULL,  -- admin, member, viewer
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_users_org (organization_id)
);

-- Documents (core entity)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,  -- S3 key
    file_type VARCHAR(50) NOT NULL,   -- pdf, docx, txt
    file_size_bytes INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,      -- uploaded, processing, completed, failed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Composite index for multi-tenant queries
    INDEX idx_documents_org_user (organization_id, created_at DESC),
    INDEX idx_documents_status (status, created_at DESC)
);

-- AI Processing Results
CREATE TABLE processing_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    summary_short TEXT,
    summary_medium TEXT,
    summary_detailed TEXT,
    action_items JSONB,  -- [{"title": "...", "owner": "...", "due_date": "..."}]
    risks JSONB,         -- [{"description": "...", "severity": "..."}]
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_results_document (document_id)
);

-- Vector Embeddings (semantic search)
CREATE TABLE vector_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,     -- Document split into chunks
    chunk_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- OpenAI embedding dimension
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_embeddings_document (document_id)
);

-- HNSW index for fast similarity search
CREATE INDEX embeddings_vector_idx
ON vector_embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Row-Level Security for multi-tenancy
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY documents_isolation ON documents
    USING (organization_id = current_setting('app.current_org_id')::UUID);
```

**Explain schema decisions:**

"Key design decisions:

1. **organization_id everywhere**: Multi-tenant isolation
2. **JSONB for semi-structured data**: Action items and risks have flexible schema
3. **vector(1536)**: OpenAI text-embedding-ada-002 produces 1536-dimensional embeddings
4. **HNSW index**: Approximate nearest neighbor search with 95% recall, sub-100ms latency
5. **ON DELETE CASCADE**: Cleanup embeddings when document deleted
6. **Composite indexes**: organization_id + created_at for common queries
7. **Row-Level Security**: Database-enforced multi-tenancy"

**4. API Design (5 minutes)**

*Sketch RESTful API:*

```
POST   /api/v1/auth/register          # User registration
POST   /api/v1/auth/login             # JWT token
POST   /api/v1/auth/refresh           # Refresh token

POST   /api/v1/documents              # Upload document
GET    /api/v1/documents              # List documents (paginated)
GET    /api/v1/documents/{id}         # Get document details
DELETE /api/v1/documents/{id}         # Delete document
GET    /api/v1/documents/{id}/download # Download original

GET    /api/v1/processing/{job_id}    # Get processing status
POST   /api/v1/search                 # Semantic search
POST   /api/v1/search/hybrid          # Hybrid search (semantic + keyword)

GET    /api/v1/analytics/usage        # Usage statistics
GET    /api/v1/analytics/costs        # Cost breakdown
```

**Explain API versioning:**

"/api/v1/ prefix allows breaking changes in v2 without disrupting v1 clients. Critical for production systems."

**5. Processing Pipeline (10 minutes)**

*Draw async processing flow:*

```
User Upload → API → S3 Upload → Create DB Record → Return job_id
                                                         ↓
                                                    Celery Task
                                                         ↓
                                      ┌──────────────────┴──────────────────┐
                                      ↓                                      ↓
                            Extract Text (PyPDF2)              Update Status (PubNub)
                                      ↓
                            Generate Embeddings (OpenAI)
                                      ↓
                            Store in vector_embeddings
                                      ↓
                            AI Analysis (Multi-Model Router)
                                      ↓
                ┌─────────────────────┼─────────────────────┐
                ↓                     ↓                      ↓
           Summary (GPT-3.5)   Action Items (GPT-4)   Risks (Claude)
                ↓                     ↓                      ↓
                └─────────────────────┴─────────────────────┘
                                      ↓
                            Store in processing_results
                                      ↓
                            Update Status: completed
                                      ↓
                            Notify User (PubNub)
```

**Explain processing decisions:**

"**Why Async Processing:**
- Document processing takes 30-60 seconds
- Can't block HTTP request for that long
- Return immediately with job_id
- Process in background with Celery

**Why Multi-Model AI:**
- Different tasks have different requirements
- GPT-3.5: Fast, cheap for simple summaries
- GPT-4: Best for structured output (action items)
- Claude: Superior reasoning for risk assessment
- 44% cost savings vs using only GPT-4

**Why PubNub:**
- Real-time progress updates
- User sees 'extracting text → analyzing → completed'
- Better UX than polling every 5 seconds
- Reduces server load by 90%"

**6. Search Architecture (10 minutes)**

*Draw hybrid search system:*

```
User Query: "budget concerns"
         ↓
    ┌────┴────┐
    ↓         ↓
Semantic   Keyword
Search     Search
    ↓         ↓
pgvector   Elasticsearch
    ↓         ↓
Results    Results
    ↓         ↓
    └────┬────┘
         ↓
    Reciprocal
    Rank Fusion
         ↓
    Combined
    Results
```

**Implementation:**

```python
async def hybrid_search(query: str, user: User, limit: int = 10):
    # 1. Generate query embedding
    query_embedding = await openai.Embedding.create(
        model='text-embedding-ada-002',
        input=query
    )

    # 2. Semantic search with pgvector
    semantic_results = await db.execute(
        text('''
            SELECT
                id,
                title,
                1 - (embedding <=> :query_embedding) AS similarity
            FROM vector_embeddings
            WHERE organization_id = :org_id
                AND 1 - (embedding <=> :query_embedding) > 0.7
            ORDER BY embedding <=> :query_embedding
            LIMIT 20
        '''),
        {
            'query_embedding': query_embedding,
            'org_id': user.organization_id
        }
    )

    # 3. Keyword search with Elasticsearch
    keyword_results = await es.search(
        index='documents',
        body={
            'query': {
                'bool': {
                    'must': [
                        {'match': {'content': query}},
                        {'term': {'organization_id': str(user.organization_id)}}
                    ]
                }
            },
            'size': 20
        }
    )

    # 4. Reciprocal Rank Fusion (RRF)
    # Combines semantic + keyword results
    combined = reciprocal_rank_fusion(
        semantic_results,
        keyword_results,
        k=60
    )

    return combined[:limit]

def reciprocal_rank_fusion(results_a, results_b, k=60):
    scores = {}

    # Score from semantic search
    for rank, doc in enumerate(results_a, 1):
        scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank)

    # Score from keyword search
    for rank, doc in enumerate(results_b, 1):
        scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank)

    # Sort by combined score
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Explain search decisions:**

"**Why Hybrid Search:**
- Semantic search: Finds conceptually similar documents
  - Query: 'budget concerns' → finds docs about 'cost overruns', 'financial risks'
- Keyword search: Finds exact matches
  - Query: 'Q1 2024' → finds exact quarter reference
- Hybrid: Best of both worlds
  - Semantic for meaning, keyword for precision

**Why pgvector:**
- $0 cost (vs $6K/year for Pinecone)
- 95ms p95 latency (faster than Pinecone)
- Same database as source documents (ACID guarantees)

**Why Reciprocal Rank Fusion:**
- Simple, effective ranking algorithm
- Combines results from multiple sources
- No tuning required (parameter k=60 works well)"

**7. Scalability & Performance (5 minutes)**

*Discuss scaling strategies:*

"**Horizontal Scaling:**

1. **API Layer**: ECS Fargate auto-scales 2-10 containers based on CPU
2. **Celery Workers**: Auto-scale based on queue depth
3. **Database**: Read replicas for analytics queries
4. **Cache**: Redis cluster with 3 nodes

**Vertical Scaling:**

1. **Database**: Start with db.t4g.medium, can upgrade to r5.xlarge
2. **Cache**: Start with cache.t4g.small, can upgrade to r6g.large

**Performance Optimizations:**

1. **Connection Pooling**: Reuse database connections (max 100 connections)
2. **Caching**: Redis for AI responses (30% hit rate)
3. **CDN**: CloudFront for static assets and document downloads
4. **Compression**: gzip responses (75% size reduction)
5. **Indexes**: Composite indexes on organization_id + created_at

**Load Testing Results:**

- 500 concurrent users
- 520 requests/second throughput
- 450ms p95 API latency
- 95ms p95 search latency
- 99.95% uptime"

**8. Cost Optimization (5 minutes)**

*Break down costs:*

"**Monthly Cost Breakdown (10K docs/month):**

| Component | Service | Cost |
|-----------|---------|------|
| Compute | ECS Fargate (2-10 tasks) | $120 |
| Database | RDS PostgreSQL (t4g.medium) | $85 |
| Cache | ElastiCache Redis (t4g.small) | $45 |
| Storage | S3 (1TB) | $23 |
| CDN | CloudFront | $20 |
| AI APIs | OpenAI + Claude | $650 |
| **Total** | | **$943/month** |

**Cost Per Document:** $0.094

**Revenue Model:**
- $0.25 per document processed
- Gross margin: 62%
- Break-even: 3,772 docs/month

**Optimization Strategies:**

1. **Multi-model routing**: Saved 44% on AI costs ($530/month)
2. **Semantic caching**: Additional 15% savings ($98/month)
3. **pgvector vs Pinecone**: Saved $500/month
4. **Auto-scaling**: Only pay for what we use (vs always-on EC2)
5. **S3 lifecycle policies**: Archive old documents to Glacier"

**9. Security Considerations (5 minutes)**

*Outline security layers:*

"**Authentication & Authorization:**
1. JWT tokens with 1-hour expiration
2. Refresh tokens with rotation
3. bcrypt password hashing (cost factor: 12)
4. RBAC: Admin, Member, Viewer roles

**Multi-Tenancy Isolation:**
1. Row-Level Security (RLS) in PostgreSQL
2. Application-level filtering (organization_id)
3. S3 bucket prefixes by organization
4. Redis key namespacing by organization

**Data Protection:**
1. TLS 1.3 for all traffic
2. Encryption at rest (AES-256)
3. PII detection in AI responses
4. Audit logging for all data access

**Compliance:**
1. GDPR: Data export/deletion on request
2. SOC 2 ready: Audit logs, access controls
3. Data residency: Configurable AWS region

**Rate Limiting:**
1. 100 requests/minute per user (prevents abuse)
2. Circuit breakers on external APIs
3. DDoS protection via CloudFront + WAF"

**10. Monitoring & Observability (5 minutes)**

*Describe monitoring stack:*

"**Metrics (CloudWatch):**
- API latency (p50, p95, p99)
- Processing time per document
- Error rate by endpoint
- Queue depth (Celery)
- Database connection pool usage
- Cache hit rate

**Logging (CloudWatch Logs):**
- Structured JSON logs
- Correlation IDs for request tracing
- Error stack traces
- AI API costs per request

**Alerting (CloudWatch Alarms + SNS):**
- Error rate > 1% → Page on-call
- API latency p95 > 500ms → Slack alert
- Processing failure rate > 5% → Slack alert
- Database CPU > 80% → Auto-scale or alert
- Queue depth > 1000 → Scale workers

**Tracing (Optional - AWS X-Ray):**
- End-to-end request tracing
- Identify slow dependencies
- Visualize service interactions"

---

This system design demonstrates:
✅ Scalable architecture (horizontal + vertical)
✅ Cost-optimized (multi-model AI, pgvector, auto-scaling)
✅ Secure (RLS, JWT, encryption, RBAC)
✅ Performant (caching, indexing, async processing)
✅ Observable (metrics, logs, alerts)
✅ Production-ready (99.95% uptime, comprehensive testing)

**Estimated time: 60 minutes for complete walkthrough**

---

## Code Walkthrough Prep

### Key Code Sections to Discuss

**1. Multi-Model Router Implementation**

File: `backend/app/services/ai_service.py:45-89`

**What to highlight:**
- Intelligent routing logic based on task type and complexity
- Cost optimization (44% savings)
- Fallback mechanism for API failures
- Validation of model selection with A/B testing

**2. pgvector Semantic Search**

File: `backend/app/services/search_service.py:112-156`

**What to highlight:**
- HNSW index for fast similarity search
- Hybrid search with RRF algorithm
- Multi-tenant filtering (organization_id)
- Performance optimization (95ms p95 latency)

**3. Async Processing Pipeline**

File: `backend/app/tasks/document_processing.py:28-92`

**What to highlight:**
- Celery task structure
- Error handling with retries
- Real-time updates via PubNub
- Transactional integrity

**4. Row-Level Security Implementation**

File: `backend/app/middleware/tenant_context.py:15-38`

**What to highlight:**
- PostgreSQL session variable injection
- Defense in depth (RLS + application filtering)
- Testing strategy for tenant isolation

**5. Circuit Breaker Pattern**

File: `backend/app/utils/circuit_breaker.py:10-58`

**What to highlight:**
- Preventing cascading failures
- State machine (CLOSED → OPEN → HALF_OPEN)
- Recovery timeout configuration

---

## Metrics & Impact Discussion

### Business Impact

**Time Savings:**
- Before: 30 minutes per document (manual review)
- After: 30 seconds per document (AI processing)
- **Reduction: 98% time savings**
- **For 10K docs/month**: 5,000 hours → 83 hours saved monthly

**Cost Reduction:**
- Manual labor cost: $48/hour (PM salary)
- Before: 5,000 hours × $48 = $240,000/month
- After: 83 hours × $48 + $943 (system cost) = $4,927/month
- **Savings: $235,073/month = $2.82M annually**

**Accuracy Improvement:**
- Manual review: 85% accuracy (human error, fatigue)
- AI processing: 91% accuracy (consistent, validated)
- **Improvement: +6 percentage points**

### Technical Metrics

**Performance:**
- API latency p95: 450ms (target: <500ms) ✅
- Search latency p95: 95ms (target: <200ms) ✅
- Processing time avg: 35s (target: <60s) ✅
- Throughput: 520 req/s (target: 500+) ✅
- Uptime: 99.95% (target: 99.9%+) ✅

**Cost Efficiency:**
- Cost per document: $0.094
- AI cost optimization: 44% vs single-model
- Infrastructure cost: $943/month for 10K docs
- Unit economics: Profitable at >4K docs/month

**Scale:**
- Concurrent users: 500+ supported
- Documents processed: 25K+ in production
- Database size: 2.3 GB (pgvector embeddings)
- Cache hit rate: 30% (AI responses)

---

## Lessons Learned Talking Points

### What Went Well

1. **Architecture Planning**: Spent week 1 writing ADRs before coding
   - Rationale: Avoided costly rewrites
   - Impact: Clear decisions, easy onboarding

2. **Multi-Model Strategy**: Task-specific model selection
   - Rationale: Different models excel at different tasks
   - Impact: 44% cost reduction + 2% accuracy improvement

3. **pgvector Choice**: Self-hosted vector search
   - Rationale: Benchmarked against Pinecone
   - Impact: $6K/year savings, better performance

4. **Comprehensive Testing**: 98% code coverage
   - Rationale: Confidence in deployments
   - Impact: Zero data breaches, safe refactoring

### What Could Be Improved

1. **Caching Timeline**: Added Redis in week 8, should have been week 2
   - Cost: $1,080 wasted on AI calls (6 weeks late)
   - Learning: Add caching on day 1, not later

2. **Load Testing**: First test in week 11 (1 week before launch)
   - Impact: Panic-mode fixes under pressure
   - Learning: Load test by week 6, allow time to fix

3. **Monitoring Setup**: CloudWatch added in week 10
   - Impact: Production bugs went unnoticed for hours
   - Learning: Monitoring from day 1, can't fix what you can't see

4. **Feature Flags**: Hard-coded toggles instead of proper system
   - Impact: Couldn't toggle features without deployment
   - Learning: Use LaunchDarkly from start, deploy != release

### Technical Insights

1. **pgvector Validation**: Don't assume managed services are better
   - Benchmark your workload
   - Calculate total cost of ownership
   - For <10M vectors, pgvector often wins

2. **FastAPI Choice**: Best framework for async Python APIs
   - Native async support
   - Type safety with Pydantic
   - Auto-generated docs
   - Would choose again

3. **Multi-Model Validation**: A/B test model selection
   - 500 documents per model per task type
   - Manual review of 50 samples
   - Data-driven decisions, not hunches

### If I Built This Again

**Keep:**
- FastAPI for async API
- PostgreSQL + pgvector for data + vectors
- Multi-model AI orchestration
- Comprehensive testing

**Change:**
- Add caching from day 1
- Load test by week 6
- Set up monitoring before first code
- Use feature flags from start
- API versioning from first endpoint

**Framework for Next Project:**

Week 1:
✅ Architecture planning + ADRs
✅ API versioning scheme
✅ Feature flag system
✅ Basic monitoring + alerting
✅ Caching strategy

Week 2-5:
✅ Core features with tests
✅ Load testing incrementally

Week 6:
✅ Full load test
✅ Security audit
✅ Performance benchmarks

Week 7-8:
✅ Documentation
✅ Deployment automation

Week 9+:
✅ Beta launch with feature flags
✅ Gradual rollout (10% → 50% → 100%)

---

## Questions to Ask Interviewers

### About the Role

1. "What does a typical project lifecycle look like for this role? From ideation to production?"

2. "What's the team structure? How many engineers, what specializations?"

3. "What's the balance between building new features and maintaining existing systems?"

4. "How much autonomy do engineers have in technical decision-making?"

5. "What's your approach to code review and technical design discussions?"

### About the Tech Stack

1. "What's your current tech stack, and are there any major migrations planned?"

2. "How do you handle deployment and release management? Blue-green, canary, feature flags?"

3. "What's your observability stack? How do you handle monitoring and alerting?"

4. "How do you balance technical debt vs new feature development?"

5. "What's your approach to testing? Unit, integration, E2E coverage expectations?"

### About AI/ML (if relevant)

1. "How are you currently using LLMs or AI in your product?"

2. "What's your approach to managing AI costs and optimizing performance?"

3. "Do you do any model fine-tuning, or primarily use API-based models?"

4. "How do you handle data privacy and security with AI integrations?"

5. "What's your strategy for staying current with rapidly evolving AI capabilities?"

### About Growth & Learning

1. "What does professional development look like here? Conference budget, learning time?"

2. "How do senior engineers mentor junior engineers?"

3. "What's the career progression path for this role?"

4. "How do you handle knowledge sharing across the team?"

5. "What's the most technically challenging project the team is working on right now?"

### About Culture & Process

1. "How do you balance moving fast with maintaining quality?"

2. "What's your on-call rotation like? How do you handle production incidents?"

3. "How do you prioritize work? Product-led, engineering-led, customer-led?"

4. "What's your approach to remote work and collaboration?"

5. "How do you celebrate wins and handle failures as a team?"

### Red Flag Questions (Ask Diplomatically)

1. "What's your approach to work-life balance? Typical hours, on-call expectations?"

2. "How do you handle technical disagreements? Can you give an example?"

3. "What's your biggest technical challenge right now?"

4. "Why is this role open? Backfill or new headcount?"

5. "What would success look like for this role in the first 6 months?"

---

## Interview Preparation Checklist

**Before the Interview:**

- [ ] Review project documentation (README, architecture, ADRs)
- [ ] Refresh on key metrics (latency, cost, accuracy)
- [ ] Prepare 2-3 stories for behavioral questions (STAR format)
- [ ] Review code sections you're most proud of
- [ ] Prepare questions for interviewers (5-7 questions)
- [ ] Test demo environment (ensure it's working)
- [ ] Prepare to share screen for code walkthrough
- [ ] Review company's product and tech stack
- [ ] Prepare 30-second elevator pitch
- [ ] Sleep well, eat before interview

**During the Interview:**

- [ ] Start with clear, concise elevator pitch
- [ ] Use STAR format for behavioral questions
- [ ] Include code examples when discussing technical decisions
- [ ] Quantify impact with metrics
- [ ] Acknowledge trade-offs and alternatives considered
- [ ] Ask clarifying questions before answering
- [ ] Show enthusiasm and genuine interest
- [ ] Take notes on interviewer responses
- [ ] Ask prepared questions
- [ ] Thank interviewers for their time

**After the Interview:**

- [ ] Send thank-you email within 24 hours
- [ ] Reflect on what went well and what to improve
- [ ] Follow up on any questions you couldn't answer
- [ ] Connect on LinkedIn (if appropriate)
- [ ] Update your interview notes

---

**Last Updated**: 2025-01-20
**Document Version**: 1.0.0
