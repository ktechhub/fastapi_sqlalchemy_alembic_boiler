from fastapi import APIRouter, Depends, status
from sqlalchemy import and_, not_, or_, select
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import count
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.roles import Role
from app.models.user_roles import UserRole
from app.utils.responses import (
    success_response,
    not_found_response,
    bad_request_response,
)
from app.deps.user import get_user_with_role
from app.schemas.users import (
    AdminUserCreateSchema,
    UserUpdateSchema,
    UserResponseSchema,
    UserTotalCountListResponseSchema,
    UserFilters,
)
from app.models.users import User
from app.cruds.users import user_crud
from app.cruds.roles import role_crud
from app.cruds.user_roles import user_roles_crud
from app.database.database import get_async_session
from app.mails.email_service import send_email_async
from app.core.config import settings


class UserRouter:
    def __init__(self):
        self.router = APIRouter()
        self.singular = "User"
        self.plural = "Users"
        self.crud = user_crud
        self.response_model = UserResponseSchema
        self.response_list_model = UserTotalCountListResponseSchema

        # CRUD Endpoints
        self.router.add_api_route(
            "/", self.create, methods=["POST"], response_model=self.response_model
        )
        self.router.add_api_route(
            "/", self.list, methods=["GET"], response_model=self.response_list_model
        )
        self.router.add_api_route(
            "/{uuid}", self.get, methods=["GET"], response_model=self.response_model
        )
        self.router.add_api_route(
            "/{uuid}", self.update, methods=["PUT"], response_model=self.response_model
        )
        self.router.add_api_route(
            "/{uuid}",
            self.delete,
            methods=["DELETE"],
            response_model=self.response_model,
        )

    async def create(
        self,
        data: AdminUserCreateSchema,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        data.email = data.email.lower()
        # check if user already exists
        db_user = await self.crud.get(db, email=data.email)
        if db_user:
            return bad_request_response(f"{self.singular} already exists")
        # check for all the roles to be assigned
        roles = await role_crud.get_multi(db, limit=-1, name=data.role_names.split(","))
        if len(roles["data"]) != len(data.roles.split(",")):
            return bad_request_response("All roles not found")
        # Create the user in the database
        try:
            db_user = await self.crud.create(db, data)
            # Assign roles to the user
            for role in roles["data"]:
                await user_roles_crud.create(
                    db, user_uuid=db_user.uuid, role_uuid=role.uuid
                )
        except Exception as e:
            return bad_request_response(str(e))

        # Send an initialization email
        initialize_url = (
            f"{settings.FRONTEND_URL}/auth/initialize?email={db_user.email}"
        )
        try:
            await send_email_async(
                subject="Initialize your account",
                email_to=db_user.email,
                html=f"""
                    <p>Hi {db_user.first_name},</p>
                    <p>Welcome! Click the link below to initialize your account and set your password:</p>
                    <p><a href="{initialize_url}">Initialize Account</a></p>
                    <p>If you didn’t request this, you can safely ignore this email.</p>
                """,
            )
        except Exception as e:
            return bad_request_response(
                f"User created, but failed to send email: {str(e)}"
            )

        return success_response(
            message=f"{self.singular} created successfully and initialization email sent",
            data=db_user,
        )

    async def list(
        self,
        filters: UserFilters = Depends(),
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        # Base query with joins
        stmt = select(User).options(joinedload(User.roles))

        # Dynamic conditions
        conditions = []

        if filters.email is not None:
            conditions.append(User.email.ilike(f"%{filters.email}%"))
        if filters.first_name is not None:
            conditions.append(User.first_name.ilike(f"%{filters.first_name}%"))
        if filters.last_name is not None:
            conditions.append(User.last_name.ilike(f"%{filters.last_name}%"))
        if filters.phone_number is not None:
            conditions.append(User.phone_number.ilike(f"%{filters.phone_number}%"))
        if filters.gender is not None:
            conditions.append(User.gender.ilike(f"%{filters.gender}%"))
        if filters.address is not None:
            conditions.append(User.address.ilike(f"%{filters.address}%"))
        if filters.username is not None:
            conditions.append(User.username.ilike(f"%{filters.username}%"))
        if filters.national_id is not None:
            conditions.append(User.national_id.ilike(f"%{filters.national_id}%"))
        if filters.status is not None:
            conditions.append(User.status.ilike(f"%{filters.status}%"))

        if filters.is_active is not None:
            conditions.append(User.is_active == filters.is_active)
        if filters.is_verified is not None:
            conditions.append(User.is_verified == filters.is_verified)
        if filters.verified_at is not None:
            conditions.append(User.verified_at == filters.verified_at)
        if filters.date_of_birth is not None:
            conditions.append(User.date_of_birth == filters.date_of_birth)

        if filters.user_type is not None:
            user_types = [role.strip() for role in filters.user_type.split(",")]
            conditions.append(Role.name.in_(user_types))

        if filters.exclude_user_types is not None:
            excluded_roles = [
                role.strip() for role in filters.exclude_user_types.split(",")
            ]
            conditions.append(not_(Role.name.in_(excluded_roles)))

        if filters.search is not None:
            conditions.append(
                or_(
                    User.first_name.ilike(f"%{filters.search}%"),
                    User.last_name.ilike(f"%{filters.search}%"),
                    User.email.ilike(f"%{filters.search}%"),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Sorting
        # if filters.sort is not None:
        #     stmt = stmt.order_by(*self.crud.extract_sort_params(filters.sort))

        # Pagination
        stmt = stmt.offset(filters.skip)

        if filters.limit is not None:
            if filters.limit > 0:
                stmt = stmt.limit(filters.limit)
        # Execute query and call unique() to collapse duplicates
        result = await db.execute(stmt)
        users = result.unique().scalars().all()

        # Total count query
        total_count_stmt = (
            select(count(User.uuid)).where(and_(*conditions))
            if conditions
            else select(count(User.uuid))
        )
        total_count_result = await db.execute(total_count_stmt)
        total_count = total_count_result.scalar()
        # for item in users:
        #     print("item", item.user_roles)
        #     print(f"{[user_role.role.name for user_role in item.user_roles]}")
        return {
            "status": status.HTTP_200_OK,
            "detail": "Users fetched successfully",
            "total_count": total_count,
            "data": users,
        }

    async def get(
        self,
        uuid: str,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        stmt = (
            select(User)
            .options(joinedload(User.user_roles).joinedload(UserRole.role))
            .where(User.uuid == uuid)
        )
        db_user = await self.crud.get(db, statement=stmt)
        if not db_user:
            return not_found_response(f"{self.singular} not found")
        return success_response(
            message=f"{self.singular} fetched successfully",
            data=db_user.to_schema_dict(),
        )

    async def update(
        self,
        uuid: str,
        data: UserUpdateSchema,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        db_user = await self.crud.get(db, uuid=uuid)
        if not db_user:
            return not_found_response(f"{self.singular} not found")

        try:
            updated_user = await self.crud.update(db, db_user, data)
        except Exception as e:
            return bad_request_response(str(e))

        return success_response(
            message=f"{self.singular} updated successfully", data=updated_user
        )

    async def delete(
        self,
        uuid: str,
        user: User = Depends(get_user_with_role("admin")),
        db: AsyncSession = Depends(get_async_session),
    ):
        db_user = await self.crud.get(db, uuid=uuid)
        if not db_user:
            return not_found_response(f"{self.singular} not found")

        # Delete user roles
        await user_roles_crud.remove_multi_by(db, user_uuid=uuid)
        deleted_user = await self.crud.remove(db, uuid=uuid)
        return success_response(
            message=f"{self.singular} deleted successfully", data=deleted_user
        )
