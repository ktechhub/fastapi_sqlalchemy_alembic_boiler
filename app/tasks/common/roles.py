from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.cruds.roles import role_crud
from app.schemas.roles import RoleCreateSchema, RoleUpdateSchema
from app.utils.telegram import send_telegram_msg
from .defaults import default_roles


engine = create_async_engine(settings.DATABASE_URL, pool_size=200, pool_pre_ping=True)
SessionLocal = sessionmaker(
    engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def create_or_update_roles():
    db = SessionLocal()
    created_count = 0
    updated_count = 0
    for role in default_roles:
        db_role = await role_crud.get(db=db, name=role["name"])
        if not db_role:
            await role_crud.create(db=db, obj_in=RoleCreateSchema(**role))
            created_count += 1
        else:
            await role_crud.update(
                db=db, db_obj=db_role, obj_in=RoleUpdateSchema(**role)
            )
            updated_count += 1
    msg = (
        f"*GOPSC::Roles Sync Report*\n\n"
        f"✅ Items Created: {created_count}\n"
        f"✅ Items Updated: {updated_count}\n"
        f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    send_telegram_msg(msg=msg)
    await db.close()
