"""Entity Agent for entity extraction and relationship mapping."""

import json
import re
from typing import Any, Dict

from app.agents.base_agent import BaseAgent
from app.services.aws_service import BedrockService, ComprehendService
from app.utils.logger import get_logger


logger = get_logger(__name__)


class EntityAgent(BaseAgent):
    """Agent for entity extraction."""

    def __init__(self):
        """Initialize entity agent."""
        super().__init__(
            name="EntityAgent",
            description="Extract entities with relationships and disambiguation",
            config={"max_requests_per_minute": 40}
        )
        self.bedrock = BedrockService()
        self.comprehend = ComprehendService()

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entities."""
        text = input_data["text"]

        # Use Comprehend for basic entities
        comprehend_result = await self.comprehend.analyze_document_entities(text)

        # Use Claude for project-specific entities
        system_prompt = """Extract project entities: projects, stakeholders, milestones, budgets, dependencies, teams."""

        user_message = f"""Extract entities from:

{text[:3000]}

Return JSON:
{{"projects": [{{"name": "...", "status": "..."}}], "stakeholders": [{{"name": "...", "role": "..."}}], "milestones": [{{"name": "...", "date": "..."}}], "budget_items": [], "dependencies": [], "teams": []}}"""

        response = await self.bedrock.invoke_claude(
            user_message=user_message,
            system_prompt=system_prompt,
            max_tokens=1500,
            temperature=0.2,
        )

        project_entities = self._parse_entities(response["text"])

        return {
            "comprehend_entities": comprehend_result["entities"],
            "project_entities": project_entities,
            "total_entities": len(comprehend_result["entities"]) + sum(len(v) for v in project_entities.values() if isinstance(v, list)),
            "cost": comprehend_result["cost"] + response["cost"],
        }

    def _parse_entities(self, response_text: str) -> Dict[str, Any]:
        """Parse entities JSON."""
        try:
            response_text = re.sub(r'```json?\n?', '', response_text).strip()
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"projects": [], "stakeholders": [], "milestones": [], "budget_items": [], "dependencies": [], "teams": []}
