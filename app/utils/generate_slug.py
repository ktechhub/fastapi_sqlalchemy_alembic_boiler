from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession
from app.cruds.base import CRUDBase


async def generate_unique_slug(db: AsyncSession, crud: CRUDBase, value: str) -> str:
    base_slug = slugify(value, max_length=255)
    slug = base_slug
    counter = 1
    while await crud.get(db=db, slug=slug) is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


"""
Usage:
    crud = CRUDBase(model)
    slug = await generate_unique_slug(db, crud, "title value")
"""
