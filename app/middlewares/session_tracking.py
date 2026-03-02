"""
Session tracking middleware for updating user session activity.
Optimized for performance: Redis-only operations, minimal DB access.
"""

from fastapi import Request
from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware
import jwt

from app.core.loggers import app_logger as logger
from app.services.redis_base import get_async_redis_client
from app.services.redis_push import redis_push_async
from app.utils.security_util import is_token_valid_async, decode_token_lightweight


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
        track_args = None
        try:
            # Lightweight decode (only get jti, skip full validation)
            # Full validation happens in get_current_user dependency
            payload = decode_token_lightweight(token)
            token_jti = payload.get("jti")
            user_uuid = payload.get("sub")

            if token_jti and user_uuid:
                # Fast check: Token revocation (single async Redis call)
                if await is_token_valid_async(
                    token, user_uuid, token_type="access", payload=payload
                ):
                    # Capture IP before response (request may not be safe to access later)
                    client_ip = self._get_client_ip(request)
                    user_agent = request.headers.get("user-agent", "")
                    track_args = (token_jti, user_uuid, client_ip, user_agent)

        except jwt.PyJWTError:
            # Invalid token - continue (will be handled by auth dependency)
            pass
        except Exception as e:
            # Don't fail the request if session tracking fails
            logger.error(f"Error in session tracking middleware: {e}")

        response = await call_next(request)

        # Attach session tracking as a proper BackgroundTask on the response.
        # This ensures Starlette manages the lifecycle and the task is not orphaned
        # on shutdown.
        if track_args is not None:
            response.background = BackgroundTask(
                self._update_session_activity_redis_only, *track_args
            )

        return response

    async def _update_session_activity_redis_only(
        self, token_jti: str, user_uuid: str, client_ip: str, user_agent: str
    ):
        """
        Update session activity using Redis-only operations.
        DB writes are deferred to background task.
        """
        async_redis = await get_async_redis_client()

        # Check if session exists in Redis cache
        session_uuid = await async_redis.get(f"jti:{token_jti}")

        if not session_uuid:
            # Session not found - queue for creation (background task)
            # This happens if login didn't create session
            await self._queue_session_creation(token_jti, user_uuid, client_ip, user_agent)
            return

        # Throttle check (Redis-only)
        throttle_key = f"session:last_update:{session_uuid}"
        if await async_redis.get(throttle_key):
            # Already updated recently, skip
            return

        # Set throttle (5 minutes) - prevents DB write
        await async_redis.setex(throttle_key, 300, "1")  # 5 minutes = 300 seconds

        # Queue DB update in background (non-blocking)
        await self._queue_session_update(session_uuid)

    async def _queue_session_creation(
        self, token_jti: str, user_uuid: str, client_ip: str, user_agent: str
    ):
        """Queue session creation as background task."""
        try:
            message = {
                "queue_name": "sessions",
                "operation": "create",
                "data": {
                    "token_jti": token_jti,
                    "user_uuid": user_uuid,
                    "ip_address": client_ip,
                    "user_agent": user_agent,
                },
            }
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
