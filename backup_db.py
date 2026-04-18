#!/usr/bin/env python3
"""
MySQL Database Backup Script
Creates a MySQL dump and uploads it to S3 bucket.
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()
from app.tasks.internal.backup_db import backup_database


def main():
    asyncio.run(backup_database())


if __name__ == "__main__":
    main()
