"""
Admin Routes for PM Document Intelligence.

This module provides administrative endpoints for system management.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.database import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_system_stats():
    """Get system statistics."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin stats endpoint not yet implemented",
    )


@router.post("/migrate-processing-columns")
async def migrate_processing_columns():
    """
    Add missing processing columns to documents table.

    This endpoint adds the following columns if they don't exist:
    - processing_checkpoint: JSONB for checkpoint tracking
    - processing_state: JSONB for state tracking
    - error_message: TEXT for error messages
    - risks: JSONB for risk tracking
    - processing_metadata: JSONB for metadata

    Returns:
        Success message with list of added columns
    """
    try:
        logger.info("Starting database migration for processing columns")

        async with get_db() as session:
            # Add missing columns
            migrations = [
                (
                    "processing_checkpoint",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_checkpoint JSONB DEFAULT NULL",
                ),
                (
                    "processing_state",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_state JSONB DEFAULT NULL",
                ),
                (
                    "error_message",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL",
                ),
                (
                    "risks",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS risks JSONB DEFAULT '[]'::jsonb",
                ),
                (
                    "processing_metadata",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_metadata JSONB DEFAULT '{}'::jsonb",
                ),
                (
                    "processed_at",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP WITH TIME ZONE",
                ),
                (
                    "extraction_method",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_method TEXT",
                ),
                (
                    "processing_duration",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_duration FLOAT",
                ),
                (
                    "analysis.summary",
                    "ALTER TABLE analysis ADD COLUMN IF NOT EXISTS summary TEXT",
                ),
                (
                    "analysis.processing_cost",
                    "ALTER TABLE analysis ADD COLUMN IF NOT EXISTS processing_cost FLOAT",
                ),
            ]

            added_columns = []
            for column_name, query in migrations:
                logger.info(f"Adding column: {column_name}")
                await session.execute(text(query))
                added_columns.append(column_name)

            # Create indexes
            logger.info("Creating indexes")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_documents_processing_checkpoint ON documents USING gin (processing_checkpoint) WHERE processing_checkpoint IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS idx_documents_processing_state ON documents USING gin (processing_state) WHERE processing_state IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS idx_documents_error_message ON documents (error_message) WHERE error_message IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS idx_documents_risks ON documents USING gin (risks)",
            ]

            for index_query in indexes:
                await session.execute(text(index_query))

            # Commit all changes
            await session.commit()

            logger.info("Database migration completed successfully")

            return {
                "success": True,
                "message": "Migration completed successfully",
                "columns_added": added_columns,
                "indexes_created": 4,
            }

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}",
        )
