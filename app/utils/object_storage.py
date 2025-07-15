from datetime import datetime
from io import BytesIO
import hashlib
import boto3
import time
from botocore.client import Config
from app.core.config import settings


async def save_file_to_s3(
    file_object, extension=".png", folder="general", access_type="public"
) -> str:
    """
    Save a file object to an S3 bucket using direct upload with explicit hash handling.

    :param file_object: The file object to upload, expected to have a .file attribute.
    :param extension: The file extension, default is '.png'.
    :param folder: The folder within the bucket where the file will be stored.
    :param access_type: Determines the ACL for the file, 'public' for public-read access, 'private' otherwise.
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
            await file_object.seek(0)

        # Read the entire file content
        if hasattr(file_object, "read"):
            content = await file_object.read()
        else:
            content = file_object.file.read()

        # Ensure content is bytes
        if isinstance(content, str):
            content = content.encode("utf-8")

        # Calculate SHA256 hash
        content_hash = hashlib.sha256(content).hexdigest()

        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        filename = f"{folder}/{timestamp}{extension}"

        # Prepare headers with explicit hash
        headers = {
            "x-amz-content-sha256": content_hash,
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
            ChecksumSHA256=content_hash,
        )

        return f"{settings.S3_STORAGE_HOST}/{settings.S3_STORAGE_BUCKET}/{filename}"

    except Exception as e:
        print(f"Full error details: {type(e).__name__}: {str(e)}")

        # Add debug information
        if "content" in locals():
            print(f"Content length: {len(content)}")
            print(f"Content type: {type(content)}")
            if len(content) > 0:
                print(f"First few bytes: {content[:50]}")

        raise Exception(f"Failed to upload file to S3: {str(e)}")


async def save_bytesio_to_s3(
    file_bytes: BytesIO, extension=".csv", folder="exports", access_type="public"
) -> str:
    """
    Save an io.BytesIO file to S3 bucket.

    :param file_bytes: The file in BytesIO format.
    :param extension: The file extension, default is '.csv'.
    :param folder: The folder within the bucket where the file will be stored.
    :param access_type: Determines the ACL for the file, 'public' for public-read access, 'private' otherwise.
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
        content_hash = hashlib.sha256(content).hexdigest()

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        filename = f"{folder}/{timestamp}{extension}"

        # Prepare S3 headers
        headers = {
            "x-amz-content-sha256": content_hash,
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
            ChecksumSHA256=content_hash,
        )

        return f"{settings.S3_STORAGE_HOST}/{settings.S3_STORAGE_BUCKET}/{filename}"

    except Exception as e:
        raise Exception(f"Failed to upload BytesIO file to S3: {str(e)}")


def upload_to_object_storage(
    file, type="public", location="general", save_as="", expiration=None
):
    """
    Uploads a file to DigitalOcean Space and returns the file URL or a pre-signed URL for private files.

    :param file: The file object to be uploaded.
    :param type: Access type - "public" or "private".
    :param location: The location of the file in the Space.
    :param save_as: The path or name to save the file as in the Space.
    :param expiration: Expiration time in seconds for the pre-signed URL if the file is private (default is None).
    :return: The URL of the uploaded file or a pre-signed URL if the file is private and expiration is provided.
    """
    # Initialize the S3 client
    session = boto3.session.Session()
    s3 = session.client(
        "s3",
        endpoint_url=settings.S3_STORAGE_HOST,
        aws_access_key_id=settings.S3_STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.S3_STORAGE_SECRET_KEY,
    )

    # Set the access control based on the type
    acl = "public-read" if type == "public" else "private"

    # Generate the file path
    path = f"media/{location}/{time.time()}_{save_as}"

    try:
        # Upload the file to DigitalOcean Space
        s3.upload_fileobj(
            file,
            settings.S3_SOTRAGE_BUCKET,
            path,
            ExtraArgs={"ACL": acl, "ContentType": file.content_type},
        )

        # Construct the file URL
        file_url = f"{settings.S3_STORAGE_HOST}/{settings.S3_SOTRAGE_BUCKET}/{path}"

        # If the file is private and expiration is provided, generate a pre-signed URL
        if type == "private" and expiration:
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.S3_SOTRAGE_BUCKET,
                    "Key": path,
                },
                ExpiresIn=expiration,
            )
            return presigned_url

        # Return the public URL for public files or direct URL for private files without expiration
        return file_url

    except Exception as e:
        raise Exception(f"Failed to upload file to Object Space: {str(e)}")


def get_private_file_url(full_url, expiration=3600):
    """
    Generates a pre-signed URL for accessing private files in DigitalOcean Space.

    :param full_url: The complete URL of the file (e.g., 'https://host/ktechhub/media/users/1729174884.288935_hero_person.png').
    :param expiration: The expiration time in seconds (default is 3600 seconds or 1 hour).
    :return: A pre-signed URL that allows temporary access to the private file.
    """
    file_key = full_url.split(
        f"{settings.S3_STORAGE_HOST}/{settings.S3_SOTRAGE_BUCKET}/"
    )[-1]

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
                "Bucket": settings.S3_SOTRAGE_BUCKET,
                "Key": file_key,
            },
            ExpiresIn=expiration,
        )
        return presigned_url

    except Exception as e:
        raise Exception(f"Failed to generate pre-signed URL: {str(e)}")
