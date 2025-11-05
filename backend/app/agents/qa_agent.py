"""Q&A Agent with RAG (Retrieval Augmented Generation)."""

from typing import Any

from app.agents.base_agent import BaseAgent
from app.services.aws_service import BedrockService
from app.services.vector_search import VectorSearch
from app.utils.exceptions import ValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QAAgent(BaseAgent):
    """Agent for question answering with RAG."""

    def __init__(self):
        """Initialize Q&A agent."""
        super().__init__(
            name="QAAgent",
            description="Answer questions using RAG with document context",
            config={"max_requests_per_minute": 30},
        )
        self.bedrock = BedrockService()
        self.vector_search = VectorSearch()

    def validate_input(self, input_data: dict[str, Any]) -> None:
        """Validate input."""
        super().validate_input(input_data)
        if "question" not in input_data or not input_data["question"].strip():
            raise ValidationError(message="Question is required", details={"agent": self.name})

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Answer question using RAG."""
        question = input_data["question"]
        user_id = input_data.get("user_id")
        document_id = input_data.get("document_id")
        use_context = input_data.get("use_context", True)
        conversation_history = input_data.get("conversation_history", [])

        logger.info(f"Q&A: '{question[:50]}...'")

        # Retrieve relevant context
        context_chunks = []
        citations = []

        if use_context:
            search_results = await self.vector_search.semantic_search(
                query=question,
                user_id=user_id,
                limit=5,
                similarity_threshold=0.7,
                use_cache=True,
            )

            for _idx, result in enumerate(search_results["results"]):
                # Filter by document_id if specified
                if document_id and result["document_id"] != document_id:
                    continue

                context_chunks.append(result["matched_chunk"]["text"])
                citations.append(
                    {
                        "document_id": result["document_id"],
                        "filename": result["filename"],
                        "chunk_index": result["matched_chunk"]["chunk_index"],
                        "similarity_score": result["similarity_score"],
                    }
                )

        # Build prompt with context
        system_prompt = """You are a helpful AI assistant answering questions about project documents.

Rules:
1. Only answer based on the provided context
2. Cite sources with [Document: filename, Chunk: X]
3. If information is not in context, say "I don't have enough information"
4. Be concise but thorough
5. Use conversation history for follow-up questions"""

        # Build context string
        context_str = ""
        if context_chunks:
            context_str = "\n\n".join(
                [
                    f"[Document: {citations[i]['filename']}, Chunk: {citations[i]['chunk_index']}]\n{chunk}"
                    for i, chunk in enumerate(context_chunks)
                ]
            )

        # Build conversation context
        conv_context = ""
        if conversation_history:
            recent_history = conversation_history[-3:]  # Last 3 exchanges
            conv_context = "Previous conversation:\n" + "\n".join(
                [
                    f"Q: {exchange['question']}\nA: {exchange['answer']}"
                    for exchange in recent_history
                ]
            )

        user_message = f"""

{conv_context}

Context from documents:
{context_str}

Question: {question}

Answer the question based on the context above. Include citations."""

        response = await self.bedrock.invoke_claude(
            user_message=user_message,
            system_prompt=system_prompt,
            max_tokens=1500,
            temperature=0.3,
        )

        return {
            "question": question,
            "answer": response["text"],
            "citations": citations,
            "context_used": len(context_chunks),
            "has_followup_context": len(conversation_history) > 0,
            "cost": response["cost"],
        }
