"""
Database Initialization Script

This script runs all database prepopulation tasks in the correct order.
Run this after running alembic migrations to initialize the database with default data.

Usage:
    python init_db.py
    # or in docker:
    docker exec app python init_db.py
"""

import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

from app.core.config import settings
from app.utils.telegram import send_telegram_msg
from app.database.get_session import engine

# Import all initialization tasks
from app.tasks.common.permissions import create_or_update_permissions
from app.tasks.common.roles import create_or_update_roles
from app.tasks.common.role_permissions import sync_role_permissions
from app.tasks.common.test_users import create_test_users
from app.tasks.common.fake_users import create_fake_users
from app.tasks.generals.countries import sync_countries


# Define all initialization tasks in order
INIT_TASKS = [
    {
        "name": "Permissions",
        "function": create_or_update_permissions,
        "description": "Creating/updating permissions",
    },
    {
        "name": "Roles",
        "function": create_or_update_roles,
        "description": "Creating/updating roles",
    },
    {
        "name": "Role Permissions",
        "function": sync_role_permissions,
        "description": "Syncing role-permission associations",
    },
    {
        "name": "Test Users",
        "function": create_test_users,
        "description": "Creating test users for each role",
    },
    {
        "name": "Fake Users",
        "function": create_fake_users,
        "description": "Creating fake users for testing",
    },
    {
        "name": "Countries",
        "function": sync_countries,
        "description": "Syncing countries data",
    },
]


async def run_initialization():
    """Run all initialization tasks in sequence."""
    start_time = datetime.now(timezone.utc)
    results = []

    print(f"\n{'='*60}")
    print(f"Starting Database Initialization")
    print(f"Environment: {settings.ENV.upper()}")
    print(f"App: {settings.APP_NAME}")
    print(f"{'='*60}\n")

    for task in INIT_TASKS:
        try:
            print(f"[{task['name']}] {task['description']}...")
            await task["function"]()
            results.append({"name": task["name"], "status": "success"})
            print(f"✅ [{task['name']}] Completed successfully\n")
            await asyncio.sleep(1)  # Small delay between tasks
        except Exception as e:
            error_msg = f"Error in {task['name']}: {str(e)}"
            print(f"❌ {error_msg}\n")
            results.append({"name": task["name"], "status": "failed", "error": str(e)})
            # Continue with other tasks even if one fails

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Summary
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    print(f"\n{'='*60}")
    print(f"Initialization Summary")
    print(f"{'='*60}")
    print(f"✅ Successful: {len(successful)}/{len(INIT_TASKS)}")
    if failed:
        print(f"❌ Failed: {len(failed)}/{len(INIT_TASKS)}")
        for task in failed:
            print(f"   - {task['name']}: {task.get('error', 'Unknown error')}")
    print(f"⏱️  Duration: {duration:.2f} seconds")
    print(f"{'='*60}\n")

    # Send summary to Telegram
    status_emoji = "✅" if not failed else "⚠️"
    msg = (
        f"*{settings.APP_NAME.upper()}::{settings.ENV.upper()}::Database Initialization Report*\n\n"
        f"{status_emoji} Tasks Completed: {len(successful)}/{len(INIT_TASKS)}\n"
    )
    if failed:
        msg += f"❌ Failed Tasks: {len(failed)}\n"
        for task in failed:
            msg += f"   - {task['name']}\n"
    msg += (
        f"⏱️ Duration: {duration:.2f}s\n"
        f"🕒 Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    send_telegram_msg(msg=msg)

    # Small delay to ensure all database operations complete
    await asyncio.sleep(0.5)

    # Properly dispose of the database engine before exiting
    await engine.dispose()

    # Additional small delay to allow engine disposal to complete
    await asyncio.sleep(0.1)

    if failed:
        return 1
    else:
        return 0


async def main():
    """Main entry point with proper cleanup."""
    try:
        return await run_initialization()
    except KeyboardInterrupt:
        print("\n\n⚠️  Initialization interrupted by user")
        await engine.dispose()
        return 1
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        await engine.dispose()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
