# Document Processing Pipeline

## Overview

The Document Processing Pipeline is an intelligent, production-ready system for extracting insights from project management documents. It orchestrates multiple AWS services (S3, Textract, Comprehend, Bedrock) and AI analysis to provide comprehensive document understanding.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Document Processing Pipeline                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Upload to S3        ───▶  Encrypted storage with metadata   │
│  2. Text Extraction     ───▶  Textract (PDF/images) or direct   │
│  3. Text Cleaning       ───▶  Normalization and preprocessing   │
│  4. NLP Analysis        ───▶  Comprehend (entities, sentiment)  │
│  5. Action Items        ───▶  Claude AI extraction              │
│  6. Risk Detection      ───▶  Claude AI analysis                │
│  7. Summary Generation  ───▶  Claude AI summarization           │
│  8. Embeddings          ───▶  Vector search preparation         │
│  9. Results Storage     ───▶  Supabase database                 │
│                                                                   │
│  ✓ Real-time Progress   ───▶  PubNub notifications              │
│  ✓ Checkpoint Recovery  ───▶  Resume from failures              │
│  ✓ Cost Tracking        ───▶  Per-document cost analysis        │
│  ✓ Rollback Support     ───▶  Cleanup on failures               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### 1. State Machine Tracking

The pipeline uses a comprehensive state machine to track processing:

```python
class ProcessingState(Enum):
    UPLOADED = "uploaded"
    UPLOADING_TO_S3 = "uploading_to_s3"
    EXTRACTING_TEXT = "extracting_text"
    CLEANING_TEXT = "cleaning_text"
    ANALYZING_ENTITIES = "analyzing_entities"
    EXTRACTING_ACTIONS = "extracting_actions"
    EXTRACTING_RISKS = "extracting_risks"
    GENERATING_SUMMARY = "generating_summary"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    STORING_RESULTS = "storing_results"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

Each state transition is:
- Logged for audit trail
- Saved as checkpoint for recovery
- Published to PubNub for real-time updates
- Stored in database

### 2. Checkpoint Recovery

If processing fails, the system can recover from the last successful checkpoint:

```python
checkpoint = ProcessingCheckpoint(
    document_id="doc_123",
    state=ProcessingState.EXTRACTING_TEXT,
    data={"s3_key": "documents/user/file.pdf", "text": "..."},
    error=None
)
```

Checkpoints include:
- Current processing state
- Intermediate data (S3 keys, extracted text, etc.)
- Error information if failed
- Timestamp for recovery decisions

### 3. Real-Time Progress Updates

PubNub integration provides live updates to clients:

```javascript
// Client-side subscription
pubnub.subscribe({
    channels: ['user_123_documents']
});

pubnub.addListener({
    message: function(event) {
        // {
        //   type: "document_processing",
        //   document_id: "doc_456",
        //   state: "extracting_text",
        //   progress: 25,
        //   message: "Extracting text from document..."
        // }
    }
});
```

Progress updates include:
- Current state
- Progress percentage (0-100)
- Human-readable message
- Additional data (duration, cost, etc.)

### 4. Error Handling & Rollback

Comprehensive error handling with automatic rollback:

```python
try:
    # Upload to S3
    s3_result = await s3.upload_document(...)

    # Extract text
    text = await extract_text(...)

    # Analyze...

except Exception as e:
    # Rollback: Delete S3 file
    await s3.delete_document(s3_key)

    # Mark as failed
    await save_checkpoint(state=FAILED, error=str(e))

    # Notify user
    await publish_progress(state=FAILED, message=f"Failed: {e}")
```

## Usage

### Basic Document Processing

```python
from app.services.document_processor import DocumentProcessor

processor = DocumentProcessor()

result = await processor.process_document(
    document_id="doc_123",
    user_id="user_456",
    file_path="/tmp/project_plan.pdf",
    filename="project_plan.pdf",
    document_type=DocumentType.PROJECT_PLAN,
    processing_options={
        "extract_actions": True,
        "extract_risks": True,
        "generate_summary": True,
        "send_webhooks": True,
        "webhook_url": "https://api.example.com/webhooks/documents"
    }
)

# Result structure:
{
    "document_id": "doc_123",
    "status": "completed",
    "s3_key": "documents/user_456/2024/01/uuid_project_plan.pdf",
    "extracted_text": "Full document text...",
    "word_count": 1234,

    "entities": [
        {"text": "John Doe", "type": "PERSON", "score": 0.95},
        {"text": "Q1 2024", "type": "DATE", "score": 0.89}
    ],

    "sentiment": {
        "sentiment": "POSITIVE",
        "scores": {"positive": 0.75, "negative": 0.05, "neutral": 0.20}
    },

    "action_items": [
        {
            "action": "Complete design review",
            "assignee": "Design Team",
            "due_date": "2024-03-15",
            "priority": "HIGH",
            "confidence": 0.9
        }
    ],

    "risks": [
        {
            "risk": "Dependency on external API",
            "severity": "HIGH",
            "category": "Technical",
            "mitigation": "Develop mock API",
            "confidence": 0.85
        }
    ],

    "summary": {
        "executive_summary": "Project plan overview...",
        "key_points": ["Point 1", "Point 2"],
        "next_steps": ["Step 1", "Step 2"]
    },

    "cost": 0.0234,  # USD
    "duration_seconds": 12.5
}
```

### Batch Processing

Process multiple documents in parallel:

```python
documents = [
    {
        "document_id": "doc_1",
        "file_path": "/tmp/doc1.pdf",
        "filename": "doc1.pdf",
        "document_type": DocumentType.STATUS_REPORT
    },
    {
        "document_id": "doc_2",
        "file_path": "/tmp/doc2.pdf",
        "filename": "doc2.pdf",
        "document_type": DocumentType.MEETING_NOTES
    },
    # ... up to 100 documents
]

batch_result = await processor.process_multiple_documents(
    documents=documents,
    user_id="user_456",
    max_parallel=3,  # Process 3 at a time
    estimate_cost=True
)

# Batch result:
{
    "batch_id": "batch_1234567890",
    "total_documents": 10,
    "successful": 9,
    "failed": 1,
    "failed_documents": [
        {"document_id": "doc_5", "error": "Unsupported file type"}
    ],
    "total_cost": 0.234,
    "total_duration_seconds": 45.2
}
```

### Cancellation

Cancel processing in progress:

```python
# Cancel from another thread/request
await processor.cancel_processing("doc_123")

# The processing will be interrupted at the next checkpoint
# and marked as CANCELLED
```

## Specialized Extraction Methods

### Action Items Extraction

Extracts actionable tasks with structured data:

```python
action_items = await processor.extract_action_items(
    text=document_text,
    document_type=DocumentType.MEETING_NOTES
)

# Returns:
[
    {
        "action": "Schedule follow-up meeting",
        "assignee": "John Doe",
        "due_date": "2024-03-20",
        "priority": "MEDIUM",
        "status": "TODO",
        "confidence": 0.92,
        "context": "Discussed in Q1 planning session"
    }
]
```

**Supported Fields:**
- `action` (required): Clear description
- `assignee` (optional): Person or team responsible
- `due_date` (optional): ISO format date
- `priority`: HIGH, MEDIUM, or LOW
- `status`: TODO, IN_PROGRESS, BLOCKED, or DONE
- `confidence`: 0.0 to 1.0
- `context`: Brief context from document

### Risk Detection

Identifies project risks and blockers:

```python
risks = await processor.extract_risks(
    text=document_text,
    document_type=DocumentType.PROJECT_PLAN
)

# Returns:
[
    {
        "risk": "Team size insufficient for timeline",
        "severity": "HIGH",
        "category": "Resource",
        "impact": "Project delay of 2-3 weeks",
        "probability": "HIGH",
        "mitigation": "Request additional contractors",
        "confidence": 0.88
    }
]
```

**Risk Categories:**
- Technical
- Resource
- Schedule
- Budget
- External
- Other

**Severity Levels:**
- CRITICAL: Immediate attention required
- HIGH: Significant impact
- MEDIUM: Moderate concern
- LOW: Minor issue

### Entity Enhancement

Combines Comprehend NER with Claude for project-specific entities:

```python
entities = await processor.extract_entities(
    text=document_text,
    document_type=DocumentType.PROJECT_PLAN
)

# Returns:
{
    "comprehend_entities": [
        {"text": "Amazon", "type": "ORGANIZATION", "score": 0.98},
        {"text": "Seattle", "type": "LOCATION", "score": 0.95}
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
        "dependencies": [
            {"from": "Design", "to": "Development", "type": "finish-to-start"}
        ],
        "teams": [
            {"name": "Backend", "members": ["Alice", "Bob"], "focus": "API"}
        ]
    }
}
```

### Summary Generation

Generates executive summaries with configurable length:

```python
summary = await processor.generate_summary(
    text=document_text,
    document_type=DocumentType.STATUS_REPORT,
    length="medium"  # short, medium, or long
)

# Returns:
{
    "executive_summary": "Project is on track for Q1 delivery...",
    "key_points": [
        "Backend API development 80% complete",
        "Frontend integration started",
        "Testing environment ready"
    ],
    "decisions": [
        "Approved additional $10K for cloud infrastructure"
    ],
    "next_steps": [
        "Complete API testing by March 15",
        "Begin user acceptance testing"
    ],
    "concerns": [
        "Potential delay in third-party integration"
    ]
}
```

## Cost Tracking

The pipeline tracks costs for each AWS service:

```python
# Cost is calculated automatically
result = await processor.process_document(...)

print(f"Processing cost: ${result['cost']:.4f}")

# Detailed breakdown:
cost_report = cost_tracker.get_cost_report()

# {
#   "total_cost": 0.0234,
#   "costs_by_service": {
#     "bedrock": 0.0120,
#     "textract": 0.0075,
#     "comprehend": 0.0015,
#     "s3": 0.000024
#   },
#   "usage": {
#     "bedrock": {"input_tokens": 1500, "output_tokens": 800},
#     "textract": {"pages": 5},
#     "comprehend": {"characters": 5000},
#     "s3": {"requests": 2, "bytes": 524288}
#   }
# }
```

**Average Costs per Document:**
- Small text file (1-2 pages): $0.01 - $0.02
- Medium PDF (5-10 pages): $0.05 - $0.10
- Large PDF (20+ pages): $0.15 - $0.30

**Cost Optimization Tips:**
1. Use direct text extraction for .txt files (free)
2. Disable embeddings if not needed
3. Process in batches for better efficiency
4. Set reasonable token limits for Claude

## Supported File Formats

| Format | Extraction Method | Features |
|--------|------------------|----------|
| `.txt` | Direct UTF-8 decode | Fastest, no cost |
| `.md` | Direct UTF-8 decode | Fastest, no cost |
| `.pdf` | Textract | Tables, forms, OCR |
| `.png`, `.jpg`, `.jpeg` | Textract | OCR, handwriting |
| `.tiff` | Textract | Multi-page support |

**File Size Limits:**
- Synchronous Textract: < 5 MB
- Asynchronous Textract: < 500 MB
- Maximum text length for analysis: ~50,000 characters

## Error Handling

### Retry Logic

Transient errors are retried automatically (3 attempts with exponential backoff):

```python
@retry(
    retry=retry_if_exception_type((ClientError, BotoCoreError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def process_step(...):
    # AWS API call
```

### Error Types

1. **DocumentProcessingError**: General processing error
2. **TextractError**: Text extraction failed
3. **ComprehendError**: NLP analysis failed
4. **BedrockError**: Claude AI error
5. **S3Error**: Storage error
6. **ValidationError**: Invalid input

### Rollback on Failure

If processing fails after S3 upload:
1. S3 file is deleted automatically
2. Document status set to FAILED
3. Error message stored in database
4. User notified via PubNub
5. Checkpoint saved for analysis

## Performance Metrics

### Processing Times

Average processing times for different document types:

| Document Type | Pages | Time | Cost |
|--------------|-------|------|------|
| Meeting Notes | 1-2 | 3-5s | $0.01 |
| Status Report | 3-5 | 8-12s | $0.05 |
| Project Plan | 10-20 | 20-30s | $0.15 |
| Technical Spec | 30-50 | 45-60s | $0.30 |

### Throughput

- Single document: ~5-30 seconds
- Batch (10 docs, 3 parallel): ~60-90 seconds
- Maximum concurrent: Limited by AWS rate limits

## Webhook Integration

Send notifications to external systems:

```python
result = await processor.process_document(
    ...,
    processing_options={
        "send_webhooks": True,
        "webhook_url": "https://api.example.com/webhooks/documents"
    }
)

# Webhook POST body:
{
    "event": "document_processed",
    "document_id": "doc_123",
    "status": "completed",
    "timestamp": "2024-01-15T10:30:00Z",
    "summary": {
        "word_count": 1234,
        "action_items": 5,
        "risks": 2,
        "cost": 0.0234,
        "duration": 12.5
    }
}
```

## Configuration

Environment variables for document processing:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=your-bucket

# Bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_MAX_TOKENS=4096
BEDROCK_TEMPERATURE=0.7

# PubNub (for real-time updates)
PUBNUB_ENABLED=true
PUBNUB_SUBSCRIBE_KEY=your_key
PUBNUB_PUBLISH_KEY=your_key

# Processing Options
MAX_PARALLEL_DOCUMENTS=3
ENABLE_EMBEDDINGS=false
```

## Best Practices

### 1. Always Use Document Types

Specify the correct document type for better analysis:

```python
await processor.process_document(
    ...,
    document_type=DocumentType.PROJECT_PLAN  # Not GENERAL
)
```

### 2. Enable Selective Processing

Only enable what you need to reduce cost:

```python
processing_options={
    "extract_actions": True,   # Enable
    "extract_risks": True,      # Enable
    "generate_embeddings": False,  # Disable if not needed
}
```

### 3. Monitor Costs

Track costs per user/project:

```python
cost = result["cost"]
await log_cost_to_analytics(user_id, document_id, cost)
```

### 4. Handle Failures Gracefully

Always check processing status:

```python
try:
    result = await processor.process_document(...)
    if result["status"] == "completed":
        # Success
    else:
        # Handle failure
except DocumentProcessingError as e:
    logger.error(f"Processing failed: {e}")
    # Notify user
```

### 5. Use Batch Processing for Bulk Uploads

More efficient than processing one-by-one:

```python
# Good: Batch processing
await processor.process_multiple_documents(documents)

# Less efficient: Loop
for doc in documents:
    await processor.process_document(doc)
```

## Monitoring & Observability

### Logs

Comprehensive logging at each step:

```
INFO: Step 1: Uploading project_plan.pdf to S3
INFO: Uploaded to S3: documents/user_456/2024/01/uuid_project_plan.pdf
INFO: Step 2: Extracting text from project_plan.pdf
INFO: Extracted 1234 words
INFO: Step 3: Cleaning text
INFO: Step 4: Analyzing with Comprehend
INFO: Found 25 entities, 15 key phrases
INFO: Step 5: Extracting action items
INFO: Extracted 5 action items
INFO: Step 6: Extracting risks
INFO: Identified 2 risks
INFO: Step 7: Generating summary
INFO: Generated summary
INFO: Step 9: Storing results
INFO: Document doc_123 processed successfully in 12.50s, cost: $0.0234
```

### Metrics

Track key metrics:
- Processing time per document
- Cost per document
- Success rate
- Error rate by type
- Average document size
- Popular document types

### Alerts

Set up alerts for:
- Processing failures > 10%
- Average cost > $0.50/document
- Processing time > 60 seconds
- S3 upload failures
- AWS service errors

## Troubleshooting

### Common Issues

**1. "Unsupported file type"**
- Solution: Check file extension is in supported list
- Verify file is not corrupted

**2. "Text extraction failed"**
- Solution: File may be password-protected or corrupted
- Try with a different file

**3. "Rate limit exceeded"**
- Solution: Reduce max_parallel in batch processing
- Contact AWS to increase service limits

**4. "PubNub publish failed"**
- Solution: Check PubNub credentials
- Verify PubNub is enabled in settings

**5. "Processing timeout"**
- Solution: Large files may take longer
- Check AWS Textract job status manually

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger("app.services.document_processor").setLevel(logging.DEBUG)
```

## Future Enhancements

Planned features:
- [ ] OpenAI GPT-4 integration as alternative to Claude
- [ ] Vector embeddings with Pinecone/Weaviate
- [ ] OCR quality assessment
- [ ] Multi-language support
- [ ] Custom entity training
- [ ] Document comparison/diff
- [ ] Real-time collaboration
- [ ] Version control for documents

## API Reference

See inline documentation in `backend/app/services/document_processor.py` for complete API reference.
