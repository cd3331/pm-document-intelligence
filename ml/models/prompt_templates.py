"""
Advanced Prompt Templates
Dynamic prompt engineering with A/B testing and optimization
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import json
from datetime import datetime


class DocumentType(Enum):
    """Document types"""
    MEETING_NOTES = "meeting_notes"
    PROJECT_PLAN = "project_plan"
    STATUS_REPORT = "status_report"
    TECHNICAL_SPEC = "technical_spec"
    BUSINESS_PROPOSAL = "business_proposal"
    REQUIREMENTS_DOC = "requirements_doc"
    GENERAL = "general"


class PromptTemplate:
    """Base prompt template with versioning"""

    def __init__(
        self,
        template_id: str,
        name: str,
        system_prompt: str,
        user_prompt_template: str,
        version: str = "1.0",
        few_shot_examples: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.template_id = template_id
        self.name = name
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.version = version
        self.few_shot_examples = few_shot_examples or []
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()

    def render(self, **kwargs) -> Dict[str, str]:
        """
        Render prompt with variables

        Args:
            **kwargs: Variables to substitute

        Returns:
            Dict with 'system' and 'user' prompts
        """
        user_prompt = self.user_prompt_template.format(**kwargs)

        # Add few-shot examples if available
        if self.few_shot_examples:
            examples_text = "\n\n".join([
                f"Example {i+1}:\nInput: {ex['input']}\nOutput: {ex['output']}"
                for i, ex in enumerate(self.few_shot_examples)
            ])
            user_prompt = f"{examples_text}\n\n{user_prompt}"

        return {
            "system": self.system_prompt,
            "user": user_prompt
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize template"""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "user_prompt_template": self.user_prompt_template,
            "version": self.version,
            "few_shot_examples": self.few_shot_examples,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class PromptLibrary:
    """
    Centralized library of prompt templates
    """

    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self._initialize_templates()

    def _initialize_templates(self):
        """Initialize all prompt templates"""

        # Executive Summary Templates
        self.templates["executive_summary_short"] = PromptTemplate(
            template_id="exec_summary_short_v1",
            name="Executive Summary (Short)",
            system_prompt="""You are an expert at creating concise executive summaries for project management documents.
Your summaries are clear, actionable, and focused on key decisions and outcomes.""",
            user_prompt_template="""Create a brief executive summary (2-3 sentences) of the following document:

{document_text}

Focus on:
- Main purpose/outcome
- Key decisions
- Critical action items

Summary:""",
            metadata={"max_tokens": 150, "target_length": "2-3 sentences"}
        )

        self.templates["executive_summary_medium"] = PromptTemplate(
            template_id="exec_summary_med_v1",
            name="Executive Summary (Medium)",
            system_prompt="""You are an expert at creating comprehensive executive summaries for project management documents.
Your summaries provide sufficient detail while remaining accessible to senior stakeholders.""",
            user_prompt_template="""Create a comprehensive executive summary (1 paragraph, 5-7 sentences) of the following document:

{document_text}

Include:
- Document purpose and context
- Key findings or decisions
- Important action items
- Notable risks or concerns
- Next steps

Summary:""",
            metadata={"max_tokens": 300, "target_length": "1 paragraph"}
        )

        self.templates["executive_summary_detailed"] = PromptTemplate(
            template_id="exec_summary_detailed_v1",
            name="Executive Summary (Detailed)",
            system_prompt="""You are an expert at creating detailed executive summaries that provide comprehensive overviews
while maintaining clarity and structure.""",
            user_prompt_template="""Create a detailed executive summary of the following document:

{document_text}

Structure your summary with these sections:
1. **Overview**: Purpose and context (2-3 sentences)
2. **Key Points**: Main findings, decisions, or outcomes (bullet points)
3. **Action Items**: Critical next steps (bullet points)
4. **Risks & Concerns**: Important issues to address (if any)
5. **Conclusion**: Overall status and recommendation (1-2 sentences)

Summary:""",
            metadata={"max_tokens": 600, "target_length": "structured format"}
        )

        # Action Item Extraction Templates
        self.templates["action_items_simple"] = PromptTemplate(
            template_id="action_items_simple_v1",
            name="Action Items (Simple List)",
            system_prompt="""You are an expert at identifying action items in project documents.
Extract clear, actionable tasks with owners and deadlines.""",
            user_prompt_template="""Extract all action items from the following document:

{document_text}

For each action item, identify:
- Task description (clear and actionable)
- Owner/responsible person (if mentioned)
- Due date or deadline (if mentioned)
- Priority (if indicated)

Return as JSON array:
[
  {{
    "description": "task description",
    "owner": "person name or null",
    "due_date": "date or null",
    "priority": "high/medium/low or null"
  }}
]

Action Items:""",
            metadata={"output_format": "json", "structured": True}
        )

        self.templates["action_items_categorized"] = PromptTemplate(
            template_id="action_items_cat_v1",
            name="Action Items (Categorized)",
            system_prompt="""You are an expert at organizing action items by category and priority.
Create well-structured, categorized task lists.""",
            user_prompt_template="""Extract and categorize all action items from the following document:

{document_text}

Group action items by category (e.g., Technical, Business, Administrative).
For each item, identify:
- Category
- Description
- Owner
- Due date
- Priority
- Dependencies (if any)

Return as JSON:
{{
  "categories": [
    {{
      "name": "category name",
      "items": [
        {{
          "description": "task",
          "owner": "name",
          "due_date": "date",
          "priority": "level",
          "dependencies": []
        }}
      ]
    }}
  ]
}}

Categorized Action Items:""",
            metadata={"output_format": "json", "structured": True, "categorized": True}
        )

        # Risk Assessment Template
        self.templates["risk_assessment"] = PromptTemplate(
            template_id="risk_assessment_v1",
            name="Risk Assessment",
            system_prompt="""You are an expert project risk analyst. Identify potential risks,
assess their severity, and suggest mitigation strategies.""",
            user_prompt_template="""Analyze the following document for potential risks:

{document_text}

Identify risks in these categories:
- Schedule/Timeline risks
- Resource/Budget risks
- Technical risks
- Stakeholder/Communication risks
- Quality risks

For each risk, provide:
1. Description
2. Likelihood (High/Medium/Low)
3. Impact (High/Medium/Low)
4. Risk Score (Likelihood x Impact)
5. Mitigation strategy

Return as JSON:
{{
  "risks": [
    {{
      "category": "category",
      "description": "risk description",
      "likelihood": "level",
      "impact": "level",
      "score": number,
      "mitigation": "strategy"
    }}
  ],
  "overall_risk_level": "High/Medium/Low"
}}

Risk Assessment:""",
            metadata={"output_format": "json", "structured": True}
        )

        # Q&A with Context Template
        self.templates["qa_with_context"] = PromptTemplate(
            template_id="qa_context_v1",
            name="Q&A with Context",
            system_prompt="""You are a helpful assistant that answers questions about project documents.
Provide accurate answers based only on the given context. If information is not in the context, say so.""",
            user_prompt_template="""Context from document:
{document_text}

Question: {question}

Instructions:
- Answer based only on the provided context
- If the answer is not in the context, say "I don't have enough information to answer that."
- Cite specific parts of the document when possible
- Be concise but complete

Answer:""",
            metadata={"requires_question": True}
        )

        # Multi-Document Synthesis Template
        self.templates["multi_doc_synthesis"] = PromptTemplate(
            template_id="multi_doc_synth_v1",
            name="Multi-Document Synthesis",
            system_prompt="""You are an expert at synthesizing information from multiple documents.
Create coherent summaries that integrate information across sources.""",
            user_prompt_template="""Synthesize information from the following documents:

{documents}

Create a comprehensive synthesis that:
1. Identifies common themes across documents
2. Highlights agreements and disagreements
3. Notes any information gaps or contradictions
4. Provides an integrated timeline if applicable
5. Extracts cross-document action items

Synthesis:""",
            metadata={"multi_document": True}
        )

        # Chain-of-Thought Template for Complex Tasks
        self.templates["cot_complex_analysis"] = PromptTemplate(
            template_id="cot_complex_v1",
            name="Chain-of-Thought Complex Analysis",
            system_prompt="""You are an expert analyst. Use step-by-step reasoning to analyze complex documents.
Show your reasoning process clearly.""",
            user_prompt_template="""Analyze the following document using step-by-step reasoning:

{document_text}

Task: {task_description}

Think through this step-by-step:

Step 1: Identify the main components/sections of the document
Step 2: Analyze each component for relevant information
Step 3: Identify relationships and dependencies
Step 4: Synthesize findings
Step 5: Draw conclusions

Analysis:""",
            metadata={"chain_of_thought": True, "requires_task": True}
        )

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)

    def get_template_for_document_type(
        self,
        task: str,
        document_type: DocumentType
    ) -> Optional[PromptTemplate]:
        """
        Get optimal template for document type and task

        Args:
            task: Task type (summary, action_items, risk, etc.)
            document_type: Document type

        Returns:
            Best template for the combination
        """
        # Mapping of (task, doc_type) -> template_id
        mappings = {
            ("summary", DocumentType.MEETING_NOTES): "executive_summary_medium",
            ("summary", DocumentType.STATUS_REPORT): "executive_summary_detailed",
            ("summary", DocumentType.TECHNICAL_SPEC): "executive_summary_detailed",
            ("summary", DocumentType.GENERAL): "executive_summary_short",

            ("action_items", DocumentType.MEETING_NOTES): "action_items_categorized",
            ("action_items", DocumentType.PROJECT_PLAN): "action_items_categorized",
            ("action_items", DocumentType.GENERAL): "action_items_simple",

            ("risk", DocumentType.PROJECT_PLAN): "risk_assessment",
            ("risk", DocumentType.STATUS_REPORT): "risk_assessment",
            ("risk", DocumentType.TECHNICAL_SPEC): "risk_assessment",
        }

        template_id = mappings.get((task, document_type))
        return self.get_template(template_id) if template_id else None

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates"""
        return [
            {
                "template_id": template.template_id,
                "name": template.name,
                "version": template.version,
                "metadata": template.metadata
            }
            for template in self.templates.values()
        ]


class DynamicPromptAssembler:
    """
    Dynamically assembles prompts based on context
    """

    def __init__(self, library: PromptLibrary):
        self.library = library

    def assemble_prompt(
        self,
        task: str,
        document_text: str,
        document_type: DocumentType = DocumentType.GENERAL,
        few_shot_examples: Optional[List[Dict[str, Any]]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Dynamically assemble optimal prompt

        Args:
            task: Task to perform
            document_text: Document content
            document_type: Type of document
            few_shot_examples: Optional examples
            additional_context: Extra context variables

        Returns:
            Rendered prompt
        """
        # Get base template
        template = self.library.get_template_for_document_type(task, document_type)

        if not template:
            # Fallback to generic template
            template = self.library.get_template("executive_summary_short")

        # Add few-shot examples if provided
        if few_shot_examples:
            template.few_shot_examples = few_shot_examples

        # Prepare render context
        context = {
            "document_text": document_text[:8000],  # Limit context size
            **(additional_context or {})
        }

        return template.render(**context)

    def add_chain_of_thought(self, prompt: Dict[str, str]) -> Dict[str, str]:
        """
        Enhance prompt with chain-of-thought reasoning

        Args:
            prompt: Original prompt

        Returns:
            Enhanced prompt
        """
        cot_instruction = """

Before providing your final answer, think through this step-by-step:
1. What is the main purpose of this document?
2. What are the key pieces of information?
3. How should these be organized in the response?
4. What format would be most useful?

Now provide your answer:"""

        prompt["user"] += cot_instruction
        return prompt


class PromptOptimizationTracker:
    """
    Track prompt performance for optimization
    """

    def __init__(self):
        self.metrics: Dict[str, List[Dict[str, Any]]] = {}

    def record_usage(
        self,
        template_id: str,
        success: bool,
        quality_score: Optional[float] = None,
        cost: Optional[float] = None,
        latency: Optional[float] = None,
        feedback: Optional[str] = None
    ):
        """
        Record prompt usage and performance

        Args:
            template_id: Template identifier
            success: Whether execution succeeded
            quality_score: Quality rating (0-1)
            cost: API cost in dollars
            latency: Response time in seconds
            feedback: User feedback
        """
        if template_id not in self.metrics:
            self.metrics[template_id] = []

        self.metrics[template_id].append({
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
            "quality_score": quality_score,
            "cost": cost,
            "latency": latency,
            "feedback": feedback
        })

    def get_template_performance(self, template_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for a template

        Args:
            template_id: Template identifier

        Returns:
            Performance statistics
        """
        if template_id not in self.metrics:
            return {}

        metrics = self.metrics[template_id]

        success_count = sum(1 for m in metrics if m["success"])
        quality_scores = [m["quality_score"] for m in metrics if m["quality_score"] is not None]
        costs = [m["cost"] for m in metrics if m["cost"] is not None]
        latencies = [m["latency"] for m in metrics if m["latency"] is not None]

        return {
            "template_id": template_id,
            "total_uses": len(metrics),
            "success_rate": success_count / len(metrics) if metrics else 0,
            "avg_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else None,
            "avg_cost": sum(costs) / len(costs) if costs else None,
            "avg_latency": sum(latencies) / len(latencies) if latencies else None,
            "total_cost": sum(costs) if costs else 0
        }

    def compare_templates(self, template_ids: List[str]) -> Dict[str, Any]:
        """
        Compare performance across multiple templates

        Args:
            template_ids: Templates to compare

        Returns:
            Comparison metrics
        """
        comparison = {}

        for template_id in template_ids:
            comparison[template_id] = self.get_template_performance(template_id)

        # Find best performing
        best_quality = max(
            template_ids,
            key=lambda t: comparison[t].get("avg_quality_score", 0)
        )
        best_cost = min(
            template_ids,
            key=lambda t: comparison[t].get("avg_cost", float('inf'))
        )
        best_latency = min(
            template_ids,
            key=lambda t: comparison[t].get("avg_latency", float('inf'))
        )

        return {
            "templates": comparison,
            "best_quality": best_quality,
            "best_cost": best_cost,
            "best_latency": best_latency
        }


# Global instances
_library = PromptLibrary()
_assembler = DynamicPromptAssembler(_library)
_tracker = PromptOptimizationTracker()


def get_prompt_library() -> PromptLibrary:
    """Get global prompt library"""
    return _library


def get_prompt_assembler() -> DynamicPromptAssembler:
    """Get global prompt assembler"""
    return _assembler


def get_optimization_tracker() -> PromptOptimizationTracker:
    """Get global optimization tracker"""
    return _tracker
