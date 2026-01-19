# Интеграция с Pluribus-Poker-AI

Этот документ описывает, как интегрировать `poker_rake_bot` (backend API) с `pluribus-poker-AI` (client node) для создания полноценного покерного бота.

## 🎯 Архитектура интеграции

```
┌─────────────────────────────────┐
│  pluribus-poker-AI (Client)     │
│  - Vision System (распознавание)│
│  - ADB Connection               │
│  - Game State Extraction        │
└──────────────┬──────────────────┘
               │ HTTP POST
               │ /api/v1/decide
               ▼
┌─────────────────────────────────┐
│  poker_rake_bot (Backend API)   │
│  - Decision Router (GTO+Exploit)│
│  - MCCFR Strategies             │
│  - Opponent Profiling           │
│  - Redis Cache                  │
└──────────────┬──────────────────┘
               │ Response
               │ {action, amount}
               ▼
┌─────────────────────────────────┐
│  Client выполняет действие       │
│  через ADB                       │
└─────────────────────────────────┘
```

## 📋 Преимущества интеграции

### Что дает pluribus-poker-AI:
- ✅ **Vision System** - автоматическое распознавание карт
- ✅ **ADB Integration** - управление реальным приложением
- ✅ **Game State Extraction** - парсинг состояния игры

### Что дает poker_rake_bot:
- ✅ **Decision Router** - умные решения (GTO + Exploit)
- ✅ **MCCFR Strategies** - обученные стратегии
- ✅ **Opponent Profiling** - анализ оппонентов
- ✅ **Performance** - Redis кэширование, быстрые ответы

## 🚀 Быстрый старт

### 1. Настройка poker_rake_bot API

```bash
cd poker_rake_bot

# Установка зависимостей
pip install -r requirements.txt

# Настройка .env
cp .env.example .env
# Отредактируйте .env (DATABASE_URL, REDIS_URL)

# Запуск API
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступен на `http://localhost:8000`

### 2. Настройка pluribus-poker-AI Client

В файле `pluribus-poker-AI/client/impl/pppoker.py` (или другом client):

```python
import requests
from typing import Dict, Optional

class PPPokerBot:
    def __init__(self):
        self.api_url = "http://localhost:8000"
        self.api_key = None  # Опционально
    
    def get_decision(self, game_state: Dict) -> Dict:
        """
        Получает решение от poker_rake_bot API
        
        Args:
            game_state: Состояние игры из vision system
            
        Returns:
            Решение: {action, amount, reasoning}
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        # Преобразуем game_state в формат API
        request_data = {
            "hand_id": game_state.get("hand_id", ""),
            "table_id": game_state.get("table_id", ""),
            "limit_type": game_state.get("limit_type", "NL10"),
            "street": game_state.get("street", "preflop"),
            "hero_position": game_state.get("hero_position", 0),
            "dealer": game_state.get("dealer", 0),
            "hero_cards": game_state.get("hero_cards", ""),
            "board_cards": game_state.get("board_cards", ""),
            "stacks": game_state.get("stacks", {}),
            "bets": game_state.get("bets", {}),
            "total_bets": game_state.get("total_bets", {}),
            "active_players": game_state.get("active_players", []),
            "pot": game_state.get("pot", 0.0),
            "current_player": game_state.get("current_player", 0),
            "last_raise_amount": game_state.get("last_raise_amount", 0.0),
            "small_blind": game_state.get("small_blind", 0.5),
            "big_blind": game_state.get("big_blind", 1.0),
            "opponent_ids": game_state.get("opponent_ids", [])
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/decide",
                json=request_data,
                headers=headers,
                timeout=2.0  # Максимум 2 секунды
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к API: {e}")
            # Fallback на локальную логику
            return self._fallback_decision(game_state)
    
    def _fallback_decision(self, game_state: Dict) -> Dict:
        """Fallback решение если API недоступен"""
        # Простая логика
        return {
            "action": "check",
            "amount": None,
            "reasoning": {"type": "fallback"}
        }
```

### 3. Использование в основном цикле

```python
def main_loop(self):
    """Основной цикл бота"""
    while True:
        # 1. Получаем состояние игры через vision
        game_state = self.vision_service.get_game_state()
        
        # 2. Получаем решение от API
        decision = self.get_decision(game_state)
        
        # 3. Выполняем действие через ADB
        self.execute_action(decision["action"], decision.get("amount"))
        
        # 4. Логируем раздачу после завершения
        if game_state.get("hand_complete"):
            self.log_hand(game_state)
        
        time.sleep(0.5)  # Небольшая задержка
```

## 🔧 Конфигурация

### Переменные окружения для Client

```bash
# В pluribus-poker-AI/.env или infra/dev.env
API_URL=http://localhost:8000
API_KEY=your_api_key_here  # Опционально
API_TIMEOUT=2.0
```

### Переменные окружения для Backend

```bash
# В poker_rake_bot/.env
DATABASE_URL=postgresql://user:pass@localhost/poker_bot
REDIS_URL=redis://localhost:6379
API_KEY=your_api_key_here  # Для аутентификации
```

## 📊 Формат данных

### Запрос к API (`POST /api/v1/decide`)

```json
{
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
  "big_blind": 1.0,
  "opponent_ids": ["opponent_1"]
}
```

### Ответ от API

```json
{
  "action": "raise",
  "amount": 3.0,
  "reasoning": {
    "gto_strategy": {"fold": 0.1, "call": 0.2, "raise": 0.7},
    "exploit_adjustments": {"raise": +0.1},
    "final_strategy": {"fold": 0.05, "call": 0.15, "raise": 0.8}
  },
  "latency_ms": 45,
  "cached": false
}
```

## 🔒 Безопасность

### HMAC Аутентификация (опционально)

Если включена HMAC аутентификация в `poker_rake_bot`:

```python
import hmac
import hashlib
import time

def generate_hmac_signature(api_key: str, body: str, nonce: str, timestamp: int) -> str:
    """Генерирует HMAC подпись"""
    message = f"{nonce}{timestamp}{body}"
    signature = hmac.new(
        api_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

# В запросе
nonce = str(uuid.uuid4())
timestamp = int(time.time())
signature = generate_hmac_signature(api_key, json.dumps(request_data), nonce, timestamp)

headers = {
    "X-Signature": signature,
    "X-Nonce": nonce,
    "X-Timestamp": str(timestamp)
}
```

## 📈 Мониторинг

### Метрики API

```bash
# Prometheus метрики
curl http://localhost:8000/metrics

# Health check
curl http://localhost:8000/api/v1/health

# Статистика
curl http://localhost:8000/api/v1/stats
```

### Логирование решений

Все решения автоматически логируются в БД через `decision_logger`:
- GTO стратегия
- Exploit коррекции
- Финальное решение
- Латентность

## 🐛 Troubleshooting

### API недоступен

```python
# Проверьте подключение
import requests
response = requests.get("http://localhost:8000/api/v1/health")
print(response.json())
```

### Медленные ответы

- Проверьте Redis кэш (должен ускорить частые споты)
- Уменьшите `max_depth` в MCCFR
- Используйте более простые стратегии для быстрых решений

### Ошибки аутентификации

- Проверьте `API_KEY` в переменных окружения
- Убедитесь, что HMAC подпись генерируется правильно
- Проверьте логи API на детали ошибки

## 🎓 Примеры использования

### Полный пример интеграции

См. файл `examples/pluribus_integration_example.py` (создать при необходимости)

## 📚 Дополнительные ресурсы

- [API Documentation](../API_DOCUMENTATION.md)
- [Decision Router Guide](../DECISION_ROUTER.md)
- [MCCFR Guide](../MCCFR_GUIDE.md)
