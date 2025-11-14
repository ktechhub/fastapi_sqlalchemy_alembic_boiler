from datetime import datetime, timezone
from app.core.config import settings
from app.cruds.roles import role_crud
from app.schemas.roles import RoleCreateSchema, RoleUpdateSchema
from app.utils.telegram import send_telegram_msg
from ...core.defaults import default_roles
from app.database.get_session import AsyncSessionLocal


async def create_or_update_roles():
    async with AsyncSessionLocal() as db:
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
            f"*{settings.APP_NAME.upper()}::{settings.ENV.upper()}::Roles Sync Report*\n\n"
            f"✅ Items Created: {created_count}\n"
            f"✅ Items Updated: {updated_count}\n"
            f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_msg(msg=msg)
    await db.close()
