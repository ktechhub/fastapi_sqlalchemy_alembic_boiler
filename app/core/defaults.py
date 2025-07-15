default_roles = [
    {
        "name": "admin",
        "label": "Admin",
        "description": "Admin role",
        "has_dashboard_access": True,
    },
    {
        "name": "auditor",
        "label": "Auditor",
        "description": "Auditor role",
        "has_dashboard_access": True,
    },
    {
        "name": "user",
        "label": "User",
        "description": "User role",
        "has_dashboard_access": False,
    },
    {
        "name": "guest",
        "label": "Guest",
        "description": "Guest role",
        "has_dashboard_access": False,
    },
    {
        "name": "anonymous",
        "label": "Anonymous",
        "description": "Anonymous role",
        "has_dashboard_access": False,
    },
]


default_actions = [
    "permissions",
    "roles",
    "role_permissions",
    "users",
    "user_roles",
    "profiles",
    "metrics",
    "reports",
    "logs",
]

default_role_permissions = [
    {
        "role": "admin",
        "permissions": {
            "permissions": ["read", "write", "delete"],
            "roles": ["read", "write", "delete"],
            "role_permissions": ["read", "write", "delete"],
            "users": ["read", "write", "delete"],
            "user_roles": ["read", "write", "delete"],
            "metrics": ["read", "write", "delete"],
            "reports": ["read", "write", "delete"],
            "profiles": ["read", "write", "delete"],
            "logs": ["read", "write", "delete"],
        },
    },
    {
        "role": "auditor",
        "permissions": {
            "permissions": ["read"],
            "roles": ["read"],
            "role_permissions": ["read"],
            "users": ["read"],
            "user_roles": ["read"],
            "profiles": ["read"],
            "metrics": ["read"],
            "reports": ["read"],
            "logs": ["read"],
        },
    },
    {
        "role": "user",
        "permissions": {
            "profiles": ["read", "write"],
        },
    },
]
