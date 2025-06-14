# app/main.py
from fastapi import FastAPI, status
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import auth_router
from app.tasks.scheduler import schedule_tasks

description_text = """
Ktechhub API
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/", response_class=RedirectResponse, include_in_schema=False)
async def docs():
    return RedirectResponse(url="/docs")


@app.get("/ready", status_code=status.HTTP_200_OK, include_in_schema=True)
async def ready() -> str:
    """Check if API it's ready"""
    return "ready"


app.include_router(auth_router, prefix="/api/v1")
