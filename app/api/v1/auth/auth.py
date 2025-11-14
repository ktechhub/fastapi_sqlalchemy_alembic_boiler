from datetime import datetime, timezone
import urllib.parse
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from app.models.roles import Role
from app.models.users import User
from app.models.codes import VerificationCode
from app.utils.password_util import verify_password, hash_password
from app.utils.security_util import (
    create_access_token,
    create_refresh_token,
)
from app.utils.responses import (
    bad_request_response,
    conflict_response,
    not_found_response,
    success_response,
    created_response,
)
from app.cruds.codes import verification_code_crud
from app.cruds.users import user_crud
from app.cruds.roles import role_crud
from app.cruds.user_roles import user_roles_crud
from app.schemas.verification_codes import (
    VerificationCodeCreateSchema,
    ConfirmVerificationCode,
)
from app.schemas.users import (
    UserCreateSchema,
    UserResponseSchema,
    UserLoginResponseSchema,
    UserConfirmEmailSchema,
    UserUpdateSchema,
    SendVerificationEmailSchema,
    ResendSendVerificationCodeSchema,
    UserUpdatePasswordSchema,
    UserConfirmForgetPasswordSchema,
    UserInitializeSchema,
    UserUpdateWithPasswordSchema,
)
from app.schemas.user_roles import UserRoleCreateSchema
from app.database.get_session import get_async_session
from app.core.config import settings
from app.core.loggers import app_logger as logger
from app.utils.telegram import send_telegram_msg
from app.services.redis_push import redis_lpush
from app.cruds.activity_logs import activity_log_crud
from app.schemas.activity_logs import ActivityLogCreateSchema


class AuthRouter:
    def __init__(self):
        self.router = APIRouter()
        self.singular = "User"
        self.plural = "Users"
        self.crud = user_crud
        self.response_model = UserResponseSchema

        self.router.add_api_route(
            "/register/",
            self.register,
            methods=["POST"],
            status_code=status.HTTP_201_CREATED,
            summary=f"Create a new {self.singular}.",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/confirm-register/",
            self.confirm_register,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Confirm {self.singular} registration.",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/resend-verification-code/",
            self.resend_verification_code,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Resend {self.singular} verification code.",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/verify-code/",
            self.verify_code,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Verify {self.singular} verification code.",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/login/",
            self.login,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Login a new {self.singular}.",
            response_model=UserLoginResponseSchema,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/create-password/",
            self.create_password,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Create a new password.",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )
        self.router.add_api_route(
            "/initialize-account/",
            self.initialize_account,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Initialize a new account.",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )

        self.router.add_api_route(
            "/forget-password/",
            self.forget_password,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Forget a password.",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )

        self.router.add_api_route(
            "/confirm-forget-password/",
            self.confirm_forget_password,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Confirm forget password.",
            response_model=self.response_model,
            response_model_exclude_unset=True,
        )

    async def register(
        self,
        *,
        data: UserCreateSchema,
        session: AsyncSession = Depends(get_async_session),
    ) -> UserResponseSchema:
        """
        Create a new user.

        Args:
        - db (AsyncSession): The database session.
        - data (UserCreateSchema): The user data.

        Returns:
        - UserResponseSchema: The created user object.

        Raises:
        - HTTPException 400: If the request data is invalid.
        - HTTPException 409: If the email already exists for another user.
        - HTTPException 406: If the email is not found or not verified.
        """
        data.email = data.email.lower()
        db_user = await self.crud.get(db=session, email=data.email)
        if db_user:
            return conflict_response(f"{self.singular} with this email already exists.")

        # compare password
        if data.password != data.confirm_password:
            return bad_request_response("Passwords do not match.")

        # create user
        data.password = hash_password(data.password)
        del data.confirm_password
        role = await role_crud.get(db=session, name=data.user_type)
        del data.user_type
        try:
            user = await self.crud.create(db=session, obj_in=data)
            verification_code = await verification_code_crud.create(
                db=session,
                obj_in=VerificationCodeCreateSchema(
                    user_uuid=user.uuid, type="confirm_email"
                ),
            )

            await user_roles_crud.create(
                db=session,
                obj_in=UserRoleCreateSchema(user_uuid=user.uuid, role_uuid=role.uuid),
                user_uuid=user.uuid,
            )

            redis_lpush(
                {
                    "queue_name": "notifications",
                    "operation": "send_email",
                    "data": {
                        "to": user.email,
                        "subject": "Verify your email",
                        "salutation": f"Hi {user.first_name},",
                        "body": f"""
                        <p>Use the code below to verify your email: <br><b> {verification_code.code}</p>
                        """,
                        "queue_name": "notifications",
                    },
                }
            )
            logger.info(f"User {user.email} created successfully.")
        except Exception as e:
            logger.error(e)
            return bad_request_response(
                f"Oops... Something went wrong. {self.singular} could not be created."
            )
        stmt = (
            select(User).options(joinedload(User.roles)).where(User.uuid == user.uuid)
        )

        db_user: User = await self.crud.get(db=session, statement=stmt)
        await activity_log_crud.create(
            db=session,
            obj_in=ActivityLogCreateSchema(
                user_uuid=None,
                entity=self.singular,
                action="create",
                previous_data={},
                new_data=db_user.to_dict(),
                description="User created successfully.",
            ),
        )

        return created_response(
            "Please confirm your signup, check your email for the verification code.",
            data=None,
        )

    async def confirm_register(
        self,
        *,
        data: UserConfirmEmailSchema,
        session: AsyncSession = Depends(get_async_session),
    ):
        stmt = (
            select(User)
            .options(joinedload(User.roles))
            .where(User.email == data.email.lower())
        )

        db_user = await self.crud.get(
            db=session, email=data.email.lower(), include_relations="roles"
        )
        if not db_user:
            return not_found_response("User not found.")

        verification_code: VerificationCode = await verification_code_crud.get(
            db=session, user_uuid=db_user.uuid, code=data.code, type="confirm_email"
        )
        if not verification_code:
            return not_found_response("Verification code not found.")

        # Check if code is expired and send a new one
        if verification_code.is_expired():
            logger.info(
                f"User {db_user.email} verification code expired. Sending a new one."
            )
            await verification_code_crud.remove_multi(
                db=session,
                user_uuid=db_user.uuid,
                type="confirm_email",
            )
            verification_code = await verification_code_crud.create(
                db=session,
                obj_in=VerificationCodeCreateSchema(
                    user_uuid=db_user.uuid, type="confirm_email"
                ),
                user_uuid=db_user.uuid,
            )

            redis_lpush(
                {
                    "queue_name": "notifications",
                    "operation": "send_email",
                    "data": {
                        "to": db_user.email,
                        "subject": "Verify your email",
                        "salutation": f"Hi {db_user.first_name},",
                        "body": f"""
                            <p>Use the code below to verify your email: <br><b> {verification_code.code}</p>
                            """,
                        "queue_name": "notifications",
                    },
                }
            )
            logger.info(f"User {db_user.email} verification code resent successfully.")
            return bad_request_response(
                "Verification code has expired. We have sent you a new one."
            )

        if db_user.is_verified:
            return bad_request_response("User is already verified")

        # remove verification code
        await verification_code_crud.remove(db=session, db_obj=verification_code)
        # update user
        user = await self.crud.update(
            db=session,
            db_obj=db_user,
            obj_in=UserUpdateSchema(
                is_verified=True,
                verified_at=datetime.now(tz=timezone.utc),
                is_active=True,
            ),
            user_uuid=db_user.uuid,
        )
        logger.info(f"User {user.email} verified successfully.")
        return success_response(
            "User verified successfully. Please login.",
        )

    async def resend_verification_code(
        self,
        data: ResendSendVerificationCodeSchema,
        session: AsyncSession = Depends(get_async_session),
    ):
        db_user = await self.crud.get(db=session, email=data.email.lower())
        if not db_user:
            return not_found_response("User not found.")
        verification_code = await verification_code_crud.create(
            db=session,
            obj_in=VerificationCodeCreateSchema(user_uuid=db_user.uuid, type=data.type),
            user_uuid=db_user.uuid,
        )

        redis_lpush(
            {
                "queue_name": "notifications",
                "operation": "send_email",
                "data": {
                    "to": db_user.email,
                    "subject": "Verify your email",
                    "salutation": f"Hi {db_user.first_name},",
                    "body": f"""
                        <p>Use the code below to verify your email: <br><b> {verification_code.code}</p>
                        """,
                    "queue_name": "notifications",
                },
            }
        )
        logger.info(f"User {db_user.email} verification code resent successfully.")
        return success_response(
            "Verification code sent successfully.",
        )

    async def verify_code(
        self,
        data: ConfirmVerificationCode,
        session: AsyncSession = Depends(get_async_session),
    ):
        verification_code: VerificationCode = await verification_code_crud.get(
            db=session,
            code=data.code,
            type=data.type,
        )
        if not verification_code:
            return not_found_response("Verification code not found.")

        if verification_code.is_expired():
            await verification_code_crud.remove(db=session, db_obj=verification_code)
            return bad_request_response(
                "Verification code has expired. Request a new one."
            )

        return success_response("Verification code is valid.")

    async def login(
        self,
        data: OAuth2PasswordRequestForm = Depends(),
        session: AsyncSession = Depends(get_async_session),
    ):
        """
        User Login.
        """
        # company, admin = email
        # user, agents = phone, email
        stmt = (
            select(User)
            .options(joinedload(User.roles))
            .where(User.email == data.username.lower())
        )
        db_user: User = await self.crud.get(db=session, statement=stmt)
        if not db_user:
            logger.error(f"User {data.username} not found.")
            return bad_request_response("Incorrect email or password")
        if not verify_password(data.password, db_user.password):
            logger.error(f"User {data.username} password mismatch.")
            return bad_request_response("Incorrect email or password")
        if not db_user.is_active:
            logger.error(f"User {data.username} is not active.")
            return bad_request_response("User is not active")
        if not db_user.is_verified:
            logger.error(f"User {data.username} is not verified.")
            return bad_request_response("User is not verified")

        logger.info(f"User {db_user.email} logged in successfully.")
        await activity_log_crud.create(
            db=session,
            obj_in=ActivityLogCreateSchema(
                user_uuid=None,
                entity=self.singular,
                action="login",
                previous_data=db_user.to_dict(),
                new_data={},
                description="User logged in successfully.",
            ),
        )
        return {
            "status": status.HTTP_200_OK,
            "detail": "Login success!",
            "access_token": create_access_token(str(db_user.uuid)),
            "refresh_token": create_refresh_token(str(db_user.uuid)),
            "data": db_user.to_dict(),
        }

    async def create_password(
        self,
        data: UserUpdatePasswordSchema,
        session: AsyncSession = Depends(get_async_session),
    ):
        """
        Create or set a password for the user.
        """
        stmt = (
            select(User)
            .options(joinedload(User.roles))
            .where(User.email == data.email.lower())
        )
        db_user = await self.crud.get(db=session, statement=stmt)
        if not db_user:
            logger.error(f"User {data.email} not found.")
            return not_found_response("User not found.")

        if db_user.is_verified and db_user.password:
            logger.error(f"User {data.email} already has a password.")
            return bad_request_response(
                "User already has a password set. Maybe you would like to reset?"
            )

        user = await self.crud.update(
            db=session,
            db_obj=db_user,
            obj_in=UserUpdateSchema(
                password=hash_password(data.password),
                is_active=True,
                is_verified=True,
                verified_at=datetime.now(tz=timezone.utc),
            ),
            user_uuid=db_user.uuid,
        )
        logger.info(f"User {db_user.email} password created successfully.")
        return success_response("Password created successfully.")

    async def initialize_account(
        self,
        data: UserInitializeSchema,
        session: AsyncSession = Depends(get_async_session),
    ):
        """
        Initialize user account.
        """
        stmt = (
            select(User)
            .options(joinedload(User.roles))
            .where(User.email == data.email.lower())
        )
        db_user = await self.crud.get(db=session, statement=stmt)
        if not db_user:
            logger.error(f"User {data.email} not found. - initializing account.")
            return not_found_response("User not found.")

        if db_user.is_verified and db_user.password:
            logger.error(f"User {data.email} already has a password set.")
            return bad_request_response(
                "User already has a password set. Maybe you would like to reset?"
            )
        user = await self.crud.update(
            db=session,
            db_obj=db_user,
            obj_in=UserUpdateWithPasswordSchema(
                password=hash_password(data.password),
                is_active=True,
                is_verified=True,
                verified_at=datetime.now(tz=timezone.utc),
                first_name=data.first_name,
                last_name=data.last_name,
                phone_number=data.phone_number,
            ),
            user_uuid=db_user.uuid,
        )
        logger.info(f"User {user.email} account initialized successfully.")
        return success_response("Account initialized successfully. Proceed to login.")

    async def forget_password(
        self,
        data: SendVerificationEmailSchema,
        session: AsyncSession = Depends(get_async_session),
    ):
        """
        Handle forgot password request by sending a reset code.
        """
        db_user = await self.crud.get(db=session, email=data.email.lower())
        if not db_user:
            logger.error(f"User {data.email} not found. Forget password")
            return not_found_response("User not found.")

        verification_code = await verification_code_crud.create(
            db=session,
            obj_in=VerificationCodeCreateSchema(
                user_uuid=db_user.uuid, type="reset_password"
            ),
            user_uuid=db_user.uuid,
        )
        url = f"{settings.FRONTEND_URL}/reset-password?code={urllib.parse.quote(verification_code.code)}&email={urllib.parse.quote(db_user.email)}"
        try:

            redis_lpush(
                {
                    "queue_name": "notifications",
                    "operation": "send_email",
                    "data": {
                        "to": db_user.email,
                        "subject": "Reset your password",
                        "salutation": f"Hi {db_user.first_name},",
                        "body": f"""
                            <p>Use the code below to reset your password: <br><b>{verification_code.code}</b></p>
                            <p>Click <a href="{url}">here</a> to reset your password on web.</p></b></b>
                            <p>Or copy and paste this link in your browser: <br> {url}</p>
                            """,
                        "queue_name": "notifications",
                    },
                }
            )
            logger.info(
                f"Password reset code sent successfully for user {db_user.email}."
            )
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            send_telegram_msg(
                f"{verification_code.code}:: Error sending email: {e}"
            )  # TODO: Remove this line later
        await activity_log_crud.create(
            db=session,
            obj_in=ActivityLogCreateSchema(
                user_uuid=None,
                entity="verification codes",
                action="create",
                previous_data={},
                new_data=verification_code.to_dict(),
                description=f"Password reset code sent successfully for user {db_user.email}.",
            ),
        )
        return success_response(
            "Password reset code sent successfully.",
        )

    async def confirm_forget_password(
        self,
        data: UserConfirmForgetPasswordSchema,
        session: AsyncSession = Depends(get_async_session),
    ):
        """
        Request a password change by verifying with a code.
        """
        stmt = (
            select(User)
            .options(joinedload(User.roles))
            .where(User.email == data.email.lower())
        )

        db_user = await self.crud.get(db=session, statement=stmt)
        if not db_user:
            logger.error(f"User {data.email} not found. Confirm forget password.")
            return not_found_response("User not found.")

        verification_code: VerificationCode = await verification_code_crud.get(
            db=session,
            user_uuid=db_user.uuid,
            code=data.code,
            type="reset_password",
        )
        if not verification_code:
            logger.error(
                f"Invalid or expired verification code for user {data.email}. Confirm forget password."
            )
            return not_found_response("Invalid or expired verification code.")

        if verification_code.is_expired():
            logger.error(
                f"Invalid or expired verification code for user {data.email}. Confirm forget password."
            )
            await verification_code_crud.remove(db=session, db_obj=verification_code)
            return bad_request_response("Verification code has expired.")

        try:
            # Code is valid; allow password update
            await self.crud.update(
                db=session,
                db_obj=db_user,
                obj_in=UserUpdateWithPasswordSchema(
                    password=hash_password(data.password),
                    is_active=True,
                    is_verified=True,
                    verified_at=(
                        datetime.now(tz=timezone.utc)
                        if not db_user.verified_at
                        else db_user.verified_at
                    ),
                ),
                user_uuid=db_user.uuid,
            )

            await verification_code_crud.remove(db=session, db_obj=verification_code)
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return bad_request_response(str(e))
        logger.info(f"User {db_user.email} password reset successfully.")

        return success_response("Password reset successfully!")
