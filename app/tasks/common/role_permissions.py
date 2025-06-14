from pydantic import BaseModel, EmailStr, constr
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.cruds.permissions import permission_crud
from app.cruds.roles import role_crud
from app.cruds.role_permissions import role_permission_crud
from app.schemas.role_permissions import RolePermissionUpdateSchema
from app.utils.telegram import send_telegram_msg
from .defaults import default_role_permissions
from app.core.loggers import scheduler_logger


engine = create_async_engine(settings.DATABASE_URL, pool_size=200, pool_pre_ping=True)
SessionLocal = sessionmaker(
    engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def sync_role_permissions():
    async with SessionLocal() as db:
        created_count = 0
        updated_count = 0

        for role_permission in default_role_permissions:
            # Get the role object based on the role name
            role_name = role_permission["role"]
            role = await role_crud.get(db=db, name=role_name)
            if not role:
                scheduler_logger.warning(f"Role '{role_name}' not found, skipping.")
                continue

            # Iterate through the permissions dictionary
            for resource, actions in role_permission["permissions"].items():
                for action in actions:
                    # Construct permission name dynamically
                    permission_name = f"can_{action}_{resource}"

                    # Fetch the permission by its name
                    permission = await permission_crud.get(db=db, name=permission_name)
                    if not permission:
                        scheduler_logger.warning(
                            f"Permission '{permission_name}' not found, skipping."
                        )
                        continue

                    # Check if the role-permission association exists
                    existing_role_permission = await role_permission_crud.get(
                        db=db,
                        role_uuid=role.uuid,
                        permission_uuid=permission.uuid,
                    )

                    role_permission_data = RolePermissionUpdateSchema(
                        role_uuid=role.uuid, permission_uuid=permission.uuid
                    )
                    if existing_role_permission:
                        # Update the existing role_permission if needed (e.g., timestamps)
                        await role_permission_crud.update(
                            db=db,
                            db_obj=existing_role_permission,
                            obj_in=role_permission_data,
                        )
                        updated_count += 1
                    else:
                        # Create a new role_permission association
                        await role_permission_crud.create(
                            db=db,
                            obj_in=role_permission_data,
                        )
                        created_count += 1

            scheduler_logger.info(f"Role {role.name} synced!")
        # Log summary
        scheduler_logger.info(
            f"Sync complete: {created_count} role-permissions created, {updated_count} updated."
        )
    msg = (
        f"*GOPSC::Role Permissions Sync Report*\n\n"
        f"✅ Items Created: {created_count}\n"
        f"✅ Items Updated: {updated_count}\n"
        f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    send_telegram_msg(msg=msg)
    await db.close()
