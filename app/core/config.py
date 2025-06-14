import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_VERSION: str = "1.0.0"
    CONTACT: dict = {
        "name": "Ktechhub API",
        "url": "https://www.ktechhub.com/",
        "email": "info@ktechhub.com",
    }

    ENV: str = "local"

    SERVICE_NAME: str = "ktechhub"

    FRONTEND_URL: str = "https://dev.ktechhub.com"
    BASE_API_URL: str = "https://api.ktechhub.com"

    if ENV == "local":
        RELOAD: bool = True
        LOG_LEVEL: str = "debug"
    else:
        RELOAD: bool = False
        LOG_LEVEL: str = "info"

    ALLOWED_HOSTS: str = "*"

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str

    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "ktechhub"
    DB_ENGINE: str = "postgresql"
    DATABASE_URL: str = ""

    REDIS_PORT: int = 6379
    REDIS_HOST: str = "localhost"
    REDIS_USERNAME: str = "default"
    REDIS_PASSWORD: str
    QUEUE_NAMES: str = "general"

    # JWT Settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # S3 Configuration
    S3_STORAGE_BUCKET: str = ""
    S3_STORAGE_HOST: str
    S3_STORAGE_ACCESS_KEY: str
    S3_STORAGE_SECRET_KEY: str

    TELEGRAM_CHAT_ID: str
    TELEGRAM_BOT_TOKEN: str

    MEILI_SEARCH_URL: str = "https://meilisearch.dev.ktechhub.com/"
    MEILI_SEARCH_API_KEY: str

    model_config = ConfigDict(extra="ignore")


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_DIR = os.path.join(BASE_DIR, "media")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

settings = Settings()

if not settings.DATABASE_URL:
    if settings.DB_ENGINE == "sqlite" or settings.ENV == "local":
        settings.DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR}/{settings.ENV}.sqlite3"
    elif settings.DB_ENGINE == "mysql":
        settings.DATABASE_URL = f"mysql+aiomysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    elif settings.DB_ENGINE == "postgresql":
        settings.DATABASE_URL = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    else:
        raise ValueError(f"Unsupported database engine: {settings.DB_ENGINE}")
