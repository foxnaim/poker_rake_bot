# 📊 Grafana + Prometheus Setup Guide

## 🚀 Быстрый старт

### 1. Запуск (уже запущено!)

```bash
docker-compose up -d prometheus grafana
```

Образы загружаются (может занять 2-3 минуты при первом запуске).

### 2. Доступ

После запуска откройте в браузере:

**Grafana:** http://localhost:3001
- Login: `admin`
- Password: `admin`
- При первом входе попросит сменить пароль (можно пропустить)

**Prometheus:** http://localhost:9090
- Для просмотра сырых метрик

---

## 📈 Первая настройка Grafana

### Шаг 1: Вход
1. Откройте http://localhost:3001
2. Введите `admin` / `admin`
3. (Опционально) Смените пароль или нажмите "Skip"

### Шаг 2: Проверка Data Source
1. Левое меню → ⚙️ Configuration → Data sources
2. Должен быть Prometheus (уже настроен автоматически!)
3. URL: `http://prometheus:9090`
4. Нажмите "Save & Test" → должно быть ✅ "Data source is working"

### Шаг 3: Создание первого Dashboard

#### Вариант A: Импорт готового Dashboard (Рекомендуется)

1. Левое меню → + → Import dashboard
2. Вставьте ID готового dashboard: **3662** (Prometheus 2.0 Stats)
3. Нажмите "Load"
4. Выберите Prometheus data source
5. Нажмите "Import"

**Готово!** Вы увидите графики метрик.

#### Вариант B: Создание своего Dashboard

1. Левое меню → + → Create Dashboard
2. Нажмите "+ Add visualization"
3. Выберите "Prometheus" data source
4. В поле "Metric" введите: `python_info`
5. Нажмите "Run queries"
6. Справа настройте заголовок: "Python Info"
7. Нажмите "Apply"

---

## 🎯 Полезные Метрики для Poker Bot

### Основные метрики (уже доступны из API):

#### 1. HTTP Request Rate (запросов в секунду)
```promql
rate(http_requests_total[1m])
```

#### 2. Average Latency (средняя задержка API)
```promql
rate(http_request_duration_seconds_sum[1m]) / rate(http_request_duration_seconds_count[1m]) * 1000
```

#### 3. Error Rate (процент ошибок)
```promql
rate(http_requests_total{status=~"5.."}[1m]) / rate(http_requests_total[1m]) * 100
```

#### 4. Memory Usage (использование памяти)
```promql
process_resident_memory_bytes / 1024 / 1024
```

#### 5. CPU Usage (использование CPU)
```promql
rate(process_cpu_seconds_total[1m]) * 100
```

### Создание панели с метриками:

1. Dashboard → Add panel
2. Query: `rate(http_requests_total[1m])`
3. Legend: `{{method}} {{path}}`
4. Unit: "requests/sec"
5. Panel title: "API Requests per Second"
6. Apply

Повторите для каждой метрики выше.

---

## 🚨 Настройка Алертов

### Пример: Алерт на высокую латентность

1. Создайте панель с метрикой latency (см. выше)
2. Перейдите на вкладку "Alert"
3. Нажмите "Create alert rule from this panel"
4. Условие: `WHEN avg() OF query(A, 1m, now) IS ABOVE 500`
5. Это значит: "Когда средняя латентность за минуту > 500ms"
6. Настройте уведомления:
   - Email
   - Telegram
   - Slack
   - Webhook
7. Сохраните

### Пример: Алерт на ошибки

```promql
rate(http_requests_total{status=~"5.."}[5m]) > 0.05
```
Означает: "Когда error rate > 5% за последние 5 минут"

---

## 📊 Готовый Dashboard для Poker Bot

Создайте файл `monitoring/poker-bot-dashboard.json`:

```json
{
  "dashboard": {
    "title": "Poker Rake Bot Monitoring",
    "panels": [
      {
        "title": "API Requests/sec",
        "targets": [
          {
            "expr": "rate(http_requests_total[1m])"
          }
        ]
      },
      {
        "title": "Average Latency (ms)",
        "targets": [
          {
            "expr": "rate(http_request_duration_seconds_sum[1m]) / rate(http_request_duration_seconds_count[1m]) * 1000"
          }
        ]
      },
      {
        "title": "Error Rate (%)",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[1m]) / rate(http_requests_total[1m]) * 100"
          }
        ]
      },
      {
        "title": "Memory Usage (MB)",
        "targets": [
          {
            "expr": "process_resident_memory_bytes / 1024 / 1024"
          }
        ]
      }
    ]
  }
}
```

Импортируйте: Grafana → + → Import → Upload JSON file

---

## 🔧 Полезные PromQL Запросы

### Топ 10 самых медленных endpoints:
```promql
topk(10,
  rate(http_request_duration_seconds_sum[5m])
  /
  rate(http_request_duration_seconds_count[5m])
)
```

### Количество активных соединений:
```promql
sum(up{job="poker_bot_api"})
```

### Общее количество запросов за день:
```promql
increase(http_requests_total[1d])
```

### 95-й перцентиль латентности:
```promql
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket[5m])
)
```

---

## 🎨 Красивые Dashboards (Импорт готовых)

### Node Exporter Full (если добавите мониторинг хоста):
ID: **1860**

### Docker Container Metrics:
ID: **893**

### FastAPI Monitoring:
ID: **14282**

**Как импортировать:**
1. Grafana → + → Import
2. Вставьте ID
3. Load → Import

---

## 📱 Telegram Уведомления

### Настройка:

1. Создайте Telegram бота через @BotFather
2. Получите токен: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`
3. Узнайте свой chat_id через @userinfobot

4. В Grafana:
   - Settings → Alerting → Contact points
   - New contact point
   - Type: Telegram
   - BOT API Token: `ваш_токен`
   - Chat ID: `ваш_chat_id`
   - Save

5. Теперь все алерты будут приходить в Telegram!

---

## 🐛 Troubleshooting

### Grafana не открывается на http://localhost:3001

```bash
# Проверьте статус
docker logs poker_bot_grafana

# Перезапустите
docker restart poker_bot_grafana
```

### Prometheus показывает "Target Down"

```bash
# Проверьте, работает ли API
curl http://localhost:8000/metrics

# Проверьте конфигурацию
docker exec poker_bot_prometheus cat /etc/prometheus/prometheus.yml

# Перезапустите
docker restart poker_bot_prometheus
```

### Нет метрик от API

Убедитесь что API endpoint `/metrics` доступен:
```bash
curl http://localhost:8000/metrics
```

Должны видеть строки вроде:
```
python_gc_objects_collected_total{generation="0"} 7828.0
...
```

---

## 📖 Дополнительные Ресурсы

**Grafana Docs:** https://grafana.com/docs/grafana/latest/

**PromQL Tutorial:** https://prometheus.io/docs/prometheus/latest/querying/basics/

**Dashboard Library:** https://grafana.com/grafana/dashboards/

**Telegram Notifications:** https://grafana.com/docs/grafana/latest/alerting/configure-notifications/telegram/

---

## ✅ Checklist Первой Настройки

- [ ] Открыл Grafana на http://localhost:3001
- [ ] Вошел (admin/admin)
- [ ] Проверил Data Source (Prometheus)
- [ ] Импортировал готовый dashboard (ID: 3662)
- [ ] Создал панель с метрикой API requests/sec
- [ ] Создал панель с метрикой latency
- [ ] Настроил алерт на высокую латентность (> 500ms)
- [ ] (Опционально) Настроил Telegram уведомления

---

**Готово!** Теперь у вас есть полный мониторинг poker_rake_bot в реальном времени! 🎉
