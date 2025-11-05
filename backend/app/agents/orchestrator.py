"""
Agent Orchestrator for PM Document Intelligence.

This module coordinates multiple specialized agents, routes tasks,
handles failures, and aggregates results.

Usage:
    orchestrator = AgentOrchestrator()
    result = await orchestrator.analyze_document(
        document_id="doc_123",
        task="deep_analysis"
    )
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any

from app.agents.base_agent import AgentStatus, BaseAgent
from app.utils.exceptions import ValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Task Types
# ============================================================================


class TaskType(str, Enum):
    """Agent task types."""

    DEEP_ANALYSIS = "deep_analysis"
    EXTRACT_ACTIONS = "extract_actions"
    SUMMARIZE = "summarize"
    EXTRACT_ENTITIES = "extract_entities"
    QUESTION_ANSWER = "question_answer"
    MULTI_AGENT = "multi_agent"


# ============================================================================
# Agent Orchestrator
# ============================================================================


class AgentOrchestrator:
    """Orchestrates multiple specialized agents."""

    def __init__(self):
        """Initialize agent orchestrator."""
        self.agents: dict[str, BaseAgent] = {}
        self.agent_registry: dict[TaskType, str] = {}

        # Conversation memory (for Q&A follow-ups)
        self.conversation_memory: dict[str, list[dict[str, Any]]] = {}

        # Shared context across agents
        self.shared_context: dict[str, Any] = {}

        logger.info("Agent orchestrator initialized")

    def register_agent(
        self,
        agent: BaseAgent,
        task_types: list[TaskType],
    ) -> None:
        """
        Register an agent for specific task types.

        Args:
            agent: Agent instance
            task_types: List of task types this agent handles
        """
        self.agents[agent.name] = agent

        for task_type in task_types:
            self.agent_registry[task_type] = agent.name

        logger.info(f"Registered agent {agent.name} for tasks: " f"{[t.value for t in task_types]}")

    def get_agent(self, task_type: TaskType) -> BaseAgent | None:
        """
        Get agent for a task type.

        Args:
            task_type: Task type

        Returns:
            Agent instance or None
        """
        agent_name = self.agent_registry.get(task_type)
        return self.agents.get(agent_name) if agent_name else None

    async def route_task(
        self,
        task_type: TaskType,
        input_data: dict[str, Any],
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Route task to appropriate agent.

        Args:
            task_type: Type of task
            input_data: Input data
            task_id: Optional task ID

        Returns:
            Task results

        Raises:
            ValidationError: If no agent for task type
            AIServiceError: If agent execution fails
        """
        agent = self.get_agent(task_type)

        if not agent:
            raise ValidationError(
                message=f"No agent registered for task type: {task_type.value}",
                details={"task_type": task_type.value},
            )

        logger.info(f"Routing {task_type.value} task to agent {agent.name}")

        # Execute agent
        result = await agent.execute(input_data, task_id=task_id)

        return result

    async def analyze_document(
        self,
        document_id: str,
        document_text: str,
        user_id: str,
        task: str = "deep_analysis",
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze document with appropriate agent(s).

        Args:
            document_id: Document ID
            document_text: Document text
            user_id: User ID
            task: Task type (deep_analysis, extract_actions, summarize, etc.)
            options: Additional options

        Returns:
            Analysis results
        """
        options = options or {}

        task_type = TaskType(task)

        input_data = {
            "document_id": document_id,
            "text": document_text,
            "user_id": user_id,
            "options": options,
        }

        result = await self.route_task(task_type, input_data, task_id=document_id)

        return result

    async def multi_agent_analysis(
        self,
        document_id: str,
        document_text: str,
        user_id: str,
        tasks: list[str],
        parallel: bool = True,
    ) -> dict[str, Any]:
        """
        Run multiple agents on a document.

        Args:
            document_id: Document ID
            document_text: Document text
            user_id: User ID
            tasks: List of tasks to run
            parallel: Whether to run in parallel

        Returns:
            Aggregated results from all agents
        """
        logger.info(
            f"Multi-agent analysis: {len(tasks)} tasks, "
            f"{'parallel' if parallel else 'sequential'}"
        )

        start_time = datetime.utcnow()

        results = {}
        total_cost = 0.0
        errors = []

        if parallel:
            # Run agents in parallel
            agent_tasks = []

            for task in tasks:
                try:
                    task_type = TaskType(task)
                    input_data = {
                        "document_id": document_id,
                        "text": document_text,
                        "user_id": user_id,
                        "options": {},
                    }

                    agent_tasks.append(
                        self.route_task(task_type, input_data, task_id=f"{document_id}_{task}")
                    )

                except ValueError:
                    errors.append({"task": task, "error": f"Invalid task type: {task}"})

            # Wait for all tasks
            if agent_tasks:
                task_results = await asyncio.gather(*agent_tasks, return_exceptions=True)

                for task, result in zip(
                    [t for t in tasks if t not in [e["task"] for e in errors]],
                    task_results,
                    strict=False,
                ):
                    if isinstance(result, Exception):
                        errors.append({"task": task, "error": str(result)})
                    else:
                        results[task] = result
                        if "_metadata" in result:
                            total_cost += result["_metadata"].get("cost_usd", 0)

        else:
            # Run agents sequentially
            for task in tasks:
                try:
                    task_type = TaskType(task)
                    input_data = {
                        "document_id": document_id,
                        "text": document_text,
                        "user_id": user_id,
                        "options": {},
                    }

                    result = await self.route_task(
                        task_type, input_data, task_id=f"{document_id}_{task}"
                    )

                    results[task] = result

                    if "_metadata" in result:
                        total_cost += result["_metadata"].get("cost_usd", 0)

                except ValueError:
                    errors.append({"task": task, "error": f"Invalid task type: {task}"})

                except Exception as e:
                    errors.append({"task": task, "error": str(e)})

        # Calculate total duration
        duration = (datetime.utcnow() - start_time).total_seconds()

        return {
            "document_id": document_id,
            "results": results,
            "errors": errors,
            "total_tasks": len(tasks),
            "successful_tasks": len(results),
            "failed_tasks": len(errors),
            "total_cost_usd": total_cost,
            "duration_seconds": duration,
            "execution_mode": "parallel" if parallel else "sequential",
        }

    async def ask_question(
        self,
        question: str,
        document_id: str | None = None,
        user_id: str | None = None,
        conversation_id: str | None = None,
        use_context: bool = True,
    ) -> dict[str, Any]:
        """
        Ask a question about documents using Q&A agent with RAG.

        Args:
            question: Question text
            document_id: Specific document ID (optional)
            user_id: User ID for filtering
            conversation_id: Conversation ID for follow-ups
            use_context: Whether to use vector search context

        Returns:
            Answer with citations
        """
        input_data = {
            "question": question,
            "document_id": document_id,
            "user_id": user_id,
            "use_context": use_context,
        }

        # Add conversation memory
        if conversation_id and conversation_id in self.conversation_memory:
            input_data["conversation_history"] = self.conversation_memory[conversation_id]

        result = await self.route_task(
            TaskType.QUESTION_ANSWER,
            input_data,
            task_id=conversation_id or f"qa_{datetime.utcnow().timestamp()}",
        )

        # Update conversation memory
        if conversation_id:
            if conversation_id not in self.conversation_memory:
                self.conversation_memory[conversation_id] = []

            self.conversation_memory[conversation_id].append(
                {
                    "question": question,
                    "answer": result.get("answer"),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            # Keep last 10 exchanges
            self.conversation_memory[conversation_id] = self.conversation_memory[conversation_id][
                -10:
            ]

        return result

    def update_shared_context(self, context: dict[str, Any]) -> None:
        """
        Update shared context across agents.

        Args:
            context: Context data to add
        """
        self.shared_context.update(context)
        logger.debug(f"Updated shared context: {list(context.keys())}")

    def get_shared_context(self, key: str | None = None) -> Any:
        """
        Get shared context.

        Args:
            key: Specific key to retrieve (optional)

        Returns:
            Context value or full context dict
        """
        if key:
            return self.shared_context.get(key)
        return self.shared_context.copy()

    def clear_conversation(self, conversation_id: str) -> None:
        """
        Clear conversation memory.

        Args:
            conversation_id: Conversation ID to clear
        """
        if conversation_id in self.conversation_memory:
            del self.conversation_memory[conversation_id]
            logger.info(f"Cleared conversation memory: {conversation_id}")

    def get_all_agent_status(self) -> dict[str, Any]:
        """
        Get status of all agents.

        Returns:
            Status dictionary for all agents
        """
        return {agent_name: agent.get_status() for agent_name, agent in self.agents.items()}

    def get_orchestrator_stats(self) -> dict[str, Any]:
        """
        Get orchestrator statistics.

        Returns:
            Statistics dictionary
        """
        total_requests = sum(agent.metrics.total_requests for agent in self.agents.values())

        total_cost = sum(agent.metrics.total_cost for agent in self.agents.values())

        return {
            "total_agents": len(self.agents),
            "registered_tasks": len(self.agent_registry),
            "total_requests": total_requests,
            "total_cost_usd": total_cost,
            "active_conversations": len(self.conversation_memory),
            "agents": {
                agent_name: {
                    "status": agent.status.value,
                    "requests": agent.metrics.total_requests,
                    "success_rate": agent.metrics.get_success_rate(),
                }
                for agent_name, agent in self.agents.items()
            },
        }

    def reset_all_metrics(self) -> None:
        """Reset metrics for all agents."""
        for agent in self.agents.values():
            agent.reset_metrics()

        logger.info("Reset metrics for all agents")

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of all agents.

        Returns:
            Health status
        """
        healthy_agents = sum(
            1
            for agent in self.agents.values()
            if agent.status not in [AgentStatus.FAILED, AgentStatus.CIRCUIT_OPEN]
        )

        circuit_open_agents = [
            agent.name for agent in self.agents.values() if agent.circuit_breaker.state == "open"
        ]

        overall_healthy = healthy_agents == len(self.agents)

        return {
            "status": "healthy" if overall_healthy else "degraded",
            "total_agents": len(self.agents),
            "healthy_agents": healthy_agents,
            "circuit_open_agents": circuit_open_agents,
            "timestamp": datetime.utcnow().isoformat(),
        }


# ============================================================================
# Global Orchestrator Instance
# ============================================================================

# This will be initialized with agents in the application startup
_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    """
    Get global orchestrator instance.

    Returns:
        AgentOrchestrator instance
    """
    global _orchestrator

    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()

    return _orchestrator


def initialize_agents() -> AgentOrchestrator:
    """
    Initialize all agents and register with orchestrator.

    Returns:
        Configured orchestrator
    """
    from app.agents.action_agent import ActionItemAgent
    from app.agents.analysis_agent import AnalysisAgent
    from app.agents.entity_agent import EntityAgent
    from app.agents.qa_agent import QAAgent
    from app.agents.summary_agent import SummaryAgent

    orchestrator = get_orchestrator()

    # Register agents
    orchestrator.register_agent(AnalysisAgent(), [TaskType.DEEP_ANALYSIS])

    orchestrator.register_agent(ActionItemAgent(), [TaskType.EXTRACT_ACTIONS])

    orchestrator.register_agent(SummaryAgent(), [TaskType.SUMMARIZE])

    orchestrator.register_agent(EntityAgent(), [TaskType.EXTRACT_ENTITIES])

    orchestrator.register_agent(QAAgent(), [TaskType.QUESTION_ANSWER])

    logger.info("All agents initialized and registered")

    return orchestrator
