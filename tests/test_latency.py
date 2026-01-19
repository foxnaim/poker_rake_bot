"""Тесты латентности API"""

import pytest
import time
import statistics
import asyncio
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_single_request_latency():
    """Тест латентности одного запроса"""
    request_data = {
        "hand_id": "test_1",
        "table_id": "table_1",
        "limit_type": "NL10",
        "street": "preflop",
        "hero_position": 0,
        "dealer": 5,
        "hero_cards": "AsKh",
        "board_cards": "",
        "stacks": {"0": "100.0", "1": "100.0"},
        "bets": {"0": "0.0", "1": "1.0"},
        "total_bets": {"0": "0.0", "1": "1.0"},
        "active_players": [0, 1],
        "pot": 1.5,
        "current_player": 0,
        "last_raise_amount": 1.0,
        "small_blind": 0.5,
        "big_blind": 1.0
    }
    
    start = time.time()
    response = client.post("/api/v1/decide", json=request_data)
    latency_ms = (time.time() - start) * 1000
    
    assert response.status_code == 200
    assert latency_ms < 500  # Один запрос должен быть быстрым
    print(f"Single request latency: {latency_ms:.2f}ms")


def test_batch_latency():
    """Тест латентности батча запросов"""
    request_data = {
        "hand_id": "test_batch",
        "table_id": "table_1",
        "limit_type": "NL10",
        "street": "preflop",
        "hero_position": 0,
        "dealer": 5,
        "hero_cards": "AsKh",
        "board_cards": "",
        "stacks": {"0": "100.0", "1": "100.0"},
        "bets": {"0": "0.0", "1": "1.0"},
        "total_bets": {"0": "0.0", "1": "1.0"},
        "active_players": [0, 1],
        "pot": 1.5,
        "current_player": 0,
        "last_raise_amount": 1.0,
        "small_blind": 0.5,
        "big_blind": 1.0
    }
    
    latencies = []
    num_requests = 100
    
    for i in range(num_requests):
        request_data["hand_id"] = f"test_{i}"
        start = time.time()
        response = client.post("/api/v1/decide", json=request_data)
        latency_ms = (time.time() - start) * 1000
        
        assert response.status_code == 200
        latencies.append(latency_ms)
    
    # Статистика
    avg_latency = statistics.mean(latencies)
    p50_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95-й перцентиль
    p99_latency = statistics.quantiles(latencies, n=100)[98]  # 99-й перцентиль
    
    print(f"\nLatency statistics ({num_requests} requests):")
    print(f"  Average: {avg_latency:.2f}ms")
    print(f"  P50 (median): {p50_latency:.2f}ms")
    print(f"  P95: {p95_latency:.2f}ms")
    print(f"  P99: {p99_latency:.2f}ms")
    
    # Проверяем требования (P95 < 200ms)
    assert p95_latency < 200, f"P95 latency {p95_latency:.2f}ms exceeds 200ms"
    assert p99_latency < 500, f"P99 latency {p99_latency:.2f}ms exceeds 500ms"


def test_concurrent_latency():
    """Тест латентности при конкурентных запросах"""
    request_data = {
        "hand_id": "test_concurrent",
        "table_id": "table_1",
        "limit_type": "NL10",
        "street": "preflop",
        "hero_position": 0,
        "dealer": 5,
        "hero_cards": "AsKh",
        "board_cards": "",
        "stacks": {"0": "100.0", "1": "100.0"},
        "bets": {"0": "0.0", "1": "1.0"},
        "total_bets": {"0": "0.0", "1": "1.0"},
        "active_players": [0, 1],
        "pot": 1.5,
        "current_player": 0,
        "last_raise_amount": 1.0,
        "small_blind": 0.5,
        "big_blind": 1.0
    }
    
    async def make_request(i):
        request_data["hand_id"] = f"test_{i}"
        response = client.post("/api/v1/decide", json=request_data)
        return response.status_code == 200
    
    # Запускаем 10 конкурентных запросов
    async def run_concurrent():
        tasks = [make_request(i) for i in range(10)]
        return await asyncio.gather(*tasks)
    
    results = asyncio.run(run_concurrent())
    assert all(results), "Some concurrent requests failed"


def test_health_check_latency():
    """Тест латентности health check"""
    start = time.time()
    response = client.get("/api/v1/health")
    latency_ms = (time.time() - start) * 1000
    
    assert response.status_code == 200
    assert latency_ms < 10  # Health check должен быть очень быстрым
    print(f"Health check latency: {latency_ms:.2f}ms")
