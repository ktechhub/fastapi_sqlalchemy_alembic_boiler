from pydantic import BaseModel, constr
from typing import Optional
from .base_schema import BaseResponseSchema


class VerificationCodeBase(BaseModel):
    type: constr(min_length=1, max_length=50) = "confirm_email"  # type: ignore
    user_uuid: str


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
