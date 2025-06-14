from app.models.users import User
from app.cruds.base import CRUDBase
from app.schemas.users import (
    UserCreateSchema,
    UserUpdateSchema,
)


class CRUDUser(CRUDBase[User, UserCreateSchema, UserUpdateSchema]):
    pass


user_crud = CRUDUser(User)
