from fastapi import APIRouter
from . import system_logs
from . import activity_logs

logs_router = APIRouter()
logs_router.include_router(
    system_logs.SystemLogRouter().router, prefix="/system-logs", tags=["system-logs"]
)
logs_router.include_router(
    activity_logs.ActivityLogRouter().router,
    prefix="/activity-logs",
    tags=["activity-logs"],
)
