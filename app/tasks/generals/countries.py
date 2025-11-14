from app.database.get_session import AsyncSessionLocal
from app.core.loggers import scheduler_logger as logger
from app.schemas.countries import CountrySchema
from app.cruds.countries import country_crud
from .countries_data import COUNTRIES


async def sync_countries():
    async with AsyncSessionLocal() as db:
        logger.info("Syncing countries...")
        for country in COUNTRIES:
            existing_country = await country_crud.get(db=db, slug=country["slug"])
            if existing_country:
                logger.info(f"Updating country: {existing_country.slug}")
                await country_crud.update(
                    db=db,
                    db_obj=existing_country,
                    obj_in=CountrySchema(
                        **country,
                    ),
                )
            else:
                logger.info(f"Creating new country: {country['slug']}")
                await country_crud.create(
                    db=db,
                    obj_in=CountrySchema(
                        **country,
                    ),
                )
