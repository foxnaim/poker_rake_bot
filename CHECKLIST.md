# Чек-лист готовности проекта (v1.3)

## ✅ Что уже работает стабильно

### Неделя 1 — Фундамент
- [x] API скелет (`/decide`, `/log_hand`, `/health`)
- [x] БД модели и миграции (идемпотентные)
- [x] Safe-mode для `/decide` (fallback при ошибках)
- [x] SQLite fallback для локального запуска без Docker
- [x] Тесты проходят (24 passed, 9 skipped)

### Неделя 2 — Control-plane (операторка)
- [x] Admin API (`/api/v1/admin/rooms`, `/tables`, `/bots`, `/sessions`, `/bot-configs`, `/rake-models`)
- [x] Onboarding комнаты по ссылке (`POST /api/v1/admin/rooms/onboard`)
- [x] `table_key` как человеческий ключ стола (везде в ответах)
- [x] Запуск сессии по `table_key` (не только по `table_id`)
- [x] Аудит-лог изменений
- [x] Агенты показывают `assigned_session_key` и `table_key`

### Неделя 3 — Agent Protocol + Observability
- [x] Agent heartbeat (`POST /api/v1/agent/heartbeat`)
- [x] Команды агентам (pause/resume/stop/sit_out)
- [x] WebSocket события с `table_key` (`decision`, `hand_result`)
- [x] `session_id` и `limit_type` прокинуты по всему пайплайну
- [x] Table Agent с флагом `--table-key`

### Неделя 4 — Hardening
- [x] Smoke-скрипт (`make smoke`)
- [x] Нормализация `table_key` в логах/ответах
- [x] Stats считает сессии по control-plane (`bot_sessions`)

---

## 🚀 Быстрый старт (без Docker)

### 1. Установка зависимостей

```bash
cd poker_rake_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Проверка что зависимости установлены
make check-deps
```

### 2. Запуск API (SQLite режим)

```bash
# API автоматически использует SQLite если нет DATABASE_URL
export DATABASE_URL="sqlite:///./pokerbot_local.db"  # опционально
make run
# или
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Проверка (smoke test)

В другом терминале:

```bash
make smoke
# или
python -m utils.smoke --api http://localhost:8000 --table-key table_1 --limit NL10
```

Ожидаемый вывод:
```
OK
health: ok
decide.action: fold table_key: table_1
log_hand.status: logged table_key: table_1
```

### 4. Запуск тестов

```bash
pytest tests/ -v
# или
make test
```

Ожидаемый результат: **24 passed, 9 skipped** (9 skipped = тесты требующие fastapi/numpy/pytest-asyncio)

---

## 🐳 Запуск через Docker (production-like)

```bash
docker-compose up -d
make migrate  # применить миграции
```

Сервисы:
- API: `http://localhost:8000`
- Dashboard: `http://localhost:3000`
- Grafana: `http://localhost:3001` (admin/admin)
- Prometheus: `http://localhost:9090`

---

## 📋 Операторский сценарий (внутренний инструмент)

### 1. Создать комнату

```bash
curl -X POST http://localhost:8000/api/v1/admin/rooms \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PPPoker Club 1",
    "type": "pppoker",
    "rake_model_id": null
  }'
```

### 2. Создать стол с `table_key`

```bash
curl -X POST http://localhost:8000/api/v1/admin/tables \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": 1,
    "table_key": "pp_123",
    "limit_type": "NL10",
    "max_players": 6
  }'
```

### 3. Запустить сессию бота

```bash
curl -X POST http://localhost:8000/api/v1/admin/session/start \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": 1,
    "table_key": "pp_123",
    "limit": "NL10",
    "style": "neutral"
  }'
```

Ответ содержит `session_id` и `table_key`.

### 4. Запустить Table Agent

```bash
python -m poker_rake_bot.table_agent.main \
  --api http://localhost:8000 \
  --bot bot_1 \
  --limit NL10 \
  --table-key pp_123 \
  --executor dummy \
  --interactive
```

Агент будет:
- слать heartbeat
- получать команды (pause/resume/stop)
- отправлять GameState в `/decide`
- логировать руки через `/log_hand`

### 5. Проверить статус агента

```bash
curl http://localhost:8000/api/v1/agent/agent_XXX \
  -H "X-API-Key: YOUR_KEY"
```

Ответ содержит `table_key` и `assigned_session_key`.

---

## 🔍 Что проверить для "80% готовности"

### Базовые проверки
- [ ] `make smoke` проходит без ошибок
- [ ] `pytest tests/ -v` даёт 24+ passed
- [ ] API стартует без Docker (SQLite)
- [ ] Admin API доступен (если `ENABLE_ADMIN_API=1`)

### Операторский flow
- [ ] Создать room → table (с `table_key`) → session
- [ ] Запустить agent с `--table-key`
- [ ] Agent heartbeat работает
- [ ] Отправить команду агенту (pause/resume)
- [ ] Проверить что `/api/v1/agent/{id}` показывает `table_key`

### Логирование и статы
- [ ] `/api/v1/log_hand` сохраняет `table_key` канонически
- [ ] `/api/v1/stats` показывает `active_control_sessions`
- [ ] `/api/v1/hands/recent` возвращает `table_key`
- [ ] WebSocket события содержат `table_key`

---

## ⚠️ Известные ограничения

1. **Тесты требуют зависимостей**: 9 тестов пропускаются если нет `fastapi`, `numpy`, `pytest-asyncio`
2. **SQLite vs Postgres**: некоторые типы (ARRAY) автоматически конвертируются в JSON для SQLite
3. **Docker нестабильность**: на некоторых машинах `docker-compose` может падать (окружение-зависимо)

---

## 📊 Текущий статус

**Операторский контур**: ~75% готов  
**Тестовый контур**: ~80% готов (24 passed, 9 skipped)  
**Production-hardening**: ~60% готов (нужны реальные прогоны)

**Общая готовность MVP (внутренний инструмент)**: **~70-75%**

---

## 🎯 Следующие шаги для "80%+"

1. **Закрепить тесты**: установить все зависимости и прогнать полный suite
2. **E2E тест**: один скрипт который делает полный цикл (room→table→session→agent→decide→log_hand)
3. **Документация оператора**: краткий гайд "как посадить бота за стол"
4. **Мониторинг**: проверить что Prometheus/Grafana собирают метрики

---

*Последнее обновление: 2026-01-21*
