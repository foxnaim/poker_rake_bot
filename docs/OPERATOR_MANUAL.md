# PokerBot v1.3 - Операторский мануал

Руководство для операторов по управлению покерным ботом.

## Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Добавление комнаты](#добавление-комнаты)
3. [Управление столами](#управление-столами)
4. [Настройка ботов](#настройка-ботов)
5. [Управление сессиями](#управление-сессиями)
6. [Настройка рейка](#настройка-рейка)
7. [Мониторинг](#мониторинг)
8. [Алерты и проблемы](#алерты-и-проблемы)

---

## Быстрый старт

### Запуск системы

```bash
# Запуск всего стека
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f api
```

### Доступ к интерфейсам

| Интерфейс | URL | Описание |
|-----------|-----|----------|
| API Docs | http://localhost:8000/docs | Swagger UI |
| Dashboard | http://localhost:3000 | React админка |
| Grafana | http://localhost:3001 | Мониторинг |
| Prometheus | http://localhost:9090 | Метрики |

---

## Добавление комнаты

### Через UI (Dashboard)

1. Откройте Dashboard → **Rooms**
2. Нажмите **"Add Room"**
3. Заполните форму:
   - **Room Link**: ссылка на комнату (например, `https://pokerking.com/room/123`)
   - **Type**: тип комнаты (`pokerstars`, `ggpoker`, `acr`, `pokerking`)
   - **Notes**: заметки (опционально)
4. Нажмите **"Submit"**

### Через API

```bash
curl -X POST "http://localhost:8000/api/v1/admin/rooms/onboard" \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "room_link": "https://pokerking.com/room/123",
    "type": "pokerking",
    "meta": {"notes": "NL10 tables"}
  }'
```

### Статусы комнаты

| Статус | Описание |
|--------|----------|
| `pending` | Ожидает проверки |
| `onboarded` | Проверена, готова к работе |
| `active` | Активно используется |
| `inactive` | Временно неактивна |

---

## Управление столами

### Создание стола

1. Dashboard → **Tables** → **Add Table**
2. Выберите комнату
3. Укажите параметры:
   - **Limit Type**: `NL10`, `NL25`, `NL50`
   - **Max Players**: 6 (по умолчанию)
   - **External Table ID**: ID стола в клиенте (опционально)

### Через API

```bash
curl -X POST "http://localhost:8000/api/v1/admin/tables" \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": 1,
    "limit_type": "NL10",
    "max_players": 6,
    "external_table_id": "table_001"
  }'
```

---

## Настройка ботов

### Создание бота

1. Dashboard → **Bots** → **Add Bot**
2. Заполните:
   - **Alias**: уникальное имя бота
   - **Default Style**: `balanced`, `aggressive`, `tight`, `loose`
   - **Default Limit**: `NL10`, `NL50`

### Стили игры

| Стиль | VPIP | PFR | AF | Описание |
|-------|------|-----|----|---------|
| `tight` | 15-18% | 12-15% | 2.5-3.0 | Консервативный |
| `balanced` | 20-25% | 15-20% | 2.0-2.5 | Сбалансированный |
| `loose` | 28-35% | 18-25% | 1.5-2.0 | Агрессивный-лузовый |
| `aggressive` | 22-28% | 18-22% | 2.5-3.5 | Агрессивный |

### Конфигурация бота (Bot Config)

Позволяет тонко настроить поведение бота:

```json
{
  "target_vpip": 22.0,
  "target_pfr": 17.0,
  "target_af": 2.2,
  "exploit_weights": {
    "preflop": 0.3,
    "flop": 0.4,
    "turn": 0.5,
    "river": 0.6
  },
  "max_winrate_cap": 8.0,
  "anti_pattern_params": {
    "bet_sizing_variance": 0.1,
    "timing_variance": 0.15
  }
}
```

**Параметры:**

| Параметр | Описание |
|----------|----------|
| `target_vpip` | Целевой VPIP (Voluntarily Put In Pot) |
| `target_pfr` | Целевой PFR (Pre-Flop Raise) |
| `target_af` | Целевой Aggression Factor |
| `exploit_weights` | Веса exploit-стратегии по улицам |
| `max_winrate_cap` | Максимальный винрейт (bb/100) для anti-detection |
| `anti_pattern_params` | Параметры анти-паттерн роутера |

---

## Управление сессиями

### Запуск сессии

1. Dashboard → **Sessions** → **Start Session**
2. Выберите:
   - Бота
   - Стол
   - Конфигурацию (опционально)
3. Нажмите **"Start"**

### Через API

```bash
# Запуск сессии
curl -X POST "http://localhost:8000/api/v1/admin/sessions/start" \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": 1,
    "table_id": 1,
    "bot_config_id": 1
  }'

# Пауза сессии
curl -X POST "http://localhost:8000/api/v1/admin/sessions/1/pause" \
  -H "X-API-Key: YOUR_ADMIN_KEY"

# Остановка сессии
curl -X POST "http://localhost:8000/api/v1/admin/sessions/1/stop" \
  -H "X-API-Key: YOUR_ADMIN_KEY"
```

### Статусы сессии

| Статус | Описание |
|--------|----------|
| `starting` | Запускается |
| `running` | Активна |
| `paused` | На паузе |
| `stopped` | Остановлена |
| `error` | Ошибка |

---

## Настройка рейка

### Модели рейка

Рейк-модель определяет как считается рейк для комнаты/лимита:

```json
{
  "room_id": 1,
  "limit_type": "NL10",
  "percent": 5.0,
  "cap": 1.0,
  "min_pot": 0.20
}
```

| Параметр | Описание |
|----------|----------|
| `percent` | Процент рейка (5% = 5.0) |
| `cap` | Максимальный рейк за руку |
| `min_pot` | Минимальный пот для взятия рейка |

### Создание рейк-модели

```bash
curl -X POST "http://localhost:8000/api/v1/admin/rake-models" \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": 1,
    "limit_type": "NL10",
    "percent": 5.0,
    "cap": 1.0,
    "min_pot": 0.20
  }'
```

---

## Мониторинг

### Dashboard метрики

| Метрика | Описание | Норма |
|---------|----------|-------|
| **Hands/Hour** | Рук в час | 200-400 |
| **Decisions/sec** | Решений в секунду | < 10 |
| **Latency p95** | 95-перцентиль задержки | < 100ms |
| **Latency p99** | 99-перцентиль задержки | < 200ms |
| **Profit bb/100** | Винрейт | 2-8 bb/100 |
| **Rake/100** | Рейк на 100 рук | Зависит от лимита |

### Grafana дашборды

1. **Runtime** - latency, errors, RPS
2. **Gameplay** - hands/hr, profit/rake
3. **Agents** - online, last_seen, failures

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Ответ:
```json
{
  "status": "healthy",
  "services": {
    "database": "up",
    "redis": "up"
  },
  "safe_mode": {
    "enabled": true,
    "db_circuit": {"state": "closed"},
    "redis_circuit": {"state": "closed"}
  }
}
```

---

## Алерты и проблемы

### Типичные алерты

| Алерт | Причина | Действие |
|-------|---------|----------|
| `Agent offline > 5min` | Агент не отправляет heartbeat | Проверить агента |
| `Latency p99 > 200ms` | Медленные решения | Проверить нагрузку |
| `High error rate` | Много ошибок в /decide | Проверить логи |
| `DB circuit open` | БД недоступна | Проверить PostgreSQL |
| `Redis circuit open` | Redis недоступен | Проверить Redis |

### Safe Mode

При недоступности сервисов система переходит в Safe Mode:

- **Redis недоступен**: решения работают без кэша (медленнее)
- **DB недоступна**: возвращается fallback-решение (check/call)

Проверить статус:
```bash
curl http://localhost:8000/api/v1/health | jq '.safe_mode'
```

### Логи

```bash
# API логи
docker-compose logs -f api

# Все логи
docker-compose logs -f

# Ошибки
docker-compose logs api 2>&1 | grep ERROR
```

### Перезапуск

```bash
# Перезапуск API
docker-compose restart api

# Полный перезапуск
docker-compose down && docker-compose up -d
```

---

## API ключи

### Создание ключа

```bash
curl -X POST "http://localhost:8000/api/v1/api-keys" \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "agent_1",
    "permissions": ["decide", "log_hand"],
    "is_admin": false
  }'
```

### Права доступа

| Permission | Описание |
|------------|----------|
| `decide` | Доступ к /decide |
| `log_hand` | Доступ к /log_hand |
| `stats` | Доступ к статистике |
| `admin` | Полный доступ |

---

## Чек-лист запуска

- [ ] PostgreSQL запущен и доступен
- [ ] Redis запущен и доступен
- [ ] API отвечает на /health
- [ ] Admin API включен (`ENABLE_ADMIN_API=1`)
- [ ] Создан admin API ключ
- [ ] Добавлена хотя бы одна комната
- [ ] Создан хотя бы один стол
- [ ] Создан и настроен бот
- [ ] Проверены Grafana дашборды
