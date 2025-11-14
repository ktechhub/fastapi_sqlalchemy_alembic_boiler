from datetime import datetime, timezone, timedelta
from sqlalchemy import or_, and_
from app.cruds.user_sessions import user_session_crud
from app.models.user_sessions import UserSession
from app.utils.telegram import send_telegram_msg
from app.database.get_session import AsyncSessionLocal
from app.core.config import settings
from app.services.redis_base import client as redis_client


async def cleanup_old_sessions():
    """
    Clean up old user sessions:
    - Closed sessions older than 30 days
    - Active sessions that haven't been active for 90 days (stale sessions)
    """
    async with AsyncSessionLocal() as db:
        deleted_count = 0
        now = datetime.now(timezone.utc)

        # 1. Clean up closed sessions older than 30 days
        closed_sessions = await user_session_crud.get_multi(
            db=db,
            limit=-1,
            query_filters=[
                UserSession.is_active == False,
                UserSession.closed_at < now - timedelta(days=30),
            ],
        )
        closed_count = len(closed_sessions["data"])
        if closed_sessions["data"]:
            await user_session_crud.remove_multi(
                db=db, uuid=[item.uuid for item in closed_sessions["data"]]
            )
            deleted_count += closed_count

            # Clean up Redis mappings for closed sessions
            for session in closed_sessions["data"]:
                if session.token_jti:
                    redis_client.delete(f"jti:{session.token_jti}")
                redis_client.delete(f"session:last_update:{session.uuid}")

        # 2. Clean up stale active sessions (haven't been active for 90 days)
        # Also include sessions with no last_active timestamp (older than 90 days from creation)
        stale_sessions = await user_session_crud.get_multi(
            db=db,
            limit=-1,
            query_filters=[
                UserSession.is_active == True,
                or_(
                    UserSession.last_active < now - timedelta(days=90),
                    and_(
                        UserSession.last_active.is_(None),
                        UserSession.created_at < now - timedelta(days=90),
                    ),
                ),
            ],
        )
        stale_count = len(stale_sessions["data"])
        if stale_sessions["data"]:
            await user_session_crud.remove_multi(
                db=db, uuid=[item.uuid for item in stale_sessions["data"]]
            )
            deleted_count += stale_count

            # Clean up Redis mappings for stale sessions
            for session in stale_sessions["data"]:
                if session.token_jti:
                    redis_client.delete(f"jti:{session.token_jti}")
                redis_client.delete(f"session:last_update:{session.uuid}")

        msg = (
            f"*{settings.APP_NAME.upper()}::{settings.ENV.upper()}::Sessions Cleanup Report*\n\n"
            f"✅ Closed Sessions Deleted: {closed_count}\n"
            f"✅ Stale Sessions Deleted: {stale_count}\n"
            f"✅ Total Deleted: {deleted_count}\n"
            f"🕒 Time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_msg(msg=msg)
    await db.close()
