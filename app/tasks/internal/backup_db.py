import asyncio
import os
import gzip
import shutil
from datetime import datetime, timezone
from pathlib import Path
from botocore.client import Config
import boto3

from app.core.config import settings
from app.core.loggers import scheduler_logger as logger
from app.utils.telegram import send_telegram_msg

# Backup retention (days) - default 30
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
S3_BACKUP_FOLDER = os.getenv("S3_BACKUP_FOLDER", "backups/mysql")
BACKUP_GZIP_LEVEL = int(os.getenv("BACKUP_GZIP_LEVEL", "1"))
BACKUP_ENABLE_NICE = os.getenv("BACKUP_ENABLE_NICE", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
BACKUP_NICE_LEVEL = int(os.getenv("BACKUP_NICE_LEVEL", "15"))
BACKUP_ENABLE_IONICE = os.getenv("BACKUP_ENABLE_IONICE", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
BACKUP_IONICE_CLASS = os.getenv("BACKUP_IONICE_CLASS", "3")


async def create_backup():
    """Create and stream-compress a MySQL dump to disk."""
    # Only run if DB_ENGINE is mysql
    if settings.DB_ENGINE != "mysql":
        logger.info(
            f"Skipping backup - DB_ENGINE is '{settings.DB_ENGINE}', backup only supports MySQL"
        )
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{settings.DB_NAME}_backup_{timestamp}.sql.gz"
    backup_path = Path("/tmp") / backup_filename

    logger.info(f"Creating backup: {backup_filename}")

    # Use root user and root password for backup access
    db_root_password = settings.DB_ROOT_PASSWORD or os.getenv("DB_ROOT_PASSWORD")
    if not db_root_password:
        logger.error("Error: DB_ROOT_PASSWORD is required for backups")
        return None

    # Create mysqldump command
    dump_cmd = [
        "mysqldump",
        f"--host={settings.DB_HOST}",
        f"--port={settings.DB_PORT}",
        "--user=root",
        "--single-transaction",
        "--triggers",
        "--events",
        "--no-tablespaces",
        "--skip-lock-tables",
        settings.DB_NAME,
    ]
    cmd = []
    if BACKUP_ENABLE_IONICE and shutil.which("ionice"):
        cmd.extend(["ionice", "-c", str(BACKUP_IONICE_CLASS)])
    if BACKUP_ENABLE_NICE and shutil.which("nice"):
        cmd.extend(["nice", "-n", str(BACKUP_NICE_LEVEL)])
    cmd.extend(dump_cmd)
    logger.info(f"Backup command priority tuning: {' '.join(cmd[:6])} ...")

    # Set password via environment variable to avoid command line warning
    env = os.environ.copy()
    env["MYSQL_PWD"] = db_root_password

    try:
        # Run mysqldump asynchronously and stream output to gzip file.
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        async def _drain_stderr(stream):
            chunks = []
            while True:
                chunk = await stream.read(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)

        stderr_task = asyncio.create_task(_drain_stderr(process.stderr))
        total_uncompressed_bytes = 0

        with gzip.open(
            backup_path, "wb", compresslevel=max(1, min(9, BACKUP_GZIP_LEVEL))
        ) as gz_out:
            while True:
                chunk = await process.stdout.read(1024 * 1024)
                if not chunk:
                    break
                total_uncompressed_bytes += len(chunk)
                gz_out.write(chunk)

        return_code = await process.wait()
        stderr_bytes = await stderr_task

        # Verify backup file was created and has content
        if return_code == 0 and backup_path.exists() and backup_path.stat().st_size > 0:
            logger.info(
                f"Backup created successfully: {backup_path} "
                f"(gzip={backup_path.stat().st_size} bytes, raw≈{total_uncompressed_bytes} bytes)"
            )
            return backup_path

        error_msg = (
            stderr_bytes.decode(errors="ignore")
            if stderr_bytes
            else f"mysqldump exited with code {return_code}"
        )
        logger.error(f"Error: Backup file was not created or is empty. {error_msg}")
        if backup_path.exists():
            backup_path.unlink()
        return None

    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        if backup_path.exists():
            backup_path.unlink()
        return None


def compress_backup(backup_path):
    """No-op: backup is already created as .sql.gz."""
    return backup_path


def upload_to_s3(file_path):
    """Upload backup file to S3"""
    logger.info(f"Uploading to S3: {file_path.name}")

    # Initialize S3 client
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.S3_STORAGE_HOST,
        aws_access_key_id=settings.S3_STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.S3_STORAGE_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )

    # S3 key (path in bucket)
    s3_key = f"{S3_BACKUP_FOLDER}/{file_path.name}"

    try:
        # Upload file
        with open(file_path, "rb") as f:
            s3.put_object(
                Bucket=settings.S3_STORAGE_BUCKET,
                Key=s3_key,
                Body=f,
                ServerSideEncryption="AES256" if settings.S3_STORAGE_HOST else None,
            )

        logger.info(
            f"Backup uploaded successfully to s3://{settings.S3_STORAGE_BUCKET}/{s3_key}"
        )
        return s3_key
    except Exception as e:
        logger.error(f"Error uploading to S3: {e}")
        return None


def cleanup_old_backups():
    """Delete old backups from S3 (older than retention period)"""
    if not BACKUP_RETENTION_DAYS:
        logger.info("Backup retention disabled, skipping cleanup")
        return 0

    logger.info(f"Cleaning up backups older than {BACKUP_RETENTION_DAYS} days")

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.S3_STORAGE_HOST,
        aws_access_key_id=settings.S3_STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.S3_STORAGE_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )

    try:
        # List all objects in backup folder
        response = s3.list_objects_v2(
            Bucket=settings.S3_STORAGE_BUCKET, Prefix=f"{S3_BACKUP_FOLDER}/"
        )

        if "Contents" not in response:
            logger.info("No backups found in S3")
            return 0

        cutoff_date = datetime.now().timestamp() - (BACKUP_RETENTION_DAYS * 24 * 3600)
        deleted_count = 0

        for obj in response["Contents"]:
            if obj["LastModified"].timestamp() < cutoff_date:
                s3.delete_object(Bucket=settings.S3_STORAGE_BUCKET, Key=obj["Key"])
                logger.info(f"Deleted old backup: {obj['Key']}")
                deleted_count += 1

        logger.info(f"Cleanup complete: {deleted_count} old backup(s) deleted")
        return deleted_count
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return 0


def cleanup_local_file(file_path):
    """Remove local backup file"""
    try:
        if file_path and file_path.exists():
            file_path.unlink()
            logger.info(f"Local backup file removed: {file_path}")
    except Exception as e:
        logger.error(f"Error removing local file: {e}")


async def backup_database():
    """
    Main backup process - creates MySQL dump, compresses it, uploads to S3, and cleans up old backups
    """
    logger.info("=" * 50)
    logger.info("Starting MySQL backup process")
    logger.info("=" * 50)

    # Validate required settings
    if settings.DB_ENGINE != "mysql":
        logger.info(
            f"Skipping backup - DB_ENGINE is '{settings.DB_ENGINE}', backup only supports MySQL"
        )
        return

    # Check for root password (from settings or env)
    db_root_password = settings.DB_ROOT_PASSWORD or os.getenv("DB_ROOT_PASSWORD")

    required_settings = [
        settings.DB_HOST,
        settings.DB_PORT,
        db_root_password,
        settings.DB_NAME,
        settings.S3_STORAGE_BUCKET,
        settings.S3_STORAGE_HOST,
        settings.S3_STORAGE_ACCESS_KEY,
        settings.S3_STORAGE_SECRET_KEY,
    ]

    if not all(required_settings):
        logger.error("Error: Missing required settings for backup")
        msg = (
            f"*{settings.APP_NAME}@{settings.ENV.upper()}::Backup Process Failed*\n\n"
            f"❌ Error: Missing required settings\n"
            f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_msg(msg=msg)
        return

    backup_path = None
    compressed_path = None

    try:
        # Create backup
        backup_path = await create_backup()
        if not backup_path:
            raise Exception("Failed to create backup")

        # Already compressed in create_backup()
        compressed_path = compress_backup(backup_path)
        if not compressed_path:
            raise Exception("Failed to compress backup")

        # Upload to S3
        s3_key = upload_to_s3(compressed_path)
        if not s3_key:
            raise Exception("Failed to upload backup to S3")

        # Cleanup old backups
        deleted_count = cleanup_old_backups()

        logger.info("=" * 50)
        logger.info("Backup process completed successfully")
        msg = (
            f"*{settings.APP_NAME}@{settings.ENV.upper()}::Backup Process Completed*\n\n"
            f"✅ Backup created successfully: {backup_path.name}\n"
            f"✅ Backup uploaded to S3: {compressed_path.name}\n"
            f"✅ Backup size: {compressed_path.stat().st_size / 1024 / 1024:.2f} MB\n"
            f"✅ Old backups cleaned up: {deleted_count}\n"
            f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_msg(msg=msg)
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Fatal error during backup: {e}")
        msg = (
            f"*{settings.APP_NAME}@{settings.ENV.upper()}::Backup Process Failed*\n\n"
            f"❌ Error: {e}\n"
            f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_msg(msg=msg)
    finally:
        # Cleanup local files
        if backup_path and backup_path.exists():
            cleanup_local_file(backup_path)
        if compressed_path and compressed_path.exists():
            cleanup_local_file(compressed_path)
