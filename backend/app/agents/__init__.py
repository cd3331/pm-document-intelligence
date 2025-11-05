"""
Multi-Agent System for PM Document Intelligence.

This package provides an intelligent multi-agent orchestration system
for document analysis with specialized agents for different tasks.

Usage:
    from app.agents import AgentOrchestrator

    orchestrator = AgentOrchestrator()
    result = await orchestrator.analyze_document(
        document_id="doc_123",
        task="deep_analysis"
    )
"""

from app.agents.base_agent import BaseAgent, AgentStatus, AgentMetrics
from app.agents.orchestrator import AgentOrchestrator

__all__ = [
    "BaseAgent",
    "AgentStatus",
    "AgentMetrics",
    "AgentOrchestrator",
]
