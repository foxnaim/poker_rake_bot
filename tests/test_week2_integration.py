"""
Интеграционные тесты для Week 2 - Операторка
Тестирует полный flow: room → table → bot → config → session
"""

import pytest
from sqlalchemy.orm import Session
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from data.database import SessionLocal, init_db
from data.models import Bot, Room, Table, BotConfig, BotSession, RakeModel
from api.main import app


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


class TestWeek2Integration:
    """Интеграционные тесты для Week 2"""
    
    def test_full_flow(self, client: TestClient, admin_key: str, db: Session):
        """Полный flow: создать room → table → bot → config → session"""
        headers = {"X-API-Key": admin_key}
        
        # 1. Создать комнату
        room_response = client.post(
            "/api/v1/admin/rooms/onboard",
            json={
                "room_link": "https://test-room.com",
                "type": "pokerstars",
                "meta": {"test": True}
            },
            headers=headers
        )
        assert room_response.status_code == 201
        room_id = room_response.json()["id"]
        assert room_response.json()["status"] == "onboarded"
        
        # 2. Создать стол
        table_response = client.post(
            "/api/v1/admin/tables",
            json={
                "room_id": room_id,
                "limit_type": "NL10",
                "max_players": 6
            },
            headers=headers
        )
        assert table_response.status_code == 201
        table_id = table_response.json()["id"]
        
        # 3. Создать бота
        bot_response = client.post(
            "/api/v1/admin/bots",
            json={
                "alias": "test_bot",
                "default_style": "balanced",
                "default_limit": "NL10",
                "active": True
            },
            headers=headers
        )
        assert bot_response.status_code == 201
        bot_id = bot_response.json()["id"]
        
        # 4. Создать конфиг бота
        config_response = client.post(
            "/api/v1/admin/bot-configs",
            json={
                "bot_id": bot_id,
                "name": "test_config",
                "target_vpip": 20.0,
                "target_pfr": 15.0,
                "target_af": 2.0,
                "exploit_weights": {
                    "preflop": 0.3,
                    "flop": 0.4,
                    "turn": 0.5,
                    "river": 0.6
                },
                "is_default": True
            },
            headers=headers
        )
        assert config_response.status_code == 201
        config_id = config_response.json()["id"]
        
        # 5. Создать модель рейка
        rake_response = client.post(
            "/api/v1/admin/rake-models",
            json={
                "room_id": room_id,
                "limit_type": "NL10",
                "percent": 5.0,
                "cap": 3.0,
                "min_pot": 0
            },
            headers=headers
        )
        assert rake_response.status_code == 201
        
        # 6. Запустить сессию
        session_response = client.post(
            "/api/v1/admin/session/start",
            json={
                "bot_id": bot_id,
                "table_id": table_id,
                "limit": "NL10",
                "style": "balanced"
            },
            headers=headers
        )
        assert session_response.status_code == 201
        session_data = session_response.json()
        session_id = session_data["session_id"]
        assert session_data["status"] == "starting"
        assert session_data["bot_config_id"] == config_id  # Должен использоваться default config
        
        # 7. Проверить сессию
        get_session = client.get(
            f"/api/v1/admin/session/{session_id}",
            headers=headers
        )
        assert get_session.status_code == 200
        assert get_session.json()["session_id"] == session_id
        
        # 8. Приостановить сессию
        pause_response = client.post(
            f"/api/v1/admin/session/{session_id}/pause",
            headers=headers
        )
        assert pause_response.status_code == 200
        assert pause_response.json()["status"] == "paused"
        
        # 9. Остановить сессию
        stop_response = client.post(
            f"/api/v1/admin/session/{session_id}/stop",
            headers=headers
        )
        assert stop_response.status_code == 200
        assert stop_response.json()["status"] == "stopped"
        assert stop_response.json()["ended_at"] is not None
        
        # 10. Проверить список сессий
        sessions_list = client.get(
            "/api/v1/admin/sessions/recent?limit=10",
            headers=headers
        )
        assert sessions_list.status_code == 200
        sessions = sessions_list.json()
        assert len(sessions) > 0
        assert any(s["session_id"] == session_id for s in sessions)
    
    def test_session_id_binding(self, client: TestClient, admin_key: str, db: Session):
        """Проверяет привязку hands и decision_log к session_id"""
        headers = {"X-API-Key": admin_key}
        
        # Создаем минимальный setup
        room = Room(room_link="test", type="test", status="active")
        db.add(room)
        db.commit()
        
        table = Table(room_id=room.id, limit_type="NL10", max_players=6)
        db.add(table)
        db.commit()
        
        bot = Bot(alias="test", default_style="balanced", default_limit="NL10")
        db.add(bot)
        db.commit()
        
        session = BotSession(
            session_id="test_session_123",
            bot_id=bot.id,
            table_id=table.id,
            status="running"
        )
        db.add(session)
        db.commit()
        
        # Проверяем, что session_id есть в таблицах
        from data.models import Hand, DecisionLog
        
        # Создаем тестовую hand с session_id
        hand = Hand(
            hand_id="test_hand_1",
            table_id="test_table",
            limit_type="NL10",
            session_id=session.id,
            players_count=2,
            hero_position=0,
            hero_cards="AsKh",
            pot_size=10.0,
            rake_amount=0.5,
            hero_result=5.0
        )
        db.add(hand)
        db.commit()
        
        # Проверяем привязку
        saved_hand = db.query(Hand).filter(Hand.hand_id == "test_hand_1").first()
        assert saved_hand is not None
        assert saved_hand.session_id == session.id
        
        # Создаем тестовый decision_log с session_id
        decision = DecisionLog(
            hand_id="test_hand_1",
            decision_id="test_decision_1",
            session_id=session.id,
            street="preflop",
            game_state={},
            final_action="call"
        )
        db.add(decision)
        db.commit()
        
        # Проверяем привязку
        saved_decision = db.query(DecisionLog).filter(DecisionLog.decision_id == "test_decision_1").first()
        assert saved_decision is not None
        assert saved_decision.session_id == session.id
    
    def test_crud_operations(self, client: TestClient, admin_key: str):
        """Тестирует CRUD операции для всех сущностей"""
        headers = {"X-API-Key": admin_key}
        
        # Bots CRUD
        bot_create = client.post(
            "/api/v1/admin/bots",
            json={"alias": "crud_test", "default_style": "tight", "default_limit": "NL25"},
            headers=headers
        )
        assert bot_create.status_code == 201
        bot_id = bot_create.json()["id"]
        
        bot_get = client.get(f"/api/v1/admin/bots/{bot_id}", headers=headers)
        assert bot_get.status_code == 200
        assert bot_get.json()["alias"] == "crud_test"
        
        bot_update = client.patch(
            f"/api/v1/admin/bots/{bot_id}",
            json={"default_style": "loose"},
            headers=headers
        )
        assert bot_update.status_code == 200
        assert bot_update.json()["default_style"] == "loose"
        
        # Rooms CRUD
        room_create = client.post(
            "/api/v1/admin/rooms",
            json={"room_link": "https://crud-test.com", "type": "ggpoker"},
            headers=headers
        )
        assert room_create.status_code == 201
        room_id = room_create.json()["id"]
        
        rooms_list = client.get("/api/v1/admin/rooms", headers=headers)
        assert rooms_list.status_code == 200
        assert len(rooms_list.json()) > 0
        
        # Tables CRUD
        table_create = client.post(
            "/api/v1/admin/tables",
            json={"room_id": room_id, "limit_type": "NL50", "max_players": 9},
            headers=headers
        )
        assert table_create.status_code == 201
        table_id = table_create.json()["id"]
        
        tables_list = client.get(f"/api/v1/admin/tables?room_id={room_id}", headers=headers)
        assert tables_list.status_code == 200
        assert len(tables_list.json()) > 0
    
    def test_admin_permissions(self, client: TestClient, db: Session):
        """Тестирует проверку admin прав"""
        from data.models_v1_2 import APIKey
        import secrets
        
        # Создаем обычный ключ (не admin)
        regular_key = f"test_regular_{secrets.token_urlsafe(16)}"
        key = APIKey(
            api_key=regular_key,
            api_secret=secrets.token_urlsafe(64),
            client_name="regular",
            permissions=["decide_only"],
            is_admin=False,
            is_active=True
        )
        db.add(key)
        db.commit()
        
        # Пытаемся создать бота с обычным ключом (должно быть 403)
        response = client.post(
            "/api/v1/admin/bots",
            json={"alias": "test", "default_style": "balanced", "default_limit": "NL10"},
            headers={"X-API-Key": regular_key}
        )
        assert response.status_code == 403
        
        # Создаем admin ключ
        admin_key = f"test_admin_{secrets.token_urlsafe(16)}"
        admin_key_obj = APIKey(
            api_key=admin_key,
            api_secret=secrets.token_urlsafe(64),
            client_name="admin",
            permissions=["admin"],
            is_admin=True,
            is_active=True
        )
        db.add(admin_key_obj)
        db.commit()
        
        # С admin ключом должно работать
        response = client.post(
            "/api/v1/admin/bots",
            json={"alias": "test_admin", "default_style": "balanced", "default_limit": "NL10"},
            headers={"X-API-Key": admin_key}
        )
        assert response.status_code == 201
