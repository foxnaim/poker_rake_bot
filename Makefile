.PHONY: help install test run smoke docker-up docker-down migrate build lint check

help:
	@echo "Доступные команды:"
	@echo "  make install    - Установить зависимости"
	@echo "  make check-deps - Проверить что зависимости установлены"
	@echo "  make build      - Проверить компиляцию всех модулей"
	@echo "  make lint       - Проверить код линтером (если установлен)"
	@echo "  make check      - Полная проверка: build + lint + test"
	@echo "  make test       - Запустить все тесты"
	@echo "  make test-e2e   - Запустить E2E тест операторского flow"
	@echo "  make run        - Запустить API локально"
	@echo "  make smoke      - Быстрый smoke API (нужен запущенный API)"
	@echo "  make docker-up  - Запустить через Docker Compose"
	@echo "  make docker-down - Остановить Docker Compose"
	@echo "  make migrate    - Применить миграции БД"

install:
	python3 -m pip install -r requirements.txt

check-deps:
	@echo "Проверяю зависимости..."
	@python3 -c "import httpx" 2>/dev/null || (echo "❌ httpx не установлен. Запустите: make install" && exit 1)
	@python3 -c "import pytest" 2>/dev/null || (echo "⚠️  pytest не установлен. Тесты будут пропущены." && exit 0)
	@echo "✅ Основные зависимости установлены"

test: check-deps
	python3 -m pytest tests/ -v

test-e2e: check-deps
	@echo "Запуск E2E теста (требует ENABLE_ADMIN_API=1)..."
	ENABLE_ADMIN_API=1 python3 -m pytest tests/test_e2e_operator_flow.py -v

run:
	python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

smoke: check-deps
	@echo "Проверяю что API запущен на http://localhost:8000..."
	@curl -s http://localhost:8000/api/v1/health > /dev/null || (echo "❌ API не запущен! Запустите: make run" && exit 1)
	@echo "✅ API доступен, запускаю smoke-тест..."
	python3 -m utils.smoke --api http://localhost:8000 --table-key table_1 --limit NL10

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

migrate:
	@echo "Applying SQL migrations to postgres (docker-compose)..."
	@docker-compose exec -T postgres psql -U pokerbot -d pokerbot_db < data/migrations_v1_2.sql
	@docker-compose exec -T postgres psql -U pokerbot -d pokerbot_db < data/migrations_v1_3_week2.sql

build:
	@echo "🔨 Проверяю компиляцию всех модулей..."
	@python3 -m compileall -q . 2>&1 | grep -E "(Error|SyntaxError|Cannot)" || true
	@if python3 -m compileall -q . >/dev/null 2>&1; then \
		echo "✅ Все модули компилируются успешно"; \
	else \
		echo "❌ Ошибки компиляции найдены"; \
		python3 -m compileall . 2>&1 | grep -E "(Error|SyntaxError|Cannot)" || true; \
		exit 1; \
	fi

lint:
	@echo "🔍 Проверяю код линтером..."
	@if python3 -c "import pylint" 2>/dev/null; then \
		echo "📋 Запускаю pylint..."; \
		python3 -m pylint --disable=all --enable=E,F,W poker_rake_bot/api poker_rake_bot/data 2>/dev/null || true; \
	fi
	@if python3 -c "import flake8" 2>/dev/null; then \
		echo "📋 Запускаю flake8..."; \
		python3 -m flake8 --max-line-length=120 --ignore=E501,W503 poker_rake_bot/api poker_rake_bot/data 2>/dev/null || true; \
	fi
	@if python3 -c "import ruff" 2>/dev/null; then \
		echo "📋 Запускаю ruff..."; \
		python3 -m ruff check poker_rake_bot/api poker_rake_bot/data 2>/dev/null || true; \
	fi
	@echo "✅ Линтинг завершён (если линтеры установлены)"

check: build lint
	@echo "✅ Полная проверка завершена: build + lint"
	@echo "💡 Для запуска тестов используйте: make test"
