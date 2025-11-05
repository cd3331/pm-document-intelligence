"""
Intelligent Model Routing and Cost Optimization
Route requests to optimal models based on complexity, cost, and requirements
"""

from typing import Dict, Any, Optional, Tuple
from enum import Enum
import hashlib
import json
from datetime import datetime, timedelta


class ModelTier(Enum):
    """Model tiers by capability and cost"""
    FAST_CHEAP = "fast_cheap"  # GPT-3.5, Claude Instant
    BALANCED = "balanced"      # GPT-4, Claude 2
    PREMIUM = "premium"        # GPT-4 Turbo, Claude 2.1


class DocumentComplexity(Enum):
    """Document complexity levels"""
    SIMPLE = "simple"      # < 1000 words, straightforward
    MODERATE = "moderate"  # 1000-5000 words
    COMPLEX = "complex"    # > 5000 words or technical


class IntelligentRouter:
    """Route requests to optimal AI models"""

    def __init__(self):
        self.model_configs = {
            ModelTier.FAST_CHEAP: {
                "models": ["gpt-3.5-turbo", "claude-instant-1"],
                "cost_per_1k_tokens": 0.002,
                "avg_latency_ms": 500,
                "best_for": ["simple tasks", "high volume"]
            },
            ModelTier.BALANCED: {
                "models": ["gpt-4", "claude-2"],
                "cost_per_1k_tokens": 0.03,
                "avg_latency_ms": 2000,
                "best_for": ["complex analysis", "accuracy critical"]
            },
            ModelTier.PREMIUM: {
                "models": ["gpt-4-turbo", "claude-2.1"],
                "cost_per_1k_tokens": 0.01,
                "avg_latency_ms": 1500,
                "best_for": ["large documents", "speed + accuracy"]
            }
        }

        self.cache = ResponseCache()

    def assess_complexity(
        self,
        document_text: str,
        document_type: str,
        task_type: str
    ) -> DocumentComplexity:
        """
        Assess document complexity

        Args:
            document_text: Document content
            document_type: Type of document
            task_type: Task to perform

        Returns:
            Complexity level
        """
        word_count = len(document_text.split())

        # Simple heuristics
        if word_count < 1000:
            base_complexity = DocumentComplexity.SIMPLE
        elif word_count < 5000:
            base_complexity = DocumentComplexity.MODERATE
        else:
            base_complexity = DocumentComplexity.COMPLEX

        # Adjust for document type
        if document_type in ["technical_spec", "requirements_doc"]:
            if base_complexity == DocumentComplexity.SIMPLE:
                base_complexity = DocumentComplexity.MODERATE
            elif base_complexity == DocumentComplexity.MODERATE:
                base_complexity = DocumentComplexity.COMPLEX

        # Adjust for task type
        if task_type in ["risk_assessment", "multi_doc_synthesis"]:
            if base_complexity == DocumentComplexity.SIMPLE:
                base_complexity = DocumentComplexity.MODERATE

        return base_complexity

    def select_model(
        self,
        complexity: DocumentComplexity,
        requirements: Dict[str, Any]
    ) -> Tuple[ModelTier, str]:
        """
        Select optimal model based on complexity and requirements

        Args:
            complexity: Document complexity
            requirements: Dict with keys:
                - accuracy_priority: float (0-1)
                - cost_priority: float (0-1)
                - speed_priority: float (0-1)

        Returns:
            (ModelTier, specific model name)
        """
        accuracy_priority = requirements.get("accuracy_priority", 0.5)
        cost_priority = requirements.get("cost_priority", 0.3)
        speed_priority = requirements.get("speed_priority", 0.2)

        # Decision logic
        if complexity == DocumentComplexity.SIMPLE:
            if cost_priority > 0.6:
                tier = ModelTier.FAST_CHEAP
            elif speed_priority > 0.6:
                tier = ModelTier.PREMIUM
            else:
                tier = ModelTier.FAST_CHEAP

        elif complexity == DocumentComplexity.MODERATE:
            if accuracy_priority > 0.7:
                tier = ModelTier.BALANCED
            elif cost_priority > 0.6:
                tier = ModelTier.FAST_CHEAP
            else:
                tier = ModelTier.BALANCED

        else:  # COMPLEX
            if accuracy_priority > 0.7:
                tier = ModelTier.PREMIUM
            elif cost_priority > 0.7:
                tier = ModelTier.BALANCED
            else:
                tier = ModelTier.PREMIUM

        # Select specific model from tier
        model_name = self.model_configs[tier]["models"][0]

        return tier, model_name

    def route_request(
        self,
        document_text: str,
        document_type: str,
        task_type: str,
        requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route request to optimal model

        Args:
            document_text: Document content
            document_type: Document type
            task_type: Task type
            requirements: Requirements dict

        Returns:
            Routing decision with metadata
        """
        # Check cache first
        cache_key = self.cache.generate_key(document_text, task_type)
        cached_response = self.cache.get(cache_key)

        if cached_response:
            return {
                "cached": True,
                "response": cached_response,
                "cost": 0,
                "latency": 0
            }

        # Assess complexity
        complexity = self.assess_complexity(document_text, document_type, task_type)

        # Select model
        if requirements is None:
            requirements = {
                "accuracy_priority": 0.7,
                "cost_priority": 0.2,
                "speed_priority": 0.1
            }

        tier, model_name = self.select_model(complexity, requirements)

        # Calculate estimated cost
        token_count = len(document_text.split()) * 1.3  # Rough estimate
        estimated_cost = (token_count / 1000) * self.model_configs[tier]["cost_per_1k_tokens"]

        return {
            "cached": False,
            "model_tier": tier.value,
            "model_name": model_name,
            "complexity": complexity.value,
            "estimated_cost": estimated_cost,
            "estimated_latency": self.model_configs[tier]["avg_latency_ms"],
            "cache_key": cache_key
        }


class ResponseCache:
    """Cache AI responses for common patterns"""

    def __init__(self, ttl_hours: int = 24):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(hours=ttl_hours)

    def generate_key(self, document_text: str, task_type: str) -> str:
        """Generate cache key from document and task"""
        content = f"{task_type}:{document_text[:1000]}"  # First 1000 chars
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get cached response"""
        if key not in self.cache:
            return None

        entry = self.cache[key]

        # Check expiration
        if datetime.utcnow() > entry["expires_at"]:
            del self.cache[key]
            return None

        entry["hits"] += 1
        return entry["response"]

    def set(self, key: str, response: Any):
        """Cache a response"""
        self.cache[key] = {
            "response": response,
            "expires_at": datetime.utcnow() + self.ttl,
            "hits": 0,
            "created_at": datetime.utcnow()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self.cache)
        total_hits = sum(entry["hits"] for entry in self.cache.values())

        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "avg_hits_per_entry": total_hits / total_entries if total_entries > 0 else 0
        }


class BatchProcessor:
    """Batch similar documents for efficient processing"""

    def __init__(self):
        self.pending_batches: Dict[str, List[Dict[str, Any]]] = {}
        self.batch_size = 10
        self.max_wait_seconds = 30

    def add_to_batch(
        self,
        document_text: str,
        task_type: str,
        callback: Any
    ) -> bool:
        """
        Add document to batch

        Returns:
            True if batch is ready to process
        """
        batch_key = self._get_batch_key(document_text, task_type)

        if batch_key not in self.pending_batches:
            self.pending_batches[batch_key] = []

        self.pending_batches[batch_key].append({
            "document_text": document_text,
            "task_type": task_type,
            "callback": callback,
            "added_at": datetime.utcnow()
        })

        # Check if batch is ready
        batch = self.pending_batches[batch_key]
        return len(batch) >= self.batch_size or self._is_batch_expired(batch)

    def _get_batch_key(self, document_text: str, task_type: str) -> str:
        """Generate batch key for similar documents"""
        # Group by task type and approximate length
        length_bucket = len(document_text) // 1000
        return f"{task_type}_{length_bucket}"

    def _is_batch_expired(self, batch: List[Dict[str, Any]]) -> bool:
        """Check if batch has waited too long"""
        if not batch:
            return False
        oldest = min(item["added_at"] for item in batch)
        return (datetime.utcnow() - oldest).total_seconds() > self.max_wait_seconds


# Global instances
_router = IntelligentRouter()
_batch_processor = BatchProcessor()


def get_router() -> IntelligentRouter:
    """Get global router instance"""
    return _router


def get_batch_processor() -> BatchProcessor:
    """Get global batch processor"""
    return _batch_processor
