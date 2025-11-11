#!/usr/bin/env python3
"""
Database Migration Script for PM Document Intelligence.

This script initializes the database schema in production AWS RDS.
Run this once after deploying to create all required tables.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


async def run_migration():
    """Execute database schema migration using raw asyncpg."""

    # Read schema SQL
    # Due to directory structure, SQL file is at /app/scripts/scripts/
    schema_path = Path("/app/scripts/scripts/init_database.sql")

    if not schema_path.exists():
        print(f"❌ Schema file not found: {schema_path}")
        return False

    print(f"📖 Reading schema from: {schema_path}")
    with open(schema_path, "r") as f:
        schema_sql = f.read()

    print("🔌 Connecting to database...")

    # Import asyncpg and settings
    import asyncpg
    from app.config import settings

    # Get database URL and clean it for asyncpg (remove +asyncpg driver)
    database_url = str(settings.get_database_url(async_driver=False))

    # Connect using raw asyncpg (supports multi-statement SQL)
    conn = None
    try:
        conn = await asyncpg.connect(database_url)

        print("⚙️  Executing schema creation...")

        # Execute the multi-statement SQL file
        # asyncpg supports executing multiple statements in one call
        await conn.execute(schema_sql)

        print("✅ Schema created successfully!")

        # Verify tables
        tables = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        )

        print(f"\n📊 Created {len(tables)} tables:")
        for table in tables:
            print(f"   - {table['table_name']}")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        if conn:
            await conn.close()
            print("🔌 Database connection closed")


if __name__ == "__main__":
    print("=" * 70)
    print("  PM Document Intelligence - Database Migration")
    print("=" * 70 + "\n")

    success = asyncio.run(run_migration())

    if success:
        print("\n" + "=" * 70)
        print("  ✅ Migration Complete!")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("  ❌ Migration Failed")
        print("=" * 70)
        sys.exit(1)
