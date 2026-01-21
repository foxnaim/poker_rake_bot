# Week 3 - Чеклист реализации

## ✅ 1. Rake в расчётах и аналитике

### 1.1 Функция расчёта rake
- [x] `utils/rake_calculator.py` - функция `calculate_rake()`
- [x] Поддержка room_id + limit_type
- [x] Fallback на дефолтную модель (5%, кап 3.0)
- [x] Учёт min_pot, percent, cap

### 1.2 Интеграция в log_hand
- [x] Автоматический расчёт rake при `rake_amount=None`
- [x] Использование `calculate_rake()` в `log_hand_endpoint`
- [x] Поддержка в bulk операциях

### 1.3 Новые поля в BotStats
- [x] `rake_100` - rake per 100 hands
- [x] `profit_bb_100` - profit in bb/100
- [x] `hands_per_hour` - hands per hour
- [x] Миграция БД: `data/migrations_week3_rake.sql`

### 1.4 Обновление endpoints
- [x] `/api/v1/session/{session_id}` - расчёт в реальном времени
- [x] `/api/v1/sessions/recent` - возврат новых полей
- [x] Обновление схем: `SessionResponse`

## ✅ 2. Протокол агентов

### 2.1 WebSocket heartbeat
- [x] `/api/v1/agent/ws/{agent_id}` - WebSocket endpoint
- [x] Обработка heartbeat сообщений
- [x] Обновление `last_seen`, `status`, `version`
- [x] Сохранение ошибок в `meta`
- [x] Отправка команд агенту

### 2.2 HTTP fallback
- [x] `/api/v1/agent/heartbeat` - HTTP endpoint
- [x] Поддержка session_id в heartbeat
- [x] Обработка ошибок

### 2.3 Команды управления
- [x] `POST /api/v1/agent/{agent_id}/command` - отправка команд
- [x] Команды: pause, resume, stop, sit_out
- [x] `GET /api/v1/agent/{agent_id}` - статус агента
- [x] `GET /api/v1/agents` - список агентов
- [x] Heartbeat lag вычисление

### 2.4 Agent Simulator
- [x] `utils/agent_simulator.py` - полный симулятор
- [x] WebSocket подключение
- [x] Heartbeat каждые 5 секунд
- [x] Генерация `/decide` и `/log_hand` запросов
- [x] Обработка команд от сервера

## ✅ 3. Мониторинг (Prometheus/Grafana)

### 3.1 Prometheus метрики
- [x] Agent метрики:
  - `agent_online` - статус онлайн/офлайн
  - `agent_heartbeat_lag_seconds` - задержка heartbeat
  - `agent_errors_total` - счётчик ошибок
- [x] Session метрики:
  - `session_active` - активные сессии
  - `session_hands_total` - руки в сессии
  - `session_profit_total` - профит сессии
  - `session_rake_total` - рейк сессии
- [x] Decision метрики:
  - `decision_p95_latency_seconds` - p95 задержка
  - `decision_p99_latency_seconds` - p99 задержка
  - `decision_errors_total` - ошибки решений
- [x] Gameplay метрики:
  - `bot_rake_100` - rake per 100 hands
  - `bot_profit_bb_100` - profit bb/100
  - `bot_hands_per_hour` - hands per hour

### 3.2 Обновление метрик в коде
- [x] Обновление метрик агентов в `agents.py` (heartbeat)
- [x] Обновление метрик сессий в `sessions.py` (start/end/get)
- [x] Обновление метрик решений в `decide.py`
- [x] Обновление метрик рук в `log_hand.py`

### 3.3 Grafana дашборд
- [x] `monitoring/grafana_dashboard_week3.json`
- [x] Runtime панели: Latency (p95/p99), Errors/sec, Decisions/sec
- [x] Gameplay панели: Hands/Hour, Profit/Rake Trends, Winrate
- [x] Agents панели: Online Status, Heartbeat Lag, Errors
- [x] Sessions панели: Active Count

### 3.4 Prometheus алерты
- [x] `monitoring/prometheus_alerts.yml`
- [x] Agent offline > 5 минут (warning)
- [x] Agent offline > 10 минут (critical)
- [x] Latency p99 > 1 секунда
- [x] Частые ошибки /decide (> 0.1 errors/sec)
- [x] Низкая производительность (< 10 hands/hour)
- [x] Отрицательный профит (< -10 bb/100)

## ✅ 4. Тестирование

### 4.1 Интеграционные тесты
- [x] `tests/test_week3_integration.py`
- [x] Тесты расчёта рейка
- [x] Тесты протокола агентов
- [x] Тесты статистики сессий
- [x] Тест полного цикла

### 4.2 Ручные тесты
- [x] `tests/test_week3_manual.py`
- [x] Тест расчёта рейка
- [x] Тест heartbeat агента
- [x] Тест сессии со статистикой
- [x] Тест команды агенту
- [x] Тест метрик endpoint
- [x] Тест полного цикла

## 📋 Запуск тестов

### Применить миграцию БД:
```bash
psql -U pokerbot -d pokerbot_db -f data/migrations_week3_rake.sql
```

### Запустить ручные тесты:
```bash
python tests/test_week3_manual.py
```

### Запустить интеграционные тесты:
```bash
pytest tests/test_week3_integration.py -v
```

### Запустить agent-simulator:
```bash
python utils/agent_simulator.py agent_test_1
```

### Проверить метрики:
```bash
curl http://localhost:8000/metrics | grep -E "(agent_|session_|decision_)"
```

## 🎯 Результат (DoD)

- [x] Оператор видит в UI "живую сессию", статус агента, метрики, profit/rake
- [x] Оператор может управлять агентами (pause/stop)
- [x] Есть Grafana/Prometheus картина
- [x] Есть базовые алерты
- [x] Agent-simulator работает и генерирует статистику
- [x] Все метрики обновляются в реальном времени

## 📝 Примечания

- WebSocket для агентов работает, но команды пока хранятся в `meta` (TODO: очередь команд)
- Rake рассчитывается автоматически при логировании руки
- Все новые поля доступны через API endpoints
- Метрики обновляются автоматически при каждом действии
