"""Подключение к БД"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from typing import Generator

from .models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # По умолчанию в docker-compose передаётся DATABASE_URL на Postgres.
    # Для локального запуска "без докера" безопаснее иметь sqlite fallback,
    # чтобы импорт пакета не падал без psycopg2.
    "sqlite:///./pokerbot_local.db",
)

def _make_engine(db_url: str):
    """
    Создаёт SQLAlchemy engine.
    Если Postgres драйвер недоступен (часто на голой машине без deps),
    автоматически падаем на sqlite, чтобы проект можно было хотя бы запустить/протестировать.
    """
    try:
        # Для Postgres хотим пул соединений.
        if db_url.startswith("postgresql://") or db_url.startswith("postgresql+psycopg2://"):
            from sqlalchemy.pool import QueuePool
            return create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=40,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
            )

        # Для sqlite — без агрессивного пула, с совместимостью потоков.
        if db_url.startswith("sqlite://"):
            return create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                echo=False,
            )

        # Любой другой URL — пробуем как есть.
        return create_engine(db_url, echo=False)
    except ModuleNotFoundError as e:
        # Частый случай: postgresql://... без psycopg2 в окружении.
        if "psycopg2" in str(e):
            sqlite_url = "sqlite:///./pokerbot_local.db"
            return create_engine(
                sqlite_url,
                connect_args={"check_same_thread": False},
                echo=False,
            )
        raise


engine = _make_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Для sqlite (локальный режим "без докера") создаём таблицы сразу,
# чтобы простые unit-тесты могли работать без явного вызова init_db().
if engine.dialect.name == "sqlite":
    Base.metadata.create_all(bind=engine)


def init_db():
    """Инициализация БД (создание таблиц)"""
    Base.metadata.create_all(bind=engine)

    # Тесты ожидают чистую БД. В CI/локально это часто один и тот же Postgres,
    # поэтому аккуратно чистим основные runtime-таблицы.
    testing = os.getenv("PYTEST_CURRENT_TEST") is not None or os.getenv("TESTING") == "1"
    if testing and engine.dialect.name == "postgresql":
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("""
                TRUNCATE TABLE
                    decision_log,
                    hands,
                    opponent_profiles,
                    training_checkpoints,
                    bot_stats
                RESTART IDENTITY CASCADE;
            """))


def get_db() -> Generator[Session, None, None]:
    """Dependency для FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
