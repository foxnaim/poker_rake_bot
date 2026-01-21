"""Prometheus метрики для мониторинга"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response
from fastapi.responses import PlainTextResponse

# HTTP метрики
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)

# Decision метрики
decision_latency_seconds = Histogram(
    'decision_latency_seconds',
    'Decision latency',
    ['limit_type', 'street'],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
)

decisions_total = Counter(
    'decisions_total',
    'Total decisions made',
    ['limit_type', 'action']
)

# Bot статистика
bot_vpip = Gauge(
    'bot_vpip',
    'Bot VPIP percentage',
    ['limit_type', 'session_id']
)

bot_pfr = Gauge(
    'bot_pfr',
    'Bot PFR percentage',
    ['limit_type', 'session_id']
)

bot_aggression_factor = Gauge(
    'bot_aggression_factor',
    'Bot Aggression Factor',
    ['limit_type', 'session_id']
)

bot_winrate_bb_100 = Gauge(
    'bot_winrate_bb_100',
    'Bot winrate in bb/100',
    ['limit_type', 'session_id']
)

bot_hands_played_total = Counter(
    'bot_hands_played_total',
    'Total hands played',
    ['limit_type', 'session_id']
)

bot_rake_per_hour = Gauge(
    'bot_rake_per_hour',
    'Rake per hour',
    ['limit_type', 'session_id']
)

bot_rake_100 = Gauge(
    'bot_rake_100',
    'Rake per 100 hands',
    ['limit_type', 'session_id']
)

bot_profit_bb_100 = Gauge(
    'bot_profit_bb_100',
    'Profit in bb/100',
    ['limit_type', 'session_id']
)

bot_hands_per_hour = Gauge(
    'bot_hands_per_hour',
    'Hands per hour',
    ['limit_type', 'session_id']
)

# Week 3: Agent метрики
agent_online = Gauge(
    'agent_online',
    'Agent online status (1=online, 0=offline)',
    ['agent_id']
)

agent_heartbeat_lag_seconds = Gauge(
    'agent_heartbeat_lag_seconds',
    'Seconds since last heartbeat',
    ['agent_id']
)

agent_errors_total = Counter(
    'agent_errors_total',
    'Total agent errors',
    ['agent_id', 'error_type']
)

# Week 3: Session метрики
session_active = Gauge(
    'session_active',
    'Active sessions count',
    ['limit_type']
)

session_hands_total = Counter(
    'session_hands_total',
    'Total hands in session',
    ['session_id', 'limit_type']
)

session_profit_total = Gauge(
    'session_profit_total',
    'Total profit in session',
    ['session_id', 'limit_type']
)

session_rake_total = Gauge(
    'session_rake_total',
    'Total rake in session',
    ['session_id', 'limit_type']
)

# Week 3: Decision метрики (расширенные)
decision_errors_total = Counter(
    'decision_errors_total',
    'Total decision errors',
    ['limit_type', 'error_type']
)

decision_p95_latency_seconds = Histogram(
    'decision_p95_latency_seconds',
    'Decision latency p95',
    ['limit_type'],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
)

decision_p99_latency_seconds = Histogram(
    'decision_p99_latency_seconds',
    'Decision latency p99',
    ['limit_type'],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)

# Cache метрики
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_requests_total = Counter(
    'cache_requests_total',
    'Total cache requests',
    ['cache_type']
)


def get_metrics():
    """Возвращает метрики Prometheus"""
    return generate_latest()


def update_bot_stats_metrics(stats, limit_type: str, session_id: str = "default"):
    """Обновляет метрики статистики бота"""
    bot_vpip.labels(limit_type=limit_type, session_id=session_id).set(stats.vpip)
    bot_pfr.labels(limit_type=limit_type, session_id=session_id).set(stats.pfr)
    bot_aggression_factor.labels(limit_type=limit_type, session_id=session_id).set(stats.aggression_factor)
    bot_winrate_bb_100.labels(limit_type=limit_type, session_id=session_id).set(stats.winrate_bb_100)
    bot_hands_played_total.labels(limit_type=limit_type, session_id=session_id).inc(stats.hands_played)
    bot_rake_per_hour.labels(limit_type=limit_type, session_id=session_id).set(stats.rake_per_hour)


def get_metric_value(metric, labels=None):
    """
    Получает текущее значение метрики
    
    Args:
        metric: Prometheus метрика (Gauge, Counter, Histogram)
        labels: Словарь с лейблами
        
    Returns:
        Значение метрики или 0.0
    """
    try:
        if labels:
            labeled_metric = metric.labels(**labels)
        else:
            labeled_metric = metric
        
        # Для Gauge
        if hasattr(labeled_metric, '_value'):
            return float(labeled_metric._value._value) if hasattr(labeled_metric._value, '_value') else float(labeled_metric._value)
        
        # Для Counter
        if hasattr(labeled_metric, '_value'):
            return float(labeled_metric._value._value) if hasattr(labeled_metric._value, '_value') else float(labeled_metric._value)
        
        # Для Histogram (возвращаем среднее)
        if hasattr(labeled_metric, '_sum') and hasattr(labeled_metric, '_count'):
            count = float(labeled_metric._count._value) if hasattr(labeled_metric._count, '_value') else float(labeled_metric._count)
            if count > 0:
                sum_val = float(labeled_metric._sum._value) if hasattr(labeled_metric._sum, '_value') else float(labeled_metric._sum)
                return sum_val / count
        
        return 0.0
    except Exception:
        return 0.0
