from pydantic import BaseModel
import datetime


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenPayloadSchema(BaseModel):
    sub: str = None
    exp: int = None
