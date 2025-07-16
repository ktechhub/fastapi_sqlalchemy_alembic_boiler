from fastapi import APIRouter
from .auth import AuthRouter
from .profile import UserProfileRouter
from .permissions import PermissionRouter
from .roles import RoleRouter
from .role_permissions import RolePermissionRouter
from .user_roles import UserRoleRouter
from .users import UserRouter
from .referesh_token import router as refresh_token_router

auth_router = APIRouter()
auth_router.include_router(AuthRouter().router, prefix="", tags=["Auth"])
auth_router.include_router(UserProfileRouter().router, prefix="", tags=["Profile"])
auth_router.include_router(refresh_token_router, prefix="", tags=["Auth"])
auth_router.include_router(
    PermissionRouter().router, prefix="/permissions", tags=["Permissions"]
)
auth_router.include_router(RoleRouter().router, prefix="/roles", tags=["Roles"])
auth_router.include_router(
    RolePermissionRouter().router,
    prefix="/role-permissions",
    tags=["Role Permissions"],
)
auth_router.include_router(
    UserRoleRouter().router, prefix="/user-roles", tags=["User Roles"]
)
auth_router.include_router(UserRouter().router, prefix="/users", tags=["Users"])
