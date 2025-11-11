#!/usr/bin/env python3
"""
Quick database migration script to add missing columns.
Uses psycopg2 to connect directly to the database.
"""

import os
import sys

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("Installing psycopg2...")
    os.system("pip install psycopg2-binary")
    import psycopg2
    from psycopg2 import sql

# Database connection string from .env
DATABASE_URL = "postgresql://postgres:n&w2V!g&oGYi@db.dzsnzgtevbdqczjieslk.supabase.co:5432/postgres"

def run_migration():
    """Run the database migration."""
    print("=" * 80)
    print("Adding Missing Processing Columns to Documents Table")
    print("=" * 80)

    try:
        # Connect to database
        print("\nConnecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cursor = conn.cursor()
        print("✓ Connected successfully")

        migrations = [
            ("processing_checkpoint", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_checkpoint JSONB DEFAULT NULL"),
            ("processing_state", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_state JSONB DEFAULT NULL"),
            ("error_message", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL"),
            ("risks", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS risks JSONB DEFAULT '[]'::jsonb"),
            ("processing_metadata", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_metadata JSONB DEFAULT '{}'::jsonb"),
        ]

        # Run migrations
        print("\nAdding columns...")
        for column_name, query in migrations:
            print(f"  - Adding {column_name}...", end=" ")
            cursor.execute(query)
            print("✓")

        # Create indexes
        print("\nCreating indexes...")
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

        for index_name, query in indexes:
            print(f"  - Creating {index_name}...", end=" ")
            cursor.execute(query)
            print("✓")

        # Commit changes
        conn.commit()

        print("\n" + "=" * 80)
        print("✅ Migration Completed Successfully!")
        print("=" * 80)
        print("\nColumns added:")
        print("  • processing_checkpoint (JSONB)")
        print("  • processing_state (JSONB)")
        print("  • error_message (TEXT)")
        print("  • risks (JSONB)")
        print("  • processing_metadata (JSONB)")
        print("\n4 indexes created for efficient querying")

        # Close connection
        cursor.close()
        conn.close()

        return 0

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return 1

if __name__ == "__main__":
    sys.exit(run_migration())
