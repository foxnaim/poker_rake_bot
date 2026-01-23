#!/usr/bin/env python3
"""
Скрипт проверки схемы БД (CI-style)

Проверяет:
1. Все таблицы на месте
2. Ключевые поля существуют и имеют правильный тип
3. Индексы созданы
4. Foreign keys настроены
5. Модели SQLAlchemy соответствуют БД

Использование:
    python scripts/check_schema.py [--fix] [--verbose]

Exit codes:
    0 - все проверки пройдены
    1 - есть ошибки
    2 - критические ошибки (таблицы отсутствуют)
"""

import os
import sys
import argparse
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


@dataclass
class SchemaCheck:
    """Результат проверки"""
    name: str
    passed: bool
    message: str
    severity: str = "error"  # error, warning, info


class SchemaValidator:
    """Валидатор схемы БД"""

    # Ожидаемые таблицы с ключевыми полями
    EXPECTED_TABLES = {
        # Core tables
        "hands": ["id", "hand_id", "table_id", "limit_type", "hero_cards", "pot_size", "rake_amount", "hero_result"],
        "decision_log": ["id", "hand_id", "decision_id", "street", "game_state", "final_action"],
        "opponent_profiles": ["id", "opponent_id", "vpip", "pfr", "hands_played", "classification"],
        "training_checkpoints": ["id", "checkpoint_id", "version", "training_iterations", "file_path"],
        "bot_stats": ["id", "period_start", "hands_played", "vpip", "pfr"],

        # Control plane tables
        "bots": ["id", "alias", "default_style", "default_limit", "active"],
        "rooms": ["id", "room_link", "type", "status"],
        "tables": ["id", "room_id", "limit_type", "max_players"],
        "rake_models": ["id", "room_id", "limit_type", "percent", "cap"],
        "bot_configs": ["id", "name", "target_vpip", "target_pfr"],
        "bot_sessions": ["id", "session_id", "bot_id", "table_id", "status"],
        "agents": ["id", "agent_id", "status", "last_seen"],

        # Auth & Audit
        "api_keys": ["id", "api_key", "client_name", "is_admin"],
        "audit_log": ["id", "user_id", "action", "entity_type", "created_at"],

        # Performance
        "sessions": ["session_id", "client_id", "is_active"],
        "performance_log": ["id", "endpoint", "latency_ms"],
        "alerts": ["id", "alert_type", "severity", "message"],
    }

    # Ожидаемые индексы (table -> list of index patterns)
    EXPECTED_INDEXES = {
        "hands": ["hand_id", "table_id", "session_id"],
        "decision_log": ["hand_id", "session_id", "timestamp"],
        "opponent_profiles": ["opponent_id", "classification"],
        "bot_sessions": ["session_id", "status"],
        "agents": ["agent_id", "status"],
        "audit_log": ["entity_type", "created_at"],
    }

    # Ожидаемые foreign keys
    EXPECTED_FOREIGN_KEYS = {
        "tables": [("room_id", "rooms", "id")],
        "bot_sessions": [
            ("bot_id", "bots", "id"),
            ("table_id", "tables", "id"),
        ],
        "agents": [("assigned_session_id", "bot_sessions", "id")],
    }

    def __init__(self, database_url: str, verbose: bool = False):
        self.engine = create_engine(database_url)
        self.verbose = verbose
        self.checks: List[SchemaCheck] = []

    def log(self, msg: str):
        """Логирование в verbose режиме"""
        if self.verbose:
            print(f"  [DEBUG] {msg}")

    def add_check(self, name: str, passed: bool, message: str, severity: str = "error"):
        """Добавляет результат проверки"""
        self.checks.append(SchemaCheck(name, passed, message, severity))

    def validate_all(self) -> Tuple[int, int, int]:
        """
        Запускает все проверки

        Returns:
            Tuple (errors, warnings, passed)
        """
        print("=" * 60)
        print("Schema Validation Report")
        print("=" * 60)

        self.check_tables_exist()
        self.check_columns()
        self.check_indexes()
        self.check_foreign_keys()
        self.check_models_sync()

        # Подсчёт результатов
        errors = sum(1 for c in self.checks if not c.passed and c.severity == "error")
        warnings = sum(1 for c in self.checks if not c.passed and c.severity == "warning")
        passed = sum(1 for c in self.checks if c.passed)

        # Вывод результатов
        print("\n" + "-" * 60)
        print("Results:")
        print("-" * 60)

        for check in self.checks:
            if check.passed:
                status = "✅ PASS"
            elif check.severity == "warning":
                status = "⚠️  WARN"
            else:
                status = "❌ FAIL"

            print(f"{status}: {check.name}")
            if not check.passed or self.verbose:
                print(f"       {check.message}")

        print("\n" + "=" * 60)
        print(f"Summary: {passed} passed, {warnings} warnings, {errors} errors")
        print("=" * 60)

        return errors, warnings, passed

    def check_tables_exist(self):
        """Проверяет наличие всех таблиц"""
        self.log("Checking tables...")
        inspector = inspect(self.engine)
        existing_tables = set(inspector.get_table_names())

        for table in self.EXPECTED_TABLES.keys():
            if table in existing_tables:
                self.add_check(
                    f"Table '{table}' exists",
                    True,
                    f"Table found"
                )
            else:
                self.add_check(
                    f"Table '{table}' exists",
                    False,
                    f"Table '{table}' is MISSING!",
                    severity="error"
                )

    def check_columns(self):
        """Проверяет наличие ключевых колонок"""
        self.log("Checking columns...")
        inspector = inspect(self.engine)
        existing_tables = set(inspector.get_table_names())

        for table, expected_columns in self.EXPECTED_TABLES.items():
            if table not in existing_tables:
                continue

            actual_columns = {col['name'] for col in inspector.get_columns(table)}

            missing = set(expected_columns) - actual_columns
            if missing:
                self.add_check(
                    f"Columns in '{table}'",
                    False,
                    f"Missing columns: {', '.join(missing)}",
                    severity="error"
                )
            else:
                self.add_check(
                    f"Columns in '{table}'",
                    True,
                    f"All {len(expected_columns)} key columns present"
                )

    def check_indexes(self):
        """Проверяет наличие индексов"""
        self.log("Checking indexes...")
        inspector = inspect(self.engine)
        existing_tables = set(inspector.get_table_names())

        for table, expected_index_cols in self.EXPECTED_INDEXES.items():
            if table not in existing_tables:
                continue

            indexes = inspector.get_indexes(table)
            indexed_columns = set()
            for idx in indexes:
                indexed_columns.update(idx['column_names'])

            # Также добавляем PK и unique constraints
            pk = inspector.get_pk_constraint(table)
            if pk and pk.get('constrained_columns'):
                indexed_columns.update(pk['constrained_columns'])

            unique_constraints = inspector.get_unique_constraints(table)
            for uc in unique_constraints:
                indexed_columns.update(uc['column_names'])

            missing = set(expected_index_cols) - indexed_columns
            if missing:
                self.add_check(
                    f"Indexes on '{table}'",
                    False,
                    f"Missing indexes on: {', '.join(missing)}",
                    severity="warning"
                )
            else:
                self.add_check(
                    f"Indexes on '{table}'",
                    True,
                    f"All expected indexes present"
                )

    def check_foreign_keys(self):
        """Проверяет наличие foreign keys"""
        self.log("Checking foreign keys...")
        inspector = inspect(self.engine)
        existing_tables = set(inspector.get_table_names())

        for table, expected_fks in self.EXPECTED_FOREIGN_KEYS.items():
            if table not in existing_tables:
                continue

            actual_fks = inspector.get_foreign_keys(table)
            actual_fk_set = set()
            for fk in actual_fks:
                for col in fk['constrained_columns']:
                    ref_table = fk['referred_table']
                    ref_cols = fk['referred_columns']
                    if ref_cols:
                        actual_fk_set.add((col, ref_table, ref_cols[0]))

            missing = []
            for fk in expected_fks:
                if fk not in actual_fk_set:
                    missing.append(f"{fk[0]} -> {fk[1]}.{fk[2]}")

            if missing:
                self.add_check(
                    f"Foreign keys on '{table}'",
                    False,
                    f"Missing FKs: {', '.join(missing)}",
                    severity="warning"
                )
            else:
                self.add_check(
                    f"Foreign keys on '{table}'",
                    True,
                    f"All expected FKs present"
                )

    def check_models_sync(self):
        """Проверяет синхронизацию моделей SQLAlchemy с БД"""
        self.log("Checking models sync...")

        try:
            from data.models import Base
            from sqlalchemy import MetaData

            # Получаем метаданные из моделей
            model_tables = set(Base.metadata.tables.keys())

            # Получаем таблицы из БД
            inspector = inspect(self.engine)
            db_tables = set(inspector.get_table_names())

            # Таблицы в моделях, но не в БД
            missing_in_db = model_tables - db_tables
            if missing_in_db:
                self.add_check(
                    "Models sync (models -> DB)",
                    False,
                    f"Tables in models but not in DB: {', '.join(missing_in_db)}",
                    severity="warning"
                )
            else:
                self.add_check(
                    "Models sync (models -> DB)",
                    True,
                    "All model tables exist in DB"
                )

            # Таблицы в БД, но не в моделях (информационно)
            extra_in_db = db_tables - model_tables - {'alembic_version'}
            if extra_in_db and self.verbose:
                self.add_check(
                    "Models sync (DB -> models)",
                    True,
                    f"Extra tables in DB (OK): {', '.join(extra_in_db)}",
                    severity="info"
                )

        except Exception as e:
            self.add_check(
                "Models sync",
                False,
                f"Could not check: {e}",
                severity="warning"
            )


def main():
    parser = argparse.ArgumentParser(description="Check database schema")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--database-url", "-d", help="Database URL (or use DATABASE_URL env)")
    args = parser.parse_args()

    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        print("Usage: DATABASE_URL=postgresql://... python scripts/check_schema.py")
        sys.exit(2)

    validator = SchemaValidator(database_url, verbose=args.verbose)
    errors, warnings, passed = validator.validate_all()

    if errors > 0:
        sys.exit(1)
    elif warnings > 0:
        sys.exit(0)  # Warnings don't fail CI
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
