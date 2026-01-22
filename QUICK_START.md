# Быстрый старт (5 минут)

## 1. Установка

```bash
cd poker_rake_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make check-deps
```

## 2. Запуск API

```bash
# В одном терминале
make run
```

API будет доступен на `http://localhost:8000`

## 3. Проверка

```bash
# В другом терминале
make smoke
```

Ожидаемый вывод:
```
OK
health: ok
decide.action: fold table_key: table_1
log_hand.status: logged table_key: table_1
```

## 4. Тесты

```bash
# Все тесты
make test

# Только E2E тест (полный операторский flow)
make test-e2e
```

## 5. Операторский сценарий

См. [CHECKLIST.md](CHECKLIST.md) → секция "Операторский сценарий"

---

**Готово!** Проект работает. 🎉
