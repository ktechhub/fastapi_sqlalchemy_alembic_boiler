#!/usr/bin/env python3
"""
MySQL Database Backup Script
Creates a MySQL dump and uploads it to S3 bucket.
"""
from dotenv import load_dotenv

load_dotenv()
import os
import sys
import subprocess
import boto3
from datetime import datetime, timezone
from botocore.client import Config
from pathlib import Path
import gzip
import shutil
import requests

# Environment variables
DB_HOST = os.getenv("DB_HOST", "mysql")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = "root"
DB_PASSWORD = os.getenv("DB_ROOT_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# S3 Configuration
S3_STORAGE_BUCKET = os.getenv("S3_STORAGE_BUCKET")
S3_STORAGE_HOST = os.getenv("S3_STORAGE_HOST")
S3_STORAGE_ACCESS_KEY = os.getenv("S3_STORAGE_ACCESS_KEY")
S3_STORAGE_SECRET_KEY = os.getenv("S3_STORAGE_SECRET_KEY")
S3_BACKUP_FOLDER = os.getenv("S3_BACKUP_FOLDER", "backups/mysql")

# Backup retention (days)
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))


TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def send_telegram_msg(msg):
    send_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&parse_mode=Markdown&text={msg}"
    response = requests.get(send_msg)
    return response.json()


def log(message):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def create_backup():
    """Create MySQL dump"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{DB_NAME}_backup_{timestamp}.sql"
    backup_path = Path("/tmp") / backup_filename

    log(f"Creating backup: {backup_filename}")

    # Create mysqldump command
    # Using environment variable for password to avoid command line warning
    # Removed --routines to avoid INFORMATION_SCHEMA.LIBRARIES error in some MySQL versions
    # If you need stored procedures, you can add --routines back, but it may fail on some MySQL configs
    cmd = [
        "mysqldump",
        f"--host={DB_HOST}",
        f"--port={DB_PORT}",
        f"--user={DB_USER}",
        "--single-transaction",
        "--triggers",
        "--events",
        "--no-tablespaces",
        "--skip-lock-tables",
        DB_NAME,
    ]

    # Set password via environment variable to avoid command line warning
    env = os.environ.copy()
    env["MYSQL_PWD"] = DB_PASSWORD

    try:
        # Run mysqldump and write to file
        with open(backup_path, "w") as f:
            result = subprocess.run(
                cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True, env=env
            )

        # Verify backup file was created and has content
        if backup_path.exists() and backup_path.stat().st_size > 0:
            log(
                f"Backup created successfully: {backup_path} ({backup_path.stat().st_size} bytes)"
            )
            return backup_path
        else:
            log(f"Error: Backup file was not created or is empty")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        # Check if file was created despite error (sometimes mysqldump outputs warnings to stderr)
        if backup_path.exists() and backup_path.stat().st_size > 0:
            log(
                f"Warning: mysqldump reported errors but backup file exists: {backup_path}"
            )
            log(f"Stderr output: {e.stderr[:300]}")
            return backup_path
        else:
            log(f"Error creating backup: {e.stderr}")
            sys.exit(1)
    except Exception as e:
        log(f"Error creating backup: {e}")
        sys.exit(1)


def compress_backup(backup_path):
    """Compress backup file using gzip"""
    compressed_path = Path(str(backup_path) + ".gz")

    log(f"Compressing backup: {compressed_path}")

    try:
        with open(backup_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove original file
        backup_path.unlink()
        log(f"Backup compressed: {compressed_path}")
        return compressed_path
    except Exception as e:
        log(f"Error compressing backup: {e}")
        sys.exit(1)


def upload_to_s3(file_path):
    """Upload backup file to S3"""
    log(f"Uploading to S3: {file_path.name}")

    # Initialize S3 client
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_STORAGE_HOST,
        aws_access_key_id=S3_STORAGE_ACCESS_KEY,
        aws_secret_access_key=S3_STORAGE_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )

    # S3 key (path in bucket)
    s3_key = f"{S3_BACKUP_FOLDER}/{file_path.name}"

    try:
        # Upload file
        with open(file_path, "rb") as f:
            s3.put_object(
                Bucket=S3_STORAGE_BUCKET,
                Key=s3_key,
                Body=f,
                ServerSideEncryption="AES256" if S3_STORAGE_HOST else None,
            )

        log(f"Backup uploaded successfully to s3://{S3_STORAGE_BUCKET}/{s3_key}")
        return s3_key
    except Exception as e:
        log(f"Error uploading to S3: {e}")
        sys.exit(1)


def cleanup_old_backups():
    """Delete old backups from S3 (older than retention period)"""
    if not BACKUP_RETENTION_DAYS:
        log("Backup retention disabled, skipping cleanup")
        return

    log(f"Cleaning up backups older than {BACKUP_RETENTION_DAYS} days")

    s3 = boto3.client(
        "s3",
        endpoint_url=S3_STORAGE_HOST,
        aws_access_key_id=S3_STORAGE_ACCESS_KEY,
        aws_secret_access_key=S3_STORAGE_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )

    try:
        # List all objects in backup folder
        response = s3.list_objects_v2(
            Bucket=S3_STORAGE_BUCKET, Prefix=f"{S3_BACKUP_FOLDER}/"
        )

        if "Contents" not in response:
            log("No backups found in S3")
            return

        cutoff_date = datetime.now().timestamp() - (BACKUP_RETENTION_DAYS * 24 * 3600)
        deleted_count = 0

        for obj in response["Contents"]:
            if obj["LastModified"].timestamp() < cutoff_date:
                s3.delete_object(Bucket=S3_STORAGE_BUCKET, Key=obj["Key"])
                log(f"Deleted old backup: {obj['Key']}")
                deleted_count += 1

        log(f"Cleanup complete: {deleted_count} old backup(s) deleted")
        return deleted_count
    except Exception as e:
        log(f"Error during cleanup: {e}")
        return 0


def cleanup_local_file(file_path):
    """Remove local backup file"""
    try:
        if file_path.exists():
            file_path.unlink()
            log(f"Local backup file removed: {file_path}")
    except Exception as e:
        log(f"Error removing local file: {e}")


def main():
    """Main backup process"""
    log("=" * 50)
    log("Starting MySQL backup process")
    log("=" * 50)

    # Validate required environment variables
    required_vars = [
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME",
        "S3_STORAGE_BUCKET",
        "S3_STORAGE_HOST",
        "S3_STORAGE_ACCESS_KEY",
        "S3_STORAGE_SECRET_KEY",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        log(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    backup_path = None
    compressed_path = None

    try:
        # Create backup
        backup_path = create_backup()

        # Compress backup
        compressed_path = compress_backup(backup_path)

        # Upload to S3
        upload_to_s3(compressed_path)

        # Cleanup old backups
        deleted_count = cleanup_old_backups()

        log("=" * 50)
        log("Backup process completed successfully")
        msg = (
            f"*PraiseExport::Backup Process Completed*\n\n"
            f"✅ Backup created successfully: {backup_path.name}\n"
            f"✅ Backup uploaded to S3: {compressed_path.name}\n"
            f"✅ Backup size: {compressed_path.stat().st_size / 1024 / 1024:.2f} MB\n"
            f"✅ Backup cleaned up: {deleted_count}\n"
            f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_msg(msg)
        log(msg)
        log("=" * 50)

    except Exception as e:
        log(f"Fatal error during backup: {e}")
        msg = (
            f"*PraiseExport::Backup Process Failed*\n\n"
            f"❌ Error: {e}\n"
            f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_msg(msg)
        log(msg)
        sys.exit(1)
    finally:
        # Cleanup local files
        if backup_path and backup_path.exists():
            cleanup_local_file(backup_path)
        if compressed_path and compressed_path.exists():
            cleanup_local_file(compressed_path)


if __name__ == "__main__":
    main()
