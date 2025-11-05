"""
Admin Routes for PM Document Intelligence.

This module provides administrative endpoints for system management.
"""

from fastapi import APIRouter, HTTPException, status

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
