.PHONY: help install test run docker-up docker-down migrate

help:
	@echo "Доступные команды:"
	@echo "  make install    - Установить зависимости"
	@echo "  make test       - Запустить тесты"
	@echo "  make run        - Запустить API локально"
	@echo "  make docker-up  - Запустить через Docker Compose"
	@echo "  make docker-down - Остановить Docker Compose"
	@echo "  make migrate    - Применить миграции БД"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

run:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

migrate:
	@echo "Applying SQL migrations to postgres (docker-compose)..."
	@docker-compose exec -T postgres psql -U pokerbot -d pokerbot_db < data/migrations_v1_2.sql
