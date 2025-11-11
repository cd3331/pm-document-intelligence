#!/usr/bin/env python3
"""
Run database schema migration to add missing columns.
This script will be executed inside an ECS task.
"""

import os
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def run_migration():
    """Add missing processing columns to documents table."""

    # Get DATABASE_URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return 1

    # Convert postgresql:// to postgresql+asyncpg://
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)

    print("=" * 80)
    print("Database Schema Migration - Adding Missing Columns")
    print("=" * 80)
    print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else 'hidden'}")

    try:
        # Create async engine
        engine = create_async_engine(database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            print("\n✓ Connected to database\n")

            # Check existing columns
            print("Checking existing columns...")
            result = await session.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'documents'
                AND column_name IN ('processing_checkpoint', 'processing_state', 'error_message', 'risks', 'processing_metadata')
                ORDER BY column_name
            """))
            existing = result.fetchall()

            if existing:
                print(f"Found {len(existing)} existing columns:")
                for col, dtype in existing:
                    print(f"  - {col} ({dtype})")
            else:
                print("  No target columns exist yet")

            print("\nAdding missing columns...")

            # Add columns
            migrations = [
                ("processing_checkpoint", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_checkpoint JSONB DEFAULT NULL"),
                ("processing_state", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_state JSONB DEFAULT NULL"),
                ("error_message", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL"),
                ("risks", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS risks JSONB DEFAULT '[]'::jsonb"),
                ("processing_metadata", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_metadata JSONB DEFAULT '{}'::jsonb"),
            ]

            for col_name, sql in migrations:
                print(f"  [{col_name}]...", end=" ")
                await session.execute(text(sql))
                print("✓")

            print("\nCreating indexes...")

            # Create indexes
            indexes = [
                ("idx_documents_processing_checkpoint", """
                    CREATE INDEX IF NOT EXISTS idx_documents_processing_checkpoint
                    ON documents USING gin (processing_checkpoint)
                    WHERE processing_checkpoint IS NOT NULL
                """),
                ("idx_documents_processing_state", """
                    CREATE INDEX IF NOT EXISTS idx_documents_processing_state
                    ON documents USING gin (processing_state)
                    WHERE processing_state IS NOT NULL
                """),
                ("idx_documents_error_message", """
                    CREATE INDEX IF NOT EXISTS idx_documents_error_message
                    ON documents (error_message)
                    WHERE error_message IS NOT NULL
                """),
                ("idx_documents_risks", """
                    CREATE INDEX IF NOT EXISTS idx_documents_risks
                    ON documents USING gin (risks)
                """),
            ]

            for idx_name, sql in indexes:
                print(f"  [{idx_name}]...", end=" ")
                await session.execute(text(sql))
                print("✓")

            # Commit all changes
            await session.commit()

            print("\n" + "=" * 80)
            print("✅ DATABASE SCHEMA FIXED SUCCESSFULLY!")
            print("=" * 80)

            # Verify columns exist
            print("\nVerifying changes...")
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'documents'
                AND column_name IN ('processing_checkpoint', 'processing_state', 'error_message', 'risks', 'processing_metadata')
                ORDER BY column_name
            """))

            columns = result.fetchall()
            print(f"\n✓ All {len(columns)} columns now exist:\n")
            for col, dtype, nullable, default in columns:
                default_str = default[:30] if default else 'NULL'
                print(f"  • {col:25} {dtype:10} nullable={nullable} default={default_str}")

            print("\n" + "=" * 80)
            print("✅ Document processing should now work!")
            print("=" * 80)

        await engine.dispose()
        return 0

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(run_migration()))
