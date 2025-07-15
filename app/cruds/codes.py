from app.models.codes import VerificationCode
from app.cruds.activity_base import ActivityCRUDBase
from app.schemas.verification_codes import (
    VerificationCodeCreate,
    VerificationCodeUpdate,
)


class CRUDVerificationCode(
    ActivityCRUDBase[VerificationCode, VerificationCodeCreate, VerificationCodeUpdate]
):
    pass


verification_code_crud = CRUDVerificationCode(VerificationCode)
