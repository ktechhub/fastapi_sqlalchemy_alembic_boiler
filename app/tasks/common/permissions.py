from datetime import datetime, timezone
from app.cruds.permissions import permission_crud
from app.schemas.permissions import (
    PermissionCreateSchema,
    PermissionUpdateSchema,
)
from app.utils.telegram import send_telegram_msg
from app.core.defaults import default_actions
from app.core.loggers import scheduler_logger
from app.database.get_session import AsyncSessionLocal

permissions = []

for action in default_actions:

    # read
    permissions.append(
        {
            "name": f"can_read_{action}",
            "label": f"Can Read {action.capitalize()}",
            "description": f"Can read {action.capitalize()}",
        }
    )

    # write
    permissions.append(
        {
            "name": f"can_write_{action}",
            "label": f"Can Write {action.capitalize()}",
            "description": f"Can write {action.capitalize()}",
        }
    )

    # delete
    permissions.append(
        {
            "name": f"can_delete_{action}",
            "label": f"Can Delete {action.capitalize()}",
            "description": f"Can delete {action.capitalize()}",
        }
    )


async def create_or_update_permissions():
    async with AsyncSessionLocal() as db:
        created_count = 0
        updated_count = 0
        # all_permissions = await permission_crud.get_multi(db=db, limit=-1, query_filters=[Permission.name.contains("can_update_")])
        for permission in permissions:
            db_permission = await permission_crud.get(db=db, name=permission["name"])
            if not db_permission:
                await permission_crud.create(
                    db=db, obj_in=PermissionCreateSchema(**permission)
                )
                created_count += 1
            else:
                await permission_crud.update(
                    db=db,
                    db_obj=db_permission,
                    obj_in=PermissionUpdateSchema(**permission),
                )
                updated_count += 1
            scheduler_logger.info(f"Permission {permission['name']} synced!")
        msg = (
            f"*ktechhub::Permissions Sync Report*\n\n"
            f"✅ Items Created: {created_count}\n"
            f"✅ Items Updated: {updated_count}\n"
            f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_msg(msg=msg)
    await db.close()
