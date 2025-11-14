"""
Legacy test_users.py script

This file is kept for backward compatibility.
For new projects, use init_db.py instead.

Usage:
    python test_users.py  # Still works
    python init_db.py     # Recommended
"""

import asyncio
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

# Import from the new organized structure
from app.tasks.common.permissions import create_or_update_permissions
from app.tasks.common.roles import create_or_update_roles
from app.tasks.common.role_permissions import sync_role_permissions
from app.tasks.common.test_users import create_test_users
from app.tasks.common.fake_users import create_fake_users
from app.tasks.generals.countries import sync_countries


async def main():
    """Legacy main function - redirects to init_db.py logic."""
    try:
        await create_or_update_permissions()
        await asyncio.sleep(1)
        await create_or_update_roles()
        await asyncio.sleep(1)
        await sync_role_permissions()
        await asyncio.sleep(1)
        await create_test_users()
        await asyncio.sleep(1)
        await create_fake_users()
        await asyncio.sleep(1)
        await sync_countries()
    except Exception as e:
        print(f"Error in main(): {e}")


if __name__ == "__main__":
    print("⚠️  Note: This script is kept for backward compatibility.")
    print("   For new projects, use 'python init_db.py' instead.\n")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
