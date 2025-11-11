"""
Document Processing Pipeline for PM Document Intelligence.

This module provides an intelligent document processing pipeline that orchestrates
AWS services (S3, Textract, Comprehend, Bedrock) and AI analysis to extract
insights from project management documents.

Features:
- State machine tracking with checkpoint recovery
- Real-time progress updates via PubNub
- Comprehensive error handling with rollback
- Cost tracking and metrics
- Batch processing support
- Webhook notifications

Usage:
    from app.services.document_processor import DocumentProcessor

    processor = DocumentProcessor()
    result = await processor.process_document(
        document_id="doc_123",
        user_id="user_456",
        file_path="/tmp/document.pdf",
        processing_options={
            "extract_actions": True,
            "extract_risks": True,
            "generate_summary": True,
        }
    )
"""

import asyncio
import json
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from app.config import settings
from app.database import execute_insert, execute_query, execute_update
from app.models.document import DocumentStatus
from app.services.aws_service import (
    BedrockService,
    ComprehendService,
    DocumentType,
    S3Service,
    TextractService,
    cost_tracker,
)
from app.services.office_extractor import OfficeExtractor
from app.utils.exceptions import (
    DocumentProcessingError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Processing State Machine
# ============================================================================


class ProcessingState(str, Enum):
    """Document processing states."""

    UPLOADED = "uploaded"
    UPLOADING_TO_S3 = "uploading_to_s3"
    EXTRACTING_TEXT = "extracting_text"
    CLEANING_TEXT = "cleaning_text"
    ANALYZING_ENTITIES = "analyzing_entities"
    ANALYZING_SENTIMENT = "analyzing_sentiment"
    EXTRACTING_ACTIONS = "extracting_actions"
    EXTRACTING_RISKS = "extracting_risks"
    GENERATING_SUMMARY = "generating_summary"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    STORING_RESULTS = "storing_results"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingCheckpoint:
    """Processing checkpoint for recovery."""

    def __init__(
        self,
        document_id: str,
        state: ProcessingState,
        data: dict[str, Any] | None = None,
        error: str | None = None,
    ):
        """
        Initialize checkpoint.

        Args:
            document_id: Document ID
            state: Current processing state
            data: Intermediate data for recovery
            error: Error message if failed
        """
        self.document_id = document_id
        self.state = state
        self.data = data or {}
        self.error = error
        self.created_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document_id,
            "state": self.state.value,
            "data": self.data,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================================
# Document Processor
# ============================================================================


class DocumentProcessor:
    """Intelligent document processing pipeline."""

    def __init__(self):
        """Initialize document processor."""
        self.bedrock = BedrockService()
        self.textract = TextractService()
        self.comprehend = ComprehendService()
        self.s3 = S3Service()
        self.office_extractor = OfficeExtractor()

        # Processing state tracking
        self.checkpoints: dict[str, ProcessingCheckpoint] = {}
        self.cancellation_tokens: set[str] = set()

        # PubNub client (will be initialized if needed)
        self.pubnub_client = None

        # Default processing options
        self.default_options = {
            "extract_actions": True,
            "extract_risks": True,
            "extract_entities": True,
            "generate_summary": True,
            "generate_embeddings": False,  # Requires vector database setup
            "send_webhooks": False,
            "webhook_url": None,
        }

    def _init_pubnub(self):
        """Initialize PubNub client for real-time updates."""
        if self.pubnub_client is None and settings.pubnub.pubnub_enabled:
            try:
                from pubnub.pnconfiguration import PNConfiguration
                from pubnub.pubnub_asyncio import PubNubAsyncio

                pnconfig = PNConfiguration()
                pnconfig.subscribe_key = settings.pubnub.pubnub_subscribe_key
                pnconfig.publish_key = settings.pubnub.pubnub_publish_key
                pnconfig.uuid = "document-processor"
                pnconfig.ssl = True

                self.pubnub_client = PubNubAsyncio(pnconfig)
                logger.info("PubNub client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize PubNub: {e}")
                self.pubnub_client = None

    async def _publish_progress(
        self,
        user_id: str,
        document_id: str,
        state: ProcessingState,
        progress: int,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """
        Publish processing progress via PubNub.

        Args:
            user_id: User ID
            document_id: Document ID
            state: Current processing state
            progress: Progress percentage (0-100)
            message: Progress message
            data: Additional data
        """
        if not settings.pubnub.pubnub_enabled or self.pubnub_client is None:
            return

        try:
            channel = f"user_{user_id}_documents"

            message_data = {
                "type": "document_processing",
                "document_id": document_id,
                "state": state.value,
                "progress": progress,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if data:
                message_data["data"] = data

            await self.pubnub_client.publish().channel(channel).message(message_data).future()

            logger.debug(f"Published progress: {document_id} - {state.value} ({progress}%)")

        except Exception as e:
            logger.error(f"Failed to publish progress: {e}")

    async def _save_checkpoint(
        self,
        document_id: str,
        state: ProcessingState,
        data: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """
        Save processing checkpoint.

        Args:
            document_id: Document ID
            state: Current processing state
            data: Intermediate data
            error: Error message if failed
        """
        checkpoint = ProcessingCheckpoint(document_id, state, data, error)
        self.checkpoints[document_id] = checkpoint

        # Update document status in database
        try:
            status_map = {
                ProcessingState.COMPLETED: DocumentStatus.COMPLETED,
                ProcessingState.FAILED: DocumentStatus.FAILED,
                ProcessingState.CANCELLED: DocumentStatus.FAILED,
            }

            doc_status = status_map.get(state, DocumentStatus.PROCESSING)

            # Only update the status field that exists in the database
            # Note: processing_state, processing_checkpoint, error_message columns don't exist
            await execute_update(
                "documents",
                {
                    "status": doc_status.value,
                    "updated_at": datetime.utcnow(),
                },
                match={"id": document_id},
            )
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _check_cancellation(self, document_id: str) -> None:
        """
        Check if processing was cancelled.

        Args:
            document_id: Document ID

        Raises:
            DocumentProcessingError: If processing was cancelled
        """
        if document_id in self.cancellation_tokens:
            self.cancellation_tokens.remove(document_id)
            raise DocumentProcessingError(
                message="Processing cancelled by user",
                details={"document_id": document_id},
            )

    async def cancel_processing(self, document_id: str) -> bool:
        """
        Cancel document processing.

        Args:
            document_id: Document ID

        Returns:
            True if cancelled successfully
        """
        self.cancellation_tokens.add(document_id)

        # Update document status
        await execute_update(
            "documents",
            {
                "status": DocumentStatus.FAILED.value,
                "updated_at": datetime.utcnow(),
            },
            match={"id": document_id},
        )

        logger.info(f"Processing cancelled for document {document_id}")
        return True

    async def process_document(
        self,
        document_id: str,
        user_id: str,
        file_path: str,
        filename: str,
        document_type: DocumentType = DocumentType.GENERAL,
        processing_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process document through complete pipeline.

        Args:
            document_id: Document ID
            user_id: User ID
            file_path: Path to uploaded file
            filename: Original filename
            document_type: Document type for analysis
            processing_options: Processing options

        Returns:
            Processing results with all extracted data

        Raises:
            DocumentProcessingError: If processing fails
        """
        # Merge options with defaults
        options = {**self.default_options, **(processing_options or {})}

        # Initialize PubNub
        self._init_pubnub()

        # Start time for metrics
        start_time = datetime.utcnow()

        # Processing results
        results = {
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "document_type": document_type.value,
            "status": "processing",
            "started_at": start_time.isoformat(),
        }

        s3_key = None

        try:
            # Step 1: Upload to S3
            self._check_cancellation(document_id)
            await self._save_checkpoint(document_id, ProcessingState.UPLOADING_TO_S3)
            await self._publish_progress(
                user_id,
                document_id,
                ProcessingState.UPLOADING_TO_S3,
                5,
                "Uploading document to secure storage...",
            )

            logger.info(f"Step 1: Uploading {filename} to S3")

            # Read file
            with open(file_path, "rb") as f:
                file_content = f.read()

            # Upload to S3
            s3_result = await self.s3.upload_document(
                file_content=file_content,
                filename=filename,
                user_id=user_id,
                document_type=document_type.value,
            )

            s3_key = s3_result["s3_key"]
            results["s3_key"] = s3_key
            results["s3_bucket"] = s3_result["s3_bucket"]
            results["file_size"] = s3_result["size_bytes"]

            logger.info(f"Uploaded to S3: {s3_key}")

            # Step 2: Extract text
            self._check_cancellation(document_id)
            await self._save_checkpoint(
                document_id, ProcessingState.EXTRACTING_TEXT, {"s3_key": s3_key}
            )
            await self._publish_progress(
                user_id,
                document_id,
                ProcessingState.EXTRACTING_TEXT,
                15,
                "Extracting text from document...",
            )

            logger.info(f"Step 2: Extracting text from {filename}")

            extracted_text = await self._extract_text(
                file_content, filename, s3_result["s3_bucket"], s3_key
            )

            results["extracted_text"] = extracted_text["text"]
            results["extraction_method"] = extracted_text["method"]
            results["word_count"] = len(extracted_text["text"].split())

            logger.info(f"Extracted {results['word_count']} words")

            # Step 3: Clean and normalize text
            self._check_cancellation(document_id)
            await self._save_checkpoint(
                document_id,
                ProcessingState.CLEANING_TEXT,
                {"s3_key": s3_key, "raw_text": extracted_text["text"]},
            )
            await self._publish_progress(
                user_id,
                document_id,
                ProcessingState.CLEANING_TEXT,
                25,
                "Cleaning and normalizing text...",
            )

            logger.info("Step 3: Cleaning text")

            cleaned_text = self._clean_text(extracted_text["text"])
            results["cleaned_text"] = cleaned_text

            # Step 4: Analyze with Comprehend
            if options["extract_entities"]:
                self._check_cancellation(document_id)
                await self._save_checkpoint(
                    document_id,
                    ProcessingState.ANALYZING_ENTITIES,
                    {"s3_key": s3_key, "text": cleaned_text},
                )
                await self._publish_progress(
                    user_id,
                    document_id,
                    ProcessingState.ANALYZING_ENTITIES,
                    35,
                    "Analyzing entities and sentiment...",
                )

                logger.info("Step 4: Analyzing with Comprehend")

                comprehend_results = await self.comprehend.analyze_document_comprehensive(
                    cleaned_text
                )

                results["entities"] = comprehend_results["entities"]["entities"]
                results["sentiment"] = comprehend_results["sentiment"]
                results["key_phrases"] = comprehend_results["key_phrases"]["key_phrases"]

                logger.info(
                    f"Found {len(results['entities'])} entities, "
                    f"{len(results['key_phrases'])} key phrases"
                )

            # Step 5: Extract action items
            if options["extract_actions"]:
                self._check_cancellation(document_id)
                await self._save_checkpoint(
                    document_id,
                    ProcessingState.EXTRACTING_ACTIONS,
                    {"s3_key": s3_key, "text": cleaned_text},
                )
                await self._publish_progress(
                    user_id,
                    document_id,
                    ProcessingState.EXTRACTING_ACTIONS,
                    50,
                    "Extracting action items...",
                )

                logger.info("Step 5: Extracting action items")

                action_items = await self.extract_action_items(cleaned_text, document_type)

                results["action_items"] = action_items
                logger.info(f"Extracted {len(action_items)} action items")

            # Step 6: Extract risks
            if options["extract_risks"]:
                self._check_cancellation(document_id)
                await self._save_checkpoint(
                    document_id,
                    ProcessingState.EXTRACTING_RISKS,
                    {"s3_key": s3_key, "text": cleaned_text},
                )
                await self._publish_progress(
                    user_id,
                    document_id,
                    ProcessingState.EXTRACTING_RISKS,
                    65,
                    "Identifying risks and blockers...",
                )

                logger.info("Step 6: Extracting risks")

                risks = await self.extract_risks(cleaned_text, document_type)

                results["risks"] = risks
                logger.info(f"Identified {len(risks)} risks")

            # Step 7: Generate summary
            if options["generate_summary"]:
                self._check_cancellation(document_id)
                await self._save_checkpoint(
                    document_id,
                    ProcessingState.GENERATING_SUMMARY,
                    {"s3_key": s3_key, "text": cleaned_text},
                )
                await self._publish_progress(
                    user_id,
                    document_id,
                    ProcessingState.GENERATING_SUMMARY,
                    75,
                    "Generating summary...",
                )

                logger.info("Step 7: Generating summary")

                summary = await self.generate_summary(cleaned_text, document_type, length="medium")

                results["summary"] = summary
                logger.info("Generated summary")

            # Step 8: Generate embeddings (if enabled)
            if options["generate_embeddings"]:
                self._check_cancellation(document_id)
                await self._save_checkpoint(
                    document_id,
                    ProcessingState.GENERATING_EMBEDDINGS,
                    {"s3_key": s3_key, "text": cleaned_text},
                )
                await self._publish_progress(
                    user_id,
                    document_id,
                    ProcessingState.GENERATING_EMBEDDINGS,
                    85,
                    "Generating embeddings for search...",
                )

                logger.info("Step 8: Generating embeddings")

                # Placeholder for embeddings generation
                # In production, integrate with OpenAI embeddings or similar
                results["embeddings"] = {
                    "status": "not_implemented",
                    "message": "Embeddings generation requires vector database setup",
                }

            # Step 9: Store results
            self._check_cancellation(document_id)
            await self._save_checkpoint(
                document_id, ProcessingState.STORING_RESULTS, {"s3_key": s3_key}
            )
            await self._publish_progress(
                user_id,
                document_id,
                ProcessingState.STORING_RESULTS,
                90,
                "Storing analysis results...",
            )

            logger.info("Step 9: Storing results")

            await self._store_results(document_id, results)

            # Calculate final metrics
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            results["status"] = "completed"
            results["completed_at"] = end_time.isoformat()
            results["duration_seconds"] = duration
            results["cost"] = self.calculate_processing_cost(results)

            # Mark as completed
            await self._save_checkpoint(document_id, ProcessingState.COMPLETED)
            await self._publish_progress(
                user_id,
                document_id,
                ProcessingState.COMPLETED,
                100,
                "Processing completed successfully!",
                {"duration": duration, "cost": results["cost"]},
            )

            logger.info(
                f"Document {document_id} processed successfully in {duration:.2f}s, "
                f"cost: ${results['cost']:.4f}"
            )

            # Send webhook if enabled
            if options["send_webhooks"] and options["webhook_url"]:
                await self._send_webhook(options["webhook_url"], results)

            return results

        except DocumentProcessingError:
            raise

        except Exception as e:
            logger.error(f"Document processing failed: {e}", exc_info=True)

            # Rollback: Delete S3 file if uploaded
            if s3_key:
                try:
                    await self.s3.delete_document(s3_key)
                    logger.info(f"Rolled back S3 upload: {s3_key}")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")

            # Save error checkpoint
            error_message = str(e)
            await self._save_checkpoint(document_id, ProcessingState.FAILED, error=error_message)

            # Notify user of failure
            await self._publish_progress(
                user_id,
                document_id,
                ProcessingState.FAILED,
                0,
                f"Processing failed: {error_message}",
            )

            raise DocumentProcessingError(
                message="Document processing failed",
                details={
                    "document_id": document_id,
                    "error": error_message,
                    "state": results.get("status", "unknown"),
                },
            )

    async def _extract_text(
        self,
        file_content: bytes,
        filename: str,
        s3_bucket: str,
        s3_key: str,
    ) -> dict[str, Any]:
        """
        Extract text from document.

        Args:
            file_content: File bytes
            filename: Original filename
            s3_bucket: S3 bucket name
            s3_key: S3 object key

        Returns:
            Extracted text and metadata
        """
        file_extension = Path(filename).suffix.lower()

        # Plain text files
        if file_extension in [".txt", ".md", ".csv"]:
            try:
                text = file_content.decode("utf-8")
                return {
                    "text": text,
                    "method": "direct",
                    "pages": 1,
                    "confidence": 100.0,
                }
            except UnicodeDecodeError:
                # Try other encodings
                for encoding in ["latin-1", "windows-1252"]:
                    try:
                        text = file_content.decode(encoding)
                        return {
                            "text": text,
                            "method": "direct",
                            "pages": 1,
                            "confidence": 100.0,
                        }
                    except UnicodeDecodeError:
                        continue

                raise DocumentProcessingError(
                    message="Failed to decode text file", details={"filename": filename}
                )

        # PDF and images - Use Textract
        elif file_extension in [".pdf", ".png", ".jpg", ".jpeg", ".tiff"]:
            # PDFs must use S3 reference (multi-page support)
            # Images can use bytes (single page only)
            if file_extension == ".pdf":
                # Always use S3 for PDFs (supports multi-page)
                result = await self.textract.extract_text_asynchronous(
                    s3_bucket, s3_key, feature_types=["TABLES", "FORMS"]
                )
            else:
                # Images: use bytes for small files, S3 for large
                file_size = len(file_content)
                if file_size < 5 * 1024 * 1024:  # < 5MB
                    result = await self.textract.extract_text_synchronous(
                        file_content, feature_types=["TABLES", "FORMS"]
                    )
                else:
                    result = await self.textract.extract_text_asynchronous(
                        s3_bucket, s3_key, feature_types=["TABLES", "FORMS"]
                    )

            return {
                "text": result["text"],
                "method": "textract",
                "pages": result.get("pages", 1),
                "confidence": result.get("average_confidence", 0),
                "tables": result.get("tables", []),
                "forms": result.get("forms", []),
            }

        # Microsoft Office documents
        elif file_extension in [".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"]:
            logger.info(f"Extracting Office document: {filename}")
            result = await self.office_extractor.extract_text(file_content, filename)

            return {
                "text": result["text"],
                "method": result["method"],
                "pages": result.get("pages", 1),
                "confidence": result.get("confidence", 100.0),
                "metadata": result.get("metadata", {}),
            }

        else:
            raise DocumentProcessingError(
                message="Unsupported file type",
                details={"filename": filename, "extension": file_extension},
            )

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove special characters but keep punctuation
        text = re.sub(r"[^\w\s\.,!?\-:;()\[\]{}\"\'@#$%&*+=/<>]", "", text)

        # Normalize line breaks
        text = re.sub(r"\n+", "\n", text)

        # Trim
        text = text.strip()

        return text

    async def extract_action_items(
        self,
        text: str,
        document_type: DocumentType = DocumentType.GENERAL,
    ) -> list[dict[str, Any]]:
        """
        Extract action items using Claude.

        Args:
            text: Document text
            document_type: Document type

        Returns:
            List of action items with assignee, due date, priority
        """
        system_prompt = """You are an expert project manager analyzing documents to extract action items.

For each action item, identify:
1. Action: Clear description of what needs to be done
2. Assignee: Person or team responsible (if mentioned)
3. Due Date: Deadline or timeline (if mentioned)
4. Priority: HIGH, MEDIUM, or LOW based on context
5. Status: TODO, IN_PROGRESS, BLOCKED, or DONE (if mentioned)
6. Confidence: Your confidence in this extraction (0.0 to 1.0)

Output ONLY valid JSON array format:
[
  {
    "action": "Complete the design review",
    "assignee": "Design Team",
    "due_date": "2024-03-15",
    "priority": "HIGH",
    "status": "TODO",
    "confidence": 0.9,
    "context": "Brief context from document"
  }
]

If no action items found, return: []"""

        user_message = f"""Extract action items from this {document_type.value} document:

{text[:4000]}  # Limit to 4000 chars to avoid token limits

Provide ONLY the JSON array, no other text."""

        try:
            response = await self.bedrock.invoke_claude(
                user_message=user_message,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for more consistent output
            )

            # Parse JSON response
            response_text = response["text"].strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = re.sub(r"```json?\n?", "", response_text)
                response_text = re.sub(r"```\n?$", "", response_text)
                response_text = response_text.strip()

            action_items = json.loads(response_text)

            # Validate action items
            validated_items = []
            for item in action_items:
                if self._validate_action_item(item):
                    validated_items.append(item)

            return validated_items

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse action items JSON: {e}")
            logger.error(f"Response: {response_text}")
            return []

        except Exception as e:
            logger.error(f"Action item extraction failed: {e}")
            return []

    def _validate_action_item(self, item: dict[str, Any]) -> bool:
        """
        Validate action item structure.

        Args:
            item: Action item dictionary

        Returns:
            True if valid
        """
        required_fields = ["action", "priority", "confidence"]

        # Check required fields
        if not all(field in item for field in required_fields):
            return False

        # Validate priority
        if item["priority"] not in ["HIGH", "MEDIUM", "LOW"]:
            return False

        # Validate confidence
        if not isinstance(item["confidence"], (int, float)) or not (0 <= item["confidence"] <= 1):
            return False

        # Action must be non-empty
        if not item["action"] or not item["action"].strip():
            return False

        return True

    async def extract_risks(
        self,
        text: str,
        document_type: DocumentType = DocumentType.GENERAL,
    ) -> list[dict[str, Any]]:
        """
        Extract risks and blockers using Claude.

        Args:
            text: Document text
            document_type: Document type

        Returns:
            List of risks with severity and mitigation
        """
        system_prompt = """You are an expert risk analyst identifying project risks and blockers.

For each risk, identify:
1. Risk: Clear description of the risk or blocker
2. Severity: CRITICAL, HIGH, MEDIUM, or LOW
3. Category: Technical, Resource, Schedule, Budget, External, or Other
4. Impact: What could happen if this risk materializes
5. Probability: How likely (HIGH, MEDIUM, LOW)
6. Mitigation: Suggested mitigation strategy
7. Confidence: Your confidence in this assessment (0.0 to 1.0)

Output ONLY valid JSON array format:
[
  {
    "risk": "Dependency on external API not yet available",
    "severity": "HIGH",
    "category": "Technical",
    "impact": "Could delay feature launch by 2 weeks",
    "probability": "MEDIUM",
    "mitigation": "Develop mock API for parallel testing",
    "confidence": 0.85
  }
]

If no risks found, return: []"""

        user_message = f"""Identify risks and blockers in this {document_type.value} document:

{text[:4000]}

Provide ONLY the JSON array, no other text."""

        try:
            response = await self.bedrock.invoke_claude(
                user_message=user_message,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.3,
            )

            # Parse JSON response
            response_text = response["text"].strip()

            # Remove markdown code blocks
            if response_text.startswith("```"):
                response_text = re.sub(r"```json?\n?", "", response_text)
                response_text = re.sub(r"```\n?$", "", response_text)
                response_text = response_text.strip()

            risks = json.loads(response_text)

            # Validate risks
            validated_risks = []
            for risk in risks:
                if self._validate_risk(risk):
                    validated_risks.append(risk)

            return validated_risks

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse risks JSON: {e}")
            return []

        except Exception as e:
            logger.error(f"Risk extraction failed: {e}")
            return []

    def _validate_risk(self, risk: dict[str, Any]) -> bool:
        """
        Validate risk structure.

        Args:
            risk: Risk dictionary

        Returns:
            True if valid
        """
        required_fields = ["risk", "severity", "confidence"]

        if not all(field in risk for field in required_fields):
            return False

        if risk["severity"] not in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            return False

        if not isinstance(risk["confidence"], (int, float)) or not (0 <= risk["confidence"] <= 1):
            return False

        if not risk["risk"] or not risk["risk"].strip():
            return False

        return True

    async def extract_entities(
        self,
        text: str,
        document_type: DocumentType = DocumentType.GENERAL,
    ) -> dict[str, Any]:
        """
        Extract project-specific entities using Comprehend + Claude.

        Args:
            text: Document text
            document_type: Document type

        Returns:
            Enhanced entity extraction results
        """
        # First, use Comprehend for basic entities
        comprehend_results = await self.comprehend.analyze_document_entities(text)

        # Then enhance with Claude for project-specific entities
        system_prompt = """You are an expert at extracting project management entities from documents.

Extract these specific entities:
1. Project names
2. Stakeholder names and their roles
3. Milestones with dates
4. Budget figures and financial information
5. Dependencies and relationships
6. Team names and compositions

Output ONLY valid JSON format:
{
  "projects": [{"name": "Project Alpha", "status": "active"}],
  "stakeholders": [{"name": "John Doe", "role": "Project Manager", "email": "john@example.com"}],
  "milestones": [{"name": "Phase 1 Complete", "date": "2024-03-15", "status": "pending"}],
  "budget_items": [{"item": "Development", "amount": 50000, "currency": "USD"}],
  "dependencies": [{"from": "Task A", "to": "Task B", "type": "finish-to-start"}],
  "teams": [{"name": "Backend Team", "members": ["Alice", "Bob"], "focus": "API development"}]
}"""

        user_message = f"""Extract project-specific entities from this {document_type.value} document:

{text[:3000]}

Provide ONLY the JSON object, no other text."""

        try:
            response = await self.bedrock.invoke_claude(
                user_message=user_message,
                system_prompt=system_prompt,
                max_tokens=1500,
                temperature=0.2,
            )

            # Parse JSON response
            response_text = response["text"].strip()

            if response_text.startswith("```"):
                response_text = re.sub(r"```json?\n?", "", response_text)
                response_text = re.sub(r"```\n?$", "", response_text)
                response_text = response_text.strip()

            claude_entities = json.loads(response_text)

            # Combine results
            return {
                "comprehend_entities": comprehend_results["entities"],
                "project_entities": claude_entities,
            }

        except Exception as e:
            logger.error(f"Enhanced entity extraction failed: {e}")
            return {
                "comprehend_entities": comprehend_results["entities"],
                "project_entities": {},
            }

    async def generate_summary(
        self,
        text: str,
        document_type: DocumentType = DocumentType.GENERAL,
        length: str = "medium",
    ) -> dict[str, Any]:
        """
        Generate document summary using Claude.

        Args:
            text: Document text
            document_type: Document type
            length: Summary length (short, medium, long)

        Returns:
            Summary with key points and next steps
        """
        length_tokens = {
            "short": 200,
            "medium": 500,
            "long": 1000,
        }

        max_tokens = length_tokens.get(length, 500)

        system_prompt = f"""You are an expert at creating concise, actionable summaries of project documents.

Create a {length} summary that includes:
1. Executive Summary: High-level overview in 2-3 sentences
2. Key Points: 3-5 most important points (bullet points)
3. Key Decisions: Any decisions made (if applicable)
4. Next Steps: 2-4 immediate action items
5. Concerns: Any risks or concerns raised

Format as JSON:
{{
  "executive_summary": "Brief overview...",
  "key_points": ["Point 1", "Point 2", "Point 3"],
  "decisions": ["Decision 1"],
  "next_steps": ["Step 1", "Step 2"],
  "concerns": ["Concern 1"]
}}"""

        user_message = f"""Summarize this {document_type.value} document:

{text[:6000]}

Provide ONLY the JSON object, no other text."""

        try:
            response = await self.bedrock.invoke_claude(
                user_message=user_message,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=0.4,
            )

            # Parse JSON response
            response_text = response["text"].strip()

            if response_text.startswith("```"):
                response_text = re.sub(r"```json?\n?", "", response_text)
                response_text = re.sub(r"```\n?$", "", response_text)
                response_text = response_text.strip()

            summary = json.loads(response_text)

            return summary

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse summary JSON: {e}")
            return {
                "executive_summary": "Error generating summary",
                "key_points": [],
                "decisions": [],
                "next_steps": [],
                "concerns": [],
            }

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {
                "executive_summary": "Error generating summary",
                "key_points": [],
                "decisions": [],
                "next_steps": [],
                "concerns": [],
            }

    async def _store_results(
        self,
        document_id: str,
        results: dict[str, Any],
    ) -> None:
        """
        Store processing results in database.

        Args:
            document_id: Document ID
            results: Processing results
        """
        # Update document record
        document_updates = {
            "extracted_text": results.get("extracted_text", ""),
            "word_count": results.get("word_count", 0),
            "extraction_method": results.get("extraction_method", ""),
            "status": DocumentStatus.COMPLETED.value,
            "processed_at": datetime.utcnow(),
        }

        await execute_update("documents", document_updates, match={"id": document_id})

        # Get user_id from document
        document_result = await execute_query(
            "SELECT user_id FROM documents WHERE id = :document_id",
            {"document_id": document_id}
        )
        user_id = document_result[0]["user_id"] if document_result else None

        if not user_id:
            raise ValueError(f"Could not find user_id for document {document_id}")

        # Store analysis results
        analysis_data = {
            "document_id": document_id,
            "user_id": user_id,
            "ai_models_used": results.get("ai_models_used", []),
            "sentiment": results.get("sentiment", {}),
            "entities": results.get("entities", []),
            "key_phrases": results.get("key_phrases", []),
            "action_items": results.get("action_items", []),
            "risks": results.get("risks", []),
            "summary": results.get("summary", {}),
            "processing_cost": results.get("cost", 0),
            "processing_duration_seconds": results.get("duration_seconds", 0),
        }

        await execute_insert("analysis", analysis_data)

        logger.info(f"Stored results for document {document_id}")

    def calculate_processing_cost(self, results: dict[str, Any]) -> float:
        """
        Calculate total processing cost.

        Args:
            results: Processing results

        Returns:
            Total cost in USD
        """
        # Get current cost from tracker
        return cost_tracker.get_total_cost()

    async def _send_webhook(self, webhook_url: str, results: dict[str, Any]) -> None:
        """
        Send webhook notification.

        Args:
            webhook_url: Webhook URL
            results: Processing results
        """
        try:
            import aiohttp

            webhook_data = {
                "event": "document_processed",
                "document_id": results["document_id"],
                "status": results["status"],
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "word_count": results.get("word_count", 0),
                    "action_items": len(results.get("action_items", [])),
                    "risks": len(results.get("risks", [])),
                    "cost": results.get("cost", 0),
                    "duration": results.get("duration_seconds", 0),
                },
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=webhook_data,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook sent successfully to {webhook_url}")
                    else:
                        logger.warning(
                            f"Webhook returned status {response.status}: {await response.text()}"
                        )

        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")

    async def process_multiple_documents(
        self,
        documents: list[dict[str, Any]],
        user_id: str,
        max_parallel: int = 3,
        estimate_cost: bool = True,
    ) -> dict[str, Any]:
        """
        Process multiple documents in parallel.

        Args:
            documents: List of document info dicts
            user_id: User ID
            max_parallel: Maximum parallel processing
            estimate_cost: Estimate cost before processing

        Returns:
            Batch processing results
        """
        batch_id = f"batch_{datetime.utcnow().timestamp()}"

        logger.info(
            f"Starting batch processing: {len(documents)} documents, "
            f"max {max_parallel} parallel"
        )

        # Cost estimation
        if estimate_cost:
            estimated_cost = self._estimate_batch_cost(documents)
            logger.info(f"Estimated batch cost: ${estimated_cost:.4f}")

        # Process in batches
        results = []
        failed = []

        for i in range(0, len(documents), max_parallel):
            batch = documents[i : i + max_parallel]

            # Process batch in parallel
            tasks = []
            for doc in batch:
                task = self.process_document(
                    document_id=doc["document_id"],
                    user_id=user_id,
                    file_path=doc["file_path"],
                    filename=doc["filename"],
                    document_type=doc.get("document_type", DocumentType.GENERAL),
                    processing_options=doc.get("options", {}),
                )
                tasks.append(task)

            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for doc, result in zip(batch, batch_results, strict=False):
                if isinstance(result, Exception):
                    failed.append(
                        {
                            "document_id": doc["document_id"],
                            "error": str(result),
                        }
                    )
                    logger.error(f"Batch processing failed for {doc['document_id']}: {result}")
                else:
                    results.append(result)

        # Summary
        total_cost = sum(r.get("cost", 0) for r in results)
        total_duration = sum(r.get("duration_seconds", 0) for r in results)

        return {
            "batch_id": batch_id,
            "total_documents": len(documents),
            "successful": len(results),
            "failed": len(failed),
            "failed_documents": failed,
            "total_cost": total_cost,
            "total_duration_seconds": total_duration,
            "results": results,
        }

    def _estimate_batch_cost(self, documents: list[dict[str, Any]]) -> float:
        """
        Estimate cost for batch processing.

        Args:
            documents: List of document info

        Returns:
            Estimated cost in USD
        """
        # Rough estimates per document
        avg_cost_per_doc = 0.10  # $0.10 average

        return len(documents) * avg_cost_per_doc
