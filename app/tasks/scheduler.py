from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .common.roles import create_or_update_roles
from .common.permissions import create_or_update_permissions
from .common.role_permissions import sync_role_permissions
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
