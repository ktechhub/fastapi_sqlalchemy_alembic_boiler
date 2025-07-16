# app/main.py
import time
from fastapi import FastAPI, status, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from pywebguard import FastAPIGuard
from app.core.webguard import pyguard_config, async_redis_storage, route_rate_limits
from app.core.config import settings
from app.api.v1.router import router
from app.tasks.scheduler import schedule_tasks
from app.core.loggers import app_logger as logger
from app.api.v1.docs.router import docs_router
from app.deps.docs import get_current_docs_user

description_text = """
Ktechhub API
"""
terms_of_service = "https://www.ktechhub.com/terms/"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting the application")
    scheduler = schedule_tasks()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(
    title="Ktechhub API",
    description=description_text,
    version=settings.API_VERSION,
    contact=settings.CONTACT,
    terms_of_service=terms_of_service,
    license_info=settings.LICENSE_INFO,
    openapi_tags=settings.OPENAPI_TAGS,
    servers=settings.OPENAPI_SERVERS,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
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
    app.add_middleware(SentryAsgiMiddleware)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "ktechhub.com",
        "*.ktechhub.com",
    ],
)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log incoming request
        logger.info(f"➡️ {request.method} {request.url.path}")

        response = await call_next(request)

        process_time = round((time.time() - start_time) * 1000, 2)

        # Log response status and duration
        logger.info(
            f"⬅️ {request.method} {request.url.path} - {response.status_code} ({process_time} ms)"
        )

        return response


app.add_middleware(LoggingMiddleware)


@app.get("/", response_class=RedirectResponse, include_in_schema=False)
async def docs():
    return RedirectResponse(url="/docs")


@app.get("/ready", status_code=status.HTTP_200_OK, include_in_schema=True)
async def ready() -> str:
    """Check if API it's ready"""
    logger.info("API is ready")
    return "ready"


app.include_router(docs_router, prefix="")


# OpenAPI JSON
@app.get(
    "/openapi.json",
    response_class=JSONResponse,
    include_in_schema=False,
    summary="OpenAPI schema",
    description="Protected OpenAPI JSON schema used for API documentation generation.",
)
async def get_openapi_json(username: str = Depends(get_current_docs_user)):
    openapi_schema = get_openapi(
        title="Ktechhub API",
        version=settings.API_VERSION,
        openapi_version="3.1.0",
        summary="Ktechhub - API",
        description=description_text,
        routes=app.routes,
        terms_of_service=terms_of_service,
        contact=settings.CONTACT,
        license_info=settings.LICENSE_INFO,  # Optional
        tags=settings.OPENAPI_TAGS,  # Optional list of dicts
        servers=settings.OPENAPI_SERVERS,  # Optional list of dicts
        separate_input_output_schemas=True,
    )
    return JSONResponse(openapi_schema)


app.include_router(router, prefix="/api/v1")
