from datetime import datetime
from io import BytesIO
import base64
import hashlib
import boto3
import time
from botocore.client import Config
from app.core.config import settings
from app.core.loggers import app_logger as logger


async def save_file_to_s3(
    file_object,
    extension=".png",
    folder="general",
    access_type="private",
    expires_in=3600 * 24 * 7,  # 7 days (max allowed by AWS S3)
) -> str:
    """
    Save a file object to an S3 bucket using direct upload with explicit hash handling.

    :param file_object: The file object to upload, expected to have a .file attribute.
    :param extension: The file extension, default is '.png'.
    :param folder: The folder within the bucket where the file will be stored.
    :param access_type: Determines the ACL for the file, 'public' for public-read access, 'private' otherwise.
    :param expires_in: The expiration time in seconds for the pre-signed URL if the file is private if access_type is private (default is 7 days, max allowed by AWS S3).
    :return: The public or private URL of the uploaded file.
    """
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.S3_STORAGE_HOST,
        aws_access_key_id=settings.S3_STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.S3_STORAGE_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )

    try:
        # Reset file position
        if hasattr(file_object, "seek"):
            file_object.seek(0)

        # Read the entire file content
        if hasattr(file_object, "read"):
            content = file_object.read()
            # Check if content is a coroutine (async function)
            if hasattr(content, "__await__"):
                content = await content
        else:
            content = file_object.file.read()
            # Check if content is a coroutine (async function)
            if hasattr(content, "__await__"):
                content = await content

        # Ensure content is bytes
        if isinstance(content, str):
            content = content.encode("utf-8")

        # Calculate SHA256 hash for file integrity
        # content_hash = hashlib.sha256(content).hexdigest()
        # Calculate SHA256 digest (bytes)
        sha256_digest = hashlib.sha256(content).digest()

        # Base64 encode for the ChecksumSHA256 param
        checksum_b64 = base64.b64encode(sha256_digest).decode("utf-8")

        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        filename = f"{folder}/{timestamp}{extension}"

        # Prepare headers with explicit hash
        headers = {
            # "x-amz-content-sha256": content_hash,
            "x-amz-content-sha256": checksum_b64,
            "x-amz-acl": "public-read" if access_type == "public" else "private",
            "Content-Type": (
                f"image/{extension.lstrip('.')}"
                if extension.startswith(".")
                else f"image/{extension}"
            ),
        }

        # Upload directly using put_object
        response = s3.put_object(
            Bucket=settings.S3_STORAGE_BUCKET,
            Key=filename,
            Body=content,
            ContentType=headers["Content-Type"],
            ACL=headers["x-amz-acl"],
            # ChecksumSHA256=content_hash,
            ChecksumSHA256=checksum_b64,
        )

        # Handle expiration logic
        if expires_in and access_type == "private":
            # Generate pre-signed URL for private files with expiration
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.S3_STORAGE_BUCKET,
                    "Key": filename,
                },
                ExpiresIn=expires_in,
            )
            return presigned_url
        else:
            # Return direct URL for public files or private files without expiration
            return f"{settings.S3_STORAGE_HOST}/{settings.S3_STORAGE_BUCKET}/{filename}"

    except Exception as e:
        logger.error(f"Full error details: {type(e).__name__}: {str(e)}")

        # Add debug information
        if "content" in locals():
            print(f"Content type: {type(content)}")
            if hasattr(content, "__await__"):
                print(
                    "Content is a coroutine - this indicates an async function was not awaited"
                )
            elif hasattr(content, "__len__"):
                print(f"Content length: {len(content)}")
                if len(content) > 0:
                    print(f"First few bytes: {content[:50]}")
            else:
                print("Content has no length attribute")

        raise Exception(f"Failed to upload file to S3: {str(e)}")


async def save_bytesio_to_s3(
    file_bytes: BytesIO,
    extension=".csv",
    folder="exports",
    access_type="private",
    expires_in=3600 * 24 * 7,  # 7 days (max allowed by AWS S3)
) -> str:
    """
    Save an io.BytesIO file to S3 bucket.

    :param file_bytes: The file in BytesIO format.
    :param extension: The file extension, default is '.csv'.
    :param folder: The folder within the bucket where the file will be stored.
    :param access_type: Determines the ACL for the file, 'public' for public-read access, 'private' otherwise.
    :param expires_in: The expiration time in seconds for the pre-signed URL if the file is private if access_type is private (default is 7 days, max allowed by AWS S3).
    :return: The public or private URL of the uploaded file.
    """
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.S3_STORAGE_HOST,
        aws_access_key_id=settings.S3_STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.S3_STORAGE_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )

    try:
        # Reset file position before reading
        file_bytes.seek(0)

        # Read file content
        content = file_bytes.read()

        # Ensure content is bytes
        if not isinstance(content, bytes):
            raise ValueError("File content must be in bytes format")

        # Calculate SHA256 hash for file integrity
        # content_hash = hashlib.sha256(content).hexdigest()
        # Calculate SHA256 digest (bytes)
        sha256_digest = hashlib.sha256(content).digest()

        # Base64 encode for the ChecksumSHA256 param
        checksum_b64 = base64.b64encode(sha256_digest).decode("utf-8")

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        filename = f"{folder}/{timestamp}{extension}"

        # Prepare S3 headers
        headers = {
            # "x-amz-content-sha256": content_hash,
            "x-amz-content-sha256": checksum_b64,
            "x-amz-acl": "public-read" if access_type == "public" else "private",
            "Content-Type": (
                "text/csv" if extension == ".csv" else "application/octet-stream"
            ),
        }

        # Upload file to S3
        s3.put_object(
            Bucket=settings.S3_STORAGE_BUCKET,
            Key=filename,
            Body=content,
            ContentType=headers["Content-Type"],
            ACL=headers["x-amz-acl"],
            #   ChecksumSHA256=content_hash,
            ChecksumSHA256=checksum_b64,
        )

        # Handle expiration logic
        if expires_in and access_type == "private":
            # Generate pre-signed URL for private files with expiration
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.S3_STORAGE_BUCKET,
                    "Key": filename,
                },
                ExpiresIn=expires_in,
            )
            return presigned_url
        else:
            # Return direct URL for public files or private files without expiration
            return f"{settings.S3_STORAGE_HOST}/{settings.S3_STORAGE_BUCKET}/{filename}"

    except Exception as e:
        raise Exception(f"Failed to upload BytesIO file to S3: {str(e)}")


def get_private_file_url(full_url, expires_in=3600 * 24 * 30):
    """
    Generates a pre-signed URL for accessing private files in Object Storage.
    If the input URL is already a pre-signed URL, it will be returned as-is.

    :param full_url: The complete URL of the file (e.g., 'https://host/bucket/media/users/1729174884.288935_hero_person.png').
    :param expires_in: The expiration time in seconds for the pre-signed URL if the file is private if access_type is private (default is 7 days, max allowed by AWS S3).
    :return: A pre-signed URL that allows temporary access to the private file.
    """
    # Remove query parameters to get the base URL (in case it's an expired pre-signed URL)
    base_url = full_url.split("?")[0]

    # Extract file key from the base URL
    try:
        file_key = base_url.split(
            f"{settings.S3_STORAGE_HOST}/{settings.S3_STORAGE_BUCKET}/"
        )[-1]
    except IndexError:
        # If the URL doesn't match the expected pattern, try to extract from the end
        file_key = base_url.split("/")[-1]

    # Initialize the S3 client
    session = boto3.session.Session()
    s3 = session.client(
        "s3",
        endpoint_url=settings.S3_STORAGE_HOST,
        aws_access_key_id=settings.S3_STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.S3_STORAGE_SECRET_KEY,
    )

    try:
        # Generate the pre-signed URL
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.S3_STORAGE_BUCKET,
                "Key": file_key,
            },
            ExpiresIn=expires_in,
        )
        return presigned_url

    except Exception as e:
        logger.error(f"Failed to generate pre-signed URL: {str(e)}")
        raise Exception(f"Failed to generate pre-signed URL: {str(e)}")
