from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .common.roles import create_or_update_roles
from .common.permissions import create_or_update_permissions
from .common.role_permissions import sync_role_permissions
from .logs.activity_logs import delete_activity_logs
from .sessions.sessions_cleanup import cleanup_old_sessions
from app.core.loggers import scheduler_logger as logger


LOCK_TTL = 3600  # 1 hour - lock auto-expires to prevent deadlock if instance crashes


async def with_distributed_lock(job_name: str, coro_fn, *args, **kwargs):
    """
    Run an async task only if this instance acquires the Redis distributed lock.
    Prevents duplicate execution when multiple app instances are running.
    """
    from app.services.redis_base import get_async_redis_client
    from app.core.config import settings

    lock_key = f"scheduler:lock:{settings.APP_NAME}:{job_name}"
    redis = await get_async_redis_client()
    acquired = await redis.set(lock_key, "1", nx=True, ex=LOCK_TTL)
    if not acquired:
        logger.info(f"Skipping {job_name}: lock held by another instance")
        return
    try:
        await coro_fn(*args, **kwargs)
    finally:
        await redis.delete(lock_key)


def schedule_tasks():
    scheduler = AsyncIOScheduler()
    tasks = [
        {
            "task": lambda: with_distributed_lock(
                "create_or_update_permissions", create_or_update_permissions
            ),
            "trigger": "cron",
            "day_of_week": "mon",
            "hour": 2,
            "minute": 0,
        },
        {
            "task": lambda: with_distributed_lock(
                "create_or_update_roles", create_or_update_roles
            ),
            "trigger": "cron",
            "day_of_week": "mon",
            "hour": 2,
            "minute": 0,
        },
        {
            "task": lambda: with_distributed_lock(
                "sync_role_permissions", sync_role_permissions
            ),
            "trigger": "cron",
            "day_of_week": "mon",
            "hour": 2,
            "minute": 30,
        },
        {
            "task": lambda: with_distributed_lock(
                "delete_activity_logs", delete_activity_logs
            ),
            "trigger": "cron",
            "day_of_week": "sun",
            "hour": 3,
            "minute": 0,
        },
        {
            "task": lambda: with_distributed_lock(
                "cleanup_old_sessions", cleanup_old_sessions
            ),
            "trigger": "cron",
            "day_of_week": "sun",
            "hour": 3,
            "minute": 30,
        },
    ]

    # Register the tasks with the scheduler
    for task_config in tasks:
        scheduler.add_job(
            task_config["task"],
            task_config["trigger"],
            **{
                k: v
                for k, v in task_config.items()
                if k not in ["task", "trigger", "args", "kwargs"]
            },
            args=task_config.get("args", []),
            kwargs=task_config.get("kwargs", {}),
        )

    scheduler.start()
    logger.info("Scheduler started with all tasks (distributed lock enabled).")

    return scheduler
