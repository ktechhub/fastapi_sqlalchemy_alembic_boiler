"""
Session service for managing user sessions.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_sessions import UserSession
from app.cruds.user_sessions import user_session_crud
from app.schemas.user_sessions import UserSessionCreateSchema, UserSessionUpdateSchema
from app.utils.session_util import (
    get_client_ip,
    parse_user_agent_string,
    get_location_from_ip,
)
from app.services.redis_base import client as redis_client
from app.core.loggers import app_logger as logger
from app.database.get_session import AsyncSessionLocal
from fastapi import Request


async def create_user_session(
    db: AsyncSession,
    user_uuid: str,
    token_jti: str,
    request: Request,
    location_data: Optional[dict] = None,
) -> UserSession:
    """
    Create a new user session.

    Args:
        db: Database session
        user_uuid: User UUID
        token_jti: JWT ID (jti) from token
        request: FastAPI request object
        location_data: Optional pre-fetched location data

    Returns:
        Created UserSession object
    """
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    parsed_ua = parse_user_agent_string(user_agent)

    # Get location (use provided or fetch)
    if location_data is None:
        location_data = await get_location_from_ip(ip_address)

    session_data = UserSessionCreateSchema(
        user_uuid=user_uuid,
        token_jti=token_jti,
        ip_address=ip_address,
        user_agent=user_agent,
        browser=parsed_ua.get("browser"),
        browser_version=parsed_ua.get("browser_version"),
        os=parsed_ua.get("os"),
        os_version=parsed_ua.get("os_version"),
        device_type=parsed_ua.get("device_type"),
        location_city=location_data.get("city"),
        location_region=location_data.get("region"),
        location_country=location_data.get("country"),
        location_country_name=location_data.get("country_name"),
        is_active=True,
        last_active=datetime.now(tz=timezone.utc),
    )

    # Check if session already exists (race condition protection)
    existing_sessions = await user_session_crud.get_multi(
        db=db, token_jti=token_jti, limit=1
    )
    if existing_sessions["data"]:
        session = existing_sessions["data"][0]
        # Cache the mapping if not already cached
        redis_client.setex(f"jti:{token_jti}", 86400 * 7, str(session.uuid))
        logger.info(f"Session already exists for jti {token_jti}: {session.uuid}")
        return session

    try:
        session = await user_session_crud.create(db=db, obj_in=session_data)

        # Store jti -> session_uuid mapping in Redis for quick lookup
        redis_client.setex(
            f"jti:{token_jti}", 86400 * 7, str(session.uuid)
        )  # 7 days TTL

        logger.info(f"Created session {session.uuid} for user {user_uuid}")
        return session
    except Exception as e:
        # Handle duplicate entry error (race condition)
        if "Duplicate entry" in str(e) or "duplicate key" in str(e).lower():
            logger.warning(
                f"Duplicate session creation attempt for jti {token_jti}, fetching existing"
            )
            # Fetch the existing session
            existing_sessions = await user_session_crud.get_multi(
                db=db, token_jti=token_jti, limit=1
            )
            if existing_sessions["data"]:
                session = existing_sessions["data"][0]
                redis_client.setex(f"jti:{token_jti}", 86400 * 7, str(session.uuid))
                return session
        raise


async def update_session_activity(
    db: AsyncSession,
    session_uuid: str,
    throttle_minutes: int = 5,
) -> bool:
    """
    Update session last_active timestamp.

    Note: Throttling is handled by the middleware before queuing.
    This function just performs the update.

    Args:
        db: Database session
        session_uuid: Session UUID
        throttle_minutes: Minimum minutes between updates (for throttle key TTL)

    Returns:
        True if updated, False if session not found or not active
    """
    try:
        session = await user_session_crud.get(db=db, uuid=session_uuid)
        if not session:
            logger.warning(f"Session {session_uuid} not found")
            return False

        if not session.is_active:
            logger.warning(f"Session {session_uuid} is not active")
            return False

        await user_session_crud.update(
            db=db,
            db_obj=session,
            obj_in=UserSessionUpdateSchema(last_active=datetime.now(tz=timezone.utc)),
        )

        # Set throttle key (5 minutes TTL) - middleware already set it, but ensure it's there
        throttle_key = f"session:last_update:{session_uuid}"
        redis_client.setex(throttle_key, throttle_minutes * 60, "1")

        logger.info(f"Updated session {session_uuid} last_active timestamp")
        return True
    except Exception as e:
        logger.error(f"Error updating session activity: {e}")
        return False


async def close_user_session(
    db: AsyncSession,
    session_uuid: str,
) -> bool:
    """
    Close a user session.

    Args:
        db: Database session
        session_uuid: Session UUID

    Returns:
        True if closed successfully
    """
    try:
        session = await user_session_crud.get(db=db, uuid=session_uuid)
        if not session:
            return False

        await user_session_crud.update(
            db=db,
            db_obj=session,
            obj_in=UserSessionUpdateSchema(
                is_active=False,
                closed_at=datetime.now(tz=timezone.utc),
            ),
        )

        # Clean up Redis mappings
        if session.token_jti:
            redis_client.delete(f"jti:{session.token_jti}")
        redis_client.delete(f"session:last_update:{session_uuid}")

        logger.info(f"Closed session {session_uuid}")
        return True
    except Exception as e:
        logger.error(f"Error closing session: {e}")
        return False


async def get_session_by_jti(
    db: AsyncSession,
    token_jti: str,
) -> Optional[UserSession]:
    """
    Get session by token JTI.

    Args:
        db: Database session
        token_jti: JWT ID (jti)

    Returns:
        UserSession if found, None otherwise
    """
    try:
        # Check Redis cache first
        session_uuid = redis_client.get(f"jti:{token_jti}")
        if session_uuid:
            # Handle both bytes and string (Redis client may return either)
            if isinstance(session_uuid, bytes):
                session_uuid = session_uuid.decode()
            session = await user_session_crud.get(db=db, uuid=session_uuid)
            if session:
                return session

        # Fallback to database lookup
        sessions = await user_session_crud.get_multi(
            db=db, token_jti=token_jti, limit=1
        )
        if sessions["data"]:
            session = sessions["data"][0]
            # Cache the mapping
            redis_client.setex(f"jti:{token_jti}", 86400 * 7, str(session.uuid))
            return session
        return None
    except Exception as e:
        logger.error(f"Error getting session by jti: {e}")
        return None


async def process_session_creation(session_data: dict):
    """Process session creation from queue"""
    try:
        token_jti = session_data.get("token_jti")
        user_uuid = session_data.get("user_uuid")
        ip_address = session_data.get("ip_address", "unknown")
        user_agent = session_data.get("user_agent", "")

        if not token_jti or not user_uuid:
            logger.error(f"Invalid session creation data: {session_data}")
            return

        # Check if session already exists in Redis
        existing_session_uuid = redis_client.get(f"jti:{token_jti}")
        if existing_session_uuid:
            logger.info(f"Session already exists for jti {token_jti}")
            return

        # Get location data
        location_data = await get_location_from_ip(ip_address)

        # Create session in database
        async with AsyncSessionLocal() as db:

            # Double-check in DB (race condition protection)
            existing_sessions = await user_session_crud.get_multi(
                db=db, token_jti=token_jti, limit=1
            )
            if existing_sessions["data"]:
                session = existing_sessions["data"][0]
                # Cache the mapping
                redis_client.setex(f"jti:{token_jti}", 86400 * 7, str(session.uuid))
                logger.info(
                    f"Session already exists in DB for jti {token_jti}: {session.uuid}"
                )
                return

            parsed_ua = parse_user_agent_string(user_agent)
            session_create_data = UserSessionCreateSchema(
                user_uuid=user_uuid,
                token_jti=token_jti,
                ip_address=ip_address,
                user_agent=user_agent,
                browser=parsed_ua.get("browser"),
                browser_version=parsed_ua.get("browser_version"),
                os=parsed_ua.get("os"),
                os_version=parsed_ua.get("os_version"),
                device_type=parsed_ua.get("device_type"),
                location_city=location_data.get("city"),
                location_region=location_data.get("region"),
                location_country=location_data.get("country"),
                location_country_name=location_data.get("country_name"),
                is_active=True,
                last_active=datetime.now(tz=timezone.utc),
            )

            try:
                session = await user_session_crud.create(
                    db=db, obj_in=session_create_data
                )

                # Store jti -> session_uuid mapping in Redis
                redis_client.setex(
                    f"jti:{token_jti}", 86400 * 7, str(session.uuid)
                )  # 7 days TTL

                logger.info(
                    f"Created session {session.uuid} for user {user_uuid} from queue"
                )
            except Exception as create_error:
                # Handle duplicate entry error (race condition)
                if (
                    "Duplicate entry" in str(create_error)
                    or "duplicate key" in str(create_error).lower()
                ):
                    logger.warning(
                        f"Duplicate session creation attempt for jti {token_jti}, fetching existing"
                    )
                    # Fetch the existing session
                    existing_sessions = await user_session_crud.get_multi(
                        db=db, token_jti=token_jti, limit=1
                    )
                    if existing_sessions["data"]:
                        session = existing_sessions["data"][0]
                        redis_client.setex(
                            f"jti:{token_jti}", 86400 * 7, str(session.uuid)
                        )
                        logger.info(
                            f"Retrieved existing session {session.uuid} for jti {token_jti}"
                        )
                        return
                # Re-raise if it's not a duplicate error
                raise
    except Exception as e:
        logger.error(f"Error creating session from queue: {e}")
        raise


async def process_session_update(session_data: dict):
    """Process session update from queue"""
    try:
        session_uuid = session_data.get("session_uuid")
        if not session_uuid:
            logger.error(f"Invalid session update data: {session_data}")
            return

        async with AsyncSessionLocal() as db:
            success = await update_session_activity(db, session_uuid)
            if success:
                logger.info(f"Updated session {session_uuid} last_active from queue")
            else:
                logger.warning(
                    f"Failed to update session {session_uuid} - session not found or not active"
                )
    except Exception as e:
        logger.error(f"Error updating session from queue: {e}")
        raise
