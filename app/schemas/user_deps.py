from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from .validate_uuid import UUIDStr


class Role(BaseModel):
    uuid: Optional[UUIDStr] = None
    views: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    delete_protection: Optional[bool] = False
    has_dashboard_access: Optional[bool] = False
    name: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None


class PermissionSchema(BaseModel):
    uuid: Optional[UUIDStr] = None
    views: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    delete_protection: Optional[bool] = None
    name: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None


class UserDepSchema(BaseModel):
    uuid: UUIDStr
    views: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    delete_protection: Optional[bool] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    verified_at: Optional[datetime] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    roles: Optional[List[Role]] = None
    permissions: Optional[List[PermissionSchema]] = None

    def is_admin(self) -> bool:
        """Check if the user has an admin role."""
        return any(role.name.lower() == "admin" for role in self.roles)

    def has_role(self, role_name: str) -> bool:
        """Check if the user has a specific role."""
        return any(role.name.lower() == role_name.lower() for role in self.roles)

    def has_permission(self, permission_name: str) -> bool:
        """Check if the user has a specific permission."""
        return any(
            permission.name.lower() == permission_name.lower()
            for permission in self.permissions
        )
