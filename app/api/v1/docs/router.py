from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from app.deps.docs import get_current_docs_user

docs_router = APIRouter()


# Swagger UI
@docs_router.get(
    "/docs",
    response_class=HTMLResponse,
    include_in_schema=False,
    summary="Swagger UI",
    description="Protected Swagger UI for interacting with the API documentation.",
)
async def get_docs(username: str = Depends(get_current_docs_user)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")


# ReDoc
@docs_router.get(
    "/redoc",
    response_class=HTMLResponse,
    include_in_schema=False,
    summary="ReDoc UI",
    description="Protected ReDoc interface for viewing the API documentation in a clean format.",
)
async def get_redoc(username: str = Depends(get_current_docs_user)):
    return get_redoc_html(openapi_url="/openapi.json", title="redoc")
