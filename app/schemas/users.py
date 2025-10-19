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

PasswordStr = Annotated[str, constr(min_length=8)]
PhoneStr = Annotated[str, constr(min_length=10, max_length=15)]
NationalIDStr = Annotated[str, constr(min_length=8, max_length=20)]


class UserBaseSchema(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[PhoneStr] = None
    national_id: Optional[NationalIDStr] = None
    address: Optional[str] = Field(None, max_length=255)
    digital_address: Optional[str] = Field(None, max_length=20)
    gender: Optional[Literal["male", "female", "other"]] = Field("other", max_length=10)

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


class RecruitUserCreateSchema(UserBaseSchema):
    date_of_birth: Optional[date] = None


class RecruitConfirmInvitationSchema(RecruitUserCreateSchema):
    password: PasswordStr


class RecruitSchema(UserBaseSchema, BaseUUIDSchema):
    status: Optional[str] = None
    date_of_birth: Optional[date] = None


class RecruitResponseSchema(BaseResponseSchema):
    data: Optional[RecruitSchema] = None


class RecruitTotalCountListResponseSchema(BaseTotalCountResponseSchema):
    data: Optional[List[RecruitSchema]] = None


class RecruitsUUIDSchema(BaseModel):
    uuids: List[UUIDStr] = Field(
        [],
        description="List of user uuids",
        examples=[
            [
                "d6fbbd0a-fbb5-4e67-93c1-4323e30a817f",
                "d6fbbd0a-fbb5-4e67-93c1-4323e30a817f",
            ]
        ],
    )


default_export_columns = [
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "national_id",
    "gender",
    "address",
    "digital_address",
    "date_of_birth",
]


class RecruitExportSchema(BaseModel):
    fields: Optional[List[str]] = Field(
        None,
        description="List of fields to include in the export. "
        "If omitted, the default fields will be used.",
        example=default_export_columns,
        min_items=1,
    )
    emails: List[EmailStr] = Field(
        ...,
        description="List of email addresses to send the export to",
        example=["user@example.com", "user2@example.com"],
        min_items=1,
    )

    @classmethod
    def validate_fields(cls, fields: Optional[List[str]]) -> List[str]:
        """Ensure that only allowed fields are selected."""
        if not fields:
            return default_export_columns  # Return all allowed fields if none provided

        invalid_fields = set(fields) - set(default_export_columns)
        if invalid_fields:
            raise ValueError(f"Invalid fields: {', '.join(invalid_fields)}")

        return fields


class UserCreateSchema(UserBaseSchema):
    password: PasswordStr
    confirm_password: str
    user_type: Literal["user", "agent", "company"] = "user"

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
    # type: Literal["confirm_email", "reset_password", "change_password"] = (
    #     "confirm_email"
    # )

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


class ResendSendVerificationCodeSchema(SendVerificationEmailSchema):
    type: Literal["confirm_email", "reset_password", "change_password"] = (
        "confirm_email"
    )


class UserConfirmEmailSchema(BaseModel):
    email: EmailStr
    code: Annotated[str, constr(min_length=1, max_length=8)]


class UserConfirmForgetPasswordSchema(BaseModel):
    email: EmailStr
    code: Annotated[str, constr(min_length=1, max_length=8)]
    password: constr(min_length=8)  # type: ignore

    @field_validator("password")
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
    phone_number: Optional[PhoneStr] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    digital_address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    national_id: Optional[str] = None
    status: Optional[str] = None


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
    digital_address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    national_id: Optional[str] = None
    password: Optional[str] = None
    status: Optional[str] = None


class AdminUpdateUserSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[PhoneStr] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    address: Optional[str] = None
    digital_address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    national_id: Optional[str] = None
    role_uuid: UUIDStr = Field(
        None,
        description="Comma separated list of role uuids",
        examples=["d6fbbd0a-fbb5-4e67-93c1-4323e30a817f"],
    )


class AdminUpdateFieldOfficerSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[PhoneStr] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    address: Optional[str] = None
    digital_address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    national_id: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None


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
    national_id: str
    phone_number: Optional[PhoneStr] = None
    date_of_birth: Optional[date] = None

    @field_validator("password")
    def validate_password_complexity(cls, value):
        # Check password complexity requirements here
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        return value


class AdminUserCreateSchema(BaseModel):
    email: EmailStr
    role_uuid: UUIDStr = Field(
        ...,
        description="Comma separated list of role uuids",
        examples=["d6fbbd0a-fbb5-4e67-93c1-4323e30a817f"],
    )


class AgentUserCreateSchema(BaseModel):
    email: EmailStr


class AgentWeekPropertyCountResponseSchema(BaseResponseSchema):
    data: int


class AdminSendEmailSchema(BaseModel):
    email: EmailStr


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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[PhoneStr] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    address: Optional[str] = None
    digital_address: Optional[str] = None
    date_of_birth: Optional[date] = None
    national_id: Optional[str] = None


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
    gender: Optional[str] = None
    address: Optional[str] = None
    digital_address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    roles: Optional[List[UserRoleWithoutRoutesSchema]] = None


class UserSchema(UserUpdateSchema, BaseUUIDSchema):
    is_active: bool = False
    is_verified: bool = False
    verified_at: Optional[datetime] | None = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    digital_address: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    roles: Optional[List[UserRoleSchema]] = None


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
    gender: Optional[str] = None
    address: Optional[str] = None
    digital_address: Optional[str] = None
    date_of_birth: Optional[date] = None
    national_id: Optional[str] = None
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
