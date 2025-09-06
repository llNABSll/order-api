from __future__ import annotations

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- Engine SQLAlchemy ---
engine = create_engine(
    str(settings.DATABASE_URL),
    future=True,
    pool_pre_ping=True,
    echo=getattr(settings, "DB_ECHO", False),
)

# --- Session factory ---
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

# --- Base déclarative ---
Base = declarative_base()


def init_db() -> None:
    """
    Enregistre tous les modèles et crée les tables manquantes.
    IMPORTANT: il faut importer les modèles avant d’appeler create_all().
    """
    from app import models   # ✅ import retardé
    Base.metadata.create_all(bind=engine)
    logger.info("[order-api] DB init: tables ensured")


def get_db():
    """Fournit une session DB par requête HTTP."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        logger.exception("[order-api] db session rolled back due to exception")
        raise
    finally:
        db.close()
        logger.debug("[order-api] db session closed")
