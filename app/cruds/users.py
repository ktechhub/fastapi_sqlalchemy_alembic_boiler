from app.models.users import User
from app.cruds.activity_base import ActivityCRUDBase
from app.schemas.users import (
    UserCreateSchema,
    UserUpdateSchema,
)


class CRUDUser(ActivityCRUDBase[User, UserCreateSchema, UserUpdateSchema]):
    pass


user_crud = CRUDUser(User)
