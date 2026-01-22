.PHONY: help install test run smoke docker-up docker-down migrate

help:
	@echo "Доступные команды:"
	@echo "  make install    - Установить зависимости"
	@echo "  make check-deps - Проверить что зависимости установлены"
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
