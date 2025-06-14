from app.models.codes import VerificationCode
from app.cruds.base import CRUDBase
from app.schemas.verification_codes import (
    VerificationCodeCreate,
    VerificationCodeUpdate,
)


class CRUDVerificationCode(
    CRUDBase[VerificationCode, VerificationCodeCreate, VerificationCodeUpdate]
):
    pass


verification_code_crud = CRUDVerificationCode(VerificationCode)
