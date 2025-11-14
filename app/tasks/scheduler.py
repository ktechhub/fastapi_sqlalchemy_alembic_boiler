from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .common.roles import create_or_update_roles
from .common.permissions import create_or_update_permissions
from .common.role_permissions import sync_role_permissions
from .logs.activity_logs import delete_activity_logs
from .sessions.sessions_cleanup import cleanup_old_sessions
from app.core.loggers import scheduler_logger as logger


def schedule_tasks():
    scheduler = AsyncIOScheduler()
    tasks = [
        {
            "task": create_or_update_permissions,
            "trigger": "cron",
            "day_of_week": "mon",
            "hour": 2,
            "minute": 0,
        },
        {
            "task": create_or_update_roles,
            "trigger": "cron",
            "day_of_week": "mon",
            "hour": 2,
            "minute": 0,
        },
        {
            "task": sync_role_permissions,
            "trigger": "cron",
            "day_of_week": "mon",
            "hour": 2,
            "minute": 30,
        },
        {
            "task": delete_activity_logs,
            "trigger": "cron",
            "day_of_week": "sun",
            "hour": 3,
            "minute": 0,
        },
        {
            "task": cleanup_old_sessions,
            "trigger": "cron",
            "day_of_week": "sun",
            "hour": 3,
            "minute": 30,
        },
    ]

    # Register the tasks with the scheduler
    for task in tasks:
        scheduler.add_job(
            task["task"],
            task["trigger"],
            **{
                k: v
                for k, v in task.items()
                if k not in ["task", "trigger", "args", "kwargs"]
            },
            args=task.get("args", []),
            kwargs=task.get("kwargs", {})
        )

    scheduler.start()
    logger.info("Scheduler started with all tasks.")

    return scheduler
