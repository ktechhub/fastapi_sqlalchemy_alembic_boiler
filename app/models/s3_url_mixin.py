from app.utils.object_storage import get_private_file_url
from app.core.config import settings


class S3URLMixin:
    """
    Mixin class that automatically converts S3 URL fields to presigned URLs.

    Usage:
        class MyModel(Base, S3URLMixin):
            _s3_url_fields = ['url', 'file_path', 'image_url']
            # ... model fields ...
    """

    _s3_url_fields = []
    _s3_url_expires_in = 3600 * 24 * 7

    def __getattribute__(self, name):
        # Get the original value
        value = super().__getattribute__(name)

        # Avoid recursion by checking if we're accessing the class or s3_url_fields
        if name in ["__class__", "_s3_url_fields", "_s3_url_expires_in"]:
            return value

        # Get the s3_url_fields safely to avoid recursion
        try:
            s3_url_fields = object.__getattribute__(self.__class__, "_s3_url_fields")
        except AttributeError:
            s3_url_fields = []

        # If this field is configured as an S3 URL field and has a value
        if name in s3_url_fields and value:
            # Handle list of URLs (e.g., images field)
            if isinstance(value, list):
                presigned_urls = []
                for url in value:
                    if isinstance(url, str) and url.startswith(
                        f"{settings.S3_STORAGE_HOST}/{settings.S3_STORAGE_BUCKET}/"
                    ):
                        try:
                            presigned_urls.append(
                                get_private_file_url(url, self._s3_url_expires_in)
                            )
                        except Exception:
                            # If presigned URL generation fails, return original URL
                            presigned_urls.append(url)
                    else:
                        # Not an S3 URL, keep as-is
                        presigned_urls.append(url)
                return presigned_urls

            # Handle single string URL
            elif isinstance(value, str) and value.startswith(
                f"{settings.S3_STORAGE_HOST}/{settings.S3_STORAGE_BUCKET}/"
            ):
                try:
                    # Return presigned URL instead of original URL
                    return get_private_file_url(value, self._s3_url_expires_in)
                except Exception:
                    # If presigned URL generation fails, return original URL
                    return value

        return value
