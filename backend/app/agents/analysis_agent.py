"""
Analysis Agent for deep document analysis.

Specializes in complex reasoning, insight extraction, and recommendations.
"""

import json
import re
from typing import Any, Dict

from app.agents.base_agent import BaseAgent
from app.services.aws_service import BedrockService, DocumentType
from app.utils.exceptions import ValidationError
from app.utils.logger import get_logger


logger = get_logger(__name__)


class AnalysisAgent(BaseAgent):
    """Agent for deep document analysis."""

    def __init__(self):
        """Initialize analysis agent."""
        super().__init__(
            name="AnalysisAgent",
            description="Deep analysis with insights, patterns, and recommendations",
            config={
                "max_requests_per_minute": 30,
                "failure_threshold": 3,
            }
        )

        self.bedrock = BedrockService()

    def validate_input(self, input_data: Dict[str, Any]) -> None:
        """Validate input data."""
        super().validate_input(input_data)

        required_fields = ["text"]
        for field in required_fields:
            if field not in input_data:
                raise ValidationError(
                    message=f"Missing required field: {field}",
                    details={"agent": self.name, "field": field}
                )

        if not input_data["text"].strip():
            raise ValidationError(
                message="Text cannot be empty",
                details={"agent": self.name}
            )

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process document for deep analysis."""
        text = input_data["text"]
        document_type = input_data.get("document_type", "general")
        options = input_data.get("options", {})

        logger.info(f"Performing deep analysis on {len(text)} characters")

        system_prompt = self._get_analysis_prompt(document_type)

        user_message = f"""Analyze this document in depth and provide structured insights:

{text[:6000]}

Provide analysis as JSON with this structure:
{{
  "executive_summary": "High-level overview",
  "key_insights": ["Insight 1", "Insight 2", ...],
  "patterns_identified": ["Pattern 1", ...],
  "recommendations": [
    {{"recommendation": "...", "priority": "HIGH|MEDIUM|LOW", "rationale": "..."}}
  ],
  "risks_and_concerns": [
    {{"risk": "...", "severity": "CRITICAL|HIGH|MEDIUM|LOW", "mitigation": "..."}}
  ],
  "opportunities": ["Opportunity 1", ...],
  "action_priorities": ["Priority 1", ...],
  "confidence_score": 0.85
}}"""

        response = await self.bedrock.invoke_claude(
            user_message=user_message,
            system_prompt=system_prompt,
            max_tokens=3000,
            temperature=0.4,
        )

        # Parse JSON response
        analysis = self._parse_analysis(response["text"])

        return {
            "analysis": analysis,
            "model": response["model_id"],
            "tokens": {
                "input": response["input_tokens"],
                "output": response["output_tokens"],
            },
            "cost": response["cost"],
        }

    def _get_analysis_prompt(self, document_type: str) -> str:
        """Get analysis prompt based on document type."""
        prompts = {
            "project_plan": """You are an expert project management analyst specializing in project plans.
Focus on: Timeline feasibility, resource allocation, dependency management, risk mitigation, success criteria.""",

            "status_report": """You are an expert at analyzing project status reports.
Focus on: Progress tracking, blocker identification, resource utilization, trend analysis, corrective actions.""",

            "meeting_notes": """You are an expert at extracting insights from meeting notes.
Focus on: Decision analysis, action item clarity, stakeholder alignment, follow-up requirements.""",

            "requirements": """You are an expert business analyst reviewing requirements.
Focus on: Completeness, clarity, feasibility, acceptance criteria, potential gaps.""",
        }

        return prompts.get(document_type, """You are an expert document analyst.
Provide deep insights, identify patterns, assess risks, and generate actionable recommendations.""")

    def _parse_analysis(self, response_text: str) -> Dict[str, Any]:
        """Parse analysis JSON from response."""
        try:
            # Remove markdown code blocks
            response_text = re.sub(r'```json?\n?', '', response_text)
            response_text = re.sub(r'```\n?$', '', response_text).strip()

            analysis = json.loads(response_text)
            return analysis

        except json.JSONDecodeError:
            logger.warning("Failed to parse analysis JSON, returning raw text")
            return {
                "executive_summary": response_text,
                "key_insights": [],
                "patterns_identified": [],
                "recommendations": [],
                "risks_and_concerns": [],
                "opportunities": [],
                "confidence_score": 0.5,
            }
