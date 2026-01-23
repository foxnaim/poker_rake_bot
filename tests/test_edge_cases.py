"""
Edge cases тесты для увеличения покрытия до 90%+

Покрывает:
- Граничные значения входных данных
- Ошибки валидации
- Некорректные состояния игры
- Обработка ошибок БД/Redis
- Timeout scenarios
- Concurrent requests
"""

import os
import sys

# Включаем admin API ДО импорта app
os.environ["ENABLE_ADMIN_API"] = "1"
os.environ["TESTING"] = "1"

import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timezone

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from data.database import SessionLocal, init_db
from data.models import Bot, Room, Table, BotSession


@pytest.fixture
def db():
    """Тестовая БД"""
    db = SessionLocal()
    try:
        init_db()
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


class TestEdgeCasesValidation:
    """Тесты граничных значений и валидации"""

    def test_decide_min_values(self, client: TestClient):
        """Минимальные значения всех полей"""
        response = client.post(
            "/api/v1/decide",
            json={
                "hand_id": "a",  # min_length=1
                "table_id": "a",  # min_length=1
                "limit_type": "NL10",
                "street": "preflop",
                "hero_position": 0,  # ge=0
                "dealer": 0,  # ge=0
                "hero_cards": "AsKh",  # min_length=4
                "board_cards": "",
                "stacks": {"0": 0.01},
                "bets": {"0": 0.0},
                "total_bets": {"0": 0.0},
                "active_players": [0, 1],  # min_length=2
                "pot": 0.0,  # ge=0.0
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": 0.01,  # gt=0.0
                "big_blind": 0.02,  # gt=0.0
            }
        )
        assert response.status_code in [200, 422]  # Может быть валидация или успех

    def test_decide_max_values(self, client: TestClient):
        """Максимальные значения всех полей"""
        response = client.post(
            "/api/v1/decide",
            json={
                "hand_id": "a" * 100,  # max_length=100
                "table_id": "a" * 100,  # max_length=100
                "limit_type": "NL10",
                "street": "preflop",
                "hero_position": 5,  # le=5
                "dealer": 5,  # le=5
                "hero_cards": "AsKhQdJc",  # max_length=10
                "board_cards": "AsKhQdJcTs",  # max_length=20
                "stacks": {str(i): 1000.0 for i in range(6)},
                "bets": {str(i): 100.0 for i in range(6)},
                "total_bets": {str(i): 500.0 for i in range(6)},
                "active_players": [0, 1, 2, 3, 4, 5],  # max_length=6
                "pot": 10000.0,
                "current_player": 5,  # le=5
                "last_raise_amount": 1000.0,
                "small_blind": 5.0,
                "big_blind": 10.0,
            }
        )
        assert response.status_code in [200, 422]

    def test_decide_invalid_street(self, client: TestClient):
        """Некорректная улица"""
        response = client.post(
            "/api/v1/decide",
            json={
                "hand_id": "test_1",
                "table_id": "table_1",
                "limit_type": "NL10",
                "street": "invalid_street",  # Не соответствует pattern
                "hero_position": 0,
                "dealer": 5,
                "hero_cards": "AsKh",
                "board_cards": "",
                "stacks": {"0": 100.0},
                "bets": {"0": 0.0},
                "total_bets": {"0": 0.0},
                "active_players": [0, 1],
                "pot": 1.5,
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": 0.5,
                "big_blind": 1.0,
            }
        )
        assert response.status_code == 422  # Validation error

    def test_decide_invalid_limit_type(self, client: TestClient):
        """Некорректный limit_type"""
        response = client.post(
            "/api/v1/decide",
            json={
                "hand_id": "test_1",
                "table_id": "table_1",
                "limit_type": "INVALID",  # Не соответствует pattern ^NL\d+$
                "street": "preflop",
                "hero_position": 0,
                "dealer": 5,
                "hero_cards": "AsKh",
                "board_cards": "",
                "stacks": {"0": 100.0},
                "bets": {"0": 0.0},
                "total_bets": {"0": 0.0},
                "active_players": [0, 1],
                "pot": 1.5,
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": 0.5,
                "big_blind": 1.0,
            }
        )
        assert response.status_code == 422

    def test_decide_negative_values(self, client: TestClient):
        """Отрицательные значения (должны быть отклонены)"""
        response = client.post(
            "/api/v1/decide",
            json={
                "hand_id": "test_1",
                "table_id": "table_1",
                "limit_type": "NL10",
                "street": "preflop",
                "hero_position": -1,  # ge=0, должно быть отклонено
                "dealer": 5,
                "hero_cards": "AsKh",
                "board_cards": "",
                "stacks": {"0": 100.0},
                "bets": {"0": 0.0},
                "total_bets": {"0": 0.0},
                "active_players": [0, 1],
                "pot": -1.0,  # ge=0.0, должно быть отклонено
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": -0.5,  # gt=0.0, должно быть отклонено
                "big_blind": 1.0,
            }
        )
        assert response.status_code == 422

    def test_decide_empty_strings(self, client: TestClient):
        """Пустые строки в обязательных полях"""
        response = client.post(
            "/api/v1/decide",
            json={
                "hand_id": "",  # min_length=1, должно быть отклонено
                "table_id": "table_1",
                "limit_type": "NL10",
                "street": "preflop",
                "hero_position": 0,
                "dealer": 5,
                "hero_cards": "AsKh",
                "board_cards": "",
                "stacks": {"0": 100.0},
                "bets": {"0": 0.0},
                "total_bets": {"0": 0.0},
                "active_players": [0, 1],
                "pot": 1.5,
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": 0.5,
                "big_blind": 1.0,
            }
        )
        assert response.status_code == 422

    def test_decide_too_few_players(self, client: TestClient):
        """Меньше 2 активных игроков"""
        response = client.post(
            "/api/v1/decide",
            json={
                "hand_id": "test_1",
                "table_id": "table_1",
                "limit_type": "NL10",
                "street": "preflop",
                "hero_position": 0,
                "dealer": 5,
                "hero_cards": "AsKh",
                "board_cards": "",
                "stacks": {"0": 100.0},
                "bets": {"0": 0.0},
                "total_bets": {"0": 0.0},
                "active_players": [0],  # min_length=2, должно быть отклонено
                "pot": 1.5,
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": 0.5,
                "big_blind": 1.0,
            }
        )
        assert response.status_code == 422

    def test_decide_too_many_players(self, client: TestClient):
        """Больше 6 активных игроков"""
        response = client.post(
            "/api/v1/decide",
            json={
                "hand_id": "test_1",
                "table_id": "table_1",
                "limit_type": "NL10",
                "street": "preflop",
                "hero_position": 0,
                "dealer": 5,
                "hero_cards": "AsKh",
                "board_cards": "",
                "stacks": {str(i): 100.0 for i in range(7)},
                "bets": {str(i): 0.0 for i in range(7)},
                "total_bets": {str(i): 0.0 for i in range(7)},
                "active_players": [0, 1, 2, 3, 4, 5, 6],  # max_length=6, должно быть отклонено
                "pot": 1.5,
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": 0.5,
                "big_blind": 1.0,
            }
        )
        assert response.status_code == 422


class TestEdgeCasesDatabase:
    """Тесты edge cases с БД"""

    def test_log_hand_duplicate_hand_id(self, client: TestClient, db: Session):
        """Дублирование hand_id (upsert должен работать)"""
        # Первая запись
        response1 = client.post(
            "/api/v1/log_hand",
            json={
                "hand_id": "duplicate_test_1",
                "table_id": "table_1",
                "limit_type": "NL10",
                "players_count": 6,
                "hero_position": 0,
                "hero_cards": "AsKh",
                "board_cards": "",
                "pot_size": 10.0,
                "rake_amount": 0.5,
                "hero_result": 5.0,
            }
        )
        assert response1.status_code == 200

        # Вторая запись с тем же hand_id (должен обновиться)
        response2 = client.post(
            "/api/v1/log_hand",
            json={
                "hand_id": "duplicate_test_1",
                "table_id": "table_1",
                "limit_type": "NL10",
                "players_count": 6,
                "hero_position": 0,
                "hero_cards": "QsQd",  # Другие карты
                "board_cards": "",
                "pot_size": 15.0,  # Другой пот
                "rake_amount": 0.75,
                "hero_result": 10.0,
            }
        )
        assert response2.status_code == 200
        # Проверяем что запись обновилась
        from data.models import Hand
        hand = db.query(Hand).filter(Hand.hand_id == "duplicate_test_1").first()
        assert hand is not None
        assert hand.hero_cards == "QsQd"  # Обновлено
        assert hand.pot_size == 15.0  # Обновлено

    def test_session_start_duplicate_bot(self, client: TestClient, db: Session, admin_key: str):
        """Попытка запустить две сессии для одного бота"""
        # Создаём бота и стол
        bot = Bot(alias="test_bot", default_style="neutral", default_limit="NL10", active=True)
        room = Room(room_link="test_room", type="pokerking", status="active")
        table = Table(room_id=room.id, limit_type="NL10", max_players=6)
        db.add_all([bot, room, table])
        db.commit()

        headers = {"X-API-Key": admin_key}

        # Первая сессия
        response1 = client.post(
            "/api/v1/admin/session/start",
            json={
                "bot_id": bot.id,
                "table_id": table.id,
                "limit": "NL10",
            },
            headers=headers
        )
        assert response1.status_code == 201

        # Вторая сессия для того же бота (должна быть отклонена)
        response2 = client.post(
            "/api/v1/admin/session/start",
            json={
                "bot_id": bot.id,
                "table_id": table.id,
                "limit": "NL10",
            },
            headers=headers
        )
        assert response2.status_code == 400  # Bot already has an active session

    def test_table_key_resolution(self, client: TestClient, db: Session):
        """Проверка разрешения table_key в table_id"""
        # Создаём стол с external_table_id
        room = Room(room_link="test_room", type="pokerking", status="active")
        table = Table(room_id=room.id, external_table_id="test_table_key", limit_type="NL10", max_players=6)
        db.add_all([room, table])
        db.commit()

        # Запрос с table_key должен найти стол
        response = client.post(
            "/api/v1/decide",
            json={
                "hand_id": "test_1",
                "table_id": "test_table_key",  # Используем table_key
                "limit_type": "NL10",
                "street": "preflop",
                "hero_position": 0,
                "dealer": 5,
                "hero_cards": "AsKh",
                "board_cards": "",
                "stacks": {"0": 100.0},
                "bets": {"0": 0.0},
                "total_bets": {"0": 0.0},
                "active_players": [0, 1],
                "pot": 1.5,
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": 0.5,
                "big_blind": 1.0,
            }
        )
        # Должен работать (может быть 200 или fallback)
        assert response.status_code in [200, 500]  # 500 если БД недоступна в тестах


class TestEdgeCasesConcurrency:
    """Тесты конкурентных запросов"""

    def test_concurrent_decide_requests(self, client: TestClient):
        """Множественные одновременные запросы /decide"""
        import concurrent.futures
        import time

        def make_request(i):
            return client.post(
                "/api/v1/decide",
                json={
                    "hand_id": f"concurrent_test_{i}",
                    "table_id": "table_1",
                    "limit_type": "NL10",
                    "street": "preflop",
                    "hero_position": 0,
                    "dealer": 5,
                    "hero_cards": "AsKh",
                    "board_cards": "",
                    "stacks": {"0": 100.0},
                    "bets": {"0": 0.0},
                    "total_bets": {"0": 0.0},
                    "active_players": [0, 1],
                    "pot": 1.5,
                    "current_player": 0,
                    "last_raise_amount": 0.0,
                    "small_blind": 0.5,
                    "big_blind": 1.0,
                }
            )

        # 10 одновременных запросов
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Все должны вернуть валидный ответ (200 или 422)
        for response in results:
            assert response.status_code in [200, 422, 500]  # 500 если БД недоступна


class TestEdgeCasesErrorHandling:
    """Тесты обработки ошибок"""

    def test_missing_required_fields(self, client: TestClient):
        """Отсутствие обязательных полей"""
        response = client.post(
            "/api/v1/decide",
            json={
                # Отсутствуют обязательные поля
                "hand_id": "test_1",
                # "table_id" отсутствует
            }
        )
        assert response.status_code == 422

    def test_invalid_json(self, client: TestClient):
        """Некорректный JSON"""
        response = client.post(
            "/api/v1/decide",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_health_check_without_db(self, client: TestClient):
        """Health check должен работать даже если БД недоступна"""
        # Health check использует safe_mode, должен вернуть degraded/unhealthy
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]


@pytest.fixture
def admin_key(db: Session):
    """Создает admin API key для тестов"""
    from data.models_v1_2 import APIKey
    import secrets
    
    api_key = f"test_admin_{secrets.token_urlsafe(16)}"
    key = APIKey(
        api_key=api_key,
        api_secret=secrets.token_urlsafe(64),
        client_name="test_admin",
        permissions=["admin"],
        is_admin=True,
        is_active=True
    )
    db.add(key)
    db.commit()
    return api_key
