from datetime import datetime, timedelta, timezone
from typing import Literal, Optional, Annotated
from pydantic import BaseModel, constr
from .base_schema import BaseUUIDSchema, BaseResponseSchema
from .validate_uuid import UUIDStr

TypeStr = Annotated[str, constr(min_length=1, max_length=50)]
CodeStr = Annotated[str, constr(min_length=1, max_length=8)]


class VerificationCodeBase(BaseModel):
    type: constr(min_length=1, max_length=50) = "confirm_email"  # type: ignore
    user_uuid: UUIDStr


class VerificationCodeBaseSchema(BaseModel):
    type: TypeStr = "confirm_email"
    user_uuid: UUIDStr
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VerificationCodeCreateSchema(VerificationCodeBaseSchema):
    pass


class VerificationCodeUpdateSchema(VerificationCodeBaseSchema):
    pass


class VerificationCodeSchema(VerificationCodeBaseSchema, BaseUUIDSchema):
    pass


class ConfirmVerificationCode(BaseModel):
    type: Literal["confirm_email", "reset_password", "change_password"] = (
        "confirm_email"
    )
    code: constr(min_length=1, max_length=8)  # type: ignore


class VerificationCodeCreate(VerificationCodeBase):
    pass


class VerificationCodeUpdate(VerificationCodeBase):
    code: constr(min_length=1, max_length=8)  # type: ignore


class VerificationCode(VerificationCodeBase):
    id: int
    code: constr(min_length=1, max_length=8)  # type: ignore
    expires_at: Optional[str]


class VerificationCodeResponseSchema(BaseResponseSchema):
    data: VerificationCode
