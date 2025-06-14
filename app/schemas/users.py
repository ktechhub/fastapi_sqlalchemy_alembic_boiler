from datetime import date, datetime
from typing import List, Literal, Optional
import dns.resolver
from pydantic import BaseModel, EmailStr, Field, field_validator, constr
from .base_schema import (
    BaseResponseSchema,
    BaseUUIDSchema,
    BaseTotalCountResponseSchema,
)
from .base_filters import BaseFilters
from app.core.constants import DISPOSABLE_EMAIL_DOMAINS


class UserBaseSchema(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str

    # @field_validator("email")
    # def validate_email(cls, value):
    #     domain = value.split("@")[1]
    #     if domain in DISPOSABLE_EMAIL_DOMAINS:
    #         raise ValueError(f"Email is not allowed")
    #     try:
    #         # Check for MX records
    #         answers = dns.resolver.resolve(domain, "MX")
    #         if not answers:
    #             raise ValueError(
    #                 f"Email domain {domain} does not have valid MX records"
    #             )
    #     except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout):
    #         raise ValueError(f"Email domain {domain} does not have valid MX records")

    #     except Exception as e:
    #         raise ValueError(f"Email domain {domain} does not have valid MX records")
    #     return value


class UserCreateSchema(UserBaseSchema):
    password: constr(min_length=6)  # type: ignore
    confirm_password: str
    national_id: Optional[str] = None
    user_type: Literal["user", "organization", "guest"] = "user"

    @field_validator("password", "confirm_password")
    def validate_password_complexity(cls, value):
        # Check password complexity requirements here
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        return value


class SendVerificationEmailSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    def validate_email(cls, value):
        domain = value.split("@")[1]
        if domain in DISPOSABLE_EMAIL_DOMAINS:
            raise ValueError(f"Email is not allowed")
        try:
            # Check for MX records
            answers = dns.resolver.resolve(domain, "MX")
            if not answers:
                raise ValueError(
                    f"Email domain {domain} does not have valid MX records"
                )
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout):
            raise ValueError(f"Email domain {domain} does not have valid MX records")

        except Exception as e:
            raise ValueError(f"Email domain {domain} does not have valid MX records")
        return value


class UserConfirmEmailSchema(BaseModel):
    email: EmailStr
    code: str


class UserConfirmForgetPasswordSchema(BaseModel):
    email: EmailStr
    code: str
    password: constr(min_length=8)  # type: ignore
    confirm_password: str

    @field_validator("password", "confirm_password")
    def validate_password_complexity(cls, value):
        # Check password complexity requirements here
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        return value


class UserUpdateSchema(UserBaseSchema):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_verified: Optional[bool] = None
    verified_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    national_id: Optional[str] = None


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


class UserUpdateNewPasswordSchema(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    def validate_password_complexity(cls, value):
        # Check password complexity requirements here
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        return value


class userUpdateProfileSchema(BaseModel):
    phone: Optional[str] = None
    location: Optional[str] = None


class UserRoleSchema(BaseUUIDSchema):
    name: Optional[str] = Field(None, description="The unique name of the role")
    label: Optional[str] = Field(
        None, description="A human-readable label for the role"
    )
    description: Optional[str] = Field(
        None, description="Optional description of the role and its purpose"
    )


class UserPermissionSchema(BaseUUIDSchema):
    name: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None


class UserSchema(UserBaseSchema, BaseUUIDSchema):
    is_active: bool = False
    is_verified: bool = False
    verified_at: Optional[datetime] | None = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    roles: Optional[List[UserRoleSchema]] = None


class UserMeSchema(UserSchema, BaseUUIDSchema):
    is_active: bool = False
    is_verified: bool = False
    verified_at: Optional[datetime] | None = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    roles: Optional[List[UserRoleSchema]] = None
    permissions: Optional[List[UserPermissionSchema]] = None


class UserResponseSchema(BaseResponseSchema):
    data: Optional[UserSchema] = None


class UserMeResponseSchema(BaseResponseSchema):
    data: Optional[UserMeSchema] = None


class UserTotalCountListResponseSchema(BaseTotalCountResponseSchema):
    data: Optional[List[UserSchema]] = None


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
    gender: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    username: Optional[str] = None
    national_id: Optional[str] = None
    status: Optional[str] = None
    user_type: Optional[str] = None
    exclude_user_types: Optional[str] = None
    search: Optional[str] = Field(
        None,
        description="Search by firstname, lastname or email",
        pattern=r"""^(?i)[\p{L}\p{N}\s]+(?:[.,'\-\s][\p{L}\p{N}\s]+)*[.]?$""",
    )


class AdminUserCreateSchema(UserBaseSchema):
    email: EmailStr
    role_names: str = Field(
        ...,
        description="Comma separated list of role names, eg: admin,user,organization",
    )
