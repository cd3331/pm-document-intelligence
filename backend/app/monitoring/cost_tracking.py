"""
Cost tracking and monitoring for AWS and OpenAI services
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import boto3


@dataclass
class CostEntry:
    """Cost tracking entry"""

    service: str
    operation: str
    units: float
    unit_cost: float
    total_cost: float
    timestamp: datetime
    metadata: Optional[Dict] = None


class CostTracker:
    """Track and aggregate service costs"""

    # AWS pricing (approximate, USD)
    AWS_PRICING = {
        "s3": {"storage_gb_month": 0.023, "requests_1000": 0.0004},
        "textract": {"page": 0.0015},
        "comprehend": {"unit": 0.0001},
        "bedrock": {"claude_input_1k": 0.008, "claude_output_1k": 0.024},
    }

    # OpenAI pricing (USD)
    OPENAI_PRICING = {
        "gpt-4": {"input_1k": 0.03, "output_1k": 0.06},
        "gpt-3.5-turbo": {"input_1k": 0.0015, "output_1k": 0.002},
        "text-embedding-ada-002": {"1k_tokens": 0.0001},
    }

    def __init__(self):
        self.cost_history: List[CostEntry] = []

    def track_aws_s3(self, operation: str, size_bytes: int):
        """Track S3 costs"""
        size_gb = size_bytes / (1024**3)
        cost = size_gb * self.AWS_PRICING["s3"]["storage_gb_month"] / 30  # Daily cost
        self._add_entry(
            "aws_s3", operation, size_gb, cost / size_gb if size_gb > 0 else 0, cost
        )

    def track_aws_textract(self, pages: int):
        """Track Textract costs"""
        unit_cost = self.AWS_PRICING["textract"]["page"]
        total_cost = pages * unit_cost
        self._add_entry(
            "aws_textract", "analyze_document", pages, unit_cost, total_cost
        )

    def track_aws_bedrock(self, model: str, input_tokens: int, output_tokens: int):
        """Track Bedrock costs"""
        input_cost = (input_tokens / 1000) * self.AWS_PRICING["bedrock"][
            "claude_input_1k"
        ]
        output_cost = (output_tokens / 1000) * self.AWS_PRICING["bedrock"][
            "claude_output_1k"
        ]
        total_cost = input_cost + output_cost
        self._add_entry(
            "aws_bedrock", model, input_tokens + output_tokens, 0, total_cost
        )

    def track_openai(
        self, model: str, operation: str, input_tokens: int, output_tokens: int = 0
    ):
        """Track OpenAI costs"""
        pricing = self.OPENAI_PRICING.get(model, self.OPENAI_PRICING["gpt-3.5-turbo"])
        input_cost = (input_tokens / 1000) * pricing["input_1k"]
        output_cost = (output_tokens / 1000) * pricing.get("output_1k", 0)
        total_cost = input_cost + output_cost
        self._add_entry(
            f"openai_{model}", operation, input_tokens + output_tokens, 0, total_cost
        )

    def _add_entry(
        self,
        service: str,
        operation: str,
        units: float,
        unit_cost: float,
        total_cost: float,
    ):
        """Add cost entry"""
        entry = CostEntry(
            service=service,
            operation=operation,
            units=units,
            unit_cost=unit_cost,
            total_cost=total_cost,
            timestamp=datetime.utcnow(),
        )
        self.cost_history.append(entry)

    def get_daily_cost(self) -> float:
        """Get total cost for today"""
        today = datetime.utcnow().date()
        return sum(
            e.total_cost for e in self.cost_history if e.timestamp.date() == today
        )

    def get_cost_by_service(self, days: int = 1) -> Dict[str, float]:
        """Get costs grouped by service"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        costs = {}
        for entry in self.cost_history:
            if entry.timestamp >= cutoff:
                costs[entry.service] = costs.get(entry.service, 0) + entry.total_cost
        return costs


# Global cost tracker
cost_tracker = CostTracker()
