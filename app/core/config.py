import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from .openapi_configs import OPENAPI_TAGS, OPENAPI_SERVERS, LICENSE_INFO


class Settings(BaseSettings):
    APP_NAME: str = "Ktechhub"
    APP_URL: str = "https://www.ktechhub.com"
    CONTACT_EMAIL: str = "info@ktechhub.com"
    API_VERSION: str = "1.0.0"
    LICENSE_INFO: dict = LICENSE_INFO
    OPENAPI_TAGS: list = OPENAPI_TAGS
    OPENAPI_SERVERS: list = OPENAPI_SERVERS

    ENV: str = "local"

    SERVICE_NAME: str = "ktechhub"
    DOMAIN: str = "ktechhub.com"
    FRONTEND_URL: str = "https://dev.ktechhub.com"
    BASE_API_URL: str = "https://api.ktechhub.com"
    DEFAULT_PASSWORD: str = "KtechHub@2025"

    ALLOWED_HOSTS: str = "*"

    EMAIL_SERVICE: str = "custom"  # custom, mailjet, sendgrid
    MAIL_USERNAME: str = "no-reply@ktechhub.com"
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = "no-reply@ktechhub.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "Ktechhub"

    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "ktechhub"
    DB_ENGINE: str = "mysql"
    DATABASE_URL: str = ""

    REDIS_PORT: int = 6379
    REDIS_HOST: str = "localhost"
    REDIS_USERNAME: str = "default"
    REDIS_PASSWORD: str
    REDIS_URL: str = ""
    QUEUE_NAMES: str = "general"
    MAX_REDIS_QUEUE_RETRIES: int = 3

    # Cache Settings
    CACHE_ENABLED: bool = True
    CACHE_TTL_SHORT: int = 300  # 5 minutes
    CACHE_TTL_MEDIUM: int = 1800  # 30 minutes
    CACHE_TTL_LONG: int = 3600  # 1 hour
    CACHE_TTL_VERY_LONG: int = 86400  # 24 hours

    # JWT Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # S3 Configuration
    S3_STORAGE_BUCKET: str = ""
    S3_STORAGE_HOST: str = ""
    S3_STORAGE_ACCESS_KEY: str = ""
    S3_STORAGE_SECRET_KEY: str = ""

    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_BOT_TOKEN: str = ""

    # Meilisearch Configuration
    MEILI_SEARCH_URL: str = ""
    MEILI_SEARCH_API_KEY: str = ""
    MEILI_SEARCH_INDEX: str = "ktechhub"

    MAILJET_API_KEY: str = ""
    MAILJET_API_SECRET: str = ""

    SENDGRID_API_KEY: str = ""

    SENTRY_DSN: str = ""

    model_config = ConfigDict(extra="ignore")


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_DIR = os.path.join(BASE_DIR, "media")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

settings = Settings()

if not settings.DATABASE_URL:
    if settings.DB_ENGINE == "sqlite" and settings.ENV == "local":
        settings.DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR}/{settings.ENV}.sqlite3"
    elif settings.DB_ENGINE == "mysql":
        settings.DATABASE_URL = f"mysql+aiomysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    elif settings.DB_ENGINE == "postgresql":
        settings.DATABASE_URL = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    else:
        raise ValueError(f"Unsupported database engine: {settings.DB_ENGINE}")

if not settings.REDIS_URL:
    settings.REDIS_URL = f"redis://{settings.REDIS_USERNAME}:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
