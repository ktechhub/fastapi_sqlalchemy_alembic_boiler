from fastapi import APIRouter
from app.api.v1.generals import entities
from app.api.v1.generals import countries


generals_router = APIRouter()


generals_router.include_router(
    countries.CountryRouter().router, prefix="/countries", tags=["Generals"]
)
generals_router.include_router(
    entities.EntityRouter().router, tags=["Generals"], prefix="/entities"
)
