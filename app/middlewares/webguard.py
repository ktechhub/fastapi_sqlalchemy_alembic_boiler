from pywebguard.core.config import (
    GuardConfig,
    RateLimitConfig,
    UserAgentConfig,
    CORSConfig,
    PenetrationDetectionConfig,
    LoggingConfig,
    StorageConfig,
)
from pywebguard.storage._redis import AsyncRedisStorage
from app.core.config import settings

async_redis_storage = AsyncRedisStorage(
    url=settings.REDIS_URL,
    prefix="pywebguard:",
)

excluded_paths = [
    "/",
    "/ready",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
]

pyguard_config = GuardConfig(
    ip_filter={
        "enabled": True,
        "whitelist": ["127.0.0.1", "::1", "192.168.1.0/24"],
        "blacklist": ["10.0.0.1", "172.16.0.0/16"],
    },
    rate_limit=RateLimitConfig(
        enabled=True,
        requests_per_minute=10000,
        burst_size=200,
        auto_ban_threshold=20000,
        auto_ban_duration_minutes=60,
        excluded_paths=excluded_paths,
    ),
    user_agent=UserAgentConfig(
        enabled=True,
        blocked_agents=["curl", "wget", "Scrapy", "bot", "Bot"],
        excluded_paths=excluded_paths,
    ),
    cors=CORSConfig(
        enabled=True,
        allow_origins=settings.ALLOWED_HOSTS.split(","),
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
        max_age=3600,
    ),
    penetration=PenetrationDetectionConfig(
        enabled=False,
        log_suspicious=True,
    ),
    logging=LoggingConfig(
        enabled=True,
        log_level="DEBUG",  # Change to DEBUG to see all messages
        propagate=False,
        stream=True,
        stream_levels=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        # meilisearch={
        #     "url": settings.MEILI_SEARCH_URL,
        #     "api_key": settings.MEILI_SEARCH_API_KEY,
        #     "index_name": "pywebguard",
        # },
    ),
    storage=StorageConfig(
        type="redis",
        url=settings.REDIS_URL,
        prefix="pywebguard:",
    ),
)

auth_route_config = []
payments_route_config = []
logs_route_config = []
analytics_route_config = []

route_rate_limits = (
    auth_route_config
    + payments_route_config
    + logs_route_config
    + analytics_route_config
)
