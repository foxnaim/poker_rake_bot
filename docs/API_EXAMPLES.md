# API Examples — Практические Примеры Использования

**Версия:** v1.3.0  
**Дата:** 2026-01-22

---

## 📚 Содержание

1. [Базовые примеры](#базовые-примеры)
2. [Python примеры](#python-примеры)
3. [cURL примеры](#curl-примеры)
4. [JavaScript/TypeScript примеры](#javascripttypescript-примеры)
5. [Запуск нескольких ботов](#запуск-нескольких-ботов)
6. [Обработка ошибок](#обработка-ошибок)
7. [WebSocket примеры](#websocket-примеры)

---

## Базовые примеры

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

**Ответ:**
```json
{
  "status": "healthy",
  "timestamp": 1705852800.0,
  "safe_mode": {
    "db": "closed",
    "redis": "closed"
  },
  "services": {
    "database": "up",
    "redis": "up"
  }
}
```

---

## Python примеры

### 1. Принятие решения (`/decide`)

```python
import httpx
import json

API_URL = "http://localhost:8000"
API_KEY = "your_api_key_here"  # Опционально

def make_decision():
    """Отправляет запрос на принятие решения"""
    client = httpx.Client(timeout=5.0)
    
    game_state = {
        "hand_id": "hand_12345",
        "table_id": "table_1",
        "limit_type": "NL10",
        "street": "preflop",
        "hero_position": 0,
        "dealer": 5,
        "hero_cards": "AsKh",
        "board_cards": "",
        "stacks": {"0": 100.0, "1": 100.0},
        "bets": {"0": 0.0, "1": 1.0},
        "total_bets": {"0": 0.0, "1": 1.0},
        "active_players": [0, 1],
        "pot": 1.5,
        "current_player": 0,
        "last_raise_amount": 1.0,
        "small_blind": 0.5,
        "big_blind": 1.0
    }
    
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    
    response = client.post(
        f"{API_URL}/api/v1/decide",
        json=game_state,
        headers=headers
    )
    
    if response.status_code == 200:
        decision = response.json()
        print(f"Действие: {decision['action']}")
        print(f"Размер: {decision.get('amount')}")
        print(f"Латентность: {decision['latency_ms']}ms")
        return decision
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    decision = make_decision()
```

### 2. Логирование раздачи (`/log_hand`)

```python
def log_hand():
    """Логирует завершенную раздачу"""
    client = httpx.Client(timeout=5.0)
    
    hand_data = {
        "hand_id": "hand_12345",
        "table_id": "table_1",
        "table_key": "table_1",  # Опционально, предпочтительнее table_id
        "limit_type": "NL10",
        "players_count": 6,
        "hero_position": 0,
        "hero_cards": "AsKh",
        "board_cards": "2c3d4h",
        "pot_size": 25.50,
        "rake_amount": 1.25,  # Опционально, будет вычислен автоматически
        "hero_result": 12.50,
        "hand_history": {
            "opponent_1": {"action": "fold", "position": 1},
            "opponent_2": {"action": "call", "position": 2}
        }
    }
    
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    
    response = client.post(
        f"{API_URL}/api/v1/log_hand",
        json=hand_data,
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Раздача залогирована: {result['hand_id']}")
        return result
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")
        return None
```

### 3. Получение статистики (`/stats`)

```python
def get_stats():
    """Получает общую статистику"""
    client = httpx.Client(timeout=5.0)
    
    response = client.get(f"{API_URL}/api/v1/stats")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"Всего раздач: {stats['total_hands']}")
        print(f"Активных сессий: {stats['active_sessions']}")
        return stats
    else:
        print(f"Ошибка: {response.status_code}")
        return None
```

### 4. Admin API — Создание бота

```python
def create_bot(admin_key: str):
    """Создает нового бота через Admin API"""
    client = httpx.Client(timeout=5.0)
    
    bot_data = {
        "alias": "Bot_Test_1",
        "default_style": "neutral",
        "default_limit": "NL10"
    }
    
    headers = {"X-API-Key": admin_key}
    
    response = client.post(
        f"{API_URL}/api/v1/admin/bots",
        json=bot_data,
        headers=headers
    )
    
    if response.status_code == 201:
        bot = response.json()
        print(f"Бот создан: {bot['id']} - {bot['alias']}")
        return bot
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")
        return None
```

### 5. Admin API — Запуск сессии

```python
def start_session(admin_key: str, bot_id: int, table_key: str):
    """Запускает сессию бота за столом"""
    client = httpx.Client(timeout=5.0)
    
    session_data = {
        "bot_id": bot_id,
        "table_key": table_key,  # Можно использовать table_key вместо table_id
        "limit": "NL10"
    }
    
    headers = {"X-API-Key": admin_key}
    
    response = client.post(
        f"{API_URL}/api/v1/admin/session/start",
        json=session_data,
        headers=headers
    )
    
    if response.status_code == 201:
        session = response.json()
        print(f"Сессия запущена: {session['session_id']}")
        return session
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")
        return None
```

---

## cURL примеры

### 1. Health Check

```bash
curl -X GET http://localhost:8000/api/v1/health
```

### 2. Принятие решения

```bash
curl -X POST http://localhost:8000/api/v1/decide \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "hand_id": "hand_12345",
    "table_id": "table_1",
    "limit_type": "NL10",
    "street": "preflop",
    "hero_position": 0,
    "dealer": 5,
    "hero_cards": "AsKh",
    "board_cards": "",
    "stacks": {"0": 100.0, "1": 100.0},
    "bets": {"0": 0.0, "1": 1.0},
    "total_bets": {"0": 0.0, "1": 1.0},
    "active_players": [0, 1],
    "pot": 1.5,
    "current_player": 0,
    "last_raise_amount": 1.0,
    "small_blind": 0.5,
    "big_blind": 1.0
  }'
```

### 3. Логирование раздачи

```bash
curl -X POST http://localhost:8000/api/v1/log_hand \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "hand_id": "hand_12345",
    "table_id": "table_1",
    "limit_type": "NL10",
    "players_count": 6,
    "hero_position": 0,
    "hero_cards": "AsKh",
    "board_cards": "2c3d4h",
    "pot_size": 25.50,
    "hero_result": 12.50
  }'
```

### 4. Admin API — Создание бота

```bash
curl -X POST http://localhost:8000/api/v1/admin/bots \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin_key_here" \
  -d '{
    "alias": "Bot_Test_1",
    "default_style": "neutral",
    "default_limit": "NL10"
  }'
```

### 5. Admin API — Запуск сессии

```bash
curl -X POST http://localhost:8000/api/v1/admin/session/start \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin_key_here" \
  -d '{
    "bot_id": 1,
    "table_key": "table_1",
    "limit": "NL10"
  }'
```

---

## JavaScript/TypeScript примеры

### 1. Принятие решения

```typescript
async function makeDecision(apiUrl: string, apiKey?: string) {
  const gameState = {
    hand_id: "hand_12345",
    table_id: "table_1",
    limit_type: "NL10",
    street: "preflop",
    hero_position: 0,
    dealer: 5,
    hero_cards: "AsKh",
    board_cards: "",
    stacks: { "0": 100.0, "1": 100.0 },
    bets: { "0": 0.0, "1": 1.0 },
    total_bets: { "0": 0.0, "1": 1.0 },
    active_players: [0, 1],
    pot: 1.5,
    current_player: 0,
    last_raise_amount: 1.0,
    small_blind: 0.5,
    big_blind: 1.0
  };

  const headers: Record<string, string> = {
    "Content-Type": "application/json"
  };
  
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  const response = await fetch(`${apiUrl}/api/v1/decide`, {
    method: "POST",
    headers,
    body: JSON.stringify(gameState)
  });

  if (response.ok) {
    const decision = await response.json();
    console.log(`Действие: ${decision.action}`);
    console.log(`Размер: ${decision.amount}`);
    return decision;
  } else {
    const error = await response.text();
    console.error(`Ошибка: ${response.status} - ${error}`);
    throw new Error(`API error: ${response.status}`);
  }
}
```

### 2. Логирование раздачи

```typescript
async function logHand(apiUrl: string, apiKey?: string) {
  const handData = {
    hand_id: "hand_12345",
    table_id: "table_1",
    table_key: "table_1",
    limit_type: "NL10",
    players_count: 6,
    hero_position: 0,
    hero_cards: "AsKh",
    board_cards: "2c3d4h",
    pot_size: 25.50,
    hero_result: 12.50
  };

  const headers: Record<string, string> = {
    "Content-Type": "application/json"
  };
  
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  const response = await fetch(`${apiUrl}/api/v1/log_hand`, {
    method: "POST",
    headers,
    body: JSON.stringify(handData)
  });

  if (response.ok) {
    const result = await response.json();
    console.log(`Раздача залогирована: ${result.hand_id}`);
    return result;
  } else {
    const error = await response.text();
    console.error(`Ошибка: ${response.status} - ${error}`);
    throw new Error(`API error: ${response.status}`);
  }
}
```

---

## Запуск нескольких ботов

### Python скрипт для запуска нескольких ботов

```python
import asyncio
import httpx

API_URL = "http://localhost:8000"
ADMIN_KEY = "your_admin_key"

async def start_multiple_bots():
    """Запускает несколько ботов за разными столами"""
    client = httpx.AsyncClient(timeout=10.0)
    headers = {"X-API-Key": ADMIN_KEY}
    
    # Конфигурация ботов
    bots_config = [
        {"bot_id": 1, "table_key": "table_1", "limit": "NL10"},
        {"bot_id": 2, "table_key": "table_2", "limit": "NL10"},
        {"bot_id": 3, "table_key": "table_3", "limit": "NL50"},
    ]
    
    tasks = []
    for config in bots_config:
        task = client.post(
            f"{API_URL}/api/v1/admin/session/start",
            json=config,
            headers=headers
        )
        tasks.append(task)
    
    # Запускаем все сессии параллельно
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, response in enumerate(responses):
        if isinstance(response, Exception):
            print(f"Ошибка для бота {bots_config[i]['bot_id']}: {response}")
        elif response.status_code == 201:
            session = response.json()
            print(f"✅ Бот {bots_config[i]['bot_id']} запущен: {session['session_id']}")
        else:
            print(f"❌ Ошибка для бота {bots_config[i]['bot_id']}: {response.status_code} - {response.text}")
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(start_multiple_bots())
```

### Bash скрипт

```bash
#!/bin/bash

API_URL="http://localhost:8000"
ADMIN_KEY="your_admin_key"

# Запускаем несколько ботов
for i in {1..3}; do
  curl -X POST "${API_URL}/api/v1/admin/session/start" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: ${ADMIN_KEY}" \
    -d "{
      \"bot_id\": ${i},
      \"table_key\": \"table_${i}\",
      \"limit\": \"NL10\"
    }"
  echo ""
done
```

---

## Обработка ошибок

### Python с retry логикой

```python
import httpx
import time
from typing import Optional

def make_decision_with_retry(
    client: httpx.Client,
    game_state: dict,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> Optional[dict]:
    """Принимает решение с retry логикой"""
    
    for attempt in range(max_retries):
        try:
            response = client.post(
                "http://localhost:8000/api/v1/decide",
                json=game_state,
                timeout=5.0
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limit
                retry_after = float(response.headers.get("Retry-After", retry_delay))
                time.sleep(retry_after)
                continue
            else:
                print(f"Ошибка {response.status_code}: {response.text}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
        except httpx.TimeoutException:
            print(f"Timeout на попытке {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None
        except Exception as e:
            print(f"Ошибка: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None
    
    return None
```

---

## WebSocket примеры

### Python WebSocket клиент

```python
import asyncio
import websockets
import json

async def websocket_client():
    """WebSocket клиент для real-time обновлений"""
    uri = "ws://localhost:8000/ws/live"
    
    async with websockets.connect(uri) as websocket:
        # Подписываемся на события
        await websocket.send(json.dumps({
            "type": "subscribe",
            "channels": ["decisions", "hand_results"]
        }))
        
        # Слушаем события
        async for message in websocket:
            event = json.loads(message)
            print(f"Событие: {event['type']}")
            
            if event["type"] == "decision":
                print(f"Решение: {event['data']['action']}")
            elif event["type"] == "hand_result":
                print(f"Раздача завершена: {event['data']['hand_id']}")

if __name__ == "__main__":
    asyncio.run(websocket_client())
```

### JavaScript WebSocket клиент

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/live');

ws.onopen = () => {
  console.log('WebSocket connected');
  
  // Подписываемся на события
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['decisions', 'hand_results']
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Событие:', data.type);
  
  if (data.type === 'decision') {
    console.log('Решение:', data.data.action);
  } else if (data.type === 'hand_result') {
    console.log('Раздача завершена:', data.data.hand_id);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket closed');
};
```

---

## HMAC Аутентификация

### Python пример с HMAC

```python
import hmac
import hashlib
import time
import json
import httpx

def make_decision_with_hmac(api_key: str, api_secret: str, game_state: dict):
    """Принимает решение с HMAC аутентификацией"""
    
    # Генерируем nonce и timestamp
    nonce = str(int(time.time() * 1000))
    timestamp = int(time.time())
    
    # Формируем body
    body_str = json.dumps(game_state, sort_keys=True)
    body_bytes = body_str.encode('utf-8')
    
    # Формируем строку для подписи
    method = "POST"
    path = "/api/v1/decide"
    message = f"{method}\n{path}\n{nonce}\n{timestamp}\n"
    message_bytes = message.encode('utf-8') + body_bytes
    
    # Вычисляем HMAC
    signature = hmac.new(
        api_secret.encode('utf-8'),
        message_bytes,
        hashlib.sha256
    ).hexdigest()
    
    # Отправляем запрос
    headers = {
        "X-API-Key": api_key,
        "X-Signature": signature,
        "X-Nonce": nonce,
        "X-Timestamp": str(timestamp),
        "Content-Type": "application/json"
    }
    
    client = httpx.Client(timeout=5.0)
    response = client.post(
        "http://localhost:8000/api/v1/decide",
        json=game_state,
        headers=headers
    )
    
    return response.json() if response.status_code == 200 else None
```

---

## Полный пример: Игровой цикл

```python
import asyncio
import httpx
import time

class PokerBotClient:
    """Клиент для взаимодействия с Poker Bot API"""
    
    def __init__(self, api_url: str, api_key: str = None):
        self.api_url = api_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=10.0)
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key
    
    async def decide(self, game_state: dict) -> dict:
        """Принимает решение"""
        response = await self.client.post(
            f"{self.api_url}/api/v1/decide",
            json=game_state,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def log_hand(self, hand_data: dict) -> dict:
        """Логирует раздачу"""
        response = await self.client.post(
            f"{self.api_url}/api/v1/log_hand",
            json=hand_data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def game_loop(self, table_key: str, limit_type: str = "NL10"):
        """Основной игровой цикл"""
        hand_id = 0
        
        while True:
            hand_id += 1
            
            # Читаем состояние игры (здесь должна быть интеграция с screen reader)
            game_state = {
                "hand_id": f"hand_{hand_id}",
                "table_id": table_key,
                "limit_type": limit_type,
                "street": "preflop",
                "hero_position": 0,
                "dealer": 5,
                "hero_cards": "AsKh",
                "board_cards": "",
                "stacks": {"0": 100.0, "1": 100.0},
                "bets": {"0": 0.0, "1": 1.0},
                "total_bets": {"0": 0.0, "1": 1.0},
                "active_players": [0, 1],
                "pot": 1.5,
                "current_player": 0,
                "last_raise_amount": 1.0,
                "small_blind": 0.5,
                "big_blind": 1.0
            }
            
            # Принимаем решение
            try:
                decision = await self.decide(game_state)
                print(f"Hand {hand_id}: {decision['action']} {decision.get('amount', '')}")
                
                # Здесь должна быть интеграция с action executor для выполнения действия
                # await execute_action(decision['action'], decision.get('amount'))
                
                # Логируем завершенную раздачу
                hand_data = {
                    "hand_id": f"hand_{hand_id}",
                    "table_id": table_key,
                    "limit_type": limit_type,
                    "players_count": 6,
                    "hero_position": 0,
                    "hero_cards": "AsKh",
                    "board_cards": "",
                    "pot_size": 25.50,
                    "hero_result": 5.0
                }
                await self.log_hand(hand_data)
                
            except Exception as e:
                print(f"Ошибка в hand {hand_id}: {e}")
            
            # Пауза между раздачами
            await asyncio.sleep(2.0)
    
    async def close(self):
        """Закрывает клиент"""
        await self.client.aclose()

# Использование
async def main():
    client = PokerBotClient("http://localhost:8000", api_key="your_key")
    try:
        await client.game_loop("table_1", "NL10")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

*Последнее обновление: 2026-01-22*
