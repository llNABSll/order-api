from sqlalchemy.orm  import sessionmaker, Session, declarative_base
from sqlalchemy      import create_engine
from typing          import Generator
from sqlalchemy.pool import NullPool


# Base ORM
Base = declarative_base()

import os

# Utilise SQLite en mémoire pour les tests (Behave/Pytest/CI), sinon PostgreSQL
if (
    os.environ.get("TESTING") == "1"
    or os.environ.get("GITHUB_ACTIONS") == "true"
    or os.environ.get("PYTEST_CURRENT_TEST") is not None
    or os.environ.get("BEHAVE_TEST") == "1"
):
    DATABASE_URL = "sqlite:///./test.db"
    connect_args = {"check_same_thread": False}
else:
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:root@localhost:5432/orders_db"
    )
    connect_args = {}

# Engine
engine = create_engine(
    DATABASE_URL,
    echo=True,          # log SQL dans la console (utile en dev)
    future=True,
    pool_pre_ping=True,
    poolclass=NullPool,  # optionnel : évite les connexions persistantes en dev
    connect_args=connect_args
)

# SessionLocal
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)

def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
