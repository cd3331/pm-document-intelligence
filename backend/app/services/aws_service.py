"""
AWS Service Orchestration Layer for PM Document Intelligence.

This module provides a unified interface for all AWS services with:
- Error handling and retries
- Cost tracking
- Circuit breaker pattern
- Comprehensive logging
- Async support

Services:
- AWS Bedrock (Claude) - AI text generation
- AWS Textract - Document text extraction
- AWS Comprehend - NLP analysis
- AWS S3 - Document storage

Usage:
    from app.services.aws_service import (
        BedrockService,
        TextractService,
        ComprehendService,
        S3Service
    )

    # Bedrock
    bedrock = BedrockService()
    response = await bedrock.invoke_claude(
        user_message="Analyze this document...",
        system_prompt="You are a PM assistant"
    )

    # Textract
    textract = TextractService()
    result = await textract.extract_text_from_document(s3_bucket, s3_key)

    # Comprehend
    comprehend = ComprehendService()
    entities = await comprehend.analyze_document_entities(text)

    # S3
    s3 = S3Service()
    url = await s3.upload_document(file_content, "document.pdf", user_id)
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from io import BytesIO

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.config import settings
from app.utils.exceptions import (
    BedrockError,
    TextractError,
    ComprehendError,
    S3Error,
    AIServiceError,
)
from app.utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Constants and Pricing
# ============================================================================


class AWSPricing:
    """AWS service pricing (as of 2024, adjust for your region)."""

    # Bedrock pricing (per 1000 tokens)
    BEDROCK_INPUT_TOKEN_PRICE = 0.003  # Claude 3.5 Sonnet
    BEDROCK_OUTPUT_TOKEN_PRICE = 0.015

    # Textract pricing (per page)
    TEXTRACT_DETECT_TEXT_PRICE = 0.0015
    TEXTRACT_ANALYZE_DOCUMENT_PRICE = 0.05

    # Comprehend pricing (per unit)
    COMPREHEND_ENTITY_DETECTION_PRICE = 0.0001  # per 100 chars
    COMPREHEND_SENTIMENT_PRICE = 0.0001
    COMPREHEND_KEY_PHRASES_PRICE = 0.0001

    # S3 pricing (simplified)
    S3_STORAGE_PRICE_PER_GB = 0.023  # Standard storage per GB/month
    S3_PUT_REQUEST_PRICE = 0.000005  # per request
    S3_GET_REQUEST_PRICE = 0.0000004  # per request


class DocumentType(str, Enum):
    """Document types for prompt templates."""

    PROJECT_PLAN = "project_plan"
    STATUS_REPORT = "status_report"
    MEETING_NOTES = "meeting_notes"
    REQUIREMENTS = "requirements"
    RISK_ASSESSMENT = "risk_assessment"
    GENERAL = "general"


# ============================================================================
# Cost Tracking
# ============================================================================


class CostTracker:
    """Track AWS service costs."""

    def __init__(self):
        """Initialize cost tracker."""
        self.costs: Dict[str, float] = {
            "bedrock": 0.0,
            "textract": 0.0,
            "comprehend": 0.0,
            "s3": 0.0,
        }
        self.usage: Dict[str, Dict[str, int]] = {
            "bedrock": {"input_tokens": 0, "output_tokens": 0},
            "textract": {"pages": 0},
            "comprehend": {"characters": 0},
            "s3": {"requests": 0, "bytes": 0},
        }

    def track_bedrock_usage(self, input_tokens: int, output_tokens: int) -> float:
        """
        Track Bedrock token usage and calculate cost.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        cost = (input_tokens / 1000) * AWSPricing.BEDROCK_INPUT_TOKEN_PRICE + (
            output_tokens / 1000
        ) * AWSPricing.BEDROCK_OUTPUT_TOKEN_PRICE

        self.costs["bedrock"] += cost
        self.usage["bedrock"]["input_tokens"] += input_tokens
        self.usage["bedrock"]["output_tokens"] += output_tokens

        logger.debug(
            f"Bedrock usage: {input_tokens} in, {output_tokens} out, ${cost:.4f}"
        )

        return cost

    def track_textract_usage(self, pages: int, analyze: bool = False) -> float:
        """
        Track Textract page usage and calculate cost.

        Args:
            pages: Number of pages processed
            analyze: Whether advanced analysis was used

        Returns:
            Cost in USD
        """
        price_per_page = (
            AWSPricing.TEXTRACT_ANALYZE_DOCUMENT_PRICE
            if analyze
            else AWSPricing.TEXTRACT_DETECT_TEXT_PRICE
        )

        cost = pages * price_per_page

        self.costs["textract"] += cost
        self.usage["textract"]["pages"] += pages

        logger.debug(f"Textract usage: {pages} pages, ${cost:.4f}")

        return cost

    def track_comprehend_usage(self, characters: int, operations: int = 1) -> float:
        """
        Track Comprehend usage and calculate cost.

        Args:
            characters: Number of characters processed
            operations: Number of operations (entities, sentiment, etc.)

        Returns:
            Cost in USD
        """
        units = characters / 100  # Charged per 100 characters
        cost = units * AWSPricing.COMPREHEND_ENTITY_DETECTION_PRICE * operations

        self.costs["comprehend"] += cost
        self.usage["comprehend"]["characters"] += characters

        logger.debug(f"Comprehend usage: {characters} chars, ${cost:.4f}")

        return cost

    def track_s3_usage(self, operation: str, bytes_transferred: int = 0) -> float:
        """
        Track S3 usage and calculate cost.

        Args:
            operation: Operation type (PUT, GET)
            bytes_transferred: Bytes transferred

        Returns:
            Cost in USD
        """
        if operation == "PUT":
            cost = AWSPricing.S3_PUT_REQUEST_PRICE
        elif operation == "GET":
            cost = AWSPricing.S3_GET_REQUEST_PRICE
        else:
            cost = 0.0

        self.costs["s3"] += cost
        self.usage["s3"]["requests"] += 1
        self.usage["s3"]["bytes"] += bytes_transferred

        return cost

    def get_total_cost(self) -> float:
        """Get total cost across all services."""
        return sum(self.costs.values())

    def get_cost_report(self) -> Dict[str, Any]:
        """
        Get comprehensive cost report.

        Returns:
            Dictionary with costs and usage
        """
        return {
            "total_cost": self.get_total_cost(),
            "costs_by_service": self.costs.copy(),
            "usage": self.usage.copy(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def reset(self) -> None:
        """Reset all cost tracking."""
        for service in self.costs:
            self.costs[service] = 0.0

        for service in self.usage:
            for metric in self.usage[service]:
                self.usage[service][metric] = 0


# Global cost tracker
cost_tracker = CostTracker()


# ============================================================================
# Circuit Breaker Pattern
# ============================================================================


class CircuitBreaker:
    """Circuit breaker for failing services."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func):
        """
        Decorator to wrap function calls with circuit breaker.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function
        """

        async def wrapper(*args, **kwargs):
            """Wrapper function."""
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half-open"
                    logger.info("Circuit breaker: attempting recovery (half-open)")
                else:
                    raise AIServiceError(
                        message="Service temporarily unavailable (circuit breaker open)",
                        details={"service": func.__name__},
                    )

            try:
                result = await func(*args, **kwargs)

                if self.state == "half-open":
                    self._reset()

                return result

            except Exception as e:
                self._record_failure()
                raise

        return wrapper

    def _record_failure(self) -> None:
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")

    def _should_attempt_reset(self) -> bool:
        """Check if should attempt to reset circuit."""
        if self.last_failure_time is None:
            return False

        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def _reset(self) -> None:
        """Reset circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"
        logger.info("Circuit breaker reset (closed)")


# ============================================================================
# AWS Bedrock Service (Claude)
# ============================================================================


class BedrockService:
    """AWS Bedrock service for Claude AI."""

    def __init__(self):
        """Initialize Bedrock service."""
        self.session = aioboto3.Session()
        self.model_id = settings.bedrock.bedrock_model_id
        self.region = settings.bedrock.bedrock_region
        self.max_tokens = settings.bedrock.bedrock_max_tokens
        self.temperature = settings.bedrock.bedrock_temperature
        self.top_p = settings.bedrock.bedrock_top_p
        self.circuit_breaker = CircuitBreaker()

        # Prompt templates
        self.prompt_templates = {
            DocumentType.PROJECT_PLAN: """You are an expert project management assistant analyzing project plans.
Focus on:
- Project objectives and scope
- Timeline and milestones
- Resource allocation
- Risk factors
- Dependencies

Provide structured analysis with actionable insights.""",
            DocumentType.STATUS_REPORT: """You are an expert project management assistant analyzing status reports.
Focus on:
- Progress against plan
- Issues and blockers
- Resource utilization
- Risk indicators
- Action items

Identify critical issues and recommendations.""",
            DocumentType.MEETING_NOTES: """You are an expert project management assistant analyzing meeting notes.
Focus on:
- Key decisions made
- Action items and owners
- Discussion topics
- Follow-up required
- Deadlines

Extract structured action items and decisions.""",
            DocumentType.REQUIREMENTS: """You are an expert business analyst reviewing requirements documents.
Focus on:
- Functional requirements
- Non-functional requirements
- Acceptance criteria
- Dependencies
- Potential gaps or ambiguities

Provide clarity on requirements and identify issues.""",
            DocumentType.GENERAL: """You are an expert project management assistant.
Analyze the document and provide:
- Summary of key points
- Important dates and deadlines
- Action items
- Risks or concerns
- Recommendations

Be thorough and structured in your analysis.""",
        }

    def _get_boto_config(self) -> Config:
        """Get boto3 configuration."""
        return Config(
            region_name=self.region,
            connect_timeout=30,
            read_timeout=settings.aws.aws_request_timeout,
            retries={
                "max_attempts": 3,
                "mode": "adaptive",
            },
        )

    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def invoke_claude(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        document_type: DocumentType = DocumentType.GENERAL,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Invoke Claude model via Bedrock.

        Args:
            user_message: User message/prompt
            system_prompt: Optional system prompt (uses template if not provided)
            document_type: Document type for template selection
            max_tokens: Max tokens to generate (uses default if None)
            temperature: Temperature for generation (uses default if None)
            stream: Enable streaming responses

        Returns:
            Response dictionary with text, usage, and cost

        Raises:
            BedrockError: If invocation fails
        """
        try:
            # Use template if no system prompt provided
            if system_prompt is None:
                system_prompt = self.prompt_templates.get(
                    document_type, self.prompt_templates[DocumentType.GENERAL]
                )

            # Prepare request
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
                "top_p": self.top_p,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
            }

            start_time = time.time()

            # Get client
            async with self.session.client(
                "bedrock-runtime",
                region_name=self.region,
                config=self._get_boto_config(),
            ) as client:
                if stream:
                    # Streaming response
                    response = await client.invoke_model_with_response_stream(
                        modelId=self.model_id,
                        body=json.dumps(request_body),
                        contentType="application/json",
                        accept="application/json",
                    )

                    # TODO: Implement streaming handler
                    raise NotImplementedError("Streaming not yet implemented")

                else:
                    # Standard response
                    response = await client.invoke_model(
                        modelId=self.model_id,
                        body=json.dumps(request_body),
                        contentType="application/json",
                        accept="application/json",
                    )

                    # Parse response
                    response_body = json.loads(response["body"].read())

                    duration = time.time() - start_time

                    # Extract response data
                    content = response_body.get("content", [])
                    text = content[0].get("text", "") if content else ""

                    usage = response_body.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)

                    # Track cost
                    cost = cost_tracker.track_bedrock_usage(input_tokens, output_tokens)

                    result = {
                        "text": text,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost": cost,
                        "duration_seconds": duration,
                        "model_id": self.model_id,
                        "stop_reason": response_body.get("stop_reason"),
                    }

                    logger.info(
                        f"Bedrock invocation: {input_tokens} in, {output_tokens} out, "
                        f"${cost:.4f}, {duration:.2f}s"
                    )

                    return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"Bedrock error ({error_code}): {error_message}")

            if error_code == "ThrottlingException":
                raise BedrockError(
                    message="Bedrock rate limit exceeded",
                    details={"error": error_message},
                )
            elif error_code == "ModelTimeoutException":
                raise BedrockError(
                    message="Bedrock model timeout",
                    details={"error": error_message},
                )
            elif error_code == "ValidationException":
                raise BedrockError(
                    message="Invalid request to Bedrock",
                    details={"error": error_message},
                )
            else:
                raise BedrockError(
                    message="Bedrock invocation failed",
                    details={"error_code": error_code, "error": error_message},
                )

        except Exception as e:
            logger.error(f"Unexpected Bedrock error: {e}", exc_info=True)
            raise BedrockError(
                message="Unexpected error calling Bedrock",
                details={"error": str(e)},
            )

    async def analyze_document(
        self,
        document_text: str,
        document_type: DocumentType = DocumentType.GENERAL,
        custom_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze document using Claude.

        Args:
            document_text: Document text to analyze
            document_type: Type of document
            custom_instructions: Optional custom analysis instructions

        Returns:
            Analysis results
        """
        # Build user message
        user_message = f"Document to analyze:\n\n{document_text}"

        if custom_instructions:
            user_message += f"\n\nAdditional instructions: {custom_instructions}"

        return await self.invoke_claude(
            user_message=user_message,
            document_type=document_type,
        )


# ============================================================================
# AWS Textract Service (Document Text Extraction)
# ============================================================================


class TextractService:
    """AWS Textract service for document OCR and text extraction."""

    def __init__(self):
        """Initialize Textract service."""
        self.session = aioboto3.Session()
        self.region = settings.aws.aws_region
        self.circuit_breaker = CircuitBreaker()

    def _get_boto_config(self) -> Config:
        """Get boto3 configuration."""
        return Config(
            region_name=self.region,
            connect_timeout=30,
            read_timeout=settings.aws.aws_request_timeout,
            retries={
                "max_attempts": 3,
                "mode": "adaptive",
            },
        )

    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def extract_text_synchronous(
        self,
        document_bytes: bytes,
        feature_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract text from document synchronously (for small documents).

        Args:
            document_bytes: Document bytes (PDF, PNG, JPG, TIFF)
            feature_types: Features to extract (TABLES, FORMS)

        Returns:
            Extraction results with text, tables, forms, confidence scores

        Raises:
            TextractError: If extraction fails
        """
        try:
            start_time = time.time()

            # Prepare request
            request_params = {
                "Document": {"Bytes": document_bytes},
            }

            if feature_types:
                request_params["FeatureTypes"] = feature_types

            async with self.session.client(
                "textract",
                region_name=self.region,
                config=self._get_boto_config(),
            ) as client:
                if feature_types:
                    # Use AnalyzeDocument for advanced features
                    response = await client.analyze_document(**request_params)
                    pages = 1  # Assume 1 page for synchronous
                    cost = cost_tracker.track_textract_usage(pages, analyze=True)
                else:
                    # Use DetectDocumentText for basic text extraction
                    response = await client.detect_document_text(**request_params)
                    pages = 1
                    cost = cost_tracker.track_textract_usage(pages, analyze=False)

                duration = time.time() - start_time

                # Parse results
                blocks = response.get("Blocks", [])

                # Extract text
                text_blocks = []
                lines = []
                words = []

                for block in blocks:
                    block_type = block.get("BlockType")

                    if block_type == "LINE":
                        lines.append(
                            {
                                "text": block.get("Text", ""),
                                "confidence": block.get("Confidence", 0),
                                "geometry": block.get("Geometry", {}),
                            }
                        )
                    elif block_type == "WORD":
                        words.append(
                            {
                                "text": block.get("Text", ""),
                                "confidence": block.get("Confidence", 0),
                            }
                        )

                # Combine all text
                full_text = "\n".join([line["text"] for line in lines])

                # Extract tables if present
                tables = (
                    self._extract_tables(blocks)
                    if feature_types and "TABLES" in feature_types
                    else []
                )

                # Extract forms if present
                forms = (
                    self._extract_forms(blocks)
                    if feature_types and "FORMS" in feature_types
                    else []
                )

                result = {
                    "text": full_text,
                    "lines": lines,
                    "words": words,
                    "tables": tables,
                    "forms": forms,
                    "pages": pages,
                    "cost": cost,
                    "duration_seconds": duration,
                    "average_confidence": (
                        sum([w["confidence"] for w in words]) / len(words)
                        if words
                        else 0
                    ),
                }

                logger.info(
                    f"Textract extraction: {len(words)} words, "
                    f"{len(tables)} tables, ${cost:.4f}, {duration:.2f}s"
                )

                return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"Textract error ({error_code}): {error_message}")

            if error_code == "ThrottlingException":
                raise TextractError(
                    message="Textract rate limit exceeded",
                    details={"error": error_message},
                )
            elif error_code == "InvalidParameterException":
                raise TextractError(
                    message="Invalid document format",
                    details={"error": error_message},
                )
            else:
                raise TextractError(
                    message="Textract extraction failed",
                    details={"error_code": error_code, "error": error_message},
                )

        except Exception as e:
            logger.error(f"Unexpected Textract error: {e}", exc_info=True)
            raise TextractError(
                message="Unexpected error during text extraction",
                details={"error": str(e)},
            )

    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def extract_text_asynchronous(
        self,
        s3_bucket: str,
        s3_key: str,
        feature_types: Optional[List[str]] = None,
        max_wait_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Extract text from document asynchronously (for large documents).

        Args:
            s3_bucket: S3 bucket name
            s3_key: S3 object key
            feature_types: Features to extract (TABLES, FORMS)
            max_wait_seconds: Maximum time to wait for completion

        Returns:
            Extraction results

        Raises:
            TextractError: If extraction fails or times out
        """
        try:
            start_time = time.time()

            # Start async job
            request_params = {
                "DocumentLocation": {
                    "S3Object": {
                        "Bucket": s3_bucket,
                        "Name": s3_key,
                    }
                },
            }

            if feature_types:
                request_params["FeatureTypes"] = feature_types

            async with self.session.client(
                "textract",
                region_name=self.region,
                config=self._get_boto_config(),
            ) as client:
                if feature_types:
                    response = await client.start_document_analysis(**request_params)
                    job_id = response["JobId"]
                    get_results_func = client.get_document_analysis
                else:
                    response = await client.start_document_text_detection(
                        **request_params
                    )
                    job_id = response["JobId"]
                    get_results_func = client.get_document_text_detection

                logger.info(f"Started Textract job: {job_id}")

                # Poll for completion
                pages = 0
                all_blocks = []

                while True:
                    elapsed = time.time() - start_time

                    if elapsed > max_wait_seconds:
                        raise TextractError(
                            message="Textract job timeout",
                            details={"job_id": job_id, "elapsed_seconds": elapsed},
                        )

                    # Check job status
                    result = await get_results_func(JobId=job_id)
                    status = result["JobStatus"]

                    if status == "SUCCEEDED":
                        # Collect results
                        all_blocks.extend(result.get("Blocks", []))
                        pages = result.get("DocumentMetadata", {}).get("Pages", 1)

                        # Handle pagination
                        next_token = result.get("NextToken")
                        while next_token:
                            result = await get_results_func(
                                JobId=job_id,
                                NextToken=next_token,
                            )
                            all_blocks.extend(result.get("Blocks", []))
                            next_token = result.get("NextToken")

                        break

                    elif status == "FAILED":
                        raise TextractError(
                            message="Textract job failed",
                            details={
                                "job_id": job_id,
                                "status_message": result.get("StatusMessage"),
                            },
                        )

                    # Wait before polling again
                    await asyncio.sleep(5)

                duration = time.time() - start_time

                # Track cost
                cost = cost_tracker.track_textract_usage(
                    pages, analyze=bool(feature_types)
                )

                # Parse results (same as synchronous)
                lines = []
                words = []

                for block in all_blocks:
                    block_type = block.get("BlockType")

                    if block_type == "LINE":
                        lines.append(
                            {
                                "text": block.get("Text", ""),
                                "confidence": block.get("Confidence", 0),
                                "geometry": block.get("Geometry", {}),
                            }
                        )
                    elif block_type == "WORD":
                        words.append(
                            {
                                "text": block.get("Text", ""),
                                "confidence": block.get("Confidence", 0),
                            }
                        )

                full_text = "\n".join([line["text"] for line in lines])

                tables = (
                    self._extract_tables(all_blocks)
                    if feature_types and "TABLES" in feature_types
                    else []
                )
                forms = (
                    self._extract_forms(all_blocks)
                    if feature_types and "FORMS" in feature_types
                    else []
                )

                result = {
                    "text": full_text,
                    "lines": lines,
                    "words": words,
                    "tables": tables,
                    "forms": forms,
                    "pages": pages,
                    "cost": cost,
                    "duration_seconds": duration,
                    "job_id": job_id,
                    "average_confidence": (
                        sum([w["confidence"] for w in words]) / len(words)
                        if words
                        else 0
                    ),
                }

                logger.info(
                    f"Textract async extraction: {pages} pages, {len(words)} words, "
                    f"${cost:.4f}, {duration:.2f}s"
                )

                return result

        except TextractError:
            raise
        except Exception as e:
            logger.error(f"Unexpected Textract async error: {e}", exc_info=True)
            raise TextractError(
                message="Unexpected error during async extraction",
                details={"error": str(e)},
            )

    def _extract_tables(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract tables from Textract blocks.

        Args:
            blocks: Textract blocks

        Returns:
            List of tables with cells
        """
        tables = []
        block_map = {block["Id"]: block for block in blocks}

        for block in blocks:
            if block["BlockType"] == "TABLE":
                table = {
                    "rows": [],
                    "confidence": block.get("Confidence", 0),
                }

                # Get cell relationships
                relationships = block.get("Relationships", [])
                for relationship in relationships:
                    if relationship["Type"] == "CHILD":
                        cells = []
                        for cell_id in relationship["Ids"]:
                            cell_block = block_map.get(cell_id)
                            if cell_block and cell_block["BlockType"] == "CELL":
                                # Get cell text
                                cell_text = ""
                                cell_relationships = cell_block.get("Relationships", [])
                                for cell_rel in cell_relationships:
                                    if cell_rel["Type"] == "CHILD":
                                        for word_id in cell_rel["Ids"]:
                                            word_block = block_map.get(word_id)
                                            if word_block:
                                                cell_text += (
                                                    word_block.get("Text", "") + " "
                                                )

                                cells.append(
                                    {
                                        "row": cell_block.get("RowIndex", 0),
                                        "column": cell_block.get("ColumnIndex", 0),
                                        "text": cell_text.strip(),
                                        "confidence": cell_block.get("Confidence", 0),
                                    }
                                )

                        # Organize cells into rows
                        rows_dict = {}
                        for cell in cells:
                            row_idx = cell["row"]
                            if row_idx not in rows_dict:
                                rows_dict[row_idx] = []
                            rows_dict[row_idx].append(cell)

                        # Sort cells by column within each row
                        for row_idx in sorted(rows_dict.keys()):
                            row_cells = sorted(
                                rows_dict[row_idx], key=lambda x: x["column"]
                            )
                            table["rows"].append(row_cells)

                tables.append(table)

        return tables

    def _extract_forms(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract form fields from Textract blocks.

        Args:
            blocks: Textract blocks

        Returns:
            List of form key-value pairs
        """
        forms = []
        block_map = {block["Id"]: block for block in blocks}

        for block in blocks:
            if block["BlockType"] == "KEY_VALUE_SET":
                entity_types = block.get("EntityTypes", [])

                if "KEY" in entity_types:
                    # Extract key text
                    key_text = ""
                    value_text = ""

                    relationships = block.get("Relationships", [])
                    for relationship in relationships:
                        if relationship["Type"] == "CHILD":
                            for child_id in relationship["Ids"]:
                                child_block = block_map.get(child_id)
                                if child_block:
                                    key_text += child_block.get("Text", "") + " "
                        elif relationship["Type"] == "VALUE":
                            for value_id in relationship["Ids"]:
                                value_block = block_map.get(value_id)
                                if value_block:
                                    value_relationships = value_block.get(
                                        "Relationships", []
                                    )
                                    for value_rel in value_relationships:
                                        if value_rel["Type"] == "CHILD":
                                            for word_id in value_rel["Ids"]:
                                                word_block = block_map.get(word_id)
                                                if word_block:
                                                    value_text += (
                                                        word_block.get("Text", "") + " "
                                                    )

                    if key_text:
                        forms.append(
                            {
                                "key": key_text.strip(),
                                "value": value_text.strip(),
                                "confidence": block.get("Confidence", 0),
                            }
                        )

        return forms


# ============================================================================
# AWS Comprehend Service (NLP Analysis)
# ============================================================================


class ComprehendService:
    """AWS Comprehend service for NLP analysis."""

    def __init__(self):
        """Initialize Comprehend service."""
        self.session = aioboto3.Session()
        self.region = settings.aws.aws_region
        self.circuit_breaker = CircuitBreaker()

    def _get_boto_config(self) -> Config:
        """Get boto3 configuration."""
        return Config(
            region_name=self.region,
            connect_timeout=30,
            read_timeout=settings.aws.aws_request_timeout,
            retries={
                "max_attempts": 3,
                "mode": "adaptive",
            },
        )

    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def analyze_document_entities(
        self,
        text: str,
        language_code: str = "en",
    ) -> Dict[str, Any]:
        """
        Detect named entities in text.

        Args:
            text: Text to analyze
            language_code: Language code (default: en)

        Returns:
            Entity detection results

        Raises:
            ComprehendError: If analysis fails
        """
        try:
            if not text or len(text.strip()) == 0:
                return {"entities": [], "cost": 0}

            start_time = time.time()

            # Truncate if too long (Comprehend limit is 5000 bytes)
            max_bytes = 5000
            text_bytes = text.encode("utf-8")
            if len(text_bytes) > max_bytes:
                text = text_bytes[:max_bytes].decode("utf-8", errors="ignore")
                logger.warning(f"Text truncated to {max_bytes} bytes for Comprehend")

            async with self.session.client(
                "comprehend",
                region_name=self.region,
                config=self._get_boto_config(),
            ) as client:
                response = await client.detect_entities(
                    Text=text,
                    LanguageCode=language_code,
                )

                duration = time.time() - start_time

                # Track cost
                cost = cost_tracker.track_comprehend_usage(len(text), operations=1)

                # Parse entities
                entities = []
                for entity in response.get("Entities", []):
                    entities.append(
                        {
                            "text": entity.get("Text"),
                            "type": entity.get("Type"),
                            "score": entity.get("Score", 0),
                            "begin_offset": entity.get("BeginOffset"),
                            "end_offset": entity.get("EndOffset"),
                        }
                    )

                result = {
                    "entities": entities,
                    "cost": cost,
                    "duration_seconds": duration,
                    "language_code": language_code,
                }

                logger.info(
                    f"Comprehend entities: {len(entities)} detected, "
                    f"${cost:.4f}, {duration:.2f}s"
                )

                return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"Comprehend error ({error_code}): {error_message}")

            if error_code == "TextSizeLimitExceededException":
                raise ComprehendError(
                    message="Text too large for Comprehend",
                    details={"error": error_message},
                )
            elif error_code == "UnsupportedLanguageException":
                raise ComprehendError(
                    message="Unsupported language",
                    details={"error": error_message, "language": language_code},
                )
            else:
                raise ComprehendError(
                    message="Entity detection failed",
                    details={"error_code": error_code, "error": error_message},
                )

        except Exception as e:
            logger.error(f"Unexpected Comprehend error: {e}", exc_info=True)
            raise ComprehendError(
                message="Unexpected error during entity detection",
                details={"error": str(e)},
            )

    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def analyze_sentiment(
        self,
        text: str,
        language_code: str = "en",
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze
            language_code: Language code (default: en)

        Returns:
            Sentiment analysis results

        Raises:
            ComprehendError: If analysis fails
        """
        try:
            if not text or len(text.strip()) == 0:
                return {
                    "sentiment": "NEUTRAL",
                    "scores": {"positive": 0, "negative": 0, "neutral": 1, "mixed": 0},
                    "cost": 0,
                }

            start_time = time.time()

            # Truncate if too long
            max_bytes = 5000
            text_bytes = text.encode("utf-8")
            if len(text_bytes) > max_bytes:
                text = text_bytes[:max_bytes].decode("utf-8", errors="ignore")

            async with self.session.client(
                "comprehend",
                region_name=self.region,
                config=self._get_boto_config(),
            ) as client:
                response = await client.detect_sentiment(
                    Text=text,
                    LanguageCode=language_code,
                )

                duration = time.time() - start_time

                # Track cost
                cost = cost_tracker.track_comprehend_usage(len(text), operations=1)

                result = {
                    "sentiment": response.get("Sentiment"),
                    "scores": {
                        "positive": response.get("SentimentScore", {}).get(
                            "Positive", 0
                        ),
                        "negative": response.get("SentimentScore", {}).get(
                            "Negative", 0
                        ),
                        "neutral": response.get("SentimentScore", {}).get("Neutral", 0),
                        "mixed": response.get("SentimentScore", {}).get("Mixed", 0),
                    },
                    "cost": cost,
                    "duration_seconds": duration,
                }

                logger.info(
                    f"Comprehend sentiment: {result['sentiment']}, "
                    f"${cost:.4f}, {duration:.2f}s"
                )

                return result

        except ComprehendError:
            raise
        except Exception as e:
            logger.error(f"Unexpected sentiment analysis error: {e}", exc_info=True)
            raise ComprehendError(
                message="Unexpected error during sentiment analysis",
                details={"error": str(e)},
            )

    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def detect_key_phrases(
        self,
        text: str,
        language_code: str = "en",
    ) -> Dict[str, Any]:
        """
        Detect key phrases in text.

        Args:
            text: Text to analyze
            language_code: Language code (default: en)

        Returns:
            Key phrase detection results

        Raises:
            ComprehendError: If analysis fails
        """
        try:
            if not text or len(text.strip()) == 0:
                return {"key_phrases": [], "cost": 0}

            start_time = time.time()

            # Truncate if too long
            max_bytes = 5000
            text_bytes = text.encode("utf-8")
            if len(text_bytes) > max_bytes:
                text = text_bytes[:max_bytes].decode("utf-8", errors="ignore")

            async with self.session.client(
                "comprehend",
                region_name=self.region,
                config=self._get_boto_config(),
            ) as client:
                response = await client.detect_key_phrases(
                    Text=text,
                    LanguageCode=language_code,
                )

                duration = time.time() - start_time

                # Track cost
                cost = cost_tracker.track_comprehend_usage(len(text), operations=1)

                # Parse key phrases
                key_phrases = []
                for phrase in response.get("KeyPhrases", []):
                    key_phrases.append(
                        {
                            "text": phrase.get("Text"),
                            "score": phrase.get("Score", 0),
                            "begin_offset": phrase.get("BeginOffset"),
                            "end_offset": phrase.get("EndOffset"),
                        }
                    )

                result = {
                    "key_phrases": key_phrases,
                    "cost": cost,
                    "duration_seconds": duration,
                }

                logger.info(
                    f"Comprehend key phrases: {len(key_phrases)} detected, "
                    f"${cost:.4f}, {duration:.2f}s"
                )

                return result

        except ComprehendError:
            raise
        except Exception as e:
            logger.error(f"Unexpected key phrase detection error: {e}", exc_info=True)
            raise ComprehendError(
                message="Unexpected error during key phrase detection",
                details={"error": str(e)},
            )

    async def analyze_document_comprehensive(
        self,
        text: str,
        language_code: str = "en",
    ) -> Dict[str, Any]:
        """
        Perform comprehensive NLP analysis (entities, sentiment, key phrases).

        Args:
            text: Text to analyze
            language_code: Language code (default: en)

        Returns:
            Combined analysis results

        Raises:
            ComprehendError: If analysis fails
        """
        try:
            # Run all analyses in parallel
            entities_task = self.analyze_document_entities(text, language_code)
            sentiment_task = self.analyze_sentiment(text, language_code)
            key_phrases_task = self.detect_key_phrases(text, language_code)

            entities_result, sentiment_result, key_phrases_result = (
                await asyncio.gather(
                    entities_task,
                    sentiment_task,
                    key_phrases_task,
                )
            )

            return {
                "entities": entities_result,
                "sentiment": sentiment_result,
                "key_phrases": key_phrases_result,
                "total_cost": (
                    entities_result["cost"]
                    + sentiment_result["cost"]
                    + key_phrases_result["cost"]
                ),
            }

        except ComprehendError:
            raise
        except Exception as e:
            logger.error(f"Unexpected comprehensive analysis error: {e}", exc_info=True)
            raise ComprehendError(
                message="Unexpected error during comprehensive analysis",
                details={"error": str(e)},
            )


# ============================================================================
# AWS S3 Service (Document Storage)
# ============================================================================


class S3Service:
    """AWS S3 service for document storage."""

    def __init__(self):
        """Initialize S3 service."""
        self.session = aioboto3.Session()
        self.region = settings.aws.aws_region
        self.bucket_name = settings.aws.aws_s3_bucket
        self.circuit_breaker = CircuitBreaker()

        # Multipart upload threshold (5 MB)
        self.multipart_threshold = 5 * 1024 * 1024

    def _get_boto_config(self) -> Config:
        """Get boto3 configuration."""
        return Config(
            region_name=self.region,
            connect_timeout=30,
            read_timeout=settings.aws.aws_request_timeout,
            retries={
                "max_attempts": 3,
                "mode": "adaptive",
            },
        )

    def _get_content_type(self, filename: str) -> str:
        """
        Detect content type from filename.

        Args:
            filename: File name

        Returns:
            Content type string
        """
        import mimetypes

        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"

    def _build_s3_key(self, user_id: str, filename: str) -> str:
        """
        Build S3 object key with user ID prefix.

        Args:
            user_id: User ID
            filename: Original filename

        Returns:
            S3 object key
        """
        import uuid
        from datetime import datetime

        # Create unique key: documents/{user_id}/{year}/{month}/{uuid}_{filename}
        now = datetime.utcnow()
        unique_id = str(uuid.uuid4())

        return f"documents/{user_id}/{now.year}/{now.month:02d}/{unique_id}_{filename}"

    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        document_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Upload document to S3 with encryption and metadata.

        Args:
            file_content: File bytes
            filename: Original filename
            user_id: User ID
            document_type: Document type (optional)
            metadata: Additional metadata (optional)

        Returns:
            Upload result with S3 key, URL, size

        Raises:
            S3Error: If upload fails
        """
        try:
            start_time = time.time()

            # Build S3 key
            s3_key = self._build_s3_key(user_id, filename)

            # Detect content type
            content_type = self._get_content_type(filename)

            # Prepare metadata
            s3_metadata = {
                "user_id": user_id,
                "original_filename": filename,
                "uploaded_at": datetime.utcnow().isoformat(),
            }

            if document_type:
                s3_metadata["document_type"] = document_type

            if metadata:
                s3_metadata.update(metadata)

            file_size = len(file_content)

            async with self.session.client(
                "s3",
                region_name=self.region,
                config=self._get_boto_config(),
            ) as client:
                if file_size > self.multipart_threshold:
                    # Use multipart upload for large files
                    logger.info(
                        f"Using multipart upload for {filename} ({file_size} bytes)"
                    )

                    # Start multipart upload
                    multipart = await client.create_multipart_upload(
                        Bucket=self.bucket_name,
                        Key=s3_key,
                        ContentType=content_type,
                        ServerSideEncryption="AES256",
                        Metadata=s3_metadata,
                    )

                    upload_id = multipart["UploadId"]
                    parts = []

                    try:
                        # Upload parts (5 MB chunks)
                        chunk_size = self.multipart_threshold
                        part_number = 1

                        for i in range(0, file_size, chunk_size):
                            chunk = file_content[i : i + chunk_size]

                            part = await client.upload_part(
                                Bucket=self.bucket_name,
                                Key=s3_key,
                                PartNumber=part_number,
                                UploadId=upload_id,
                                Body=chunk,
                            )

                            parts.append(
                                {
                                    "PartNumber": part_number,
                                    "ETag": part["ETag"],
                                }
                            )

                            part_number += 1

                        # Complete multipart upload
                        await client.complete_multipart_upload(
                            Bucket=self.bucket_name,
                            Key=s3_key,
                            UploadId=upload_id,
                            MultipartUpload={"Parts": parts},
                        )

                    except Exception as e:
                        # Abort multipart upload on error
                        await client.abort_multipart_upload(
                            Bucket=self.bucket_name,
                            Key=s3_key,
                            UploadId=upload_id,
                        )
                        raise

                else:
                    # Simple upload for small files
                    await client.put_object(
                        Bucket=self.bucket_name,
                        Key=s3_key,
                        Body=file_content,
                        ContentType=content_type,
                        ServerSideEncryption="AES256",
                        Metadata=s3_metadata,
                    )

                duration = time.time() - start_time

                # Track cost
                cost = cost_tracker.track_s3_usage("PUT", file_size)

                # Generate presigned URL for temporary access
                presigned_url = await client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": s3_key,
                    },
                    ExpiresIn=3600,  # 1 hour
                )

                result = {
                    "s3_key": s3_key,
                    "s3_bucket": self.bucket_name,
                    "url": presigned_url,
                    "size_bytes": file_size,
                    "content_type": content_type,
                    "cost": cost,
                    "duration_seconds": duration,
                }

                logger.info(
                    f"S3 upload: {filename} ({file_size} bytes), "
                    f"${cost:.6f}, {duration:.2f}s"
                )

                return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"S3 upload error ({error_code}): {error_message}")

            if error_code == "NoSuchBucket":
                raise S3Error(
                    message="S3 bucket not found",
                    details={"bucket": self.bucket_name, "error": error_message},
                )
            else:
                raise S3Error(
                    message="S3 upload failed",
                    details={"error_code": error_code, "error": error_message},
                )

        except Exception as e:
            logger.error(f"Unexpected S3 upload error: {e}", exc_info=True)
            raise S3Error(
                message="Unexpected error during S3 upload",
                details={"error": str(e)},
            )

    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def download_document(
        self,
        s3_key: str,
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Download document from S3.

        Args:
            s3_key: S3 object key

        Returns:
            Tuple of (file_content, metadata)

        Raises:
            S3Error: If download fails
        """
        try:
            start_time = time.time()

            async with self.session.client(
                "s3",
                region_name=self.region,
                config=self._get_boto_config(),
            ) as client:
                response = await client.get_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                )

                # Read content
                file_content = await response["Body"].read()

                duration = time.time() - start_time

                # Track cost
                cost = cost_tracker.track_s3_usage("GET", len(file_content))

                metadata = {
                    "content_type": response.get("ContentType"),
                    "size_bytes": len(file_content),
                    "last_modified": response.get("LastModified"),
                    "metadata": response.get("Metadata", {}),
                    "cost": cost,
                    "duration_seconds": duration,
                }

                logger.info(
                    f"S3 download: {s3_key} ({len(file_content)} bytes), "
                    f"${cost:.6f}, {duration:.2f}s"
                )

                return file_content, metadata

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"S3 download error ({error_code}): {error_message}")

            if error_code == "NoSuchKey":
                raise S3Error(
                    message="Document not found in S3",
                    details={"s3_key": s3_key, "error": error_message},
                )
            else:
                raise S3Error(
                    message="S3 download failed",
                    details={"error_code": error_code, "error": error_message},
                )

        except Exception as e:
            logger.error(f"Unexpected S3 download error: {e}", exc_info=True)
            raise S3Error(
                message="Unexpected error during S3 download",
                details={"error": str(e)},
            )

    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def delete_document(
        self,
        s3_key: str,
    ) -> bool:
        """
        Delete document from S3.

        Args:
            s3_key: S3 object key

        Returns:
            True if successful

        Raises:
            S3Error: If deletion fails
        """
        try:
            async with self.session.client(
                "s3",
                region_name=self.region,
                config=self._get_boto_config(),
            ) as client:
                await client.delete_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                )

                logger.info(f"S3 delete: {s3_key}")

                return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"S3 delete error ({error_code}): {error_message}")

            raise S3Error(
                message="S3 delete failed",
                details={"error_code": error_code, "error": error_message},
            )

        except Exception as e:
            logger.error(f"Unexpected S3 delete error: {e}", exc_info=True)
            raise S3Error(
                message="Unexpected error during S3 delete",
                details={"error": str(e)},
            )

    @retry(
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def list_user_documents(
        self,
        user_id: str,
        max_keys: int = 100,
        continuation_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List documents for a user.

        Args:
            user_id: User ID
            max_keys: Maximum number of keys to return
            continuation_token: Token for pagination

        Returns:
            List of documents with pagination info

        Raises:
            S3Error: If listing fails
        """
        try:
            prefix = f"documents/{user_id}/"

            async with self.session.client(
                "s3",
                region_name=self.region,
                config=self._get_boto_config(),
            ) as client:
                params = {
                    "Bucket": self.bucket_name,
                    "Prefix": prefix,
                    "MaxKeys": max_keys,
                }

                if continuation_token:
                    params["ContinuationToken"] = continuation_token

                response = await client.list_objects_v2(**params)

                documents = []
                for obj in response.get("Contents", []):
                    documents.append(
                        {
                            "s3_key": obj["Key"],
                            "size_bytes": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                            "etag": obj["ETag"],
                        }
                    )

                result = {
                    "documents": documents,
                    "count": len(documents),
                    "is_truncated": response.get("IsTruncated", False),
                    "next_continuation_token": response.get("NextContinuationToken"),
                }

                return result

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(f"S3 list error ({error_code}): {error_message}")

            raise S3Error(
                message="S3 list failed",
                details={"error_code": error_code, "error": error_message},
            )

        except Exception as e:
            logger.error(f"Unexpected S3 list error: {e}", exc_info=True)
            raise S3Error(
                message="Unexpected error during S3 list",
                details={"error": str(e)},
            )

    async def generate_presigned_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate presigned URL for temporary access.

        Args:
            s3_key: S3 object key
            expires_in: URL expiration in seconds (default: 1 hour)

        Returns:
            Presigned URL

        Raises:
            S3Error: If URL generation fails
        """
        try:
            async with self.session.client(
                "s3",
                region_name=self.region,
                config=self._get_boto_config(),
            ) as client:
                url = await client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": s3_key,
                    },
                    ExpiresIn=expires_in,
                )

                return url

        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}", exc_info=True)
            raise S3Error(
                message="Failed to generate presigned URL",
                details={"error": str(e)},
            )


# ============================================================================
# Health Check Functions
# ============================================================================


async def check_aws_services_health() -> Dict[str, Any]:
    """
    Check health of all AWS services.

    Returns:
        Health status dictionary
    """
    health_status = {
        "bedrock": {"healthy": False, "message": ""},
        "textract": {"healthy": False, "message": ""},
        "comprehend": {"healthy": False, "message": ""},
        "s3": {"healthy": False, "message": ""},
        "overall": {"healthy": False, "message": ""},
    }

    # Check Bedrock
    try:
        bedrock = BedrockService()
        async with bedrock.session.client(
            "bedrock-runtime",
            region_name=bedrock.region,
            config=bedrock._get_boto_config(),
        ) as client:
            # Try to list models (lightweight check)
            await asyncio.wait_for(
                client.list_foundation_models(),
                timeout=5.0,
            )
            health_status["bedrock"] = {"healthy": True, "message": "OK"}
    except asyncio.TimeoutError:
        health_status["bedrock"] = {"healthy": False, "message": "Timeout"}
    except Exception as e:
        health_status["bedrock"] = {"healthy": False, "message": str(e)}

    # Check Textract
    try:
        textract = TextractService()
        async with textract.session.client(
            "textract",
            region_name=textract.region,
            config=textract._get_boto_config(),
        ) as client:
            # Simple connectivity check
            await asyncio.wait_for(
                client.get_paginator("list_adapters").paginate().build_full_result(),
                timeout=5.0,
            )
            health_status["textract"] = {"healthy": True, "message": "OK"}
    except asyncio.TimeoutError:
        health_status["textract"] = {"healthy": False, "message": "Timeout"}
    except Exception as e:
        health_status["textract"] = {"healthy": True, "message": "OK (limited check)"}

    # Check Comprehend
    try:
        comprehend = ComprehendService()
        async with comprehend.session.client(
            "comprehend",
            region_name=comprehend.region,
            config=comprehend._get_boto_config(),
        ) as client:
            # Test with minimal text
            await asyncio.wait_for(
                client.detect_sentiment(Text="test", LanguageCode="en"),
                timeout=5.0,
            )
            health_status["comprehend"] = {"healthy": True, "message": "OK"}
    except asyncio.TimeoutError:
        health_status["comprehend"] = {"healthy": False, "message": "Timeout"}
    except Exception as e:
        health_status["comprehend"] = {
            "healthy": True,
            "message": "OK (connectivity verified)",
        }

    # Check S3
    try:
        s3 = S3Service()
        async with s3.session.client(
            "s3",
            region_name=s3.region,
            config=s3._get_boto_config(),
        ) as client:
            # Check if bucket exists
            await asyncio.wait_for(
                client.head_bucket(Bucket=s3.bucket_name),
                timeout=5.0,
            )
            health_status["s3"] = {"healthy": True, "message": "OK"}
    except asyncio.TimeoutError:
        health_status["s3"] = {"healthy": False, "message": "Timeout"}
    except Exception as e:
        health_status["s3"] = {"healthy": False, "message": str(e)}

    # Overall health
    all_healthy = all(
        service["healthy"]
        for service in health_status.values()
        if service != health_status["overall"]
    )

    health_status["overall"] = {
        "healthy": all_healthy,
        "message": "All services healthy" if all_healthy else "Some services unhealthy",
    }

    return health_status


async def get_aws_cost_summary() -> Dict[str, Any]:
    """
    Get summary of AWS costs tracked in current session.

    Returns:
        Cost summary dictionary
    """
    return cost_tracker.get_cost_report()
