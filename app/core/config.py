# app/core/config.py (Order API)

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    """
    Configuration unique de l'app (stateless).
    - DB: privilégie DATABASE_URL, sinon compose avec POSTGRES_* ou fallback SQLite.
    - Sécurité: Keycloak (ISSUER + JWKS).
    - Messaging: RabbitMQ (str uniquement, pas AmqpDsn).
    - Logs: JSON + rotation par défaut.
    """

    def __init__(self) -> None:
        # ---------- Métadonnées ----------
        self.ENV = os.getenv("ENV", "dev")
        self.APP_NAME = os.getenv("APP_NAME", "order-api")
        self.APP_TITLE = os.getenv("APP_TITLE", "Order API - PayeTonKawa")
        self.APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
        self.APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "API Commandes CRUD")

        # ---------- Base de données ----------
        self.DATABASE_URL = os.getenv("DATABASE_URL") or self._compose_db_url()
        self.DB_ECHO = _get_bool("DB_ECHO", False)

        # ---------- Sécurité (Keycloak) ----------
        self.KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER")
        self.KEYCLOAK_JWKS_URL = os.getenv("KEYCLOAK_JWKS_URL") or (
            f"{self.KEYCLOAK_ISSUER}/protocol/openid-connect/certs"
            if self.KEYCLOAK_ISSUER
            else None
        )
        self.ROLE_READ = os.getenv("ROLE_READ", "order:read")
        self.ROLE_WRITE = os.getenv("ROLE_WRITE", "order:write")

        # ---------- RabbitMQ ----------
        self.RABBITMQ_URL = os.getenv("RABBITMQ_URL") or "amqp://app:app@rabbitmq:5672/%2F"
        self.RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "events")
        self.RABBITMQ_EXCHANGE_TYPE = os.getenv("RABBITMQ_EXCHANGE_TYPE", "topic")

        # ---------- Logging ----------
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
        self.LOG_DIR = os.getenv("LOG_DIR", "logs")
        self.LOG_FILE = os.getenv("LOG_FILE", "app.log")
        self.LOG_ACCESS_FILE = os.getenv("LOG_ACCESS_FILE", "access.log")
        self.LOG_MAX_BYTES = _get_int("LOG_MAX_BYTES", 10 * 1024 * 1024)
        self.LOG_BACKUP_COUNT = _get_int("LOG_BACKUP_COUNT", 5)
        self.LOG_ENABLE_CONSOLE = _get_bool("LOG_ENABLE_CONSOLE", True)

        # ---------- CORS ----------
        self.CORS_ALLOW_ORIGINS = [
            o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
        ]
        self.CORS_ALLOW_CREDENTIALS = _get_bool("CORS_ALLOW_CREDENTIALS", True)
        self.CORS_ALLOW_METHODS = os.getenv("CORS_ALLOW_METHODS", "*")
        self.CORS_ALLOW_HEADERS = os.getenv("CORS_ALLOW_HEADERS", "*")

    # -------- Helpers internes --------
    def _compose_db_url(self) -> str:
        pg_host = os.getenv("POSTGRES_HOST")
        pg_db = os.getenv("POSTGRES_DB")
        pg_user = os.getenv("POSTGRES_USER")
        pg_pwd = os.getenv("POSTGRES_PASSWORD", "")
        pg_port = os.getenv("POSTGRES_PORT", "5432")

        if pg_host and pg_db and pg_user:
            return f"postgresql+psycopg2://{pg_user}:{pg_pwd}@{pg_host}:{pg_port}/{pg_db}"

        sqlite_path = os.getenv("SQLITE_PATH", "data/order.db")
        path = Path(sqlite_path)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"


settings = Settings()
