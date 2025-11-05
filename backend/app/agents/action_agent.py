"""
Action Item Agent for extracting and tracking action items.
"""

import json
import re
from typing import Any

from app.agents.base_agent import BaseAgent
from app.services.aws_service import BedrockService
from app.utils.exceptions import ValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ActionItemAgent(BaseAgent):
    """Agent for action item extraction."""

    def __init__(self):
        """Initialize action item agent."""
        super().__init__(
            name="ActionItemAgent",
            description="Extract action items with assignees, due dates, and priorities",
            config={"max_requests_per_minute": 40},
        )
        self.bedrock = BedrockService()

    def validate_input(self, input_data: dict[str, Any]) -> None:
        """Validate input data."""
        super().validate_input(input_data)
        if "text" not in input_data or not input_data["text"].strip():
            raise ValidationError(message="Text is required", details={"agent": self.name})

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Extract action items from text."""
        text = input_data["text"]

        system_prompt = """You are an expert at extracting action items from documents.

For each action item, identify:
- action: Clear description
- assignee: Person/team responsible
- due_date: Deadline (YYYY-MM-DD format or "TBD")
- priority: HIGH, MEDIUM, or LOW
- status: TODO, IN_PROGRESS, BLOCKED, or DONE
- dependencies: Other action items this depends on
- confidence: 0.0-1.0

Output ONLY valid JSON array."""

        user_message = f"""Extract ALL action items from this document:

{text[:4000]}

Return JSON array:
[{{"action": "...", "assignee": "...", "due_date": "...", "priority": "HIGH", "status": "TODO", "dependencies": [], "confidence": 0.9}}]"""

        response = await self.bedrock.invoke_claude(
            user_message=user_message,
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.2,
        )

        action_items = self._parse_actions(response["text"])

        return {
            "action_items": action_items,
            "total_actions": len(action_items),
            "high_priority": sum(1 for a in action_items if a.get("priority") == "HIGH"),
            "cost": response["cost"],
        }

    def _parse_actions(self, response_text: str) -> list[dict[str, Any]]:
        """Parse action items from response."""
        try:
            response_text = re.sub(r"```json?\n?", "", response_text)
            response_text = re.sub(r"```\n?$", "", response_text).strip()
            actions = json.loads(response_text)

            # Validate each action
            validated = []
            for action in actions:
                if self._validate_action(action):
                    validated.append(action)

            return validated

        except json.JSONDecodeError:
            logger.warning("Failed to parse action items JSON")
            return []

    def _validate_action(self, action: dict[str, Any]) -> bool:
        """Validate action item structure."""
        required = ["action", "priority", "confidence"]
        if not all(f in action for f in required):
            return False
        if action["priority"] not in ["HIGH", "MEDIUM", "LOW"]:
            return False
        if not isinstance(action["confidence"], (int, float)) or not (
            0 <= action["confidence"] <= 1
        ):
            return False
        return True
