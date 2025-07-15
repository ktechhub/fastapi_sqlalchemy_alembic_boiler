# app/main.py
from fastapi import FastAPI, status
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from pywebguard import FastAPIGuard
from app.core.webguard import pyguard_config, async_redis_storage, route_rate_limits
from app.core.config import settings
from app.api.v1.router import router
from app.tasks.scheduler import schedule_tasks
from app.core.loggers import app_logger

if settings.SENTRY_DSN != "":
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        send_default_pii=True,
        traces_sample_rate=0,
        max_request_body_size="always",
        environment=settings.ENV,
        release=settings.API_VERSION,
        profiles_sample_rate=1.0,
        attach_stacktrace=True,
    )

description_text = """
Ktechhub API
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("Starting the application")
    scheduler = schedule_tasks()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(
    title="Ktechhub API",
    openapi_url="/openapi.json",
    description=description_text,
    version=settings.API_VERSION,
    contact=settings.CONTACT,
    terms_of_service="https://www.ktechhub.com/terms/",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    FastAPIGuard,
    config=pyguard_config,
    storage=async_redis_storage,
    route_rate_limits=route_rate_limits,
)


@app.get("/", response_class=RedirectResponse, include_in_schema=False)
async def docs():
    return RedirectResponse(url="/docs")


@app.get("/ready", status_code=status.HTTP_200_OK, include_in_schema=True)
async def ready() -> str:
    """Check if API it's ready"""
    app_logger.info("API is ready")
    return "ready"


app.include_router(router, prefix="/api/v1")
