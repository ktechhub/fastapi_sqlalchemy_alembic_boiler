from pydantic import BaseModel
import datetime


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenPayloadSchema(BaseModel):
    sub: str = None
    exp: int = None
    iat: int = None  # Issued at
    nbf: int = None  # Not before
    jti: str = None  # JWT ID
    iss: str = None  # Issuer
    aud: str = None  # Audience
    typ: str = None  # Token type (access/refresh)
