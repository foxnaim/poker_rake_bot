"""Подключение к БД"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import os
from typing import Generator

from .models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://pokerbot:pokerbot_dev@postgres:5432/pokerbot_db"  # Исправлено: postgres вместо localhost для Docker
)

# Оптимизированный engine с connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # Количество соединений в пуле
    max_overflow=40,  # Максимальное количество дополнительных соединений
    pool_pre_ping=True,  # Проверка соединений перед использованием
    pool_recycle=3600,  # Переиспользование соединений каждый час
    echo=False  # Установить True для отладки SQL запросов
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
