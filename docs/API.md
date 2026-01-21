# PokerBot API Documentation

## Overview

PokerBot API v1 - REST API для управления покерным ботом, принятия решений и сбора статистики.

**Base URL:** `http://localhost:8000/api/v1`

**Автоматическая документация:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Authentication

API поддерживает два метода аутентификации:

### 1. Simple API Key

```http
X-API-Key: your-api-key
```

### 2. HMAC-SHA256 (рекомендуется для продакшена)

```http
X-API-Key: your-api-key
X-Signature: hmac-sha256-signature
X-Nonce: unique-request-id
X-Timestamp: unix-timestamp
```

**Генерация подписи:**
```python
import hmac
import hashlib
import time
import uuid

def sign_request(api_key: str, secret: str, method: str, path: str, body: bytes) -> dict:
    nonce = str(uuid.uuid4())
    timestamp = int(time.time())

    message = f"{method}|{path}|{nonce}|{timestamp}|{body.decode()}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return {
        "X-API-Key": api_key,
        "X-Signature": signature,
        "X-Nonce": nonce,
        "X-Timestamp": str(timestamp)
    }
```

---

## Core Endpoints

### POST /decide

Получить решение бота для текущего состояния игры.

**Request Body:**
```json
{
  "hand_id": "hand_12345",
  "table_id": "table_1",
  "limit_type": "NL10",
  "street": "preflop",
  "hero_position": 5,
  "dealer": 0,
  "hero_cards": "AsKh",
  "board_cards": "",
  "stacks": {"0": 100, "1": 99.5, "2": 99, "3": 100, "4": 100, "5": 100},
  "bets": {"0": 0, "1": 0.5, "2": 1, "3": 0, "4": 0, "5": 0},
  "total_bets": {"0": 0, "1": 0.5, "2": 1, "3": 0, "4": 0, "5": 0},
  "active_players": [0, 1, 2, 5],
  "pot": 1.5,
  "current_player": 5,
  "last_raise_amount": 0,
  "small_blind": 0.5,
  "big_blind": 1.0,
  "opponent_ids": ["player_1", "player_2"]
}
```

**Response:**
```json
{
  "action": "raise",
  "amount": 3.5,
  "reasoning": {
    "gto_action": "raise",
    "gto_confidence": 0.85,
    "exploit_adjustment": 0.1,
    "opponent_type": "fish",
    "ev_estimate": 0.5
  },
  "latency_ms": 45,
  "cached": false
}
```

**Actions:**
- `fold` - Сброс карт
- `check` - Чек (когда нет ставки)
- `call` - Колл (уравнять ставку)
- `raise` - Рейз (amount указывает размер)
- `all_in` - Олл-ин

**Latency Target:** P95 < 200ms

---

### POST /log_hand

Логирование завершенной раздачи.

**Request Body:**
```json
{
  "hand_id": "hand_12345",
  "table_id": "table_1",
  "limit_type": "NL10",
  "players_count": 6,
  "hero_position": 5,
  "hero_cards": "AsKh",
  "board_cards": "QdJcTs8h2c",
  "pot_size": 25.5,
  "rake_amount": 1.27,
  "hero_result": 12.0,
  "hand_history": {
    "player_1": {
      "vpip": true,
      "pfr": false,
      "three_bet": false,
      "cbet": false
    }
  }
}
```

**Response:**
```json
{
  "status": "logged",
  "hand_id": "hand_12345"
}
```

---

### POST /hands/bulk

Массовая загрузка раздач.

**Request Body:**
```json
{
  "hands": [
    { ... hand1 ... },
    { ... hand2 ... }
  ],
  "skip_existing": true
}
```

**Response:**
```json
{
  "status": "completed",
  "total_requested": 100,
  "successful": 98,
  "failed": 2,
  "errors": [
    {"index": 5, "hand_id": "...", "error": "..."}
  ]
}
```

---

## Session Management

### POST /session/start

Начать игровую сессию.

**Request Body:**
```json
{
  "session_id": "session_20240115_001",
  "limit_type": "NL10",
  "table_ids": ["table_1", "table_2"]
}
```

**Response:**
```json
{
  "status": "started",
  "session_id": "session_20240115_001",
  "limit_type": "NL10",
  "start_time": "2024-01-15T10:30:00Z"
}
```

### POST /session/end

Завершить игровую сессию.

**Request Body:**
```json
{
  "session_id": "session_20240115_001",
  "hands_played": 500,
  "total_profit": 25.5
}
```

**Response:**
```json
{
  "status": "ended",
  "session_id": "session_20240115_001",
  "duration_minutes": 180.5,
  "hands_played": 500,
  "winrate_bb_100": 5.1,
  "total_rake": 25.0,
  "rake_per_hour": 8.3
}
```

### GET /session/{session_id}

Получить информацию о сессии.

### GET /sessions/recent

Получить список последних сессий.

**Query Parameters:**
- `limit` (int, default=50): Количество записей
- `limit_type` (string, optional): Фильтр по лимиту

---

## Opponent Profiles

### GET /opponent/{opponent_id}

Получить профиль оппонента.

**Response:**
```json
{
  "opponent_id": "player_123",
  "vpip": 42.5,
  "pfr": 12.3,
  "three_bet_pct": 3.5,
  "aggression_factor": 1.2,
  "hands_played": 250,
  "classification": "fish"
}
```

**Player Classifications:**
- `fish` - Слабый игрок (высокий VPIP, низкий AF)
- `nit` - Тайтовый пассивный (низкий VPIP/PFR)
- `tag` - Tight-aggressive (оптимальный VPIP/PFR, высокий AF)
- `lag` - Loose-aggressive (высокий VPIP, высокий AF)
- `calling_station` - Много коллирует, мало рейзит
- `unknown` - Недостаточно данных

### GET /opponents

Получить список всех профилей.

**Query Parameters:**
- `skip` (int, default=0): Пропустить N записей
- `limit` (int, default=100): Максимум записей
- `classification` (string, optional): Фильтр по типу
- `min_hands` (int, default=0): Минимум сыгранных рук

### POST /opponent

Создать профиль оппонента вручную.

### PUT /opponent/{opponent_id}

Обновить профиль оппонента.

### DELETE /opponent/{opponent_id}

Удалить профиль оппонента.

### POST /opponents/bulk

Массовая загрузка профилей.

**Request Body:**
```json
{
  "profiles": [
    {
      "opponent_id": "player_1",
      "vpip": 45.0,
      "pfr": 10.0,
      "three_bet_pct": 3.0,
      "aggression_factor": 1.5,
      "hands_played": 100
    }
  ],
  "skip_existing": true,
  "update_existing": false
}
```

---

## Training

### POST /training/start

Запустить обучение MCCFR.

**Request Body:**
```json
{
  "format": "NL10",
  "iterations": 50000,
  "checkpoint_version": "v1.1"
}
```

### POST /training/stop

Остановить обучение.

### GET /training/status

Получить статус обучения.

**Response:**
```json
{
  "is_running": true,
  "current_iteration": 25000,
  "total_iterations": 50000,
  "format": "NL10",
  "start_time": "2024-01-15T10:00:00Z",
  "estimated_completion": "2024-01-15T12:00:00Z"
}
```

### GET /checkpoints

Получить список чекпоинтов.

### POST /checkpoint/{checkpoint_id}/activate

Активировать чекпоинт для использования.

---

## Statistics

### GET /stats

Общая статистика бота.

**Response:**
```json
{
  "total_hands": 50000,
  "total_decisions": 150000,
  "total_opponents": 2500,
  "active_checkpoints": 2,
  "last_hand_time": "2024-01-15T14:30:00Z",
  "last_decision_time": "2024-01-15T14:30:05Z"
}
```

### GET /stats/winrate

Статистика винрейта.

**Query Parameters:**
- `days` (int, default=30): Период в днях

**Response:**
```json
{
  "period_days": 30,
  "total_hands": 15000,
  "total_profit": 450.5,
  "winrate_bb_100": 3.0,
  "avg_profit_per_hand": 0.03
}
```

---

## WebSocket

### WS /ws/decisions

Real-time поток решений.

**Message Format:**
```json
{
  "type": "decision",
  "data": {
    "hand_id": "hand_12345",
    "action": "raise",
    "amount": 3.5,
    "latency_ms": 45,
    "limit_type": "NL10",
    "street": "preflop"
  }
}
```

### WS /ws/hands

Real-time поток результатов раздач.

**Message Format:**
```json
{
  "type": "hand_result",
  "data": {
    "hand_id": "hand_12345",
    "pot_size": 25.5,
    "hero_result": 12.0,
    "limit_type": "NL10"
  }
}
```

---

## Metrics (Prometheus)

### GET /metrics

Prometheus метрики.

**Available Metrics:**
- `poker_decisions_total{limit_type, action}` - Количество решений
- `poker_decision_latency_seconds{limit_type, street}` - Латентность решений
- `poker_hands_total{limit_type}` - Количество раздач
- `poker_profit_bb{limit_type}` - Профит в BB
- `poker_active_sessions` - Активные сессии

---

## Error Handling

**Error Response Format:**
```json
{
  "detail": "Error message"
}
```

**HTTP Status Codes:**
- `200` - OK
- `201` - Created
- `204` - No Content (успешное удаление)
- `400` - Bad Request (неверные параметры)
- `401` - Unauthorized (неверный API key/HMAC)
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

---

## Rate Limits

- `/decide`: 100 req/sec per API key
- `/log_hand`: 50 req/sec per API key
- Other endpoints: 20 req/sec per API key

---

## Examples

### Python (requests)

```python
import requests

API_URL = "http://localhost:8000/api/v1"
API_KEY = "your-api-key"

headers = {"X-API-Key": API_KEY}

# Get decision
response = requests.post(
    f"{API_URL}/decide",
    headers=headers,
    json={
        "hand_id": "hand_1",
        "table_id": "table_1",
        "limit_type": "NL10",
        "street": "preflop",
        "hero_position": 5,
        "dealer": 0,
        "hero_cards": "AsKh",
        "board_cards": "",
        "stacks": {"0": 100, "1": 99.5, "2": 99, "3": 100, "4": 100, "5": 100},
        "bets": {"0": 0, "1": 0.5, "2": 1, "3": 0, "4": 0, "5": 0},
        "total_bets": {"0": 0, "1": 0.5, "2": 1, "3": 0, "4": 0, "5": 0},
        "active_players": [0, 1, 2, 5],
        "pot": 1.5,
        "current_player": 5
    }
)

decision = response.json()
print(f"Action: {decision['action']}, Amount: {decision.get('amount')}")
```

### cURL

```bash
# Get decision
curl -X POST "http://localhost:8000/api/v1/decide" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "hand_id": "hand_1",
    "table_id": "table_1",
    "limit_type": "NL10",
    "street": "preflop",
    "hero_position": 5,
    "dealer": 0,
    "hero_cards": "AsKh",
    "board_cards": "",
    "stacks": {"0": 100, "1": 99.5, "2": 99},
    "bets": {"0": 0, "1": 0.5, "2": 1},
    "total_bets": {"0": 0, "1": 0.5, "2": 1},
    "active_players": [0, 1, 2],
    "pot": 1.5,
    "current_player": 2
  }'

# Get opponent profile
curl "http://localhost:8000/api/v1/opponent/player_123" \
  -H "X-API-Key: your-api-key"
```

---

## Table Agent Integration

Table Agent подключается к API для получения решений:

```python
from table_agent import TableAgent, ConnectionConfig, AgentConfig

# Конфигурация
conn_config = ConnectionConfig(
    api_url="http://localhost:8000",
    api_key="your-api-key",
    timeout=5.0
)

agent_config = AgentConfig(
    bot_id="bot_1",
    limit_type="NL10"
)

# Запуск
agent = TableAgent(conn_config, agent_config)
await agent.start()

# Обработка состояния игры
decision = await agent.process_game_state(game_state)
print(f"Action: {decision['action']}")

await agent.stop()
```

---

## Changelog

### v1.0.0
- Initial release
- Core endpoints: /decide, /log_hand
- Session management
- Opponent profiles
- Training control
- WebSocket support
- Prometheus metrics
