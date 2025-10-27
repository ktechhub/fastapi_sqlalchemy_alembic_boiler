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

    def __getattribute__(self, name):
        # Get the original value
        value = super().__getattribute__(name)

        # Avoid recursion by checking if we're accessing the class or s3_url_fields
        if name in ["__class__", "_s3_url_fields"]:
            return value

        # Get the s3_url_fields safely to avoid recursion
        try:
            s3_url_fields = object.__getattribute__(self.__class__, "_s3_url_fields")
        except AttributeError:
            s3_url_fields = []

        # If this field is configured as an S3 URL field and has a value
        if (
            name in s3_url_fields
            and value
            and isinstance(value, str)
            and value.startswith(
                f"{settings.S3_STORAGE_HOST}/{settings.S3_STORAGE_BUCKET}/"
            )
        ):

            try:
                # Return presigned URL instead of original URL
                return get_private_file_url(value)
            except Exception:
                # If presigned URL generation fails, return original URL
                return value

        return value
