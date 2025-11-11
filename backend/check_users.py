#!/usr/bin/env python3
"""Quick script to check users in database."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import asyncpg
from app.config import settings


async def check_users():
    """Check users in database."""
    database_url = str(settings.get_database_url(async_driver=False))

    conn = await asyncpg.connect(database_url)

    try:
        users = await conn.fetch(
            """
            SELECT id, email, full_name, role, created_at, email_verified
            FROM users
            ORDER BY created_at DESC
            LIMIT 10
        """
        )

        print(f"\n✅ Found {len(users)} users in database:\n")
        for user in users:
            print(f"  📧 {user['email']}")
            print(f"     Name: {user['full_name']}")
            print(f"     Role: {user['role']}")
            print(f"     Created: {user['created_at']}")
            print(f"     Verified: {user['email_verified']}")
            print()

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(check_users())
    sys.exit(0 if success else 1)
