"""
Document Processing Routes for PM Document Intelligence.

This module provides endpoints for document upload, processing, retrieval,
and analysis.

Routes:
    POST /api/v1/documents/upload - Upload document
    GET /api/v1/documents/{document_id} - Get document
    GET /api/v1/documents - List documents
    POST /api/v1/documents/{document_id}/process - Process document
    DELETE /api/v1/documents/{document_id} - Delete document
"""

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.database import execute_insert, execute_select
from app.models.document import DocumentStatus
from app.models.user import UserInDB
from app.services.aws_service import S3Service
from app.utils.auth_helpers import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)


router = APIRouter()

# File upload constraints
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md", ".ppt", ".pptx", ".xls", ".xlsx"}


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
async def get_document(document_id: str):
    """
    Get document by ID.

    Args:
        document_id: Document identifier

    Returns:
        Document data
    """
    # TODO: Implement get document
    logger.info(f"Get document endpoint called: {document_id}")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Get document endpoint not yet implemented",
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


@router.post("/{document_id}/process")
async def process_document(document_id: str):
    """
    Process document with AI analysis.

    Args:
        document_id: Document identifier

    Returns:
        Processing job information
    """
    # TODO: Implement document processing
    logger.info(f"Process document endpoint called: {document_id}")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Process document endpoint not yet implemented",
    )


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete document.

    Args:
        document_id: Document identifier

    Returns:
        Success message
    """
    # TODO: Implement delete document
    logger.info(f"Delete document endpoint called: {document_id}")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete document endpoint not yet implemented",
    )
