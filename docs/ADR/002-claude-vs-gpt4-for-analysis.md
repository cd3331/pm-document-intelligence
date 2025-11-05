# 002. Claude vs GPT-4 for Document Analysis

**Date**: 2024-01-05

**Status**: Accepted

**Deciders**: AI Team, Engineering Lead, Product Manager

**Tags**: ai, ml, models, cost-optimization

---

## Context

PM Document Intelligence requires high-quality AI models for document analysis tasks:
- Executive summaries of project documents
- Action item extraction
- Risk assessment
- Q&A capabilities

Requirements:
- High accuracy (>90%) for business-critical tasks
- Reasonable cost (<$1 per document)
- API reliability and availability
- Context window: support for 10,000+ token documents
- Structured output support

We needed to decide between:
1. Using a single AI provider exclusively
2. Using multiple providers with intelligent routing
3. Fine-tuning our own models

## Decision

We decided to use **multi-model approach** with intelligent routing between Claude (AWS Bedrock) and OpenAI GPT-4/GPT-3.5.

**Primary models**:
- **Claude 2.1** (via AWS Bedrock): Complex analysis, risk assessment
- **GPT-4**: Structured outputs, action item extraction
- **GPT-3.5 Turbo**: Simple summaries, high-volume tasks

**Routing logic**:
```python
def select_model(document_complexity, task_type, requirements):
    if complexity == SIMPLE and cost_priority > 0.6:
        return "gpt-3.5-turbo"
    elif task_type == "risk_assessment":
        return "claude-2"
    elif task_type == "action_items" and structured_output_needed:
        return "gpt-4"
    else:
        return "claude-2"
```

## Consequences

### Positive

- **Cost Optimization**: 40-50% cost reduction through intelligent routing
  - Simple tasks → GPT-3.5 Turbo ($0.008/doc)
  - Complex tasks → Claude 2 or GPT-4 ($0.03-0.04/doc)
  - Average cost: $0.015/doc (vs $0.03+ with single model)

- **Vendor Resilience**: Not locked into single provider
  - Fallback if one API has issues
  - Negotiation leverage with providers
  - Flexibility to adapt to pricing changes

- **Model Specialization**: Use best model for each task
  - Claude: Superior reasoning and analysis
  - GPT-4: Better structured outputs
  - GPT-3.5: Fast and cost-effective for simple tasks

- **Performance**: Higher accuracy than single-model approach
  - Claude 2: 93% accuracy on risk assessment
  - GPT-4: 95% accuracy on action item extraction
  - Combined: 91% average accuracy

- **AWS Integration**: Claude via Bedrock
  - Same AWS account, simplified billing
  - VPC endpoints for private connectivity
  - Fine-tuning capabilities in future

### Negative

- **Complexity**: More complex system
  - Need routing logic
  - More code to maintain
  - Testing multiple providers

- **Cost Tracking**: More difficult to attribute costs
  - Need detailed logging per model
  - More complex cost analysis
  - Multiple invoices to reconcile

- **Consistency**: Different models may produce varying outputs
  - Need to handle output format differences
  - Prompt engineering for each model
  - Quality assurance more complex

- **Latency**: Routing adds minimal overhead
  - ~50ms for model selection
  - Negligible compared to AI inference time (2-5s)

### Neutral

- **Learning Curve**: Team needs to understand multiple APIs
  - Different API formats
  - Different pricing models
  - Different rate limits

- **Monitoring**: Need separate monitoring per provider
  - Track performance of each model
  - Monitor costs per provider
  - Alert on failures

## Alternatives Considered

### Alternative 1: OpenAI GPT-4 Exclusively

**Description**: Use only GPT-4 for all tasks

**Pros**:
- Simple integration (single API)
- Consistent output format
- Well-documented
- Excellent structured output support
- Good performance

**Cons**:
- Higher cost ($1,180/mo for 10K docs)
- Vendor lock-in
- No fallback if API has issues
- Not optimized for all task types

**Why not chosen**:
- Cost too high for high-volume usage
- Vendor lock-in risk
- Claude performs better on some tasks
- No cost optimization opportunity

### Alternative 2: Claude 2 Exclusively (via Bedrock)

**Description**: Use only Claude 2 via AWS Bedrock

**Pros**:
- Excellent reasoning and analysis
- Lower cost than GPT-4
- AWS integration benefits
- Good for complex documents
- Constitutional AI for safety

**Cons**:
- Less mature API than OpenAI
- Structured output less reliable
- Vendor lock-in
- API less widely used (fewer resources)

**Why not chosen**:
- GPT-4 better for structured outputs
- Missing cost optimization with GPT-3.5
- Single point of failure

### Alternative 3: Fine-tuned Open Source Model

**Description**: Fine-tune LLama 2 or similar open source model

**Pros**:
- Lower long-term costs (after training)
- Full control over model
- No API vendor dependency
- Can optimize for specific use case

**Cons**:
- High upfront cost (training: $10K-50K)
- Need ML expertise for fine-tuning
- Hosting costs ($500-2000/mo)
- Maintenance burden
- Likely lower quality than GPT-4/Claude
- Time to train and optimize (2-3 months)

**Why not chosen**:
- Too risky for MVP
- Not cost-effective at current scale
- Prefer proven models for launch
- Can reconsider at 100K+ docs/month

## Implementation

**Timeline**:
- Week 1: Implement multi-provider abstraction layer
- Week 2: Develop intelligent routing logic
- Week 3: Migrate existing GPT-4 calls to new system
- Week 4: Add Claude 2 via Bedrock
- Week 5: Testing and optimization
- Week 6: Production deployment with gradual rollout

**Key Implementation Steps**:

1. **Multi-Provider Abstraction**:
```python
class AIProvider:
    async def generate(self, prompt: str, model: str) -> str:
        pass

class OpenAIProvider(AIProvider):
    async def generate(self, prompt: str, model: str) -> str:
        return await openai.ChatCompletion.create(...)

class BedrockProvider(AIProvider):
    async def generate(self, prompt: str, model: str) -> str:
        return await bedrock.invoke_model(...)
```

2. **Intelligent Router**:
```python
router = IntelligentRouter()
model = router.select_model(
    document_complexity=assess_complexity(document),
    task_type="summary",
    requirements={"accuracy_priority": 0.7, "cost_priority": 0.3}
)
```

3. **Cost Tracking**:
```python
def track_ai_cost(model: str, tokens: int, cost: float):
    logger.info(f"AI call: {model}, tokens={tokens}, cost=${cost}")
    metrics.ai_cost_total.labels(model=model).inc(cost)
```

**Migration Path**:
- Week 1-2: New code paths use multi-provider system
- Week 3-4: Migrate existing GPT-4 calls
- Week 5-6: A/B test with 10% traffic to new system
- Week 7: Full cutover if metrics look good

**Rollback Plan**:
- Keep OpenAI-only code path available
- Feature flag for routing logic
- Can disable Claude calls without code change
- Revert to GPT-4 exclusive if issues arise

## References

- [Claude 2 Documentation](https://docs.anthropic.com/claude/reference)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Internal Cost Analysis](../COST_ANALYSIS.md)
- Cost comparison spreadsheet: [link]
- Performance benchmarks: [link]

## Notes

**Performance Benchmarks** (100 documents tested):

| Model | Accuracy | Avg Latency | Cost/Doc |
|-------|----------|-------------|----------|
| GPT-4 | 94% | 3.2s | $0.118 |
| Claude 2 | 93% | 2.8s | $0.032 |
| GPT-3.5 | 87% | 1.1s | $0.008 |
| **Hybrid** | **91%** | **2.1s** | **$0.015** |

**Follow-up Actions**:
- Monitor model performance in production
- Collect user feedback on output quality
- Optimize routing logic based on real usage
- Evaluate new models as they're released (GPT-4 Turbo, Claude 3)
- Consider fine-tuning after 100K documents processed

**Update (2024-06-01)**:
- Hybrid approach working excellently
- Achieved 44% cost reduction vs GPT-4 only
- Quality metrics stable (92% accuracy)
- Added GPT-4 Turbo to routing logic
- Considering Claude 3 when available
