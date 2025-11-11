#!/usr/bin/env python3
"""
Database migration script for PM Document Intelligence.

This script runs database schema migrations. It's designed to be run from
GitHub Actions during deployments or manually via the admin API endpoint.

Usage:
    python3 scripts/run_migrations.py

Environment variables required:
    - DATABASE_URL: PostgreSQL connection string
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_migrations():
    """Run all database migrations."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    # Convert postgres:// to postgresql+asyncpg://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    logger.info(f"Connecting to database...")

    engine = create_async_engine(database_url, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session_maker() as session:
            logger.info("Connected to database successfully")

            # Define migrations
            migrations = [
                (
                    "documents.file_type",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_type TEXT",
                ),
                (
                    "documents.extraction_method",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_method TEXT",
                ),
                (
                    "documents.processing_duration",
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
                (
                    "analysis.processing_duration",
                    "ALTER TABLE analysis ADD COLUMN IF NOT EXISTS processing_duration FLOAT",
                ),
            ]

            logger.info(f"Running {len(migrations)} migrations...")
            added_columns = []

            for column_name, query in migrations:
                try:
                    logger.info(f"  [{column_name}] Running migration...")
                    await session.execute(text(query))
                    await session.commit()
                    added_columns.append(column_name)
                    logger.info(f"  [{column_name}] ✓ Success")
                except Exception as e:
                    logger.error(f"  [{column_name}] ✗ Failed: {e}")
                    await session.rollback()
                    # Continue with other migrations even if one fails
                    continue

            # Create indexes
            logger.info("Creating indexes...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_documents_processing_checkpoint ON documents USING gin (processing_checkpoint) WHERE processing_checkpoint IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS idx_documents_processing_state ON documents USING gin (processing_state) WHERE processing_state IS NOT NULL",
                "CREATE INDEX IF NOT EXISTS idx_documents_user_status ON documents (user_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_analysis_document_id ON analysis (document_id)",
                "CREATE INDEX IF NOT EXISTS idx_analysis_user_id ON analysis (user_id)",
            ]

            for index_query in indexes:
                try:
                    logger.info(f"  Creating index...")
                    await session.execute(text(index_query))
                    await session.commit()
                    logger.info(f"  ✓ Index created")
                except Exception as e:
                    logger.error(f"  ✗ Index creation failed: {e}")
                    await session.rollback()
                    continue

            logger.info("=" * 60)
            logger.info(f"✅ Migration completed successfully!")
            logger.info(f"   Added/verified {len(added_columns)} columns")
            logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migrations())
