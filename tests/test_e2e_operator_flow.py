"""
E2E тест полного операторского flow с table_key.

Проверяет:
1. Создание room → table (с table_key) → bot → config → session
2. Agent heartbeat с привязкой к session
3. /decide запрос с table_key
4. /log_hand с table_key
5. Проверка что всё связано через table_key
6. Остановка session
"""

import os
# Включаем admin API ДО импорта app
os.environ["ENABLE_ADMIN_API"] = "1"

import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timezone

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from data.database import SessionLocal, init_db
from data.models import Bot, Room, Table, BotConfig, BotSession, Agent
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
    # ENABLE_ADMIN_API уже установлен в начале файла
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


class TestE2EOperatorFlow:
    """E2E тест полного операторского flow"""
    
    def test_full_operator_flow_with_table_key(
        self, client: TestClient, admin_key: str, db: Session
    ):
        """Полный flow с table_key: room → table → bot → session → agent → decide → log_hand"""
        headers = {"X-API-Key": admin_key}
        table_key = f"e2e_table_{int(datetime.now(timezone.utc).timestamp())}"
        
        # 1. Создать комнату
        room_response = client.post(
            "/api/v1/admin/rooms",
            json={
                "room_link": "https://test-room-e2e.com",
                "type": "pokerstars",
                "meta": {"test": "e2e"}
            },
            headers=headers
        )
        assert room_response.status_code == 201, room_response.text
        room_id = room_response.json()["id"]
        
        # 2. Создать стол с table_key
        table_response = client.post(
            "/api/v1/admin/tables",
            json={
                "room_id": room_id,
                "table_key": table_key,  # Ключевой момент: используем table_key
                "limit_type": "NL10",
                "max_players": 6
            },
            headers=headers
        )
        assert table_response.status_code == 201, table_response.text
        table_data = table_response.json()
        assert table_data["table_key"] == table_key, "table_key должен быть в ответе"
        table_id = table_data["id"]
        
        # 3. Создать бота
        bot_response = client.post(
            "/api/v1/admin/bots",
            json={
                "alias": "e2e_test_bot",
                "default_style": "balanced",
                "default_limit": "NL10",
                "active": True
            },
            headers=headers
        )
        assert bot_response.status_code == 201, bot_response.text
        bot_id = bot_response.json()["id"]
        
        # 4. Создать конфиг бота
        config_response = client.post(
            "/api/v1/admin/bot-configs",
            json={
                "bot_id": bot_id,
                "name": "e2e_config",
                "target_vpip": 25.0,
                "target_pfr": 20.0,
                "target_af": 2.5,
                "is_default": True
            },
            headers=headers
        )
        assert config_response.status_code == 201, config_response.text
        config_id = config_response.json()["id"]
        
        # 5. Запустить сессию с table_key
        session_response = client.post(
            "/api/v1/admin/session/start",
            json={
                "bot_id": bot_id,
                "table_key": table_key,  # Используем table_key вместо table_id
                "limit": "NL10",
                "style": "balanced"
            },
            headers=headers
        )
        assert session_response.status_code == 201, session_response.text
        session_data = session_response.json()
        assert session_data["table_key"] == table_key, "table_key должен быть в ответе"
        session_id = session_data["session_id"]
        
        # 6. Agent heartbeat (регистрация агента)
        agent_id = f"e2e_agent_{int(datetime.now(timezone.utc).timestamp())}"
        heartbeat_response = client.post(
            "/api/v1/agent/heartbeat",
            json={
                "agent_id": agent_id,
                "session_id": session_id,
                "status": "online",
                "version": "1.0.0"
            },
            headers=headers
        )
        assert heartbeat_response.status_code == 200, heartbeat_response.text
        
        # 7. Проверить статус агента (должен показать table_key)
        agent_status_response = client.get(
            f"/api/v1/agent/{agent_id}",
            headers=headers
        )
        assert agent_status_response.status_code == 200, agent_status_response.text
        agent_status = agent_status_response.json()
        assert agent_status["table_key"] == table_key, "Агент должен показывать table_key"
        assert agent_status["assigned_session_key"] == session_id
        
        # 8. /decide запрос с table_key
        decide_response = client.post(
            "/api/v1/decide",
            json={
                "hand_id": f"e2e_hand_{int(datetime.now(timezone.utc).timestamp())}",
                "table_id": table_key,  # Отправляем table_key
                "limit_type": "NL10",
                "session_id": session_id,
                "street": "preflop",
                "hero_position": 0,
                "dealer": 5,
                "hero_cards": "AsKh",
                "board_cards": "",
                "stacks": {str(i): 100.0 for i in range(6)},
                "bets": {str(i): 0.0 for i in range(6)},
                "total_bets": {str(i): 0.0 for i in range(6)},
                "active_players": [0, 1, 2, 3, 4, 5],
                "pot": 1.5,
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": 0.5,
                "big_blind": 1.0
            },
            headers=headers
        )
        assert decide_response.status_code == 200, decide_response.text
        decide_data = decide_response.json()
        assert "action" in decide_data
        assert decide_data.get("table_key") == table_key, "/decide должен вернуть table_key"
        
        # 9. /log_hand с table_key
        hand_id = f"e2e_hand_{int(datetime.now(timezone.utc).timestamp())}"
        log_hand_response = client.post(
            "/api/v1/log_hand",
            json={
                "hand_id": hand_id,
                "table_id": table_key,  # Отправляем table_key
                "table_key": table_key,  # Явно для совместимости
                "limit_type": "NL10",
                "session_id": session_id,
                "players_count": 6,
                "hero_position": 0,
                "hero_cards": "AsKh",
                "board_cards": "QdJc2s",
                "pot_size": 10.0,
                "rake_amount": 0.0,
                "hero_result": 2.0,
                "hand_history": None
            },
            headers=headers
        )
        assert log_hand_response.status_code == 200, log_hand_response.text
        log_data = log_hand_response.json()
        assert log_data.get("table_key") == table_key, "/log_hand должен вернуть table_key"
        
        # 10. Проверить что hand сохранён с правильным table_key
        from data.models import Hand
        hand = db.query(Hand).filter(Hand.hand_id == hand_id).first()
        assert hand is not None, "Hand должен быть сохранён"
        assert hand.table_id == table_key, f"Hand.table_id должен быть table_key, получено: {hand.table_id}"
        
        # 11. Проверить /hands/recent возвращает table_key
        recent_hands_response = client.get(
            "/api/v1/hands/recent?limit=10",
            headers=headers
        )
        assert recent_hands_response.status_code == 200, recent_hands_response.text
        recent_hands = recent_hands_response.json()
        assert len(recent_hands) > 0
        # Находим наш hand
        our_hand = next((h for h in recent_hands if h["hand_id"] == hand_id), None)
        assert our_hand is not None, "Наш hand должен быть в списке"
        assert our_hand.get("table_key") == table_key, "recent hands должен показывать table_key"
        
        # 12. Проверить /stats показывает активные сессии
        stats_response = client.get("/api/v1/stats", headers=headers)
        assert stats_response.status_code == 200, stats_response.text
        stats = stats_response.json()
        assert stats.get("active_control_sessions", 0) > 0, "Должна быть активная сессия"
        
        # 13. Остановить сессию
        stop_response = client.post(
            f"/api/v1/admin/session/{session_id}/stop",
            headers=headers
        )
        assert stop_response.status_code == 200, stop_response.text
        stop_data = stop_response.json()
        assert stop_data["status"] == "stopped"
        assert stop_data.get("table_key") == table_key, "Остановленная сессия должна показывать table_key"
        
        # 14. Проверить что сессия остановлена
        session_get_response = client.get(
            f"/api/v1/admin/session/{session_id}",
            headers=headers
        )
        assert session_get_response.status_code == 200, session_get_response.text
        session_final = session_get_response.json()
        assert session_final["status"] == "stopped"
        assert session_final.get("table_key") == table_key
        
        print(f"\n✅ E2E тест пройден успешно!")
        print(f"   Room ID: {room_id}")
        print(f"   Table ID: {table_id}, table_key: {table_key}")
        print(f"   Bot ID: {bot_id}")
        print(f"   Session ID: {session_id}")
        print(f"   Agent ID: {agent_id}")
        print(f"   Hand ID: {hand_id}")
