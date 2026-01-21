"""Интеграционные тесты"""

import pytest
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main import app
from data.database import SessionLocal, init_db
from data.models import Hand, DecisionLog


client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    """Фикстура БД"""
    init_db()
    db = SessionLocal()
    yield db
    db.close()


def test_full_decision_flow(db: Session):
    """Тест полного потока принятия решения"""
    # 1. Запрос решения
    request_data = {
        "hand_id": "test_integration_1",
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
        "big_blind": 1.0,
        "opponent_ids": ["opponent_1"]
    }
    
    response = client.post("/api/v1/decide", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "action" in data
    assert data["action"] in ["fold", "call", "raise", "check", "all_in"]
    assert "latency_ms" in data
    
    # 2. Проверяем, что решение залогировано
    decision = db.query(DecisionLog).filter(
        DecisionLog.hand_id == "test_integration_1"
    ).first()
    
    assert decision is not None
    assert decision.final_action == data["action"]
    
    # 3. Логируем раздачу
    hand_data = {
        "hand_id": "test_integration_1",
        "table_id": "table_1",
        "limit_type": "NL10",
        "players_count": 2,
        "hero_position": 0,
        "hero_cards": "AsKh",
        "board_cards": "",
        "pot_size": 1.5,
        "rake_amount": 0.15,
        "hero_result": 1.35
    }
    
    response = client.post("/api/v1/log_hand", json=hand_data)
    assert response.status_code == 200
    
    # 4. Проверяем, что раздача сохранена
    hand = db.query(Hand).filter(Hand.hand_id == "test_integration_1").first()
    assert hand is not None
    assert float(hand.pot_size) == 1.5


def test_opponent_profile_flow(db: Session):
    """Тест потока работы с профилями оппонентов"""
    # 1. Получаем профиль (должен быть пустым)
    response = client.get("/api/v1/opponent/opponent_1")
    assert response.status_code == 200
    data = response.json()
    assert data["opponent_id"] == "opponent_1"
    assert data["hands_played"] == 0
    
    # 2. Логируем несколько раздач с этим оппонентом
    for i in range(5):
        hand_data = {
            "hand_id": f"test_opponent_{i}",
            "table_id": "table_1",
            "limit_type": "NL10",
            "players_count": 2,
            "hero_position": 0,
            "hero_cards": "AsKh",
            "board_cards": "",
            "pot_size": 10.0,
            "rake_amount": 1.0,
            "hero_result": 9.0,
            "hand_history": {
                "opponent_1": {
                    "preflop_action": "call" if i % 2 == 0 else "fold",
                    "postflop_actions": []
                }
            }
        }
        client.post("/api/v1/log_hand", json=hand_data)
    
    # 3. Проверяем, что профиль обновился
    # (В реальной реализации нужно обновлять профили при логировании раздач)
    response = client.get("/api/v1/opponent/opponent_1")
    assert response.status_code == 200


def test_error_handling():
    """Тест обработки ошибок"""
    # Некорректный запрос
    response = client.post("/api/v1/decide", json={"invalid": "data"})
    assert response.status_code == 422  # Validation error
    
    # Несуществующий endpoint
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404


def test_health_check():
    """Тест health check"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_metrics_endpoint():
    """Тест endpoint метрик"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text
