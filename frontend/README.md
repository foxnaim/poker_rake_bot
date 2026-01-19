# Frontend Dashboard

React приложение для мониторинга покерного бота в реальном времени.

## Установка

```bash
cd frontend
npm install
```

## Запуск

```bash
# Development
npm start

# Production build
npm run build
```

## Структура

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.tsx      # Главный дашборд
│   │   ├── LiveStats.tsx      # Real-time статистика
│   │   ├── DecisionFeed.tsx   # Лента решений
│   │   └── MetricsChart.tsx   # Графики метрик
│   ├── hooks/
│   │   └── useWebSocket.ts    # WebSocket hook
│   ├── services/
│   │   └── api.ts             # API клиент
│   ├── App.tsx
│   └── index.tsx
├── public/
│   └── index.html
└── package.json
```

## WebSocket подключение

Dashboard автоматически подключается к `ws://localhost:8000/ws/live` и получает:
- Статистику (каждые 5 секунд)
- Решения в реальном времени
- Результаты раздач

## Компоненты

### Dashboard
Главный компонент, объединяет все остальные.

### LiveStats
Отображает:
- Winrate (NL10, NL50)
- Hands per hour
- Average latency
- Requests per second

### DecisionFeed
Показывает последние 10 решений с:
- Временем
- Действием
- Размером ставки
- Метаданными

### MetricsChart
Визуализирует метрики производительности через прогресс-бары.

## Настройка

Создайте `.env` файл:
```
REACT_APP_API_URL=http://localhost:8000
```

## Docker

```bash
# Через docker-compose
docker-compose up dashboard

# Или отдельно
cd frontend
docker build -t poker-bot-dashboard .
docker run -p 3000:3000 poker-bot-dashboard
```
