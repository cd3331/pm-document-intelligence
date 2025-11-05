# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records (ADRs) for PM Document Intelligence.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences.

## ADR Format

Each ADR follows this structure:

```markdown
# [number]. [Title]

Date: YYYY-MM-DD
Status: [Proposed | Accepted | Deprecated | Superseded]
Deciders: [List of people involved]

## Context

What is the issue we're trying to solve?

## Decision

What decision did we make?

## Consequences

What are the positive and negative consequences of this decision?

## Alternatives Considered

What other options did we evaluate?
```

## Index of ADRs

| # | Title | Status | Date |
|---|-------|--------|------|
| [001](001-choice-of-fastapi.md) | Choice of FastAPI as Backend Framework | Accepted | 2024-01-01 |
| [002](002-claude-vs-gpt4-for-analysis.md) | Claude vs GPT-4 for Document Analysis | Accepted | 2024-01-05 |
| [003](003-vector-search-implementation.md) | pgvector vs Dedicated Vector Database | Accepted | 2024-01-10 |
| [004](004-multi-tenancy-approach.md) | Multi-Tenancy Implementation Strategy | Accepted | 2024-01-15 |

## Creating a New ADR

1. Copy `TEMPLATE.md` to a new file with the next number
2. Fill in all sections
3. Submit for review via Pull Request
4. Update this README index after approval

## Related Resources

- [ADR Process Guide](https://adr.github.io/)
- [Architecture Documentation](../ARCHITECTURE.md)
- [Contributing Guide](../../CONTRIBUTING.md)
