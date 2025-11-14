from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.generate_slug import generate_unique_slug
from app.utils.responses import (
    bad_request_response,
    created_response,
    not_found_response,
    success_response,
)
from app.deps.user import get_user_with_permission
from app.schemas.countries import (
    CountryBaseSchema,
    CountryResponseSchema,
    CountryTotalCountListResponseSchema,
    CountryCreateSchema,
    CountryUpdateSchema,
    CountryFilters,
)
from app.cruds.countries import country_crud
from app.models.users import User
from app.database.get_session import get_async_session
from app.core.loggers import app_logger as logger


class CountryRouter:
    def __init__(self):
        self.router = APIRouter()
        self.crud = country_crud
        self.singular = "Country"
        self.plural = "Countries"
        self.response_model = CountryResponseSchema
        self.list_response_model = CountryTotalCountListResponseSchema

        # List and create countries
        self.router.add_api_route(
            "/",
            self.list,
            methods=["GET"],
            response_model=self.list_response_model,
            description="Get all countries with optional filtering",
            summary="Get all countries",
        )

        self.router.add_api_route(
            "/",
            self.create,
            methods=["POST"],
            response_model=self.response_model,
            description="Create a new country",
            summary="Create country",
        )

        # Single country operations
        self.router.add_api_route(
            "/{id}",
            self.get,
            methods=["GET"],
            response_model=self.response_model,
            description="Get a country by UUID",
            summary="Get country",
        )

        self.router.add_api_route(
            "/{id}",
            self.update,
            methods=["PUT"],
            response_model=self.response_model,
            description="Update a country",
            summary="Update country",
        )

        self.router.add_api_route(
            "/{id}",
            self.delete,
            methods=["DELETE"],
            description="Delete a country",
            summary="Delete country",
        )

    async def list(
        self,
        filters: CountryFilters = Depends(),
        db: AsyncSession = Depends(get_async_session),
    ):
        """Get all countries with optional filtering"""
        logger.info(f"Listing {self.plural} with filters: {filters} ")

        countries = await self.crud.get_multi(
            db=db, **filters.model_dump(exclude_none=True)
        )

        return success_response(
            message=f"Successfully fetched {self.plural}!",
            data=countries["data"],
            total_count=countries["total_count"],
        )

    async def create(
        self,
        country_data: CountryBaseSchema,
        user: User = Depends(get_user_with_permission("can_write_countries")),
        db: AsyncSession = Depends(get_async_session),
    ):
        """Create a new country"""
        logger.info(
            f"Creating {self.singular} with data: {country_data} and user: {user.uuid}"
        )

        # Check if country with same name already exists
        existing_country = await self.crud.get(
            db=db, name=country_data.name.capitalize()
        )
        if existing_country:
            raise bad_request_response(
                message=f"Country {country_data.name} already exists",
            )
        slug = await generate_unique_slug(db, self.crud, country_data.name)

        country_create = CountryCreateSchema(
            name=country_data.name.capitalize(), slug=slug
        )

        country = await self.crud.create(db=db, obj_in=country_create)

        return created_response(
            message=f"Successfully created {self.singular}!",
            data=country,
        )

    async def get(
        self,
        id: int,
        db: AsyncSession = Depends(get_async_session),
    ):
        """Get a country by UUID"""
        logger.info(f"Getting {self.singular} with id: {id} ")

        country = await self.crud.get(db=db, id=id)
        if not country:
            return not_found_response(f"{self.singular} not found!")

        return success_response(
            message=f"Successfully fetched {self.singular}!", data=country
        )

    async def update(
        self,
        id: int,
        country_data: CountryUpdateSchema,
        user: User = Depends(get_user_with_permission("can_write_countries")),
        db: AsyncSession = Depends(get_async_session),
    ):
        """Update a country"""
        logger.info(f"Updating {self.singular} with ID: {id} and user: {user.uuid}")

        country = await self.crud.get(db=db, id=id)
        if not country:
            return not_found_response(f"{self.singular} not found!")

        # Check if new name conflicts with existing country
        if country_data.name and country_data.name.lower() != country.name.lower():
            existing_country = await self.crud.get(db=db, name=country_data.name)
            if existing_country:
                raise bad_request_response(
                    message="Country with this name already exists",
                )

        updated_country = await self.crud.update(
            db=db, db_obj=country, obj_in=country_data
        )

        return success_response(
            message=f"Successfully updated {self.singular}!", data=updated_country
        )

    async def delete(
        self,
        id: int,
        user: User = Depends(get_user_with_permission("can_delete_countries")),
        db: AsyncSession = Depends(get_async_session),
    ):
        """Delete a country"""
        logger.info(f"Deleting {self.singular} with ID: {id} and user: {user.uuid}")

        country = await self.crud.get(db=db, id=id)
        if not country:
            return not_found_response(f"{self.singular} not found!")

        await self.crud.remove(db=db, id=id)

        return success_response(message=f"Successfully deleted {self.singular}!")
