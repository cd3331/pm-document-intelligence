

# AI Model Optimization & Fine-tuning Guide

## Overview

This document covers the comprehensive AI optimization system for PM Document Intelligence, including fine-tuning, prompt engineering, performance monitoring, and cost optimization.

## Table of Contents

1. [Architecture](#architecture)
2. [Data Preparation](#data-preparation)
3. [Model Fine-tuning](#model-fine-tuning)
4. [Prompt Engineering](#prompt-engineering)
5. [Performance Monitoring](#performance-monitoring)
6. [Feedback Loop](#feedback-loop)
7. [Intelligent Routing](#intelligent-routing)
8. [Cost Optimization](#cost-optimization)
9. [API Reference](#api-reference)
10. [Best Practices](#best-practices)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Request                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Intelligent Router                              │
│  ┌──────────────┬──────────────┬──────────────────┐        │
│  │ Complexity   │ Requirements │ Cache Check      │        │
│  │ Assessment   │ Analysis     │                  │        │
│  └──────────────┴──────────────┴──────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Fast/Cheap   │ │   Balanced   │ │   Premium    │
    │              │ │              │ │              │
    │ GPT-3.5      │ │   GPT-4      │ │ GPT-4 Turbo  │
    │ Claude Inst  │ │   Claude 2   │ │ Claude 2.1   │
    └──────────────┘ └──────────────┘ └──────────────┘
              │             │             │
              └─────────────┼─────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Prompt Template Library                         │
│  ┌────────────────────────────────────────────────┐        │
│  │ Dynamic assembly based on:                     │        │
│  │ - Document type                                │        │
│  │ - Task type                                    │        │
│  │ - Few-shot examples                            │        │
│  │ - Chain-of-thought                             │        │
│  └────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Response Processing                             │
│  ┌────────────────────────────────────────────────┐        │
│  │ - Quality checks                               │        │
│  │ - Performance logging                          │        │
│  │ - Cache storage                                │        │
│  └────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Feedback Collection                             │
│  ┌────────────────────────────────────────────────┐        │
│  │ - User ratings                                 │        │
│  │ - Corrections                                  │        │
│  │ - Issue tracking                               │        │
│  │ - Retraining triggers                          │        │
│  └────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Preparation

### Overview

The data preparation pipeline (`ml/training/data_preparation.py`) collects and prepares training data from processed documents for fine-tuning.

### Key Features

1. **PII Detection and Removal**
   - Automatically removes emails, phone numbers, SSNs, credit cards
   - Replaces with placeholders like `[EMAIL]`, `[PHONE]`
   - Ensures GDPR and compliance

2. **Quality Scoring**
   - Based on user feedback
   - Result completeness
   - Confidence scores
   - Automatic filtering of low-quality examples

3. **Multiple Data Sources**
   - Document summaries
   - Action item extractions
   - Entity recognition
   - Risk assessments

### Usage

```python
from ml.training.data_preparation import TrainingDataCollector

collector = TrainingDataCollector(output_dir="ml/data/training")

# Collect examples
summaries = collector.collect_document_summaries(
    min_quality_score=0.8,
    limit=1000
)

# Format for platform
claude_format = collector.format_for_claude_finetuning(
    summaries,
    task_type="summarization"
)

# Split dataset
train, val, test = collector.split_dataset(
    claude_format,
    train_ratio=0.8,
    val_ratio=0.1,
    test_ratio=0.1
)

# Save
collector.save_dataset(train, "train.jsonl", format="jsonl")
```

### Running the Pipeline

```bash
cd ml/training
python data_preparation.py
```

---

## Model Fine-tuning

### Supported Platforms

1. **AWS Bedrock (Claude)**
   - Claude 2 and Claude Instant
   - Custom model import
   - Provisioned throughput

2. **OpenAI**
   - GPT-3.5 Turbo
   - GPT-4
   - Embeddings models

### Claude Fine-tuning

```python
from ml.training.fine_tuning import run_claude_finetuning

result = run_claude_finetuning(
    training_file="ml/data/training/train.jsonl",
    validation_file="ml/data/training/val.jsonl",
    job_name="my_finetuned_model",
    wait=True
)

print(f"Model ARN: {result['output_model_arn']}")
```

### OpenAI Fine-tuning

```python
from ml.training.fine_tuning import run_openai_finetuning

result = run_openai_finetuning(
    training_file="ml/data/training/openai_train.jsonl",
    model="gpt-3.5-turbo",
    suffix="pm_docs_v1",
    wait=True
)

print(f"Fine-tuned model: {result['fine_tuned_model']}")
```

### CLI Usage

```bash
# Claude fine-tuning
python ml/training/fine_tuning.py \
  --platform claude \
  --train ml/data/training/train.jsonl \
  --val ml/data/training/val.jsonl \
  --name my_model

# OpenAI fine-tuning
python ml/training/fine_tuning.py \
  --platform openai \
  --train ml/data/training/openai_train.jsonl \
  --model gpt-3.5-turbo \
  --name pm_docs
```

### Hyperparameter Optimization

```python
from ml.training.fine_tuning import HyperparameterOptimizer

# Get suggested parameters based on dataset size
params = HyperparameterOptimizer.optimize_for_openai(
    training_data_size=500
)
# Returns: {"n_epochs": 3, "learning_rate_multiplier": 1.5}

# Grid search
grid = HyperparameterOptimizer.grid_search_params()
for params in grid:
    # Run training with params
    pass
```

---

## Prompt Engineering

### Template Library

The system includes 10+ optimized prompt templates:

```python
from ml.models.prompt_templates import get_prompt_library

library = get_prompt_library()

# Get template
template = library.get_template("executive_summary_detailed")

# Render with variables
prompts = template.render(document_text="...")

# Use in API call
response = anthropic.messages.create(
    model="claude-2",
    system=prompts["system"],
    messages=[{"role": "user", "content": prompts["user"]}]
)
```

### Available Templates

1. **Executive Summaries**
   - `executive_summary_short`: 2-3 sentences
   - `executive_summary_medium`: 1 paragraph
   - `executive_summary_detailed`: Structured format

2. **Action Items**
   - `action_items_simple`: Simple list
   - `action_items_categorized`: Grouped by category

3. **Analysis**
   - `risk_assessment`: Risk identification and mitigation
   - `qa_with_context`: Q&A with citations
   - `multi_doc_synthesis`: Multi-document integration
   - `cot_complex_analysis`: Chain-of-thought reasoning

### Dynamic Prompt Assembly

```python
from ml.models.prompt_templates import get_prompt_assembler, DocumentType

assembler = get_prompt_assembler()

prompts = assembler.assemble_prompt(
    task="summary",
    document_text=doc_text,
    document_type=DocumentType.MEETING_NOTES,
    few_shot_examples=[
        {"input": "Example 1...", "output": "Summary 1..."},
        {"input": "Example 2...", "output": "Summary 2..."}
    ]
)
```

### Prompt Performance Tracking

```python
from ml.models.prompt_templates import get_optimization_tracker

tracker = get_optimization_tracker()

# Record usage
tracker.record_usage(
    template_id="exec_summary_short_v1",
    success=True,
    quality_score=0.92,
    cost=0.015,
    latency=1.2,
    feedback="Great summary!"
)

# Get performance
perf = tracker.get_template_performance("exec_summary_short_v1")
# Returns: {
#   "total_uses": 150,
#   "success_rate": 0.96,
#   "avg_quality_score": 0.89,
#   "avg_cost": 0.014,
#   "avg_latency": 1.1
# }

# Compare templates
comparison = tracker.compare_templates([
    "exec_summary_short_v1",
    "exec_summary_medium_v1"
])
```

---

## Performance Monitoring

### Tracking Model Performance

```python
from ml.monitoring.model_performance import ModelPerformanceMonitor

monitor = ModelPerformanceMonitor()

# Track prediction
monitor.track_prediction(
    model_version="v1.1.0",
    task_type="action_items",
    ground_truth=actual_items,
    prediction=predicted_items,
    confidence=0.95,
    latency=1.5,
    cost=0.02
)

# Calculate metrics
metrics = monitor.calculate_accuracy_metrics(
    model_version="v1.1.0",
    task_type="action_items",
    time_window=timedelta(days=7)
)
# Returns: {
#   "accuracy": 0.92,
#   "total_predictions": 450,
#   "avg_confidence": 0.89,
#   "avg_latency": 1.2,
#   "avg_cost": 0.018
# }
```

### Drift Detection

```python
# Detect model drift
drift = monitor.detect_drift(
    model_version="v1.1.0",
    task_type="summary",
    baseline_window=timedelta(days=30),
    current_window=timedelta(days=7),
    threshold=0.05
)

if drift["drift_detected"]:
    print(f"Drift detected! Accuracy drop: {drift['accuracy_drift']:.2%}")
```

### Alerts

```python
from ml.monitoring.model_performance import AlertManager

alert_mgr = AlertManager()

alerts = alert_mgr.check_alerts(current_metrics, baseline_metrics)

for alert in alerts:
    if alert["severity"] == "high":
        send_notification(alert["message"])
```

---

## Feedback Loop

### Collecting Feedback

```python
from app.services.feedback_loop import FeedbackCollector

collector = FeedbackCollector(db)

# Submit feedback
collector.submit_feedback(
    result_id=result_uuid,
    user_id=user_uuid,
    rating="positive",  # or "negative", "neutral"
    corrections={"summary": "Corrected summary text..."},
    comments="The summary missed the key decision point",
    specific_issues=["missing_action_items", "incomplete_summary"]
)
```

### Analyzing Feedback

```python
from app.services.feedback_loop import FeedbackAnalyzer

analyzer = FeedbackAnalyzer(db)

# Get improvement opportunities
opportunities = analyzer.identify_improvement_opportunities()

for opp in opportunities:
    print(f"{opp['priority']} priority: {opp['recommendation']}")
```

### Retraining Triggers

```python
# Check if retraining is needed
should_retrain = collector.should_trigger_retraining()

if should_retrain:
    # Get corrections for training data
    corrections = collector.get_corrections_for_training(limit=100)

    # Prepare and run fine-tuning
    # ... (see Fine-tuning section)
```

### API Usage

```bash
# Submit feedback
curl -X POST https://api.your-app.com/api/models/feedback \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "result_id": "550e8400-e29b-41d4-a716-446655440000",
    "rating": "positive",
    "comments": "Excellent summary"
  }'

# Get feedback summary
curl https://api.your-app.com/api/models/feedback/summary?days=30 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Intelligent Routing

### How It Works

1. **Complexity Assessment**: Analyzes document length, type, and task
2. **Requirement Analysis**: Considers accuracy, cost, and speed priorities
3. **Model Selection**: Routes to optimal model tier
4. **Cache Check**: Returns cached response if available

### Usage

```python
from ml.optimization.intelligent_router import get_router

router = get_router()

# Route request
routing = router.route_request(
    document_text=doc_text,
    document_type="technical_spec",
    task_type="summary",
    requirements={
        "accuracy_priority": 0.8,
        "cost_priority": 0.1,
        "speed_priority": 0.1
    }
)

if routing["cached"]:
    return routing["response"]
else:
    # Call model
    model = routing["model_name"]
    # ... make API call
```

### Model Tiers

| Tier | Models | Cost | Latency | Best For |
|------|--------|------|---------|----------|
| Fast/Cheap | GPT-3.5, Claude Instant | $0.002/1K | 500ms | Simple tasks, high volume |
| Balanced | GPT-4, Claude 2 | $0.03/1K | 2000ms | Complex analysis, accuracy critical |
| Premium | GPT-4 Turbo, Claude 2.1 | $0.01/1K | 1500ms | Large documents, speed + accuracy |

### Caching

```python
from ml.optimization.intelligent_router import ResponseCache

cache = ResponseCache(ttl_hours=24)

# Cache response
cache.set(cache_key, response)

# Retrieve
cached = cache.get(cache_key)

# Get stats
stats = cache.get_stats()
# Returns: {
#   "total_entries": 150,
#   "total_hits": 450,
#   "avg_hits_per_entry": 3.0
# }
```

### Batch Processing

```python
from ml.optimization.intelligent_router import get_batch_processor

batch_proc = get_batch_processor()

# Add to batch
ready = batch_proc.add_to_batch(
    document_text=doc_text,
    task_type="summary",
    callback=process_result
)

if ready:
    # Process batch
    batch = batch_proc.get_batch(batch_key)
    # ... process all at once
```

---

## Cost Optimization

### Strategies

1. **Intelligent Routing**
   - Use cheaper models for simple tasks
   - Route to appropriate tier based on complexity

2. **Caching**
   - Cache common document patterns
   - 24-hour TTL by default
   - Significant cost savings on repeated queries

3. **Batch Processing**
   - Group similar documents
   - Process in batches for efficiency
   - Reduce API call overhead

4. **Model Selection**
   - Fine-tuned smaller models for specific tasks
   - Use embeddings caching
   - Optimize context window usage

### Cost Tracking

```python
from ml.monitoring.model_performance import ModelPerformanceMonitor

monitor = ModelPerformanceMonitor()

metrics = monitor.get_success_metrics_summary(timedelta(days=30))
total_cost = metrics.get("total_cost", 0)

print(f"Total AI cost (30 days): ${total_cost:.2f}")
print(f"Cost per document: ${total_cost / metrics['total_documents']:.3f}")
```

### API Endpoint

```bash
# Get cost summary
curl https://api.your-app.com/api/models/costs/summary?days=30 \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {
#   "total_cost": 1250.50,
#   "cost_per_document": 0.15,
#   "cost_by_model": {
#     "gpt-4": 850.30,
#     "gpt-3.5-turbo": 200.20
#   },
#   "savings_from_caching": 125.50
# }
```

---

## API Reference

### Model Performance

```
GET /api/models/performance
  - Query: model_version, task_type, days
  - Returns: Performance metrics

GET /api/models/performance/drift
  - Query: model_version, task_type
  - Returns: Drift detection results

GET /api/models/performance/alerts
  - Returns: Active performance alerts
```

### Feedback

```
POST /api/models/feedback
  - Body: FeedbackSubmission
  - Returns: Confirmation

GET /api/models/feedback/summary
  - Query: document_type, task_type, days
  - Returns: Feedback statistics

GET /api/models/feedback/improvements
  - Returns: Improvement opportunities

GET /api/models/feedback/retraining-needed
  - Returns: Retraining recommendation
```

### Model Versions

```
GET /api/models/versions
  - Returns: Available model versions

POST /api/models/versions/{version}/activate
  - Activates specific version

GET /api/models/versions/compare
  - Query: version_a, version_b
  - Returns: Comparison metrics
```

### Prompts

```
GET /api/models/prompts/performance
  - Query: template_id (optional)
  - Returns: Template performance

GET /api/models/prompts/compare
  - Query: template_ids (list)
  - Returns: Comparison
```

### Costs

```
GET /api/models/costs/summary
  - Query: days
  - Returns: Cost breakdown
```

---

## Best Practices

### 1. Data Quality

- ✅ Remove PII before training
- ✅ Use high-quality examples (quality_score > 0.8)
- ✅ Balance dataset across document types
- ✅ Regular quality checks

### 2. Fine-tuning

- ✅ Start with 100-500 high-quality examples
- ✅ Monitor validation metrics
- ✅ Use hyperparameter optimization
- ✅ Version all models
- ✅ A/B test before full deployment

### 3. Prompt Engineering

- ✅ Use appropriate template for document type
- ✅ Add few-shot examples for complex tasks
- ✅ Track template performance
- ✅ Iterate based on feedback
- ✅ Version prompts alongside models

### 4. Monitoring

- ✅ Track all predictions with metadata
- ✅ Monitor drift weekly
- ✅ Set up alerts for degradation
- ✅ Review user feedback regularly
- ✅ Analyze cost trends

### 5. Feedback Loop

- ✅ Make feedback easy (thumbs up/down)
- ✅ Collect corrections when available
- ✅ Analyze feedback patterns
- ✅ Trigger retraining at thresholds
- ✅ Close the loop with users

### 6. Cost Optimization

- ✅ Use intelligent routing
- ✅ Enable caching for repeated patterns
- ✅ Batch similar documents
- ✅ Monitor cost per document
- ✅ Right-size models for tasks

### 7. Production Deployment

- ✅ Gradual rollout (10% → 50% → 100%)
- ✅ Monitor metrics closely
- ✅ Have rollback plan
- ✅ Document model versions
- ✅ Maintain model registry

---

## Troubleshooting

### Fine-tuning Issues

**Issue**: Fine-tuning job fails
- Check data format (JSONL for OpenAI, specific format for Claude)
- Verify no PII in training data
- Ensure sufficient examples (minimum 50)
- Check S3 permissions (for Bedrock)

**Issue**: Poor fine-tuned model performance
- Increase training data size
- Improve data quality (filter low scores)
- Adjust hyperparameters
- Try longer training (more epochs)

### Performance Issues

**Issue**: High latency
- Check model tier selection
- Enable caching
- Use batch processing
- Consider faster model tier

**Issue**: High costs
- Review routing decisions
- Increase cache TTL
- Use cheaper models for simple tasks
- Batch similar requests

### Monitoring Issues

**Issue**: Drift detected
- Collect more recent training data
- Analyze feedback for patterns
- Consider retraining
- Review prompt templates

**Issue**: Low feedback rate
- Simplify feedback UI
- Add prompts at key points
- Incentivize feedback
- Make it easier (one-click)

---

## Maintenance Schedule

### Daily
- Review performance alerts
- Check error rates
- Monitor costs

### Weekly
- Analyze feedback trends
- Review drift detection
- Check cache hit rates
- Optimize slow queries

### Monthly
- Review model performance comprehensively
- Analyze cost trends
- Consider retraining if needed
- Update prompt templates
- Archive old training data

### Quarterly
- Full model evaluation
- A/B test new approaches
- Review and optimize costs
- Update best practices
- Train team on new features

---

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [OpenAI Fine-tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)

---

## Support

For questions or issues:
- Technical Support: support@your-app.com
- ML Team: ml-team@your-app.com
- Documentation: https://docs.your-app.com/ml

