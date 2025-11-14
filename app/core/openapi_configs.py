LICENSE_INFO = {
    "name": "MIT",
    "url": "https://opensource.org/licenses/MIT",
}

OPENAPI_SERVERS = [
    {
        "url": "http://127.0.0.1:8000",
        "description": "Local Server",
    },
    {
        "url": "https://api.dev.ktechhub.com",
        "description": "Development server",
    },
    {
        "url": "https://api.staging.ktechhub.com",
        "description": "Staging server",
    },
    {
        "url": "https://api.ktechhub.com",
        "description": "Production server",
    },
]

OPENAPI_TAGS = [
    {
        "name": "default",
        "description": "Default endpoints.",
    },
    {
        "name": "Auth",
        "description": "Authentication endpoints.",
    },
    {
        "name": "Profile",
        "description": "Profile endpoints.",
    },
    {
        "name": "Roles",
        "description": "Roles Endpoints.",
    },
    {
        "name": "Permissions",
        "description": "Permissions endpoints.",
    },
    {
        "name": "Role Permissions",
        "description": "Role permissions endpoints.",
    },
    {
        "name": "Users",
        "description": "Users endpoints.",
    },
    {
        "name": "User Roles",
        "description": "User roles endpoints.",
    },
    {
        "name": "System Logs",
        "description": "System logs endpoints.",
    },
    {
        "name": "Activity Logs",
        "description": "Activity logs endpoints.",
    },
    {
        "name": "Sessions",
        "description": "Sessions endpoints.",
    },
    {
        "name": "Generals",
        "description": "Generals endpoints.",
    },
]
