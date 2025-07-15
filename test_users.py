import asyncio
from faker import Faker
from datetime import datetime, timezone
from app.tasks.common.fake_users import create_fake_users
from app.utils.password_util import hash_password
from app.cruds.users import user_crud
from app.cruds.roles import role_crud
from app.cruds.user_roles import user_roles_crud
from app.schemas.user_roles import UserRoleCreateSchema
from app.utils.telegram import send_telegram_msg

from app.tasks.common.permissions import create_or_update_permissions
from app.tasks.common.roles import create_or_update_roles
from app.schemas.users import UserUpdateWithPasswordSchema
from app.tasks.common.role_permissions import sync_role_permissions
from app.core.defaults import default_roles
from app.database.get_session import AsyncSessionLocal
from app.core.config import settings

ghana_cities = [
    "Accra",
    "Kumasi",
    "Tamale",
    "Takoradi",
    "Cape Coast",
    "Sunyani",
    "Koforidua",
    "Wa",
    "Ho",
    "Bolgatanga",
    "Tema",
    "Obuasi",
]

fake = Faker()


def ghana_phone_number():
    prefixes = [
        "20",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "29",
        "50",
        "53",
        "54",
        "55",
        "56",
        "57",
        "58",
        "59",
    ]
    return f"+233{fake.random_element(prefixes)}{fake.random_int(100000, 999999)}"


async def create_test_users() -> None:
    async with AsyncSessionLocal() as session:

        users = []
        for role_data in default_roles:
            role = await role_crud.get(db=session, name=role_data["name"])

            # check if user exists
            user = await user_crud.get(
                db=session, email=f"{role_data['name'].lower()}@{settings.DOMAIN}"
            )
            city = fake.random_element(ghana_cities)
            location = f"{fake.street_address()}, {city}, Ghana"
            national_id_prefix = f"{city[:3].upper()}"
            national_id = f"{national_id_prefix}-{fake.random_number(digits=10)}-{fake.random_number(digits=1)}"
            last_name = fake.last_name()
            if not user:
                # create user
                user = await user_crud.create(
                    db=session,
                    obj_in=UserUpdateWithPasswordSchema(
                        first_name=role_data["label"],
                        last_name=last_name,
                        email=f"{role_data['name'].lower()}@{settings.DOMAIN}",
                        password=hash_password("KtechHub2025"),
                        phone_number=ghana_phone_number(),
                        address=location,
                        date_of_birth=fake.date_of_birth(
                            minimum_age=18, maximum_age=60
                        ),
                        gender=fake.random_element(["male", "female"]),
                        is_active=True,
                        is_verified=True,
                        verified_at=datetime.now(tz=timezone.utc),
                        national_id=national_id,
                        avatar=fake.image_url(),
                    ),
                )

                # create user_role
                await user_roles_crud.create(
                    db=session,
                    obj_in=UserRoleCreateSchema(
                        role_uuid=role.uuid,
                        user_uuid=user.uuid,
                    ),
                )

                users.append(
                    {
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "role": role.name,
                    }
                )
            else:
                user = await user_crud.update(
                    db=session,
                    db_obj=user,
                    obj_in=UserUpdateWithPasswordSchema(
                        first_name=role_data["label"],
                        last_name=last_name,
                        password=hash_password("KtechHub2025"),
                    ),
                )
                users.append(
                    {
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "role": role.name,
                    }
                )
        print("users", users)
        msg = (
            f"*ktechhub::Users Sync Report*\n\n"
            f"✅ Users Created: {len(users)}\n"
            f"🕒 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_msg(msg=msg)


async def main():
    try:
        await create_or_update_permissions()
        await asyncio.sleep(1)
        await create_or_update_roles()
        await asyncio.sleep(1)
        await sync_role_permissions()
        await asyncio.sleep(1)
        await create_test_users()
        await asyncio.sleep(1)
        await create_fake_users()
    except Exception as e:
        print(f"Error in main(): {e}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
