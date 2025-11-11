#!/usr/bin/env python3
"""
Fix database schema by adding missing columns to documents table.
Connects directly to RDS PostgreSQL.
"""

import sys
import urllib.parse

# Install psycopg2 if needed
try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])
    import psycopg2

# RDS Database connection
DATABASE_URL = "postgresql://pmadmin:D$%WyQqhMQf#NQS7X#hH}:juE0VUU)(e@pm-doc-intel-db-production.c6ns4qaggh0y.us-east-1.rds.amazonaws.com:5432/pm_document_intelligence"

def fix_schema():
    """Add missing columns to documents table."""
    print("=" * 80)
    print("Fixing Database Schema - Adding Missing Columns")
    print("=" * 80)
    print(f"\nConnecting to RDS PostgreSQL...")
    print(f"Database: pm_document_intelligence")
    print(f"Endpoint: pm-doc-intel-db-production.c6ns4qaggh0y.us-east-1.rds.amazonaws.com")

    try:
        # Direct connection parameters
        conn = psycopg2.connect(
            host="pm-doc-intel-db-production.c6ns4qaggh0y.us-east-1.rds.amazonaws.com",
            port=5432,
            database="pm_document_intelligence",
            user="pmadmin",
            password="D$%WyQqhMQf#NQS7X#hH}:juE0VUU)(e",
            connect_timeout=10
        )

        conn.autocommit = False
        cursor = conn.cursor()

        print("✓ Connected successfully\n")

        # Check current columns
        print("Checking existing columns...")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'documents'
            AND column_name IN ('processing_checkpoint', 'processing_state', 'error_message', 'risks', 'processing_metadata')
            ORDER BY column_name
        """)
        existing = cursor.fetchall()

        if existing:
            print(f"Found {len(existing)} existing columns:")
            for col, dtype in existing:
                print(f"  - {col} ({dtype})")
        else:
            print("  No target columns exist yet")

        print("\nAdding missing columns...")

        # Add columns one by one
        columns_to_add = [
            ("processing_checkpoint", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_checkpoint JSONB DEFAULT NULL"),
            ("processing_state", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_state JSONB DEFAULT NULL"),
            ("error_message", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL"),
            ("risks", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS risks JSONB DEFAULT '[]'::jsonb"),
            ("processing_metadata", "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_metadata JSONB DEFAULT '{}'::jsonb"),
        ]

        for col_name, sql in columns_to_add:
            print(f"  [{col_name}]...", end=" ")
            cursor.execute(sql)
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
            cursor.execute(sql)
            print("✓")

        # Commit all changes
        conn.commit()

        print("\n" + "=" * 80)
        print("✅ DATABASE SCHEMA FIXED SUCCESSFULLY!")
        print("=" * 80)

        # Verify columns exist
        print("\nVerifying changes...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'documents'
            AND column_name IN ('processing_checkpoint', 'processing_state', 'error_message', 'risks', 'processing_metadata')
            ORDER BY column_name
        """)

        columns = cursor.fetchall()
        print(f"\n✓ All {len(columns)} columns now exist:\n")
        for col, dtype, nullable, default in columns:
            print(f"  • {col:25} {dtype:10} nullable={nullable} default={default[:30] if default else 'NULL'}")

        # Check indexes
        cursor.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'documents'
            AND indexname LIKE 'idx_documents_%ing%'
            ORDER BY indexname
        """)
        indexes_list = cursor.fetchall()
        print(f"\n✓ Created {len(indexes_list)} indexes:\n")
        for idx in indexes_list:
            print(f"  • {idx[0]}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 80)
        print("✅ Document processing should now work!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Wait for latest code deployment to complete")
        print("2. Go to https://app.joyofpm.com")
        print("3. Upload a document (PDF, TXT, or image)")
        print("4. Click 'Process Document'")
        print("5. Wait 30-60 seconds for processing to complete")
        print("\n✅ Processing should now work without errors!\n")

        return 0

    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nPossible causes:")
        print("1. Network connectivity issue")
        print("2. RDS security group not allowing connections")
        print("3. Database credentials incorrect")
        return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return 1

if __name__ == "__main__":
    sys.exit(fix_schema())
