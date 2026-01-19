# Hand History Parser

Парсер hand history файлов из покер-румов для автоматической загрузки раздач в систему.

## Поддерживаемые покер-румы

- ✅ **PokerStars** - полная поддержка
- ⏳ **888poker** - в разработке
- ⏳ **PartyPoker** - в разработке

## Установка зависимостей

```bash
pip install requests
```

## Использование

### 1. Как Python модуль

```python
from utils.hand_history_parser import HandHistoryParser, parse_and_upload

# Парсинг файла
parser = HandHistoryParser()
hands = parser.parse_file('hands.txt', room='pokerstars')

print(f"Распарсено раздач: {len(hands)}")

# Парсинг и автоматическая загрузка через API
result = parse_and_upload(
    'hands.txt',
    api_url='http://localhost:8080',
    api_key='your-api-key',  # опционально
    room='pokerstars',
    skip_existing=True
)

print(result)
# {'status': 'completed', 'total_requested': 100, 'successful': 95, 'failed': 5}
```

### 2. Командная строка

```bash
# Только парсинг (без загрузки)
python utils/hand_history_parser.py hands.txt --room pokerstars

# Парсинг и загрузка в API
python utils/hand_history_parser.py hands.txt --upload --api-url http://localhost:8080

# С API ключом
python utils/hand_history_parser.py hands.txt --upload --api-key your-key-here

# Не пропускать существующие раздачи (будет ошибка)
python utils/hand_history_parser.py hands.txt --upload --no-skip-existing
```

## Формат hand history

### PokerStars

Стандартный формат PokerStars Hand History:

```
PokerStars Hand #123456789: Hold'em No Limit ($0.05/$0.10 USD) - 2024/01/15 12:34:56 ET
Table 'TableName' 6-max Seat #1 is the button
Seat 1: Player1 ($10.00 in chips)
Seat 2: Hero ($10.00 in chips)
Seat 3: Player3 ($10.00 in chips)
Hero: posts small blind $0.05
Player3: posts big blind $0.10
*** HOLE CARDS ***
Dealt to Hero [As Kh]
Player1: folds
Hero: raises $0.20 to $0.30
Player3: calls $0.20
*** FLOP *** [Jh Ts 9c]
Hero: bets $0.50
Player3: calls $0.50
*** TURN *** [Jh Ts 9c] [Qc]
Hero: bets $1.20
Player3: calls $1.20
*** RIVER *** [Jh Ts 9c Qc] [2d]
Hero: bets $2.50
Player3: folds
Uncalled bet ($2.50) returned to Hero
Hero collected $3.85 from pot
*** SUMMARY ***
Total pot $4.00 | Rake $0.15
```

## Экспорт hand history из PokerStars

1. Откройте PokerStars клиент
2. Меню → **Tools** → **Instant Hand History**
3. Или: **Меню** → **Requests** → **Hand History**
4. Выберите период (последние N рук)
5. Нажмите **Request**
6. Сохраните файл как `.txt`

## Что парсится

Для каждой раздачи извлекается:

- `hand_id` - уникальный ID раздачи (с префиксом PS_)
- `table_id` - название стола
- `limit_type` - лимит (NL2, NL5, NL10, NL25, NL50, NL100, NL200)
- `players_count` - количество игроков
- `hero_position` - позиция героя (BTN, SB, BB, UTG, MP, CO)
- `hero_cards` - карты героя (например: AsKh)
- `board_cards` - борд (например: JhTs9cQc2d)
- `pot_size` - размер банка
- `rake_amount` - рейк
- `hero_result` - результат героя (прибыль/убыток)
- `hand_history` - данные оппонентов для профилирования

## Профилирование оппонентов

Для каждого оппонента автоматически собирается:

- Все действия (folds, checks, calls, bets, raises)
- Показал ли карты на шоудауне
- Какие карты показал (если показал)

Эти данные используются для обновления профилей оппонентов через API.

## Примеры

### Быстрая загрузка 1000 раздач

```bash
# Экспортируйте из PokerStars последние 1000 рук
# Сохраните как hands_1000.txt

python utils/hand_history_parser.py hands_1000.txt --upload --api-url http://localhost:8080
```

### Проверка парсинга перед загрузкой

```bash
# Сначала посмотрите что распарсится
python utils/hand_history_parser.py hands.txt

# Если всё хорошо - загрузите
python utils/hand_history_parser.py hands.txt --upload
```

### Массовая загрузка

```bash
# Обработать все файлы в папке
for file in hand_histories/*.txt; do
    python utils/hand_history_parser.py "$file" --upload --api-url http://localhost:8080
done
```

## Troubleshooting

### Ошибка "Не удалось распарсить раздачи"

- Проверьте формат файла (должен быть PokerStars Hand History)
- Убедитесь что файл содержит полные раздачи (не обрезан)
- Проверьте кодировку файла (должна быть UTF-8)

### Ошибка загрузки в API

- Проверьте что API запущено (`docker-compose ps`)
- Проверьте URL API
- Проверьте API ключ (если используется)

### Раздачи не загружаются

- Если используется `skip_existing=True`, существующие раздачи будут пропущены
- Проверьте что `hand_id` уникальны
- Посмотрите логи API: `docker-compose logs api`

## Расширение парсера

Чтобы добавить поддержку нового покер-рума:

1. Добавьте метод `_parse_ROOMNAME` в класс `HandHistoryParser`
2. Зарегистрируйте его в `self.parsers`
3. Реализуйте парсинг в формат API

```python
def _parse_888poker(self, content: str) -> List[Dict[str, Any]]:
    """Парсит 888poker hand history"""
    hands = []
    
    # Ваша логика парсинга
    # ...
    
    return hands
```

## API Endpoint

Парсер использует bulk endpoint для загрузки:

```
POST /api/v1/hands/bulk
Content-Type: application/json

{
  "hands": [
    {
      "hand_id": "PS_123456789",
      "table_id": "TableName",
      "limit_type": "NL10",
      ...
    }
  ],
  "skip_existing": true
}
```

## Производительность

- Парсинг: ~1000 раздач/сек
- Загрузка: зависит от API (обычно 100-500 раздач/сек)
- Рекомендуется загружать файлы пакетами по 1000-5000 раздач

## Лицензия

Этот парсер является частью poker_rake_bot проекта.
