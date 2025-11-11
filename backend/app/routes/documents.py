"""
Document Processing Routes for PM Document Intelligence.

This module provides endpoints for document upload, processing, retrieval,
and analysis.

Routes:
    POST /api/v1/documents/upload - Upload document
    GET /api/v1/documents/{document_id} - Get document
    GET /api/v1/documents - List documents
    GET /api/v1/documents/{document_id}/download - Download original file
    POST /api/v1/documents/{document_id}/process - Process document
    POST /api/v1/documents/{document_id}/question - Ask questions about document
    DELETE /api/v1/documents/{document_id} - Delete document
"""

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.database import execute_insert, execute_select, execute_update
from app.models.document import DocumentStatus
from app.models.user import UserInDB
from app.services.aws_service import S3Service
from app.utils.auth_helpers import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)


router = APIRouter()

# File upload constraints
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
# Supported file types:
# - PDF documents: .pdf
# - Text files: .txt, .md
# - Images: .png, .jpg, .jpeg, .tiff
# - Microsoft Office (modern): .docx, .xlsx, .pptx
# - Microsoft Office (legacy): .doc, .xls, .ppt
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Upload a new document for processing.

    Args:
        file: Document file to upload
        current_user: Authenticated user

    Returns:
        Document metadata

    Raises:
        HTTPException: If upload fails or file is invalid
    """
    try:
        logger.info(f"Document upload started by user {current_user.id}: {file.filename}")

        # Validate file extension
        file_ext = None
        if file.filename:
            file_ext = (
                "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else None
            )

        if not file_ext or file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
            )

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty",
            )

        # Upload to S3
        s3_service = S3Service()
        upload_result = await s3_service.upload_document(
            file_content=file_content,
            filename=file.filename or "unnamed",
            user_id=current_user.id,
            document_type=file.content_type or "application/octet-stream",
        )

        # Create database record
        document_data = {
            "id": str(uuid4()),
            "user_id": current_user.id,
            "filename": file.filename or "unnamed",
            "file_type": file.content_type or "application/octet-stream",
            "size": file_size,
            "s3_reference": {
                "bucket": upload_result.get("bucket", ""),
                "key": upload_result["s3_key"],
            },
            "status": DocumentStatus.UPLOADED.value,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        document = await execute_insert("documents", document_data)

        logger.info(f"Document uploaded successfully: {document['id']}")

        return {
            "id": document["id"],
            "filename": document["filename"],
            "file_type": document["file_type"],
            "file_size": document["size"],
            "status": document["status"],
            "created_at": document["created_at"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed. Please try again.",
        )


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Get document by ID.

    Args:
        document_id: Document identifier
        current_user: Authenticated user

    Returns:
        Document data
    """
    try:
        logger.info(f"Get document endpoint called: {document_id} by user {current_user.id}")

        # Query document by ID
        documents = await execute_select(
            "documents",
            match={"id": document_id, "user_id": current_user.id},
        )

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        document = documents[0]
        logger.info(f"Document retrieved: {document_id}")

        # Fetch analysis data if it exists
        analysis_results = await execute_select(
            "analysis",
            match={"document_id": document_id},
        )

        if analysis_results:
            # Merge analysis data into document response
            analysis = analysis_results[0]
            document["summary"] = analysis.get("summary", "")
            document["action_items"] = analysis.get("action_items", [])
            document["entities"] = analysis.get("entities", [])
            document["key_phrases"] = analysis.get("key_phrases", [])
            document["risks"] = analysis.get("risks", [])
            document["sentiment"] = analysis.get("sentiment", {})
            document["processing_cost"] = analysis.get("processing_cost", 0)
            document["processing_duration_seconds"] = analysis.get("processing_duration_seconds", 0)
            document["needs_processing"] = False
            logger.info(f"Analysis data included for document {document_id}")
        else:
            # Add placeholder analysis if not processed
            document["summary"] = (
                "This document hasn't been analyzed yet. Click 'Process Document' to generate AI-powered insights."
            )
            document["action_items"] = []
            document["entities"] = []
            document["key_phrases"] = []
            document["risks"] = []
            document["sentiment"] = {}
            document["needs_processing"] = True
            logger.info(f"No analysis found for document {document_id}")

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document",
        )


@router.get("")
async def list_documents(
    current_user: UserInDB = Depends(get_current_user),
):
    """
    List all documents for the current user.

    Args:
        current_user: Authenticated user

    Returns:
        List of documents
    """
    try:
        logger.info(f"Listing documents for user {current_user.id}")

        # Query documents for current user
        documents = await execute_select(
            "documents",
            match={"user_id": current_user.id},
            order="created_at.desc",
        )

        logger.info(f"Found {len(documents)} documents for user {current_user.id}")

        return {
            "documents": documents,
            "total": len(documents),
        }

    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents",
        )


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Download original document file.

    Args:
        document_id: Document identifier
        current_user: Authenticated user

    Returns:
        File stream response with original document
    """
    try:
        from fastapi.responses import StreamingResponse
        import io

        logger.info(f"Download document endpoint called: {document_id} by user {current_user.id}")

        # Get document from database
        documents = await execute_select(
            "documents",
            match={"id": document_id, "user_id": current_user.id},
        )

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        document = documents[0]

        # Get S3 reference
        s3_ref = document.get("s3_reference", {})
        if not s3_ref.get("key"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document file not available for download",
            )

        # Download from S3
        s3_service = S3Service()
        file_content, metadata = await s3_service.download_document(s3_ref["key"])

        # Determine content type
        filename = document.get("filename", "document")
        content_type = metadata.get("ContentType", "application/octet-stream")

        # Create streaming response
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(file_content)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document download failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download document",
        )


@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Process document with AI analysis.

    Args:
        document_id: Document identifier
        current_user: Authenticated user

    Returns:
        Processing job information
    """
    try:
        logger.info(f"Process document endpoint called: {document_id} by user {current_user.id}")

        # Get document from database
        documents = await execute_select(
            "documents",
            match={"id": document_id, "user_id": current_user.id},
        )

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        document = documents[0]

        # Check if already processing or processed
        if document.get("status") == DocumentStatus.PROCESSING.value:
            return {
                "message": "Document is already being processed",
                "status": "processing",
                "document_id": document_id,
            }

        # If already completed, return existing results
        if document.get("status") == DocumentStatus.COMPLETED.value:
            # Fetch analysis results
            analysis_results = await execute_select(
                "analysis",
                match={"document_id": document_id},
            )
            if analysis_results:
                analysis = analysis_results[0]
                return {
                    "message": "Document already processed",
                    "status": "completed",
                    "document_id": document_id,
                    "summary": analysis.get("summary", ""),
                    "entities": analysis.get("entities", []),
                    "action_items": analysis.get("action_items", []),
                    "risks": analysis.get("risks", []),
                    "sentiment": analysis.get("sentiment", {}),
                }

        # Update status to processing
        await execute_update(
            "documents",
            data={"status": DocumentStatus.PROCESSING.value, "updated_at": datetime.utcnow()},
            match={"id": document_id},
        )

        # Import processor
        from app.services.document_processor import DocumentProcessor, DocumentType
        import tempfile
        import os

        # Download document from S3
        s3_service = S3Service()
        s3_ref = document.get("s3_reference", {})

        if not s3_ref.get("key"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document S3 reference not found",
            )

        # Download from S3 to temp file
        file_content, _ = await s3_service.download_document(s3_ref["key"])

        # Create temp file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(document["filename"])[1]
        ) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name

        try:
            # Process document
            processor = DocumentProcessor()
            results = await processor.process_document(
                document_id=document_id,
                user_id=current_user.id,
                file_path=tmp_file_path,
                filename=document["filename"],
                document_type=DocumentType.GENERAL,
                processing_options={
                    "extract_actions": True,
                    "extract_risks": True,
                    "generate_summary": True,
                },
            )

            # Update document status only (analysis data is in analysis table)
            update_data = {
                "status": DocumentStatus.COMPLETED.value,
                "updated_at": datetime.utcnow(),
            }

            await execute_update(
                "documents",
                data=update_data,
                match={"id": document_id},
            )

            logger.info(f"Document processed successfully: {document_id}")

            return {
                "message": "Document processed successfully",
                "status": "processed",
                "document_id": document_id,
                "summary": results.get("summary", ""),
            }

        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document processing failed: {e}", exc_info=True)

        # Update status to failed
        try:
            await execute_update(
                "documents",
                data={
                    "status": DocumentStatus.FAILED.value,
                    "updated_at": datetime.utcnow(),
                },
                match={"id": document_id},
            )
        except Exception as update_error:
            logger.error(f"Failed to update document status: {update_error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}",
        )


@router.post("/{document_id}/question")
async def ask_question(
    document_id: str,
    question: dict,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Ask a question about a document.

    Args:
        document_id: Document identifier
        question: Question data with 'question' field
        current_user: Authenticated user

    Returns:
        Answer to the question
    """
    try:
        logger.info(f"Question asked for document {document_id}: {question.get('question', '')}")

        # Verify document exists and belongs to user
        documents = await execute_select(
            "documents",
            match={"id": document_id, "user_id": current_user.id},
        )

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        document = documents[0]

        # Check if document has been analyzed
        if not document.get("extracted_text"):
            return {
                "answer": "This document hasn't been analyzed yet. Please process the document first to ask questions about its content.",
                "confidence": 0.0,
                "sources": [],
            }

        # TODO: Implement actual Q&A with AI
        # For now, return a placeholder response
        return {
            "answer": "Document Q&A is not yet fully implemented. Please check back later when AI processing is enabled.",
            "confidence": 0.0,
            "sources": [],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to answer question: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get answer",
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Delete document.

    Args:
        document_id: Document identifier
        current_user: Authenticated user

    Returns:
        Success message
    """
    try:
        logger.info(f"Delete document endpoint called: {document_id} by user {current_user.id}")

        # Get document from database
        documents = await execute_select(
            "documents",
            match={"id": document_id, "user_id": current_user.id},
        )

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        document = documents[0]

        # Delete from S3 if reference exists
        s3_ref = document.get("s3_reference", {})
        if s3_ref.get("key"):
            try:
                s3_service = S3Service()
                await s3_service.delete_document(s3_ref["key"])
                logger.info(f"Deleted document from S3: {s3_ref['key']}")
            except Exception as s3_error:
                logger.warning(f"Failed to delete from S3: {s3_error}")
                # Continue with database deletion even if S3 delete fails

        # Delete from database
        from app.database import execute_delete

        await execute_delete("documents", match={"id": document_id})

        logger.info(f"Document deleted successfully: {document_id}")

        return {
            "message": "Document deleted successfully",
            "document_id": document_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )
