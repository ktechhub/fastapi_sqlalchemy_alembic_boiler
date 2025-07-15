from datetime import datetime, timezone, timedelta
from app.cruds.activity_logs import activity_log_crud
from app.models.activity_logs import ActivityLog
from app.utils.telegram import send_telegram_msg
from app.database.get_session import AsyncSessionLocal


async def delete_activity_logs():
    """
    Delete all activity logs older than 30 days
    """
    async with AsyncSessionLocal() as db:
        activity_logs = await activity_log_crud.get_multi(
            db=db,
            limit=-1,
            query_filters=[
                ActivityLog.created_at < datetime.now(timezone.utc) - timedelta(days=30)
            ],
        )
        deleted_count = len(activity_logs["data"])
        if activity_logs["data"]:
            await activity_log_crud.remove_multi(
                db=db, uuid=[item.uuid for item in activity_logs["data"]]
            )
        msg = (
            f"*ktechhub::Activity Logs Deletion Report*\n\n"
            f"✅ Items Deleted: {deleted_count}\n"
            f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_msg(msg=msg)
    await db.close()
