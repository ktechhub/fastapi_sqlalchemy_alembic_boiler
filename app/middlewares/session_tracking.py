"""
Session tracking middleware for updating user session activity.
Optimized for performance: Redis-only operations, minimal DB access.
"""

import json
import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.loggers import app_logger as logger
from app.services.redis_base import client as redis_client
from app.services.redis_push import redis_push_async
from app.utils.security_util import is_token_valid


# Paths to exclude from session tracking
EXCLUDED_PATHS = {
    "/",
    "/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
}


class SessionTrackingMiddleware(BaseHTTPMiddleware):
    """
    Optimized middleware to track user session activity.

    Performance optimizations:
    - Redis-only operations (no DB queries in hot path)
    - Throttled updates (5 min) to reduce writes
    - Background task for DB writes
    - Minimal JWT decode (only when needed)
    """

    async def dispatch(self, request: Request, call_next):
        # Fast path: Skip excluded paths
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # Fast path: Check Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return await call_next(request)

        # Extract token
        token = auth_header.replace("Bearer ", "").strip()
        if not token:
            return await call_next(request)

        # Optimized: Use Redis-only operations, defer DB writes
        try:
            # Lightweight decode (only get jti, skip full validation)
            # Full validation happens in get_current_user dependency
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_signature": True, "verify_exp": False},
            )
            token_jti = payload.get("jti")
            user_uuid = payload.get("sub")

            if not token_jti or not user_uuid:
                return await call_next(request)

            # Fast check: Token revocation (single Redis call)
            if not is_token_valid(
                token, user_uuid, token_type="access", payload=payload
            ):
                return await call_next(request)

            # Redis-only session activity tracking (no DB query)
            # Run in background to not block request
            import asyncio

            asyncio.create_task(
                self._update_session_activity_redis_only(token_jti, user_uuid, request)
            )

        except jwt.PyJWTError:
            # Invalid token - continue (will be handled by auth dependency)
            pass
        except Exception as e:
            # Don't fail the request if session tracking fails
            logger.error(f"Error in session tracking middleware: {e}")

        # Continue with the request (non-blocking)
        response = await call_next(request)
        return response

    async def _update_session_activity_redis_only(
        self, token_jti: str, user_uuid: str, request: Request
    ):
        """
        Update session activity using Redis-only operations.
        DB writes are deferred to background task.
        """
        # Check if session exists in Redis cache
        session_uuid = redis_client.get(f"jti:{token_jti}")

        if not session_uuid:
            # Session not found - queue for creation (background task)
            # This happens if login didn't create session
            await self._queue_session_creation(token_jti, user_uuid, request)
            return

        # Handle both bytes and string (Redis client may return either)
        if isinstance(session_uuid, bytes):
            session_uuid = session_uuid.decode()

        # Throttle check (Redis-only)
        throttle_key = f"session:last_update:{session_uuid}"
        if redis_client.get(throttle_key):
            # Already updated recently, skip
            return

        # Set throttle (5 minutes) - prevents DB write
        redis_client.setex(throttle_key, 300, "1")  # 5 minutes = 300 seconds

        # Queue DB update in background (non-blocking, synchronous Redis)
        await self._queue_session_update(session_uuid)

    async def _queue_session_creation(
        self, token_jti: str, user_uuid: str, request: Request
    ):
        """Queue session creation as background task (synchronous Redis)."""
        try:
            # Format message to match standard queue format
            message = {
                "queue_name": "sessions",
                "operation": "create",
                "data": {
                    "token_jti": token_jti,
                    "user_uuid": user_uuid,
                    "ip_address": self._get_client_ip(request),
                    "user_agent": request.headers.get("user-agent", ""),
                },
            }

            # Push to sessions queue (processed by background worker)
            await redis_push_async(message=message)
        except Exception as e:
            logger.error(f"Error queueing session creation: {e}")

    async def _queue_session_update(self, session_uuid: str):
        """Queue session update as background task (synchronous Redis)."""
        try:
            # Format message to match standard queue format
            message = {
                "queue_name": "sessions",
                "operation": "update",
                "data": {
                    "session_uuid": session_uuid,
                },
            }

            # Push to sessions queue (processed by background worker)
            await redis_push_async(message=message)
        except Exception as e:
            logger.error(f"Error queueing session update: {e}")

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP (lightweight, no external calls)."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        if request.client:
            return request.client.host

        return "unknown"
