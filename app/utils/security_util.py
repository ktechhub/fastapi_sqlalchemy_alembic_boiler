import uuid
from datetime import datetime, timedelta, timezone
from typing import Union, Any, Tuple
import jwt
from ..core.config import settings
from ..services.redis_base import client as redis_client
from ..core.loggers import app_logger as logger


def _create_token(
    subject: Union[str, Any],
    secret_key: str,
    expire_minutes: int,
    expires_delta: timedelta = None,
    jti: str = None,
    token_type: str = "access",
) -> Tuple[str, str]:
    """Internal helper to create JWT tokens with standard claims."""
    now = datetime.now(tz=timezone.utc)
    now_timestamp = int(now.timestamp())
    exp = now + (expires_delta or timedelta(minutes=expire_minutes))
    token_jti = jti or str(uuid.uuid4())

    to_encode = {
        "exp": int(exp.timestamp()),
        "sub": str(subject),
        "iat": now_timestamp,
        "nbf": now_timestamp,  # Not before - token not valid before this time
        "jti": token_jti,
        "iss": settings.APP_NAME,  # Issuer - who created the token
        "aud": settings.APP_NAME,  # Audience - who the token is intended for
        "typ": token_type,  # Token type: "access" or "refresh"
    }
    encoded_token = jwt.encode(to_encode, secret_key, settings.ALGORITHM)
    return encoded_token, token_jti


def decode_access_token(token: str) -> dict:
    """
    Decode and validate an access token with full validation.
    Validates signature, expiration, nbf, issuer, and audience.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_nbf": True,
        },
        issuer=settings.APP_NAME,
        audience=settings.APP_NAME,
    )


def decode_refresh_token(token: str) -> dict:
    """
    Decode and validate a refresh token with full validation.
    Validates signature, expiration, nbf, issuer, and audience.
    """
    return jwt.decode(
        token,
        settings.JWT_REFRESH_SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_nbf": True,
        },
        issuer=settings.APP_NAME,
        audience=settings.APP_NAME,
    )


def decode_token_lightweight(token: str) -> dict:
    """
    Lightweight token decode for middleware (signature only, no exp/nbf validation).
    Full validation happens in get_current_user dependency.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"verify_signature": True, "verify_exp": False},
    )


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None, jti: str = None
) -> Tuple[str, str]:
    """Create an access token with standard JWT claims. Returns (token, jti)."""
    return _create_token(
        subject,
        settings.JWT_SECRET_KEY,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        expires_delta,
        jti,
        token_type="access",
    )


def create_refresh_token(
    subject: Union[str, Any], expires_delta: timedelta = None, jti: str = None
) -> Tuple[str, str]:
    """Create a refresh token with standard JWT claims. Returns (token, jti)."""
    return _create_token(
        subject,
        settings.JWT_REFRESH_SECRET_KEY,
        settings.REFRESH_TOKEN_EXPIRE_MINUTES,
        expires_delta,
        jti,
        token_type="refresh",
    )


def create_access_token_from_refresh_token(
    refresh_token: str, expires_delta: timedelta = None
) -> Tuple[str, str]:
    """Create access token from refresh token. Returns (token, jti)."""
    decoded_refresh_token = decode_refresh_token(refresh_token)
    # Use same jti from refresh token for session continuity
    refresh_jti = decoded_refresh_token.get("jti")
    return create_access_token(
        decoded_refresh_token["sub"], expires_delta, jti=refresh_jti
    )


def invalidate_user_tokens(user_uuid: str) -> bool:
    """
    Invalidate all tokens for a user by setting a logout timestamp.
    Memory-efficient: only one entry per user instead of per token.
    """
    try:
        logout_timestamp = int(datetime.now(tz=timezone.utc).timestamp())
        max_token_ttl = settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
        redis_client.setex(
            f"user:logout:{user_uuid}", max_token_ttl, str(logout_timestamp)
        )
        return True
    except Exception as e:
        logger.error(f"Error invalidating user tokens: {e}")
        return False


def is_token_valid(
    token: str, user_uuid: str, token_type: str = "access", payload: dict = None
) -> bool:
    """
    Check if a token is valid by comparing its issued time with user's logout timestamp.
    If payload is provided, skips token decoding for performance.
    """
    try:
        logout_timestamp_str = redis_client.get(f"user:logout:{user_uuid}")
        if not logout_timestamp_str:
            return True

        logout_timestamp = int(logout_timestamp_str)

        # Use provided payload or decode token
        if payload is None:
            if token_type == "access":
                payload = decode_access_token(token)
            else:
                payload = decode_refresh_token(token)

        iat = payload.get("iat")
        return int(iat) >= logout_timestamp if iat is not None else False
    except (jwt.ExpiredSignatureError, jwt.PyJWTError):
        return False
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return False
