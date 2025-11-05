"""Summary Agent for document summarization."""

import json
import re
from typing import Any, Dict

from app.agents.base_agent import BaseAgent
from app.services.aws_service import BedrockService
from app.utils.exceptions import ValidationError
from app.utils.logger import get_logger


logger = get_logger(__name__)


class SummaryAgent(BaseAgent):
    """Agent for document summarization."""

    def __init__(self):
        """Initialize summary agent."""
        super().__init__(
            name="SummaryAgent",
            description="Generate summaries with configurable length and audience",
            config={"max_requests_per_minute": 50}
        )
        self.bedrock = BedrockService()

    def validate_input(self, input_data: Dict[str, Any]) -> None:
        """Validate input."""
        super().validate_input(input_data)
        if "text" not in input_data:
            raise ValidationError(message="Text required", details={"agent": self.name})

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary."""
        text = input_data["text"]
        length = input_data.get("options", {}).get("length", "medium")
        audience = input_data.get("options", {}).get("audience", "general")

        token_limits = {"brief": 200, "medium": 500, "comprehensive": 1000}
        max_tokens = token_limits.get(length, 500)

        system_prompt = self._get_prompt(audience)

        user_message = f"""Summarize this document ({length} length for {audience} audience):

{text[:6000]}

Return JSON:
{{"executive_summary": "...", "key_points": ["..."], "decisions": ["..."], "next_steps": ["..."], "concerns": ["..."]}}"""

        response = await self.bedrock.invoke_claude(
            user_message=user_message,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=0.3,
        )

        summary = self._parse_summary(response["text"])

        return {"summary": summary, "length": length, "audience": audience, "cost": response["cost"]}

    def _get_prompt(self, audience: str) -> str:
        """Get prompt for audience."""
        prompts = {
            "executive": "You are summarizing for executives. Focus on high-level insights, decisions, and business impact. Be concise.",
            "technical": "You are summarizing for technical teams. Include technical details, implementation considerations, and technical risks.",
            "team": "You are summarizing for project teams. Focus on actionable items, progress updates, and collaboration needs.",
        }
        return prompts.get(audience, "You are creating a clear, structured summary. Focus on key points and next steps.")

    def _parse_summary(self, response_text: str) -> Dict[str, Any]:
        """Parse summary JSON."""
        try:
            response_text = re.sub(r'```json?\n?', '', response_text).strip()
            response_text = re.sub(r'```\n?$', '', response_text).strip()
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"executive_summary": response_text, "key_points": [], "decisions": [], "next_steps": [], "concerns": []}
