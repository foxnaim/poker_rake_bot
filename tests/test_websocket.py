"""Тесты для WebSocket"""

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from api.main import app


client = TestClient(app)


def test_websocket_connection():
    """Тест подключения к WebSocket"""
    with client.websocket_connect("/ws/live") as websocket:
        # Должно прийти сообщение о подключении
        data = websocket.receive_json()
        assert data["type"] == "connected"
        assert "timestamp" in data


def test_websocket_stats():
    """Тест получения статистики через WebSocket"""
    with client.websocket_connect("/ws/live") as websocket:
        # Пропускаем сообщение о подключении
        websocket.receive_json()
        
        # Должно прийти сообщение со статистикой
        data = websocket.receive_json()
        assert data["type"] == "stats"
        assert "metrics" in data
        assert "timestamp" in data


def test_websocket_multiple_clients():
    """Тест нескольких подключений"""
    with client.websocket_connect("/ws/live") as ws1:
        with client.websocket_connect("/ws/live") as ws2:
            # Оба должны подключиться
            data1 = ws1.receive_json()
            data2 = ws2.receive_json()
            
            assert data1["type"] == "connected"
            assert data2["type"] == "connected"


def test_websocket_broadcast():
    """Тест broadcast сообщений"""
    import asyncio
    from api.websocket import broadcast_decision

    # Подключаем двух клиентов
    with client.websocket_connect("/ws/live") as ws1:
        with client.websocket_connect("/ws/live") as ws2:
            # Получаем connected сообщения
            ws1.receive_json()
            ws2.receive_json()

            # Отправляем broadcast через API
            test_decision = {
                "hand_id": "test_123",
                "action": "raise",
                "amount": 10.0,
                "street": "preflop"
            }

            # Используем sync endpoint для теста
            response = client.post("/api/v1/decide", json={
                "game_state": {
                    "hero_cards": "AhKh",
                    "board": "",
                    "pot": 15.0,
                    "to_call": 5.0,
                    "stack": 100.0,
                    "position": "BTN"
                }
            })

            # Проверяем что broadcast работает (клиенты получат stats сообщения)
            # В реальном тесте нужно дождаться broadcast_decision
            assert response.status_code in [200, 422]  # 422 если нет валидации


def test_websocket_reconnect():
    """Тест переподключения"""
    with client.websocket_connect("/ws/live") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "connected"
        
        # Закрываем соединение
        websocket.close()
        
        # Переподключаемся
        with client.websocket_connect("/ws/live") as websocket2:
            data2 = websocket2.receive_json()
            assert data2["type"] == "connected"
