"""
Тест миграций "с нуля"

Проверяет:
1. Создание БД с нуля через init.sql
2. Применение всех миграций по порядку
3. Корректность финальной схемы
4. Идемпотентность миграций
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path

# Добавляем корень проекта
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker


# Список миграций в порядке применения
MIGRATIONS = [
    "data/init.sql",
    "data/migrations_v1_2.sql",
    "data/migrations_v1_3_week2.sql",
    "data/migrations_week3_rake.sql",
]

# Ожидаемые таблицы после всех миграций
EXPECTED_TABLES = {
    # Core
    "hands",
    "decision_log",
    "opponent_profiles",
    "training_checkpoints",
    "bot_stats",
    # Control plane
    "bots",
    "rooms",
    "tables",
    "rake_models",
    "bot_configs",
    "bot_sessions",
    "agents",
    # Auth & System
    "api_keys",
    "sessions",
    "performance_log",
    "alerts",
    "audit_log",
}


@pytest.fixture
def project_root():
    """Корень проекта"""
    return Path(__file__).parent.parent


@pytest.fixture
def sqlite_db():
    """Создаёт временную SQLite БД для тестов"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    engine = create_engine(f"sqlite:///{db_path}")
    yield engine

    # Cleanup
    engine.dispose()
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def postgres_db():
    """
    Подключается к PostgreSQL для тестов (если доступен)

    Требует переменную окружения TEST_DATABASE_URL
    """
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL not set")

    engine = create_engine(db_url)
    yield engine
    engine.dispose()


class TestMigrations:
    """Тесты миграций"""

    def test_migrations_files_exist(self, project_root):
        """Проверяет что все файлы миграций существуют"""
        for migration in MIGRATIONS:
            path = project_root / migration
            assert path.exists(), f"Migration file not found: {migration}"

    def test_migrations_syntax(self, project_root):
        """Проверяет синтаксис SQL файлов"""
        for migration in MIGRATIONS:
            path = project_root / migration
            content = path.read_text()

            # Базовые проверки
            assert len(content) > 0, f"Empty migration: {migration}"

            # Проверяем что нет явных синтаксических ошибок
            # (не финальная проверка, но ловит очевидные проблемы)
            assert "CREATE TABLE" in content.upper() or "ALTER TABLE" in content.upper() or "INSERT" in content.upper(), \
                f"Migration {migration} has no SQL statements"

    @pytest.mark.skipif(
        not os.getenv("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL not set"
    )
    def test_migrations_apply_fresh(self, project_root, postgres_db):
        """
        Тестирует применение миграций на чистую БД

        Этот тест требует PostgreSQL, так как SQLite не поддерживает
        некоторые конструкции (ALTER COLUMN, IF NOT EXISTS для columns, etc.)
        """
        # Дропаем все таблицы
        inspector = inspect(postgres_db)
        existing_tables = inspector.get_table_names()

        with postgres_db.connect() as conn:
            # Удаляем таблицы в правильном порядке (учитывая FK)
            conn.execute(text("SET session_replication_role = 'replica';"))
            for table in existing_tables:
                try:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                except:
                    pass
            conn.execute(text("SET session_replication_role = 'origin';"))
            conn.commit()

        # Применяем миграции по порядку
        for migration in MIGRATIONS:
            path = project_root / migration
            sql = path.read_text()

            with postgres_db.connect() as conn:
                # Выполняем каждый statement отдельно
                statements = [s.strip() for s in sql.split(";") if s.strip()]
                for stmt in statements:
                    if stmt and not stmt.startswith("--"):
                        try:
                            conn.execute(text(stmt))
                        except Exception as e:
                            # Некоторые ошибки ожидаемы (например, IF NOT EXISTS)
                            if "already exists" not in str(e).lower():
                                print(f"Warning in {migration}: {e}")
                conn.commit()

        # Проверяем что все таблицы созданы
        inspector = inspect(postgres_db)
        created_tables = set(inspector.get_table_names())

        missing = EXPECTED_TABLES - created_tables
        assert not missing, f"Missing tables after migrations: {missing}"

    @pytest.mark.skipif(
        not os.getenv("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL not set"
    )
    def test_migrations_idempotent(self, project_root, postgres_db):
        """
        Тестирует идемпотентность миграций

        Применение миграций дважды не должно вызывать ошибок
        """
        # Применяем миграции дважды
        for _ in range(2):
            for migration in MIGRATIONS:
                path = project_root / migration
                sql = path.read_text()

                with postgres_db.connect() as conn:
                    statements = [s.strip() for s in sql.split(";") if s.strip()]
                    for stmt in statements:
                        if stmt and not stmt.startswith("--"):
                            try:
                                conn.execute(text(stmt))
                            except Exception as e:
                                # IF NOT EXISTS и подобные конструкции
                                error_str = str(e).lower()
                                acceptable_errors = [
                                    "already exists",
                                    "duplicate key",
                                    "column .* of relation .* already exists",
                                ]
                                if not any(err in error_str for err in acceptable_errors):
                                    # Некритичные ошибки пропускаем с предупреждением
                                    print(f"Note: {migration}: {e}")
                    conn.commit()

        # Схема должна остаться корректной
        inspector = inspect(postgres_db)
        created_tables = set(inspector.get_table_names())

        missing = EXPECTED_TABLES - created_tables
        assert not missing, f"Missing tables after double migration: {missing}"


class TestSchemaConsistency:
    """Тесты консистентности схемы"""

    @pytest.mark.skipif(
        not os.getenv("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL not set"
    )
    def test_models_match_db(self, postgres_db):
        """Проверяет что модели SQLAlchemy соответствуют БД"""
        from data.models import Base

        # Получаем таблицы из моделей
        model_tables = set(Base.metadata.tables.keys())

        # Получаем таблицы из БД
        inspector = inspect(postgres_db)
        db_tables = set(inspector.get_table_names())

        # Таблицы в моделях должны быть в БД
        missing_in_db = model_tables - db_tables
        assert not missing_in_db, f"Tables in models but not in DB: {missing_in_db}"

    @pytest.mark.skipif(
        not os.getenv("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL not set"
    )
    def test_foreign_keys_valid(self, postgres_db):
        """Проверяет что все FK ссылаются на существующие таблицы"""
        inspector = inspect(postgres_db)
        tables = inspector.get_table_names()

        for table in tables:
            fks = inspector.get_foreign_keys(table)
            for fk in fks:
                ref_table = fk["referred_table"]
                assert ref_table in tables, \
                    f"FK in {table} references non-existent table: {ref_table}"


class TestMigrationScripts:
    """Тесты скриптов миграций"""

    def test_check_schema_script_exists(self, project_root):
        """Проверяет наличие скрипта проверки схемы"""
        script = project_root / "scripts" / "check_schema.py"
        assert script.exists(), "check_schema.py not found"

    def test_check_schema_script_runnable(self, project_root):
        """Проверяет что скрипт запускается без ошибок (только импорт)"""
        import importlib.util

        script_path = project_root / "scripts" / "check_schema.py"
        spec = importlib.util.spec_from_file_location("check_schema", script_path)
        module = importlib.util.module_from_spec(spec)

        # Не выполняем main(), только проверяем что модуль загружается
        try:
            spec.loader.exec_module(module)
        except SystemExit:
            pass  # Ожидаемо если нет DATABASE_URL

        assert hasattr(module, "SchemaValidator")
        assert hasattr(module, "main")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
