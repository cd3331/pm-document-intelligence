"""
Comprehensive tests for the Multi-Agent System.

Tests cover:
- BaseAgent functionality
- AgentOrchestrator routing and coordination
- Individual specialized agents
- Multi-agent workflows
- Circuit breaker patterns
- Conversation memory
- Error handling and recovery
"""

import asyncio
import pytest
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

from app.agents.base_agent import (
    BaseAgent,
    AgentStatus,
    AgentMetrics,
    AgentCircuitBreaker,
)
from app.agents.orchestrator import (
    AgentOrchestrator,
    TaskType,
    get_orchestrator,
    initialize_agents,
)
from app.agents.analysis_agent import AnalysisAgent
from app.agents.action_agent import ActionItemAgent
from app.agents.summary_agent import SummaryAgent
from app.agents.entity_agent import EntityAgent
from app.agents.qa_agent import QAAgent
from app.utils.exceptions import ValidationError, AIServiceError


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_document_text():
    """Sample document text for testing."""
    return """
    Project Status Meeting - Q4 2024

    Date: December 15, 2024
    Attendees: John Smith (PM), Sarah Johnson (Tech Lead), Mike Chen (Dev)

    Key Discussion Points:
    1. The authentication module is 90% complete
    2. We need to migrate the database by January 15, 2025
    3. Security audit revealed 3 critical vulnerabilities that must be fixed
    4. Budget concerns - we're 15% over allocated resources

    Action Items:
    - John to schedule security review meeting by Dec 20
    - Sarah to complete authentication module by Dec 22
    - Mike to prepare database migration plan by Jan 5

    Risks:
    - Timeline pressure due to holiday season
    - Potential security breach if vulnerabilities not fixed quickly
    - Budget overrun may require additional approval

    Next meeting: January 8, 2025
    """


@pytest.fixture
def mock_bedrock_response():
    """Mock Bedrock service response."""
    return {
        "text": '{"executive_summary": "Test summary", "key_points": ["Point 1", "Point 2"]}',
        "cost": 0.002,
        "tokens": {"input": 100, "output": 50},
    }


@pytest.fixture
def mock_vector_search_results():
    """Mock vector search results."""
    return {
        "results": [
            {
                "document_id": "doc_123",
                "filename": "test.pdf",
                "matched_chunk": {
                    "text": "Relevant context text",
                    "chunk_index": 0,
                },
                "similarity_score": 0.85,
            }
        ],
        "total_results": 1,
    }


# ============================================================================
# BaseAgent Tests
# ============================================================================

class TestAgentMetrics:
    """Test AgentMetrics functionality."""

    def test_initial_metrics(self):
        """Test initial metrics state."""
        metrics = AgentMetrics()

        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.total_cost == 0.0
        assert metrics.get_success_rate() == 0.0

    def test_record_success(self):
        """Test recording successful requests."""
        metrics = AgentMetrics()

        metrics.record_success(duration=1.5, cost=0.01)

        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0
        assert metrics.total_cost == 0.01
        assert metrics.get_success_rate() == 1.0
        assert metrics.average_duration == 1.5

    def test_record_failure(self):
        """Test recording failed requests."""
        metrics = AgentMetrics()

        metrics.record_failure(duration=2.0, error="Test error")

        assert metrics.total_requests == 1
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 1
        assert metrics.get_success_rate() == 0.0

    def test_mixed_success_failure(self):
        """Test success rate with mixed results."""
        metrics = AgentMetrics()

        metrics.record_success(1.0, 0.01)
        metrics.record_success(1.5, 0.02)
        metrics.record_failure(2.0, "Error")

        assert metrics.total_requests == 3
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 1
        assert metrics.get_success_rate() == pytest.approx(0.666, rel=0.01)

    def test_reset_metrics(self):
        """Test resetting metrics."""
        metrics = AgentMetrics()

        metrics.record_success(1.0, 0.01)
        metrics.reset()

        assert metrics.total_requests == 0
        assert metrics.total_cost == 0.0


class TestAgentCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_initial_state(self):
        """Test circuit breaker starts closed."""
        breaker = AgentCircuitBreaker()

        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    def test_record_success_resets_failures(self):
        """Test that success resets failure count."""
        breaker = AgentCircuitBreaker()

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.failure_count == 2

        breaker.record_success()
        assert breaker.failure_count == 0
        assert breaker.state == "closed"

    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""
        breaker = AgentCircuitBreaker(failure_threshold=3)

        # Record failures up to threshold
        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == "open"
        assert not breaker.can_execute()

    def test_circuit_half_open_after_timeout(self):
        """Test circuit transitions to half-open after timeout."""
        breaker = AgentCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1  # 100ms for testing
        )

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "open"

        # Wait for recovery timeout
        import time
        time.sleep(0.15)

        # Should transition to half-open
        assert breaker.can_execute()

    def test_half_open_closes_on_success(self):
        """Test half-open circuit closes on success."""
        breaker = AgentCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=2
        )

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        # Wait and transition to half-open
        import time
        time.sleep(0.15)
        breaker.can_execute()

        # Record successes to close
        breaker.record_success()
        breaker.record_success()

        assert breaker.state == "closed"


class TestBaseAgent:
    """Test BaseAgent functionality."""

    def test_agent_initialization(self):
        """Test agent initializes with correct state."""

        class TestAgent(BaseAgent):
            async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
                return {"result": "success"}

        agent = TestAgent(
            name="TestAgent",
            description="Test agent",
            config={"max_requests_per_minute": 30}
        )

        assert agent.name == "TestAgent"
        assert agent.status == AgentStatus.IDLE
        assert agent.metrics.total_requests == 0

    @pytest.mark.asyncio
    async def test_agent_execution_success(self):
        """Test successful agent execution."""

        class TestAgent(BaseAgent):
            async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
                return {"result": "success", "data": input_data["value"]}

        agent = TestAgent(name="TestAgent", description="Test")

        result = await agent.execute({"value": "test"})

        assert result["result"] == "success"
        assert result["data"] == "test"
        assert agent.metrics.successful_requests == 1
        assert agent.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_agent_execution_failure(self):
        """Test agent execution with failure."""

        class TestAgent(BaseAgent):
            async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
                raise ValueError("Test error")

        agent = TestAgent(name="TestAgent", description="Test")

        with pytest.raises(AIServiceError):
            await agent.execute({"value": "test"})

        assert agent.metrics.failed_requests == 1
        assert agent.status == AgentStatus.FAILED


# ============================================================================
# AgentOrchestrator Tests
# ============================================================================

class TestAgentOrchestrator:
    """Test AgentOrchestrator functionality."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initializes correctly."""
        orchestrator = AgentOrchestrator()

        assert len(orchestrator.agents) == 0
        assert len(orchestrator.agent_registry) == 0

    def test_register_agent(self):
        """Test registering agents."""
        orchestrator = AgentOrchestrator()

        class TestAgent(BaseAgent):
            async def process(self, input_data):
                return {}

        agent = TestAgent(name="TestAgent", description="Test")
        orchestrator.register_agent(agent, [TaskType.DEEP_ANALYSIS])

        assert "TestAgent" in orchestrator.agents
        assert TaskType.DEEP_ANALYSIS in orchestrator.agent_registry
        assert orchestrator.agent_registry[TaskType.DEEP_ANALYSIS].name == "TestAgent"

    def test_unregister_agent(self):
        """Test unregistering agents."""
        orchestrator = AgentOrchestrator()

        class TestAgent(BaseAgent):
            async def process(self, input_data):
                return {}

        agent = TestAgent(name="TestAgent", description="Test")
        orchestrator.register_agent(agent, [TaskType.SUMMARIZE])
        orchestrator.unregister_agent("TestAgent")

        assert "TestAgent" not in orchestrator.agents
        assert TaskType.SUMMARIZE not in orchestrator.agent_registry

    @pytest.mark.asyncio
    async def test_route_task(self):
        """Test task routing to appropriate agent."""
        orchestrator = AgentOrchestrator()

        class TestAgent(BaseAgent):
            async def process(self, input_data):
                return {"processed": True}

        agent = TestAgent(name="TestAgent", description="Test")
        orchestrator.register_agent(agent, [TaskType.EXTRACT_ACTIONS])

        result = await orchestrator.route_task(
            TaskType.EXTRACT_ACTIONS,
            {"text": "test"}
        )

        assert result["processed"] is True

    @pytest.mark.asyncio
    async def test_route_task_no_agent(self):
        """Test routing with no registered agent."""
        orchestrator = AgentOrchestrator()

        with pytest.raises(ValidationError) as exc_info:
            await orchestrator.route_task(
                TaskType.DEEP_ANALYSIS,
                {"text": "test"}
            )

        assert "No agent registered" in str(exc_info.value)

    def test_conversation_memory(self):
        """Test conversation memory management."""
        orchestrator = AgentOrchestrator()

        orchestrator.add_to_conversation(
            "conv_123",
            question="What is the project status?",
            answer="The project is on track."
        )

        history = orchestrator.get_conversation_history("conv_123")
        assert len(history) == 1
        assert history[0]["question"] == "What is the project status?"

        # Clear conversation
        orchestrator.clear_conversation("conv_123")
        assert len(orchestrator.get_conversation_history("conv_123")) == 0

    def test_conversation_memory_limit(self):
        """Test conversation memory respects max size."""
        orchestrator = AgentOrchestrator()

        # Add more than max (10) exchanges
        for i in range(15):
            orchestrator.add_to_conversation(
                "conv_123",
                question=f"Question {i}",
                answer=f"Answer {i}"
            )

        history = orchestrator.get_conversation_history("conv_123")
        assert len(history) == 10  # Should keep only last 10


# ============================================================================
# Individual Agent Tests
# ============================================================================

class TestAnalysisAgent:
    """Test AnalysisAgent functionality."""

    @pytest.mark.asyncio
    @patch('app.agents.analysis_agent.BedrockService')
    async def test_analysis_agent(self, mock_bedrock, sample_document_text):
        """Test analysis agent processing."""
        # Mock Bedrock response
        mock_instance = mock_bedrock.return_value
        mock_instance.invoke_claude = AsyncMock(return_value={
            "text": '''{
                "executive_summary": "Project on track with some risks",
                "key_insights": ["Authentication nearly complete", "Security issues found"],
                "patterns_identified": ["Timeline pressure", "Budget concerns"],
                "recommendations": [{
                    "recommendation": "Prioritize security fixes",
                    "priority": "HIGH",
                    "rationale": "Critical vulnerabilities found"
                }],
                "risks_and_concerns": [{
                    "risk": "Security vulnerabilities",
                    "severity": "HIGH",
                    "mitigation": "Immediate security review"
                }],
                "opportunities": ["Opportunity to improve security posture"],
                "confidence_score": 0.85
            }''',
            "cost": 0.003
        })

        agent = AnalysisAgent()
        result = await agent.execute({
            "text": sample_document_text,
            "options": {
                "document_type": "meeting_notes",
                "include_risks": True,
                "include_opportunities": True
            }
        })

        assert "analysis" in result
        assert result["analysis"]["confidence_score"] == 0.85
        assert len(result["analysis"]["key_insights"]) > 0


class TestActionItemAgent:
    """Test ActionItemAgent functionality."""

    @pytest.mark.asyncio
    @patch('app.agents.action_agent.BedrockService')
    async def test_action_extraction(self, mock_bedrock, sample_document_text):
        """Test action item extraction."""
        mock_instance = mock_bedrock.return_value
        mock_instance.invoke_claude = AsyncMock(return_value={
            "text": '''{
                "action_items": [
                    {
                        "action": "Schedule security review meeting",
                        "assignee": "John",
                        "due_date": "2024-12-20",
                        "priority": "HIGH",
                        "status": "TODO",
                        "dependencies": [],
                        "confidence": 0.9
                    },
                    {
                        "action": "Complete authentication module",
                        "assignee": "Sarah",
                        "due_date": "2024-12-22",
                        "priority": "HIGH",
                        "status": "IN_PROGRESS",
                        "dependencies": [],
                        "confidence": 0.95
                    }
                ]
            }''',
            "cost": 0.002
        })

        agent = ActionItemAgent()
        result = await agent.execute({
            "text": sample_document_text,
            "options": {"track_dependencies": True}
        })

        assert "action_items" in result
        assert len(result["action_items"]) == 2
        assert result["action_items"][0]["priority"] == "HIGH"


class TestSummaryAgent:
    """Test SummaryAgent functionality."""

    @pytest.mark.asyncio
    @patch('app.agents.summary_agent.BedrockService')
    async def test_summary_generation(self, mock_bedrock, sample_document_text):
        """Test summary generation."""
        mock_instance = mock_bedrock.return_value
        mock_instance.invoke_claude = AsyncMock(return_value={
            "text": '''{
                "executive_summary": "Q4 2024 project meeting discussing authentication module completion, security concerns, and budget issues.",
                "key_points": [
                    "Authentication module 90% complete",
                    "3 critical security vulnerabilities found",
                    "Budget 15% over allocation"
                ],
                "decisions": [
                    "Prioritize security fixes before release"
                ],
                "next_steps": [
                    "Security review by Dec 20",
                    "Database migration plan by Jan 5"
                ],
                "concerns": [
                    "Holiday timeline pressure",
                    "Budget overrun"
                ]
            }''',
            "cost": 0.002
        })

        agent = SummaryAgent()
        result = await agent.execute({
            "text": sample_document_text,
            "options": {
                "length": "medium",
                "audience": "executive"
            }
        })

        assert "summary" in result
        assert len(result["summary"]["key_points"]) > 0
        assert result["length"] == "medium"
        assert result["audience"] == "executive"


class TestEntityAgent:
    """Test EntityAgent functionality."""

    @pytest.mark.asyncio
    @patch('app.agents.entity_agent.BedrockService')
    @patch('app.agents.entity_agent.ComprehendService')
    async def test_entity_extraction(
        self, mock_comprehend, mock_bedrock, sample_document_text
    ):
        """Test entity extraction."""
        # Mock Comprehend response
        mock_comprehend_instance = mock_comprehend.return_value
        mock_comprehend_instance.analyze_document_entities = AsyncMock(return_value={
            "entities": [
                {"text": "John Smith", "type": "PERSON", "score": 0.95},
                {"text": "December 15, 2024", "type": "DATE", "score": 0.99}
            ],
            "cost": 0.0001
        })

        # Mock Bedrock response
        mock_bedrock_instance = mock_bedrock.return_value
        mock_bedrock_instance.invoke_claude = AsyncMock(return_value={
            "text": '''{
                "projects": [{"name": "Authentication Module", "status": "in_progress"}],
                "stakeholders": [
                    {"name": "John Smith", "role": "Project Manager"},
                    {"name": "Sarah Johnson", "role": "Tech Lead"}
                ],
                "milestones": [
                    {"name": "Database Migration", "date": "2025-01-15"}
                ],
                "budget_items": [],
                "dependencies": [],
                "teams": []
            }''',
            "cost": 0.002
        })

        agent = EntityAgent()
        result = await agent.execute({"text": sample_document_text})

        assert "comprehend_entities" in result
        assert "project_entities" in result
        assert len(result["comprehend_entities"]) > 0


class TestQAAgent:
    """Test QAAgent functionality."""

    @pytest.mark.asyncio
    @patch('app.agents.qa_agent.BedrockService')
    @patch('app.agents.qa_agent.VectorSearch')
    async def test_qa_with_context(self, mock_vector_search, mock_bedrock):
        """Test Q&A with document context."""
        # Mock vector search
        mock_vs_instance = mock_vector_search.return_value
        mock_vs_instance.semantic_search = AsyncMock(return_value={
            "results": [
                {
                    "document_id": "doc_123",
                    "filename": "meeting_notes.pdf",
                    "matched_chunk": {
                        "text": "Authentication module is 90% complete",
                        "chunk_index": 0
                    },
                    "similarity_score": 0.88
                }
            ]
        })

        # Mock Bedrock
        mock_bedrock_instance = mock_bedrock.return_value
        mock_bedrock_instance.invoke_claude = AsyncMock(return_value={
            "text": "The authentication module is currently 90% complete according to the meeting notes.",
            "cost": 0.001
        })

        agent = QAAgent()
        result = await agent.execute({
            "question": "What is the status of the authentication module?",
            "user_id": "user_123",
            "use_context": True
        })

        assert "answer" in result
        assert "citations" in result
        assert result["context_used"] > 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestMultiAgentIntegration:
    """Test multi-agent integration and workflows."""

    @pytest.mark.asyncio
    @patch('app.agents.analysis_agent.BedrockService')
    @patch('app.agents.action_agent.BedrockService')
    async def test_multi_agent_parallel_execution(
        self, mock_bedrock_action, mock_bedrock_analysis, sample_document_text
    ):
        """Test parallel multi-agent execution."""
        # Mock responses
        mock_bedrock_analysis.return_value.invoke_claude = AsyncMock(return_value={
            "text": '{"executive_summary": "Test", "key_insights": [], "patterns_identified": [], "recommendations": [], "risks_and_concerns": [], "opportunities": [], "confidence_score": 0.8}',
            "cost": 0.003
        })

        mock_bedrock_action.return_value.invoke_claude = AsyncMock(return_value={
            "text": '{"action_items": []}',
            "cost": 0.002
        })

        # Initialize orchestrator with agents
        orchestrator = initialize_agents()

        # Execute multi-agent analysis
        result = await orchestrator.multi_agent_analysis(
            document_id="doc_123",
            document_text=sample_document_text,
            user_id="user_123",
            tasks=["deep_analysis", "extract_actions"],
            parallel=True
        )

        assert "results" in result
        assert len(result["results"]) == 2
        assert "deep_analysis" in result["results"]
        assert "extract_actions" in result["results"]

    def test_get_all_agent_status(self):
        """Test getting status of all agents."""
        orchestrator = initialize_agents()

        status = orchestrator.get_all_agent_status()

        assert "AnalysisAgent" in status
        assert "ActionItemAgent" in status
        assert "SummaryAgent" in status
        assert "EntityAgent" in status
        assert "QAAgent" in status

    def test_orchestrator_stats(self):
        """Test orchestrator statistics."""
        orchestrator = initialize_agents()

        stats = orchestrator.get_orchestrator_stats()

        assert stats["total_agents"] == 5
        assert "agents" in stats
        assert stats["total_cost_usd"] >= 0

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test agent health check."""
        orchestrator = initialize_agents()

        health = await orchestrator.health_check()

        assert health["status"] in ["healthy", "degraded"]
        assert health["total_agents"] == 5
        assert "timestamp" in health


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling across the agent system."""

    @pytest.mark.asyncio
    async def test_validation_error_handling(self):
        """Test validation error handling."""
        agent = SummaryAgent()

        with pytest.raises(ValidationError):
            await agent.execute({})  # Missing required "text" field

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_execution(self):
        """Test circuit breaker prevents execution when open."""

        class FailingAgent(BaseAgent):
            async def process(self, input_data):
                raise Exception("Simulated failure")

        agent = FailingAgent(name="FailingAgent", description="Test")
        agent.circuit_breaker.failure_threshold = 2

        # Cause failures to open circuit
        for _ in range(2):
            try:
                await agent.execute({"test": "data"})
            except:
                pass

        # Circuit should be open
        assert agent.circuit_breaker.state == "open"
        assert agent.status == AgentStatus.CIRCUIT_OPEN


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
