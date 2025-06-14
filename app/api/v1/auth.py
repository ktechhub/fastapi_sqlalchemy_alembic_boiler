from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.models.users import User
from app.utils.password_util import verify_password, hash_password
from app.utils.security_util import create_access_token, create_refresh_token
from app.utils.responses import (
    bad_request_response,
    conflict_response,
    not_found_response,
    success_response,
    created_response,
)
from app.cruds.codes import verification_code_crud
from app.cruds.users import user_crud
from app.schemas.verification_codes import VerificationCodeCreate
from app.schemas.users import (
    UserCreateSchema,
    UserResponseSchema,
    UserLoginResponseSchema,
    UserConfirmEmailSchema,
    UserUpdateSchema,
    SendVerificationEmailSchema,
    UserUpdatePasswordSchema,
    UserConfirmForgetPasswordSchema,
)
from app.mails.email_service import send_email_async
from app.database.database import get_async_session


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
        )
        self.router.add_api_route(
            "/confirm-register/",
            self.confirm_register,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Confirm {self.singular} registration.",
            response_model=UserLoginResponseSchema,
        )
        self.router.add_api_route(
            "/resend-verification-code",
            self.resend_verification_code,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Resend {self.singular} verification code.",
            response_model=self.response_model,
        )
        self.router.add_api_route(
            "/login/",
            self.login,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Login a new {self.singular}.",
            response_model=UserLoginResponseSchema,
        )
        self.router.add_api_route(
            "/create-password/",
            self.create_password,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Create a new password.",
            response_model=self.response_model,
        )

        self.router.add_api_route(
            "/forget-password/",
            self.forget_password,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Forget a password.",
            response_model=self.response_model,
        )

        self.router.add_api_route(
            "/confirm-forget-password/",
            self.confirm_forget_password,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            summary=f"Confirm forget password.",
            response_model=self.response_model,
        )

    async def register(
        self,
        *,
        data: UserCreateSchema,
        session: Session = Depends(get_async_session),
    ) -> UserResponseSchema:
        """
        Create a new user.

        Args:
        - db (Session): The database session.
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
        try:
            user = await self.crud.create(db=session, obj_in=data)
            verification_code = await verification_code_crud.create(
                db=session,
                obj_in=VerificationCodeCreate(
                    user_uuid=user.uuid, type="confirm_email"
                ),
            )

            await send_email_async(
                subject="Verify your email",
                email_to=user.email,
                html=f"""
                <p>Hi {user.first_name},</p><br>
                <p>Use the code below to verify your email: <br><b> {verification_code.code}</p>
                """,
            )

        except Exception as e:
            return bad_request_response(
                f"Oops... Something went wrong. {self.singular} could not be created."
            )

        return created_response(
            "Please confirm your signup, check your email for the verification code.",
            data=None,
        )

    async def confirm_register(
        self,
        *,
        data: UserConfirmEmailSchema,
        session: Session = Depends(get_async_session),
    ):
        db_user = await self.crud.get(db=session, email=data.email.lower())
        if not db_user:
            return not_found_response("User not found.")

        verification_code = await verification_code_crud.get(
            db=session, user_uuid=db_user.uuid, code=data.code, type="confirm_email"
        )
        if not verification_code:
            return not_found_response("Verification code not found.")

        # Check if code is expired and send a new one
        if verification_code.expires_at < datetime.now(tz=timezone.utc):
            await verification_code_crud.remove(db=session, id=verification_code.id)
            verification_code = await verification_code_crud.create(
                db=session,
                obj_in=VerificationCodeCreate(
                    user_uuid=db_user.uuid, type="confirm_email"
                ),
            )
            await send_email_async(
                subject="Verify your email",
                email_to=db_user.email,
                html=f"""
                <p>Hi {db_user.first_name},</p><br>
                <p>Use the code below to verify your email: <br><b> {verification_code.code}</p>
                """,
            )
            return bad_request_response(
                "Verification code has expired. We have sent you a new one."
            )

        if db_user.is_verified:
            raise HTTPException(status_code=400, detail="User is already verified")

        # remove verification code
        await verification_code_crud.remove(db=session, id=verification_code.id)

        # update user
        user = await self.crud.update(
            db=session,
            db_obj=db_user,
            obj_in=UserUpdateSchema(
                is_verified=True,
                verified_at=datetime.now(tz=timezone.utc),
                is_active=True,
            ),
        )

        return {
            "status": status.HTTP_200_OK,
            "detail": f"{self.singular} verified successfully.",
            "access_token": create_access_token(str(db_user.uuid)),
            "refresh_token": create_refresh_token(str(db_user.uuid)),
            "data": user,
        }

    async def resend_verification_code(
        self,
        data: SendVerificationEmailSchema,
        session: Session = Depends(get_async_session),
    ):
        db_user = await self.crud.get(db=session, email=data.email.lower())
        if not db_user:
            return not_found_response("User not found.")
        verification_code = await verification_code_crud.create(
            db=session,
            obj_in=VerificationCodeCreate(user_uuid=db_user.uuid, type="confirm_email"),
        )
        await send_email_async(
            subject="Verify your email",
            email_to=db_user.email,
            html=f"""
                <p>Hi {db_user.first_name},</p><br>
                <p>Use the code below to verify your email: <br><b> {verification_code.code}</p>
                """,
        )
        return success_response(
            "Verification code sent successfully.",
        )

    async def login(
        self,
        data: OAuth2PasswordRequestForm = Depends(),
        session: Session = Depends(get_async_session),
    ):
        """
        User Login.
        """
        db_user = await self.crud.get(
            db=session, email=data.username.lower(), eager_load=[User.roles]
        )
        if not db_user:
            return bad_request_response("Incorrect email or password")
        if not verify_password(data.password, db_user.password):
            return bad_request_response("Incorrect email or password")
        if not db_user.is_active:
            return bad_request_response("User is not active")
        if not db_user.is_verified:
            return bad_request_response("User is not verified")

        return {
            "status": status.HTTP_200_OK,
            "detail": "Login success!",
            "access_token": create_access_token(str(db_user.uuid)),
            "refresh_token": create_refresh_token(str(db_user.uuid)),
            "data": db_user,
        }

    async def create_password(
        self,
        data: UserUpdatePasswordSchema,
        session: Session = Depends(get_async_session),
    ):
        """
        Create or set a password for the user.
        """
        db_user = await self.crud.get(db=session, email=data.email.lower())
        if not db_user:
            return not_found_response("User not found.")

        if db_user.is_verified and db_user.password:
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
        )
        return success_response("Password created successfully.", user)

    async def forget_password(
        self,
        data: SendVerificationEmailSchema,
        session: Session = Depends(get_async_session),
    ):
        """
        Handle forgot password request by sending a reset code.
        """
        db_user = await self.crud.get(db=session, email=data.email.lower())
        if not db_user:
            return not_found_response("User not found.")

        verification_code = await verification_code_crud.create(
            db=session,
            obj_in=VerificationCodeCreate(
                user_uuid=db_user.uuid, type="reset_password"
            ),
        )
        await send_email_async(
            subject="Reset your password",
            email_to=db_user.email,
            html=f"""
                <p>Hi {db_user.first_name},</p><br>
                <p>Use the code below to reset your password: <br><b>{verification_code.code}</b></p>
                """,
        )
        return success_response(
            "Password reset code sent successfully.",
        )

    async def confirm_forget_password(
        self,
        data: UserConfirmForgetPasswordSchema,
        session: Session = Depends(get_async_session),
    ):
        """
        Request a password change by verifying with a code.
        """
        db_user = await self.crud.get(db=session, email=data.email.lower())
        if not db_user:
            return not_found_response("User not found.")

        verification_code = await verification_code_crud.get(
            db=session,
            user_uuid=db_user.uuid,
            code=data.code,
            type="reset_password",
        )
        if not verification_code:
            return not_found_response("Invalid or expired verification code.")

        if verification_code.expires_at < datetime.now(tz=timezone.utc):
            await verification_code_crud.remove(db=session, id=verification_code.id)
            return bad_request_response("Verification code has expired.")

        try:
            # Code is valid; allow password update
            await self.crud.update(
                db=session,
                db_obj=db_user,
                obj_in=UserUpdateSchema(
                    password=hash_password(data.password),
                    is_active=True,
                    is_verified=True,
                    verified_at=(
                        datetime.now(tz=timezone.utc)
                        if not db_user.verified_at
                        else db_user.verified_at
                    ),
                ),
            )
            await verification_code_crud.remove(db=session, id=verification_code.id)
        except Exception as e:
            return bad_request_response(str(e))

        return success_response(
            "Verification code validated. Proceed to update password.",
        )
