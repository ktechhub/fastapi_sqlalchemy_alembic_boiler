from datetime import datetime, timedelta, timezone
from typing import Union, Any
from jose import jwt
from ..core.config import settings


def create_access_token(subject: Union[str, Any], expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.now(tz=timezone.utc) + expires_delta
    else:
        expires_delta = datetime.now(tz=timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any], expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.now(tz=timezone.utc) + expires_delta
    else:
        expires_delta = datetime.now(tz=timezone.utc) + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_REFRESH_SECRET_KEY, settings.ALGORITHM
    )
    return encoded_jwt


def create_access_token_from_refresh_token(
    refresh_token: str, expires_delta: int = None
) -> str:
    # Decode the refresh token to obtain the subject
    decoded_refresh_token = jwt.decode(
        refresh_token, settings.JWT_REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    subject = decoded_refresh_token["sub"]

    # Create an access token with the same subject and desired expiration
    return create_access_token(subject, expires_delta)
