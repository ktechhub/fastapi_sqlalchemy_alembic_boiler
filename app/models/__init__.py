from app.database.base_class import Base
from app.models.users import User
from app.models.codes import VerificationCode
from app.models.roles import Role
from app.models.permissions import Permission
from app.models.role_permissions import RolePermission
from app.models.user_roles import UserRole
from app.models.activity_logs import ActivityLog
from app.models.countries import Country
from app.models.user_sessions import UserSession


MODEL_CLASSES = {
    "User": User,
    "VerificationCode": VerificationCode,
    "Permission": Permission,
    "Role": Role,
    "RolePermission": RolePermission,
    "UserRole": UserRole,
    "ActivityLog": ActivityLog,
    "Country": Country,
    "UserSession": UserSession,
}


def get_model_class(model_name: str):
    return MODEL_CLASSES.get(model_name)
