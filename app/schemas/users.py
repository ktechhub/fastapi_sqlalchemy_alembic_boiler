from datetime import date, datetime
from typing import List, Literal, Optional, Annotated
import dns.resolver
from pydantic import BaseModel, EmailStr, Field, field_validator, constr
from .base_schema import (
    BaseResponseSchema,
    BaseUUIDSchema,
    BaseTotalCountResponseSchema,
)
from ..core.constants import DISPOSABLE_EMAIL_DOMAINS
from .base_filters import BaseFilters
from .validate_uuid import UUIDStr
from app.utils.responses import bad_request_response
from .countries import CountrySchema

PasswordStr = Annotated[str, constr(min_length=8)]
PhoneStr = Annotated[str, constr(min_length=10, max_length=15)]
NationalIDStr = Annotated[str, constr(min_length=8, max_length=20)]
GenderType = Literal["male", "female", "other"]


class UserBaseSchema(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[PhoneStr] = None
    address: Optional[str] = Field(None, max_length=255)
    gender: Optional[GenderType] = Field("other", max_length=10)
    country_id: Optional[int] = None


class EmailValidationSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    def validate_email(cls, value):
        domain = value.split("@")[1]
        if domain in DISPOSABLE_EMAIL_DOMAINS:
            return bad_request_response(f"Email is not allowed")
        try:
            # Check for MX records
            answers = dns.resolver.resolve(domain, "MX")
            if not answers:
                return bad_request_response(
                    f"Email domain {domain} does not have valid MX records"
                )
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout):
            return bad_request_response(
                f"Email domain {domain} does not have valid MX records"
            )

        except Exception as e:
            return bad_request_response(
                f"Email domain {domain} does not have valid MX records"
            )
        return value


default_export_columns = [
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "gender",
    "address",
    "date_of_birth",
]


class UserCreateSchema(UserBaseSchema):
    password: PasswordStr
    confirm_password: str
    user_type: Literal["user", "company"] = "user"

    @field_validator("password", "confirm_password")
    def validate_password_complexity(cls, value):
        # Check password complexity requirements here
        if not any(char.isupper() for char in value):
            return bad_request_response(
                "Password must contain at least one uppercase letter"
            )
        if not any(char.isdigit() for char in value):
            return bad_request_response("Password must contain at least one digit")
        return value


class SendVerificationEmailSchema(EmailValidationSchema):
    pass


class ResendSendVerificationCodeSchema(SendVerificationEmailSchema):
    type: Literal["confirm_email", "reset_password", "change_password"] = (
        "confirm_email"
    )


class UserConfirmEmailSchema(EmailValidationSchema):
    code: Annotated[str, constr(min_length=1, max_length=8)]


class UserConfirmForgetPasswordSchema(EmailValidationSchema):
    code: Annotated[str, constr(min_length=1, max_length=8)]
    password: PasswordStr

    @field_validator("password")
    def validate_password_complexity(cls, value):
        # Check password complexity requirements here
        if not any(char.isupper() for char in value):
            return bad_request_response(
                "Password must contain at least one uppercase letter"
            )
        if not any(char.isdigit() for char in value):
            return bad_request_response("Password must contain at least one digit")
        return value


class UserUpdateSchema(UserBaseSchema):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_verified: Optional[bool] = None
    verified_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    phone_number: Optional[PhoneStr] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    status: Optional[str] = None
    country_id: Optional[int] = None


class UserUpdateWithPasswordSchema(UserBaseSchema):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_verified: Optional[bool] = None
    verified_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    phone_number: Optional[PhoneStr] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    password: Optional[str] = None
    status: Optional[str] = None
    country_id: Optional[int] = None


class AdminUpdateUserSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[PhoneStr] = None
    gender: Optional[GenderType] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    role_uuid: UUIDStr = Field(
        None,
        description="Comma separated list of role uuids",
        examples=["d6fbbd0a-fbb5-4e67-93c1-4323e30a817f"],
    )
    country_id: Optional[int] = None


class AdminUpdateFieldOfficerSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[PhoneStr] = None
    gender: Optional[GenderType] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    country_id: Optional[int] = None


class UserUpdatePasswordSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    def validate_password_complexity(cls, value):
        # Check password complexity requirements here
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        return value


class UserInitializeSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone_number: Optional[PhoneStr] = None
    date_of_birth: Optional[date] = None
    country_id: Optional[int] = None

    @field_validator("password")
    def validate_password_complexity(cls, value):
        # Check password complexity requirements here
        if not any(char.isupper() for char in value):
            return bad_request_response(
                "Password must contain at least one uppercase letter"
            )
        if not any(char.isdigit() for char in value):
            return bad_request_response("Password must contain at least one digit")
        return value


class AdminUserCreateSchema(BaseModel):
    email: EmailStr
    role_uuid: UUIDStr = Field(
        ...,
        description="Comma separated list of role uuids",
        examples=["d6fbbd0a-fbb5-4e67-93c1-4323e30a817f"],
    )


class AdminSendEmailSchema(BaseModel):
    email: EmailStr


class UserUpdateNewPasswordSchema(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    def validate_password_complexity(cls, value):
        # Check password complexity requirements here
        if not any(char.isupper() for char in value):
            return bad_request_response(
                "Password must contain at least one uppercase letter"
            )
        if not any(char.isdigit() for char in value):
            return bad_request_response("Password must contain at least one digit")
        return value


class UserUpdateProfileSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[PhoneStr] = None
    gender: Optional[GenderType] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    country_id: Optional[int] = None


class UserRoleSchema(BaseUUIDSchema):
    name: Optional[str] = Field(None, description="The unique name of the role")
    label: Optional[str] = Field(
        None, description="A human-readable label for the role"
    )
    description: Optional[str] = Field(
        None, description="Optional description of the role and its purpose"
    )
    has_dashboard_access: Optional[bool] = False


class UserRoleWithoutRoutesSchema(BaseUUIDSchema):
    name: Optional[str] = Field(None, description="The unique name of the role")
    label: Optional[str] = Field(
        None, description="A human-readable label for the role"
    )
    description: Optional[str] = Field(
        None, description="Optional description of the role and its purpose"
    )
    has_dashboard_access: Optional[bool] = False


class UserWithoutRoutesSchema(UserUpdateSchema, BaseUUIDSchema):
    is_active: bool = False
    is_verified: bool = False
    verified_at: Optional[datetime] | None = None
    phone_number: Optional[str] = None
    gender: Optional[GenderType] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    country_id: Optional[int] = None
    roles: Optional[List[UserRoleWithoutRoutesSchema]] = None
    country: Optional[CountrySchema] = None


class UserSchema(UserUpdateSchema, BaseUUIDSchema):
    is_active: bool = False
    is_verified: bool = False
    verified_at: Optional[datetime] | None = None
    phone_number: Optional[str] = None
    gender: Optional[GenderType] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    country_id: Optional[int] = None
    roles: Optional[List[UserRoleSchema]] = None
    country: Optional[CountrySchema] = None


class UserResponseSchema(BaseResponseSchema):
    data: Optional[UserSchema] = None


class UserResponseWithoutRoutesSchema(BaseResponseSchema):
    data: Optional[UserWithoutRoutesSchema] = None


class UserListResponseSchema(BaseResponseSchema):
    data: Optional[List[UserSchema]] = None


class UserTotalCountListResponseSchema(BaseTotalCountResponseSchema):
    data: Optional[List[UserWithoutRoutesSchema]] = None


class UserLoginResponseSchema(BaseResponseSchema):
    access_token: str
    refresh_token: str
    data: Optional[UserSchema] = None


class UserFilters(BaseFilters):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    verified_at: Optional[datetime] | None = None
    phone_number: Optional[str] = None
    gender: Optional[GenderType] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    status: Optional[str] = None
    user_type: Optional[str] = None
    exclude_user_types: Optional[str] = None
    search: Optional[str] = Field(
        None,
        description="Search by firstname, lastname or email",
        pattern=r"""^(?i)[\p{L}\p{N}\s]+(?:[.,'\-\s][\p{L}\p{N}\s]+)*[.]?$""",
    )
    has_dashboard_access: Optional[bool] = None
    include_relations: Optional[str] = Field(
        "roles",
        description="A comma-separated list of related models to include in the result set (e.g., 'permissions,users')",
        example="roles",
    )
    country_id: Optional[int] = None
