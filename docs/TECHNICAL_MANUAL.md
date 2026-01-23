# PokerBot v1.3 - Технический мануал

Архитектура, модули и протоколы системы.

## Содержание

1. [Архитектура](#архитектура)
2. [Структура модулей](#структура-модулей)
3. [Схема базы данных](#схема-базы-данных)
4. [Протокол агентов](#протокол-агентов)
5. [API Reference](#api-reference)
6. [Конфигурация](#конфигурация)
7. [Развертывание](#развертывание)

---

## Архитектура

### Обзор

```
┌─────────────────────────────────────────────────────────────────┐
│                        POKER BOT SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Agents     │    │  Dashboard   │    │   Grafana    │       │
│  │  (Table)     │    │   (React)    │    │  (Metrics)   │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                    │               │
│         ▼                   ▼                    ▼               │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                    FastAPI Backend                    │       │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐ │       │
│  │  │ /decide │ │/log_hand│ │ /admin  │ │  /ws/agent  │ │       │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └──────┬──────┘ │       │
│  │       │           │           │              │        │       │
│  │       ▼           ▼           ▼              ▼        │       │
│  │  ┌────────────────────────────────────────────────┐  │       │
│  │  │              Decision Router                    │  │       │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │  │       │
│  │  │  │  MCCFR  │  │ Exploit │  │  Anti-Pattern   │ │  │       │
│  │  │  │  (GTO)  │  │ Adjust  │  │     Router      │ │  │       │
│  │  │  └─────────┘  └─────────┘  └─────────────────┘ │  │       │
│  │  └────────────────────────────────────────────────┘  │       │
│  └──────────────────────────────────────────────────────┘       │
│         │                   │                    │               │
│         ▼                   ▼                    ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  PostgreSQL  │    │    Redis     │    │  Prometheus  │       │
│  │   (Data)     │    │   (Cache)    │    │  (Metrics)   │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Слои приложения (ARK)

```
poker_rake_bot/
├── brain/           # DOMAIN: Бизнес-логика принятия решений
│   ├── mccfr.py           # GTO стратегии (MCCFR алгоритм)
│   ├── decision_router.py # Микширование GTO/Exploit
│   ├── opponent_profiler.py # Классификация оппонентов
│   └── anti_pattern_router.py # Избежание паттернов
│
├── engine/          # DOMAIN: Покерная механика
│   ├── hand_evaluator.py  # Оценка рук
│   ├── cards.py           # Представление карт
│   └── state_encoder.py   # Кодирование состояний
│
├── api/             # APPLICATION: Use-cases и API
│   ├── endpoints/         # REST endpoints
│   ├── decision_maker.py  # Orchestration
│   ├── auth.py            # Аутентификация
│   └── safe_mode.py       # Отказоустойчивость
│
├── data/            # INFRASTRUCTURE: Персистентность
│   ├── models.py          # SQLAlchemy модели
│   ├── database.py        # Подключение к БД
│   └── redis_cache.py     # Redis кэширование
│
└── table_agent/     # INFRASTRUCTURE: Интеграция с клиентами
    ├── agent.py           # Агент стола
    └── screen_reader.py   # Распознавание экрана
```

---

## Структура модулей

### Brain Module (5,589 строк)

Отвечает за принятие решений.

#### MCCFR (`mccfr.py`)

External Sampling Monte Carlo CFR:

```python
class MCCFR:
    """
    Внешняя выборка MCCFR для 6-max NLHE.

    Особенности:
    - Linear complexity per iteration
    - Numba JIT для производительности
    - Поддержка разных размеров рейзов
    """

    def train(self, iterations: int) -> None:
        """Обучение стратегии"""

    def get_strategy(self, infoset: str) -> Dict[str, float]:
        """Получение стратегии для информационного множества"""
```

#### Decision Router (`decision_router.py`)

Смешивание GTO и Exploit стратегий:

```python
class DecisionRouter:
    """
    Роутер решений с учётом:
    - GTO baseline (MCCFR)
    - Exploit adjustments (opponent profiler)
    - Style targets (VPIP, PFR, AF)
    - Anti-pattern randomization
    """

    def get_decision(
        self,
        game_state: GameState,
        opponent_profiles: Dict[str, OpponentProfile]
    ) -> Decision:
        """Возвращает оптимальное решение"""
```

#### Opponent Profiler (`opponent_profiler.py`)

Классификация оппонентов:

```python
class OpponentProfiler:
    """
    Классификация по VPIP/PFR матрице:

    |           | PFR < 12 | PFR 12-20 | PFR > 20 |
    |-----------|----------|-----------|----------|
    | VPIP < 20 | Nit      | TAG       | LAG      |
    | VPIP 20-30| Weak     | Reg       | LAG      |
    | VPIP > 30 | Fish     | Fish      | Maniac   |
    """

    def classify(self, stats: PlayerStats) -> str:
        """Возвращает классификацию: nit/tag/lag/fish/maniac"""
```

### Engine Module (389 строк)

#### Hand Evaluator (`hand_evaluator.py`)

```python
class HandEvaluator:
    """
    Оценка 7-карточных рук Texas Hold'em.

    Возвращает tuple (rank, high_cards) где rank:
    - 8: Straight Flush
    - 7: Four of a Kind
    - 6: Full House
    - 5: Flush
    - 4: Straight
    - 3: Three of a Kind
    - 2: Two Pair
    - 1: One Pair
    - 0: High Card
    """

    def evaluate(self, cards: List[Card]) -> Tuple[int, List[int]]:
        """Оценивает руку из 7 карт"""
```

### API Module

#### Safe Mode (`safe_mode.py`)

Circuit Breaker паттерн:

```python
class CircuitBreaker:
    """
    Состояния:
    - CLOSED: нормальная работа
    - OPEN: сервис недоступен (fast-fail)
    - HALF_OPEN: пробуем восстановить

    Переходы:
    CLOSED -> OPEN: после N ошибок
    OPEN -> HALF_OPEN: после timeout
    HALF_OPEN -> CLOSED: после M успехов
    HALF_OPEN -> OPEN: при ошибке
    """
```

---

## Схема базы данных

### Core Tables

```sql
-- Раздачи
CREATE TABLE hands (
    id SERIAL PRIMARY KEY,
    hand_id VARCHAR(100) UNIQUE NOT NULL,
    table_id VARCHAR(100) NOT NULL,
    session_id INTEGER REFERENCES bot_sessions(id),
    limit_type VARCHAR(20) NOT NULL,
    hero_cards VARCHAR(10) NOT NULL,
    board_cards VARCHAR(20),
    pot_size DECIMAL(10, 2) NOT NULL,
    rake_amount DECIMAL(10, 2) NOT NULL,
    hero_result DECIMAL(10, 2) NOT NULL,
    hand_history JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Решения
CREATE TABLE decision_log (
    id SERIAL PRIMARY KEY,
    hand_id VARCHAR(100) NOT NULL,
    decision_id VARCHAR(100) UNIQUE NOT NULL,
    session_id INTEGER REFERENCES bot_sessions(id),
    street VARCHAR(20) NOT NULL,
    game_state JSONB NOT NULL,
    gto_action JSONB,
    exploit_action JSONB,
    final_action VARCHAR(50) NOT NULL,
    action_amount DECIMAL(10, 2),
    reasoning JSONB,
    latency_ms INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Профили оппонентов
CREATE TABLE opponent_profiles (
    id SERIAL PRIMARY KEY,
    opponent_id VARCHAR(100) UNIQUE NOT NULL,
    vpip DECIMAL(5, 2) DEFAULT 0,
    pfr DECIMAL(5, 2) DEFAULT 0,
    three_bet_pct DECIMAL(5, 2) DEFAULT 0,
    aggression_factor DECIMAL(5, 2) DEFAULT 0,
    cbet_pct DECIMAL(5, 2) DEFAULT 0,
    fold_to_cbet_pct DECIMAL(5, 2) DEFAULT 0,
    hands_played INTEGER DEFAULT 0,
    classification VARCHAR(50),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Control Plane Tables

```sql
-- Боты
CREATE TABLE bots (
    id SERIAL PRIMARY KEY,
    alias VARCHAR(100) UNIQUE NOT NULL,
    default_style VARCHAR(50) DEFAULT 'balanced',
    default_limit VARCHAR(20) DEFAULT 'NL10',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Комнаты
CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    room_link VARCHAR(500) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    rake_model_id INTEGER REFERENCES rake_models(id),
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Столы
CREATE TABLE tables (
    id SERIAL PRIMARY KEY,
    room_id INTEGER REFERENCES rooms(id) ON DELETE CASCADE,
    external_table_id VARCHAR(100),
    limit_type VARCHAR(20) NOT NULL,
    max_players INTEGER DEFAULT 6,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Сессии ботов
CREATE TABLE bot_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    bot_id INTEGER REFERENCES bots(id),
    table_id INTEGER REFERENCES tables(id),
    bot_config_id INTEGER REFERENCES bot_configs(id),
    status VARCHAR(20) DEFAULT 'starting',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    hands_played INTEGER DEFAULT 0,
    profit DECIMAL(10, 2) DEFAULT 0,
    rake_paid DECIMAL(10, 2) DEFAULT 0,
    bb_100 DECIMAL(6, 2) DEFAULT 0,
    rake_100 DECIMAL(6, 2) DEFAULT 0
);

-- Агенты
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'offline',
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    version VARCHAR(50),
    assigned_session_id INTEGER REFERENCES bot_sessions(id),
    meta JSONB
);

-- Аудит
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Индексы

```sql
-- Performance indexes
CREATE INDEX idx_hands_session_id ON hands(session_id);
CREATE INDEX idx_hands_table_id ON hands(table_id);
CREATE INDEX idx_decision_log_session_id ON decision_log(session_id);
CREATE INDEX idx_decision_log_timestamp ON decision_log(timestamp);
CREATE INDEX idx_opponent_profiles_classification ON opponent_profiles(classification);
CREATE INDEX idx_bot_sessions_status ON bot_sessions(status);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
```

---

## Протокол агентов

### WebSocket Heartbeat

Агенты подключаются через WebSocket для real-time коммуникации.

**Endpoint:** `ws://host:8000/api/v1/agent/ws/{agent_id}`

#### Heartbeat (Agent -> Server)

```json
{
  "type": "heartbeat",
  "agent_id": "agent_001",
  "session_id": "sess_abc123",
  "status": "online",
  "version": "1.3.0",
  "errors": []
}
```

#### Heartbeat ACK (Server -> Agent)

```json
{
  "type": "heartbeat_ack",
  "timestamp": "2024-01-15T12:00:00Z",
  "commands": [
    {
      "command": "pause",
      "timestamp": "2024-01-15T11:59:50Z",
      "reason": "manual"
    }
  ]
}
```

### HTTP Fallback

При недоступности WebSocket используется HTTP polling.

**Endpoint:** `POST /api/v1/agent/heartbeat`

```json
{
  "agent_id": "agent_001",
  "session_id": "sess_abc123",
  "status": "online",
  "version": "1.3.0"
}
```

### Команды агенту

**Endpoint:** `POST /api/v1/agent/{agent_id}/command`

| Команда | Описание |
|---------|----------|
| `pause` | Приостановить игру |
| `resume` | Возобновить игру |
| `stop` | Остановить сессию |
| `sit_out` | Выйти из игры (остаться за столом) |

```json
{
  "command": "pause",
  "reason": "manual operator action"
}
```

### Диаграмма состояний агента

```
                    ┌─────────────┐
                    │   offline   │
                    └──────┬──────┘
                           │ connect
                           ▼
┌────────┐        ┌─────────────┐        ┌────────┐
│ error  │◄───────│   online    │───────►│ paused │
└────────┘  error └──────┬──────┘  pause └────┬───┘
     │                   │ stop              │ resume
     │                   ▼                   │
     │            ┌─────────────┐            │
     └───────────►│   stopped   │◄───────────┘
                  └─────────────┘
```

---

## API Reference

### Decision API

#### POST /api/v1/decide

Принятие решения ботом.

**Request:**
```json
{
  "hand_id": "hand_123",
  "table_id": "table_001",
  "limit_type": "NL10",
  "street": "flop",
  "hero_position": 3,
  "hero_cards": "AsKh",
  "board_cards": "Qs Jd Tc",
  "pot_size": 2.50,
  "bets": {"0": 0.10, "1": 0.25},
  "big_blind": 0.10,
  "opponents": ["opp_1", "opp_2"]
}
```

**Response:**
```json
{
  "action": "raise",
  "amount": 1.25,
  "table_key": "table_001",
  "reasoning": {
    "gto_action": "raise",
    "exploit_adjustment": 0.15,
    "opponent_type": "fish"
  },
  "latency_ms": 45
}
```

### Admin API

Все admin endpoints требуют `X-API-Key` с правами admin.

| Endpoint | Method | Описание |
|----------|--------|----------|
| `/api/v1/admin/bots` | GET/POST | CRUD ботов |
| `/api/v1/admin/rooms` | GET/POST | CRUD комнат |
| `/api/v1/admin/tables` | GET/POST | CRUD столов |
| `/api/v1/admin/rake-models` | GET/POST | CRUD рейк-моделей |
| `/api/v1/admin/bot-configs` | GET/POST | CRUD конфигов |
| `/api/v1/admin/sessions` | GET/POST | Управление сессиями |

---

## Конфигурация

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/pokerbot

# Redis
REDIS_URL=redis://localhost:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Auth
API_SECRET_KEY=your-secret-key
HMAC_SECRET=your-hmac-secret

# Features
ENABLE_ADMIN_API=1
SAFE_MODE_ENABLED=1
ENABLE_SECURITY_HEADERS=false

# Training
MCCFR_ITERATIONS=50000
CHECKPOINT_DIR=./checkpoints

# Rate Limiting
RATE_LIMIT_PER_MINUTE=120
```

### Bot Styles (`config/bot_styles.yaml`)

```yaml
NL10:
  gentle:
    vpip_range: [18, 22]
    pfr_range: [14, 18]
    af_range: [1.8, 2.2]
    exploit_weights:
      preflop: 0.25
      flop: 0.35
      turn: 0.45
      river: 0.55
    winrate_target: 4.0

  neutral:
    vpip_range: [22, 26]
    pfr_range: [17, 21]
    af_range: [2.0, 2.5]
    exploit_weights:
      preflop: 0.30
      flop: 0.40
      turn: 0.50
      river: 0.60
    winrate_target: 6.0

  aggressive:
    vpip_range: [25, 30]
    pfr_range: [20, 25]
    af_range: [2.5, 3.0]
    exploit_weights:
      preflop: 0.35
      flop: 0.45
      turn: 0.55
      river: 0.65
    winrate_target: 8.0
```

---

## Развертывание

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://pokerbot:pokerbot@db:5432/pokerbot
      - REDIS_URL=redis://redis:6379/0
      - ENABLE_ADMIN_API=1
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=pokerbot
      - POSTGRES_PASSWORD=pokerbot
      - POSTGRES_DB=pokerbot
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"

volumes:
  postgres_data:
```

### Миграции

```bash
# Применить все миграции
psql -U pokerbot -d pokerbot -f data/init.sql
psql -U pokerbot -d pokerbot -f data/migrations_v1_2.sql
psql -U pokerbot -d pokerbot -f data/migrations_v1_3_week2.sql
psql -U pokerbot -d pokerbot -f data/migrations_week3_rake.sql
```

### Production Checklist

- [ ] PostgreSQL с репликацией
- [ ] Redis с persistence (AOF)
- [ ] HTTPS через reverse proxy
- [ ] Ограничить CORS_ORIGINS
- [ ] Настроить rate limiting
- [ ] Включить security headers
- [ ] Настроить backup
- [ ] Настроить alerting
- [ ] Проверить Safe Mode
- [ ] Создать admin API key
