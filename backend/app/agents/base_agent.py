"""
Base Agent for PM Document Intelligence Multi-Agent System.

This module provides the abstract base class for all specialized agents
with common functionality including error handling, cost tracking, validation,
and metrics.

Usage:
    class MyAgent(BaseAgent):
        async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            # Implement agent logic
            return result
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from app.utils.exceptions import ValidationError, AIServiceError
from app.utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Agent Status
# ============================================================================


class AgentStatus(str, Enum):
    """Agent execution status."""

    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"


# ============================================================================
# Agent Metrics
# ============================================================================


class AgentMetrics:
    """Track agent performance metrics."""

    def __init__(self, agent_name: str):
        """
        Initialize agent metrics.

        Args:
            agent_name: Name of the agent
        """
        self.agent_name = agent_name
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_duration = 0.0
        self.total_cost = 0.0
        self.last_execution_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.errors_by_type: Dict[str, int] = {}

    def record_success(self, duration: float, cost: float) -> None:
        """
        Record successful execution.

        Args:
            duration: Execution duration in seconds
            cost: Execution cost in USD
        """
        self.total_requests += 1
        self.successful_requests += 1
        self.total_duration += duration
        self.total_cost += cost
        self.last_execution_time = datetime.utcnow()

    def record_failure(self, error_type: str, error_message: str) -> None:
        """
        Record failed execution.

        Args:
            error_type: Type of error
            error_message: Error message
        """
        self.total_requests += 1
        self.failed_requests += 1
        self.last_error = error_message
        self.last_execution_time = datetime.utcnow()

        # Track error types
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1

    def get_success_rate(self) -> float:
        """Get success rate (0-1)."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def get_average_duration(self) -> float:
        """Get average execution duration in seconds."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_duration / self.successful_requests

    def get_average_cost(self) -> float:
        """Get average execution cost in USD."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_cost / self.successful_requests

    def get_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics.

        Returns:
            Dictionary with agent metrics
        """
        return {
            "agent_name": self.agent_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.get_success_rate(),
            "average_duration_seconds": self.get_average_duration(),
            "average_cost_usd": self.get_average_cost(),
            "total_cost_usd": self.total_cost,
            "last_execution": (
                self.last_execution_time.isoformat() if self.last_execution_time else None
            ),
            "last_error": self.last_error,
            "errors_by_type": self.errors_by_type.copy(),
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_duration = 0.0
        self.total_cost = 0.0
        self.last_execution_time = None
        self.last_error = None
        self.errors_by_type.clear()


# ============================================================================
# Circuit Breaker
# ============================================================================


class AgentCircuitBreaker:
    """Circuit breaker for agent failures."""

    def __init__(
        self,
        agent_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.

        Args:
            agent_name: Name of the agent
            failure_threshold: Number of failures to open circuit
            recovery_timeout: Seconds before attempting recovery
            success_threshold: Consecutive successes to close circuit
        """
        self.agent_name = agent_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.state = "closed"  # closed, open, half-open
        self.last_failure_time: Optional[float] = None
        self.opened_at: Optional[datetime] = None

    def record_success(self) -> None:
        """Record successful execution."""
        if self.state == "half-open":
            self.success_count += 1

            if self.success_count >= self.success_threshold:
                self._close_circuit()
        elif self.state == "closed":
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0

        if self.state == "closed" and self.failure_count >= self.failure_threshold:
            self._open_circuit()
        elif self.state == "half-open":
            self._open_circuit()

    def can_execute(self) -> bool:
        """
        Check if agent can execute.

        Returns:
            True if can execute, False if circuit is open
        """
        if self.state == "closed":
            return True

        if self.state == "open":
            if self._should_attempt_recovery():
                self._half_open_circuit()
                return True
            return False

        # half-open state
        return True

    def _open_circuit(self) -> None:
        """Open circuit breaker."""
        self.state = "open"
        self.opened_at = datetime.utcnow()

        logger.warning(
            f"Circuit breaker OPENED for agent {self.agent_name} "
            f"after {self.failure_count} failures"
        )

    def _half_open_circuit(self) -> None:
        """Half-open circuit breaker (testing recovery)."""
        self.state = "half-open"
        self.success_count = 0

        logger.info(f"Circuit breaker HALF-OPEN for agent {self.agent_name}, testing recovery")

    def _close_circuit(self) -> None:
        """Close circuit breaker (recovered)."""
        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None

        logger.info(f"Circuit breaker CLOSED for agent {self.agent_name}, recovered")

    def _should_attempt_recovery(self) -> bool:
        """Check if should attempt recovery."""
        if self.last_failure_time is None:
            return False

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout

    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state."""
        return {
            "agent_name": self.agent_name,
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
        }


# ============================================================================
# Base Agent
# ============================================================================


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        name: str,
        description: str,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize base agent.

        Args:
            name: Agent name
            description: Agent description
            config: Agent configuration
        """
        self.name = name
        self.description = description
        self.config = config or {}

        # Metrics
        self.metrics = AgentMetrics(name)

        # Circuit breaker
        self.circuit_breaker = AgentCircuitBreaker(
            name,
            failure_threshold=self.config.get("failure_threshold", 5),
            recovery_timeout=self.config.get("recovery_timeout", 60),
        )

        # Status
        self.status = AgentStatus.IDLE
        self.current_task_id: Optional[str] = None

        # Rate limiting
        self.max_requests_per_minute = self.config.get("max_requests_per_minute", 60)
        self.request_timestamps: List[float] = []

        logger.info(f"Agent initialized: {name}")

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data and return results.

        Args:
            input_data: Input data for processing

        Returns:
            Processing results

        Raises:
            ValidationError: If input is invalid
            AIServiceError: If processing fails
        """
        pass

    def validate_input(self, input_data: Dict[str, Any]) -> None:
        """
        Validate input data.

        Args:
            input_data: Input data to validate

        Raises:
            ValidationError: If input is invalid
        """
        # Override in subclasses for specific validation
        if not isinstance(input_data, dict):
            raise ValidationError(
                message="Input must be a dictionary", details={"agent": self.name}
            )

    def validate_output(self, output_data: Dict[str, Any]) -> None:
        """
        Validate output data.

        Args:
            output_data: Output data to validate

        Raises:
            ValidationError: If output is invalid
        """
        # Override in subclasses for specific validation
        if not isinstance(output_data, dict):
            raise ValidationError(
                message="Output must be a dictionary", details={"agent": self.name}
            )

    async def execute(
        self,
        input_data: Dict[str, Any],
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute agent with full error handling and metrics.

        Args:
            input_data: Input data for processing
            task_id: Optional task ID for tracking

        Returns:
            Processing results with metadata

        Raises:
            AIServiceError: If circuit is open or processing fails
        """
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            self.status = AgentStatus.CIRCUIT_OPEN

            raise AIServiceError(
                message=f"Agent {self.name} circuit breaker is open",
                details={
                    "agent": self.name,
                    "circuit_state": self.circuit_breaker.get_state(),
                },
            )

        # Check rate limit
        await self._check_rate_limit()

        # Set status
        self.status = AgentStatus.PROCESSING
        self.current_task_id = task_id

        start_time = time.time()
        cost = 0.0

        try:
            # Validate input
            self.validate_input(input_data)

            # Process
            logger.info(f"Agent {self.name} processing task {task_id}")

            result = await self.process(input_data)

            # Validate output
            self.validate_output(result)

            # Calculate duration
            duration = time.time() - start_time

            # Extract cost if available
            cost = result.get("cost", 0.0)

            # Record success
            self.metrics.record_success(duration, cost)
            self.circuit_breaker.record_success()

            # Set status
            self.status = AgentStatus.COMPLETED

            # Add metadata
            result["_metadata"] = {
                "agent": self.name,
                "task_id": task_id,
                "duration_seconds": duration,
                "cost_usd": cost,
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(
                f"Agent {self.name} completed task {task_id} in {duration:.2f}s, "
                f"cost: ${cost:.6f}"
            )

            return result

        except ValidationError as e:
            logger.error(f"Agent {self.name} validation error: {e}")

            self.metrics.record_failure("validation", str(e))
            self.status = AgentStatus.FAILED

            raise

        except AIServiceError as e:
            logger.error(f"Agent {self.name} AI service error: {e}")

            self.metrics.record_failure("ai_service", str(e))
            self.circuit_breaker.record_failure()
            self.status = AgentStatus.FAILED

            raise

        except Exception as e:
            logger.error(f"Agent {self.name} unexpected error: {e}", exc_info=True)

            self.metrics.record_failure("unexpected", str(e))
            self.circuit_breaker.record_failure()
            self.status = AgentStatus.FAILED

            raise AIServiceError(
                message=f"Agent {self.name} execution failed",
                details={"agent": self.name, "error": str(e)},
            )

        finally:
            self.current_task_id = None

    async def _check_rate_limit(self) -> None:
        """
        Check and enforce rate limits.

        Raises:
            AIServiceError: If rate limit would be exceeded
        """
        import asyncio

        now = time.time()

        # Remove timestamps older than 1 minute
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]

        # Check if at limit
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            wait_time = 60 - (now - self.request_timestamps[0])

            logger.warning(f"Agent {self.name} rate limit reached, waiting {wait_time:.2f}s")

            self.status = AgentStatus.RATE_LIMITED

            await asyncio.sleep(wait_time)

        # Add current timestamp
        self.request_timestamps.append(now)

    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status.

        Returns:
            Status dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "current_task": self.current_task_id,
            "metrics": self.metrics.get_stats(),
            "circuit_breaker": self.circuit_breaker.get_state(),
            "config": {
                "max_requests_per_minute": self.max_requests_per_minute,
                "failure_threshold": self.circuit_breaker.failure_threshold,
                "recovery_timeout": self.circuit_breaker.recovery_timeout,
            },
        }

    def reset_metrics(self) -> None:
        """Reset agent metrics."""
        self.metrics.reset()
        logger.info(f"Agent {self.name} metrics reset")

    def __repr__(self) -> str:
        """String representation."""
        return f"<{self.__class__.__name__}(name='{self.name}', status='{self.status.value}')>"
