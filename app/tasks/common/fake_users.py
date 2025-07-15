import random
from faker import Faker
from datetime import datetime, timezone
from app.utils.password_util import hash_password
from app.cruds.users import user_crud
from app.cruds.roles import role_crud
from app.cruds.user_roles import user_roles_crud
from app.schemas.user_roles import UserRoleCreateSchema
from app.schemas.users import UserUpdateWithPasswordSchema
from app.database.get_session import AsyncSessionLocal
from app.core.config import settings


async def create_fake_users() -> None:
    async with AsyncSessionLocal() as session:
        fake = Faker()

        # Ghana cities list
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

        roles = await role_crud.get_multi(db=session, limit=-1)

        users = []
        for role in roles["data"]:
            for _ in range(random.randint(10, 20)):
                # Generate random Ghana address
                city = fake.random_element(ghana_cities)
                address = f"{fake.street_address()}, {city}, Ghana"

                # Generate national ID prefix based on city (first 3 letters, uppercase)
                national_id_prefix = f"{city[:3].upper()}"

                # Create national ID
                national_id = f"{national_id_prefix}-{fake.random_number(digits=10)}-6"

                try:
                    user = await user_crud.create(
                        db=session,
                        obj_in=UserUpdateWithPasswordSchema(
                            first_name=fake.first_name(),
                            last_name=fake.last_name(),
                            email=fake.email(domain=settings.DOMAIN),
                            password=hash_password(
                                fake.password(
                                    length=10,
                                    special_chars=True,
                                    digits=True,
                                    upper_case=True,
                                    lower_case=True,
                                )
                            ),
                            phone_number=fake.phone_number(),
                            address=address,
                            date_of_birth=fake.date_of_birth(
                                minimum_age=18, maximum_age=60
                            ),
                            gender=fake.random_element(["male", "female"]),
                            is_active=True,
                            is_verified=True,
                            verified_at=datetime.now(tz=timezone.utc),
                            national_id=national_id,
                            avatar=fake.image_url(),  # Or set to an empty string if needed
                        ),
                    )
                    # Create user role
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
                            "city": city,
                            "national_id": national_id,
                        }
                    )
                except Exception as e:
                    print(e)

        print("users", users)
    await session.close()
