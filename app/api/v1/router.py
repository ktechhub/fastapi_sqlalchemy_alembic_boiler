from fastapi import APIRouter
from .auth.router import auth_router
from .logs.router import logs_router

router = APIRouter()
router.include_router(auth_router, prefix="")
router.include_router(logs_router, prefix="")
