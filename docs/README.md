# PokerBot v1.3 Documentation

## Документация

| Документ | Описание |
|----------|----------|
| [OPERATOR_MANUAL.md](OPERATOR_MANUAL.md) | Руководство оператора - как использовать систему |
| [TECHNICAL_MANUAL.md](TECHNICAL_MANUAL.md) | Техническое руководство - архитектура и API |

## Quick Links

### Для операторов
- [Быстрый старт](OPERATOR_MANUAL.md#быстрый-старт)
- [Добавление комнаты](OPERATOR_MANUAL.md#добавление-комнаты)
- [Управление сессиями](OPERATOR_MANUAL.md#управление-сессиями)
- [Мониторинг](OPERATOR_MANUAL.md#мониторинг)

### Для разработчиков
- [Архитектура](TECHNICAL_MANUAL.md#архитектура)
- [Схема БД](TECHNICAL_MANUAL.md#схема-базы-данных)
- [Протокол агентов](TECHNICAL_MANUAL.md#протокол-агентов)
- [API Reference](TECHNICAL_MANUAL.md#api-reference)

## Версия

Текущая версия: **1.3.0**

## Поддержка

При возникновении проблем:
1. Проверьте [раздел алертов](OPERATOR_MANUAL.md#алерты-и-проблемы)
2. Изучите логи: `docker-compose logs -f api`
3. Проверьте health: `curl http://localhost:8000/api/v1/health`
