from app.models.countries import Country
from app.cruds.base import CRUDBase
from app.schemas.countries import (
    CountryCreateSchema,
    CountryCreateSchema,
)


class CRUDCountry(CRUDBase[Country, CountryCreateSchema, CountryCreateSchema]):
    pass


country_crud = CRUDCountry(Country)
