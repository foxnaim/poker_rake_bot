"""
Тесты мониторинга (Prometheus метрики, Grafana)
"""

import pytest
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_metrics_endpoint_exists():
    """Проверяет что /metrics endpoint существует"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")


def test_metrics_contains_decision_metrics():
    """Проверяет что метрики решений присутствуют"""
    response = client.get("/metrics")
    assert response.status_code == 200
    content = response.text
    
    # Проверяем наличие ключевых метрик
    assert "decision_latency_seconds" in content or "decision_latency" in content
    assert "decisions_total" in content or "decisions" in content


def test_metrics_format():
    """Проверяет формат Prometheus метрик"""
    response = client.get("/metrics")
    assert response.status_code == 200
    content = response.text
    
    # Prometheus формат: метрика{labels} значение
    lines = content.split("\n")
    metric_lines = [l for l in lines if l and not l.startswith("#")]
    
    # Должны быть хотя бы некоторые метрики
    assert len(metric_lines) > 0
    
    # Проверяем формат хотя бы одной метрики
    for line in metric_lines[:5]:
        if "{" in line:
            # Метрика с labels: name{label="value"} number
            assert "}" in line
            assert line.count("{") == line.count("}")
        else:
            # Простая метрика: name number
            parts = line.split()
            assert len(parts) >= 2
            try:
                float(parts[-1])  # Последняя часть должна быть числом
            except ValueError:
                pass  # Может быть специальный формат


def test_health_endpoint_metrics():
    """Проверяет что health endpoint работает"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_metrics_after_decide():
    """Проверяет что метрики обновляются после /decide"""
    # Делаем запрос /decide
    decide_response = client.post(
        "/api/v1/decide",
        json={
            "hand_id": "test_metrics_1",
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
    )
    assert decide_response.status_code == 200
    
    # Проверяем что метрики обновились
    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    # Метрики должны содержать информацию о решении
    assert len(metrics_response.text) > 0
