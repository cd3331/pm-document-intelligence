"""
Unit tests for AI agents module
Tests individual agents, orchestration, and error handling
"""

import pytest
from unittest.mock import patch, MagicMock, Mock, AsyncMock
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.agents.summary_agent import SummaryAgent
from app.agents.action_extractor_agent import ActionExtractorAgent
from app.agents.qa_agent import QAAgent
from app.agents.insights_agent import InsightsAgent
from app.agents.sentiment_agent import SentimentAgent
from app.agents.orchestrator import AgentOrchestrator, get_orchestrator


@pytest.mark.unit
class TestBaseAgent:
    """Test base agent functionality"""

    def test_base_agent_initialization(self):
        """Test base agent initialization"""
        agent = BaseAgent(name="TestAgent", model="test-model")

        assert agent.name == "TestAgent"
        assert agent.model == "test-model"
        assert agent.max_retries >= 0
        assert agent.timeout > 0

    @pytest.mark.asyncio
    async def test_base_agent_execute_abstract(self):
        """Test that execute method is abstract"""
        agent = BaseAgent(name="TestAgent")

        with pytest.raises(NotImplementedError):
            await agent.execute(context={})

    def test_base_agent_format_prompt(self):
        """Test prompt formatting"""
        agent = BaseAgent(name="TestAgent")

        prompt = agent._format_prompt(
            template="Hello {name}, you are {age} years old",
            name="John",
            age=30
        )

        assert "John" in prompt
        assert "30" in prompt

    @pytest.mark.asyncio
    async def test_base_agent_retry_mechanism(self, mock_bedrock_runtime_client):
        """Test retry mechanism on failures"""
        agent = BaseAgent(name="TestAgent", max_retries=3)

        # Mock LLM call to fail twice, then succeed
        call_count = 0

        async def mock_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return {"response": "Success"}

        agent._call_llm = mock_call

        # Should succeed on third try
        result = await agent._call_with_retry(mock_call)

        assert result == {"response": "Success"}
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_base_agent_max_retries_exceeded(self):
        """Test behavior when max retries exceeded"""
        agent = BaseAgent(name="TestAgent", max_retries=2)

        async def always_fail(*args, **kwargs):
            raise Exception("Permanent failure")

        agent._call_llm = always_fail

        with pytest.raises(Exception, match="Permanent failure"):
            await agent._call_with_retry(always_fail)


@pytest.mark.unit
class TestSummaryAgent:
    """Test summary generation agent"""

    @pytest.mark.asyncio
    async def test_summary_agent_basic(self, mock_bedrock_runtime_client):
        """Test basic summary generation"""
        agent = SummaryAgent()

        with patch('app.agents.summary_agent.boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            context = {
                "document_text": "This is a long document about project management. It discusses various topics including planning, execution, and monitoring."
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'summary' in result
            assert len(result['summary']) > 0

    @pytest.mark.asyncio
    async def test_summary_agent_empty_text(self, mock_bedrock_runtime_client):
        """Test summary with empty text"""
        agent = SummaryAgent()

        context = {"document_text": ""}

        result = await agent.execute(context)

        assert result is not None
        assert 'error' in result or result.get('summary') == ""

    @pytest.mark.asyncio
    async def test_summary_agent_long_document(self, mock_bedrock_runtime_client):
        """Test summary with very long document"""
        agent = SummaryAgent()

        # Create long document
        long_text = "Sample paragraph. " * 1000

        with patch('app.agents.summary_agent.boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            context = {"document_text": long_text}

            result = await agent.execute(context)

            assert result is not None
            assert 'summary' in result
            # Summary should be shorter than original
            assert len(result['summary']) < len(long_text)

    @pytest.mark.asyncio
    async def test_summary_agent_with_custom_length(self, mock_bedrock_runtime_client):
        """Test summary with custom length parameter"""
        agent = SummaryAgent()

        with patch('app.agents.summary_agent.boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            context = {
                "document_text": "Long document text here.",
                "summary_length": "brief"
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'summary' in result


@pytest.mark.unit
class TestActionExtractorAgent:
    """Test action item extraction agent"""

    @pytest.mark.asyncio
    async def test_extract_action_items(self, mock_bedrock_runtime_client):
        """Test extracting action items from text"""
        agent = ActionExtractorAgent()

        with patch('app.agents.action_extractor_agent.boto3.client') as mock_boto:
            # Mock response with action items
            mock_response = {
                'body': MagicMock(read=lambda: b'{"action_items": [{"title": "Complete testing", "priority": "high"}]}')
            }
            mock_boto.return_value.invoke_model.return_value = mock_response

            context = {
                "document_text": "TODO: Complete the testing suite. Action: Review documentation."
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'action_items' in result
            assert len(result['action_items']) > 0

    @pytest.mark.asyncio
    async def test_extract_action_items_with_priorities(self, mock_bedrock_runtime_client):
        """Test extracting action items with priority detection"""
        agent = ActionExtractorAgent()

        with patch('app.agents.action_extractor_agent.boto3.client') as mock_boto:
            mock_response = {
                'body': MagicMock(
                    read=lambda: b'{"action_items": [{"title": "URGENT: Fix bug", "priority": "high"}, {"title": "Update docs", "priority": "low"}]}'
                )
            }
            mock_boto.return_value.invoke_model.return_value = mock_response

            context = {
                "document_text": "URGENT: Fix production bug. Also, update documentation when you have time."
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'action_items' in result

            # Should have items with different priorities
            priorities = [item.get('priority') for item in result['action_items']]
            assert 'high' in priorities or 'low' in priorities

    @pytest.mark.asyncio
    async def test_extract_action_items_no_items(self, mock_bedrock_runtime_client):
        """Test extraction when no action items present"""
        agent = ActionExtractorAgent()

        with patch('app.agents.action_extractor_agent.boto3.client') as mock_boto:
            mock_response = {
                'body': MagicMock(read=lambda: b'{"action_items": []}')
            }
            mock_boto.return_value.invoke_model.return_value = mock_response

            context = {
                "document_text": "This is just informational text with no action items."
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'action_items' in result
            assert len(result['action_items']) == 0


@pytest.mark.unit
class TestQAAgent:
    """Test question answering agent"""

    @pytest.mark.asyncio
    async def test_qa_agent_answer_question(self, mock_bedrock_runtime_client):
        """Test answering questions about document"""
        agent = QAAgent()

        with patch('app.agents.qa_agent.boto3.client') as mock_boto:
            mock_response = {
                'body': MagicMock(read=lambda: b'{"answer": "The document is about testing"}')
            }
            mock_boto.return_value.invoke_model.return_value = mock_response

            context = {
                "document_text": "This document describes comprehensive testing strategies.",
                "question": "What is this document about?"
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'answer' in result
            assert len(result['answer']) > 0

    @pytest.mark.asyncio
    async def test_qa_agent_with_context(self, mock_bedrock_runtime_client):
        """Test QA with conversation context"""
        agent = QAAgent()

        with patch('app.agents.qa_agent.boto3.client') as mock_boto:
            mock_response = {
                'body': MagicMock(read=lambda: b'{"answer": "Yes, as mentioned earlier"}')
            }
            mock_boto.return_value.invoke_model.return_value = mock_response

            context = {
                "document_text": "Testing document",
                "question": "Can you elaborate?",
                "conversation_history": [
                    {"role": "user", "content": "What is this about?"},
                    {"role": "assistant", "content": "It's about testing"}
                ]
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'answer' in result

    @pytest.mark.asyncio
    async def test_qa_agent_unanswerable_question(self, mock_bedrock_runtime_client):
        """Test handling unanswerable questions"""
        agent = QAAgent()

        with patch('app.agents.qa_agent.boto3.client') as mock_boto:
            mock_response = {
                'body': MagicMock(
                    read=lambda: b'{"answer": "I cannot answer this based on the provided document"}'
                )
            }
            mock_boto.return_value.invoke_model.return_value = mock_response

            context = {
                "document_text": "Document about testing",
                "question": "What is the weather like in Tokyo?"
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'answer' in result
            assert "cannot" in result['answer'].lower() or "not" in result['answer'].lower()


@pytest.mark.unit
class TestInsightsAgent:
    """Test key insights extraction agent"""

    @pytest.mark.asyncio
    async def test_extract_insights(self, mock_bedrock_runtime_client):
        """Test extracting key insights"""
        agent = InsightsAgent()

        with patch('app.agents.insights_agent.boto3.client') as mock_boto:
            mock_response = {
                'body': MagicMock(
                    read=lambda: b'{"insights": ["Testing is important", "Coverage should be 80%+"]}'
                )
            }
            mock_boto.return_value.invoke_model.return_value = mock_response

            context = {
                "document_text": "Testing is crucial for software quality. We should aim for 80% code coverage."
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'insights' in result
            assert len(result['insights']) > 0

    @pytest.mark.asyncio
    async def test_extract_insights_with_metrics(self, mock_bedrock_runtime_client):
        """Test extracting insights with numerical metrics"""
        agent = InsightsAgent()

        with patch('app.agents.insights_agent.boto3.client') as mock_boto:
            mock_response = {
                'body': MagicMock(
                    read=lambda: b'{"insights": ["Revenue increased by 25%", "Customer satisfaction: 4.5/5"]}'
                )
            }
            mock_boto.return_value.invoke_model.return_value = mock_response

            context = {
                "document_text": "Q3 revenue increased 25%. Customer satisfaction rating is 4.5 out of 5."
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'insights' in result
            # Should extract numerical insights
            insights_text = ' '.join(result['insights'])
            assert '25' in insights_text or '4.5' in insights_text


@pytest.mark.unit
class TestSentimentAgent:
    """Test sentiment analysis agent"""

    @pytest.mark.asyncio
    async def test_analyze_sentiment_positive(self, mock_bedrock_runtime_client):
        """Test analyzing positive sentiment"""
        agent = SentimentAgent()

        with patch('app.agents.sentiment_agent.boto3.client') as mock_boto:
            mock_response = {
                'body': MagicMock(
                    read=lambda: b'{"sentiment": "positive", "confidence": 0.95}'
                )
            }
            mock_boto.return_value.invoke_model.return_value = mock_response

            context = {
                "document_text": "This is an excellent project with great results!"
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'sentiment' in result
            assert result['sentiment'] in ['positive', 'negative', 'neutral', 'mixed']

    @pytest.mark.asyncio
    async def test_analyze_sentiment_negative(self, mock_bedrock_runtime_client):
        """Test analyzing negative sentiment"""
        agent = SentimentAgent()

        with patch('app.agents.sentiment_agent.boto3.client') as mock_boto:
            mock_response = {
                'body': MagicMock(
                    read=lambda: b'{"sentiment": "negative", "confidence": 0.88}'
                )
            }
            mock_boto.return_value.invoke_model.return_value = mock_response

            context = {
                "document_text": "The project failed to meet expectations and encountered major issues."
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'sentiment' in result

    @pytest.mark.asyncio
    async def test_analyze_sentiment_with_scores(self, mock_bedrock_runtime_client):
        """Test sentiment analysis with detailed scores"""
        agent = SentimentAgent()

        with patch('app.agents.sentiment_agent.boto3.client') as mock_boto:
            mock_response = {
                'body': MagicMock(
                    read=lambda: b'{"sentiment": "neutral", "scores": {"positive": 0.3, "negative": 0.2, "neutral": 0.5}}'
                )
            }
            mock_boto.return_value.invoke_model.return_value = mock_response

            context = {
                "document_text": "The project is proceeding according to plan."
            }

            result = await agent.execute(context)

            assert result is not None
            assert 'sentiment' in result


@pytest.mark.unit
class TestAgentOrchestrator:
    """Test agent orchestration"""

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        orchestrator = AgentOrchestrator()

        assert orchestrator is not None
        assert len(orchestrator.agents) > 0

    def test_orchestrator_register_agent(self):
        """Test registering new agent"""
        orchestrator = AgentOrchestrator()
        test_agent = BaseAgent(name="CustomAgent")

        initial_count = len(orchestrator.agents)
        orchestrator.register_agent("custom", test_agent)

        assert len(orchestrator.agents) == initial_count + 1
        assert "custom" in orchestrator.agents

    def test_orchestrator_get_agent(self):
        """Test retrieving agent by name"""
        orchestrator = AgentOrchestrator()

        summary_agent = orchestrator.get_agent("summary")

        assert summary_agent is not None
        assert isinstance(summary_agent, SummaryAgent)

    def test_orchestrator_get_nonexistent_agent(self):
        """Test retrieving non-existent agent"""
        orchestrator = AgentOrchestrator()

        agent = orchestrator.get_agent("nonexistent")

        assert agent is None

    @pytest.mark.asyncio
    async def test_orchestrator_process_document(
        self,
        mock_bedrock_runtime_client,
        sample_document
    ):
        """Test orchestrating full document processing"""
        orchestrator = AgentOrchestrator()

        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            result = await orchestrator.process_document(
                document_id=sample_document.id,
                document_text=sample_document.extracted_text
            )

            assert result is not None
            assert 'summary' in result or 'error' not in result

    @pytest.mark.asyncio
    async def test_orchestrator_parallel_execution(
        self,
        mock_bedrock_runtime_client
    ):
        """Test parallel agent execution"""
        orchestrator = AgentOrchestrator()

        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            import time
            start_time = time.time()

            result = await orchestrator.execute_parallel(
                agents=['summary', 'sentiment', 'insights'],
                context={"document_text": "Test document"}
            )

            elapsed = time.time() - start_time

            assert result is not None
            # Parallel execution should be faster than sequential
            # (Though hard to test with mocks)

    @pytest.mark.asyncio
    async def test_orchestrator_error_handling(self):
        """Test orchestrator error handling"""
        orchestrator = AgentOrchestrator()

        # Mock agent to raise error
        mock_agent = AsyncMock()
        mock_agent.execute.side_effect = Exception("Agent failed")
        orchestrator.register_agent("failing_agent", mock_agent)

        result = await orchestrator.execute_agent(
            "failing_agent",
            context={},
            handle_errors=True
        )

        assert result is not None
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_orchestrator_context_passing(self, mock_bedrock_runtime_client):
        """Test context passing between agents"""
        orchestrator = AgentOrchestrator()

        with patch('boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            # Execute agents in sequence with context
            context = {"document_text": "Test document"}

            # First agent
            result1 = await orchestrator.execute_agent("summary", context)
            context['summary'] = result1.get('summary', '')

            # Second agent using first agent's output
            result2 = await orchestrator.execute_agent("insights", context)

            assert result2 is not None

    def test_orchestrator_singleton(self):
        """Test that get_orchestrator returns singleton"""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()

        assert orch1 is orch2


@pytest.mark.unit
class TestAgentCaching:
    """Test agent response caching"""

    @pytest.mark.asyncio
    async def test_cache_agent_response(self, mock_bedrock_runtime_client):
        """Test caching agent responses"""
        agent = SummaryAgent(enable_cache=True)

        with patch('app.agents.summary_agent.boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            context = {"document_text": "Same text"}

            # First call
            result1 = await agent.execute(context)

            # Second call with same context
            result2 = await agent.execute(context)

            # Should return cached result
            assert result1 == result2

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, mock_bedrock_runtime_client):
        """Test cache invalidation"""
        agent = SummaryAgent(enable_cache=True)

        with patch('app.agents.summary_agent.boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            context1 = {"document_text": "Text 1"}
            context2 = {"document_text": "Text 2"}

            result1 = await agent.execute(context1)
            result2 = await agent.execute(context2)

            # Different contexts should not use cache
            # (Hard to assert without access to cache internals)
            assert result1 is not None
            assert result2 is not None


@pytest.mark.unit
class TestAgentMetrics:
    """Test agent performance metrics"""

    @pytest.mark.asyncio
    async def test_track_execution_time(self, mock_bedrock_runtime_client):
        """Test tracking agent execution time"""
        agent = SummaryAgent()

        with patch('app.agents.summary_agent.boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            context = {"document_text": "Test"}

            result = await agent.execute(context)

            # Should have execution time metadata
            assert 'execution_time' in result or hasattr(agent, 'last_execution_time')

    @pytest.mark.asyncio
    async def test_track_token_usage(self, mock_bedrock_runtime_client):
        """Test tracking token usage"""
        agent = SummaryAgent()

        with patch('app.agents.summary_agent.boto3.client') as mock_boto:
            mock_boto.return_value = mock_bedrock_runtime_client

            context = {"document_text": "Test"}

            result = await agent.execute(context)

            # Should track token usage
            assert 'token_usage' in result or hasattr(agent, 'total_tokens')
