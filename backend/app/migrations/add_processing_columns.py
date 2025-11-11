"""
Database migration to add missing processing columns.

This migration adds columns required by DocumentProcessor:
- processing_checkpoint: Current processing step
- processing_state: Full processing state for resume
- error_message: Last error message if processing failed
- risks: Extracted risk items (if missing)
- processing_metadata: Additional metadata (if missing)

Run with:
    python -m app.migrations.add_processing_columns
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import get_db_session
from sqlalchemy import text


async def run_migration():
    """Run the database migration."""
    print("=" * 80)
    print("Adding missing processing columns to documents table")
    print("=" * 80)

    async with get_db_session() as session:
        try:
            # Add processing_checkpoint column
            print("\n1. Adding processing_checkpoint column...")
            await session.execute(
                text(
                    """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS processing_checkpoint JSONB DEFAULT NULL
                """
                )
            )
            print("   ✓ processing_checkpoint column added")

            # Add processing_state column
            print("\n2. Adding processing_state column...")
            await session.execute(
                text(
                    """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS processing_state JSONB DEFAULT NULL
                """
                )
            )
            print("   ✓ processing_state column added")

            # Add error_message column
            print("\n3. Adding error_message column...")
            await session.execute(
                text(
                    """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL
                """
                )
            )
            print("   ✓ error_message column added")

            # Add risks column if missing
            print("\n4. Adding risks column (if missing)...")
            await session.execute(
                text(
                    """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS risks JSONB DEFAULT '[]'::jsonb
                """
                )
            )
            print("   ✓ risks column added")

            # Add processing_metadata column if missing
            print("\n5. Adding processing_metadata column (if missing)...")
            await session.execute(
                text(
                    """
                ALTER TABLE documents
                ADD COLUMN IF NOT EXISTS processing_metadata JSONB DEFAULT '{}'::jsonb
                """
                )
            )
            print("   ✓ processing_metadata column added")

            # Create indexes
            print("\n6. Creating indexes for efficient querying...")

            await session.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_documents_processing_checkpoint
                ON documents USING gin (processing_checkpoint)
                WHERE processing_checkpoint IS NOT NULL
                """
                )
            )
            print("   ✓ Index on processing_checkpoint created")

            await session.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_documents_processing_state
                ON documents USING gin (processing_state)
                WHERE processing_state IS NOT NULL
                """
                )
            )
            print("   ✓ Index on processing_state created")

            await session.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_documents_error_message
                ON documents (error_message)
                WHERE error_message IS NOT NULL
                """
                )
            )
            print("   ✓ Index on error_message created")

            await session.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_documents_risks
                ON documents USING gin (risks)
                """
                )
            )
            print("   ✓ Index on risks created")

            # Commit the changes
            await session.commit()
            print("\n" + "=" * 80)
            print("✅ Migration completed successfully!")
            print("=" * 80)
            print("\nColumns added to documents table:")
            print("  - processing_checkpoint (JSONB)")
            print("  - processing_state (JSONB)")
            print("  - error_message (TEXT)")
            print("  - risks (JSONB)")
            print("  - processing_metadata (JSONB)")
            print("\nIndexes created for efficient querying")

        except Exception as e:
            await session.rollback()
            print("\n" + "=" * 80)
            print(f"❌ Migration failed: {e}")
            print("=" * 80)
            raise


if __name__ == "__main__":
    asyncio.run(run_migration())
