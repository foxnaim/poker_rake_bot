"""Интеграционные тесты для Week 3 функциональности"""

import pytest
pytest.importorskip("fastapi")
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from data.database import get_db, init_db
from data.models import Agent, BotStats, Hand, RakeModel, Room, Table
from api.endpoints.agents import agent_heartbeat_http
from api.endpoints.sessions import start_session, end_session, get_session
from api.endpoints.log_hand import log_hand_endpoint
from api.endpoints.decide import decide_endpoint
from api.schemas import (
    AgentHeartbeatRequest,
    SessionCreate, SessionEnd,
    HandLogRequest, GameStateRequest
)
from utils.rake_calculator import calculate_rake


@pytest.fixture
def db_session():
    """Создаёт тестовую сессию БД"""
    init_db()
    db = next(get_db())
    yield db
    db.close()


@pytest.fixture
def test_room_and_table(db_session: Session):
    """Создаёт тестовую комнату и стол"""
    room = Room(
        room_link="test_room",
        type="test",
        status="active"
    )
    db_session.add(room)
    db_session.commit()
    db_session.refresh(room)
    
    table = Table(
        room_id=room.id,
        limit_type="NL10",
        max_players=6
    )
    db_session.add(table)
    db_session.commit()
    db_session.refresh(table)
    
    # Создаём модель рейка
    rake_model = RakeModel(
        room_id=room.id,
        limit_type="NL10",
        percent=5.0,
        cap=3.0,
        min_pot=0.0
    )
    db_session.add(rake_model)
    db_session.commit()
    
    return room, table, rake_model


class TestRakeCalculation:
    """Тесты расчёта рейка"""
    
    def test_rake_calculation_with_model(self, db_session: Session, test_room_and_table):
        """Тест расчёта рейка по модели"""
        room, table, rake_model = test_room_and_table
        
        # Пот 100, рейк должен быть 5% = 5.0, но кап 3.0
        rake = calculate_rake(
            pot_size=100.0,
            room_id=room.id,
            limit_type="NL10",
            db=db_session
        )
        assert rake == 3.0  # Кап применён
        
        # Пот 20, рейк должен быть 5% = 1.0
        rake = calculate_rake(
            pot_size=20.0,
            room_id=room.id,
            limit_type="NL10",
            db=db_session
        )
        assert rake == 1.0
    
    def test_rake_calculation_default(self, db_session: Session):
        """Тест расчёта рейка с дефолтной моделью"""
        # Без модели - дефолтные значения (5%, кап 3.0)
        rake = calculate_rake(
            pot_size=100.0,
            room_id=None,
            limit_type="NL10",
            db=db_session
        )
        assert rake == 3.0


class TestAgentProtocol:
    """Тесты протокола агентов"""
    
    @pytest.mark.asyncio
    async def test_agent_heartbeat_http(self, db_session: Session):
        """Тест HTTP heartbeat"""
        request = AgentHeartbeatRequest(
            agent_id="test_agent_1",
            status="online",
            version="1.0.0"
        )
        
        response = await agent_heartbeat_http(request, db_session)
        
        assert response.status == "ok"
        assert response.agent_id == "test_agent_1"
        
        # Проверяем, что агент создан в БД
        agent = db_session.query(Agent).filter(Agent.agent_id == "test_agent_1").first()
        assert agent is not None
        assert agent.status == "online"
        assert agent.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_agent_heartbeat_with_errors(self, db_session: Session):
        """Тест heartbeat с ошибками"""
        request = AgentHeartbeatRequest(
            agent_id="test_agent_2",
            status="online",
            version="1.0.0",
            errors=["Error 1", "Error 2"]
        )
        
        response = await agent_heartbeat_http(request, db_session)
        
        agent = db_session.query(Agent).filter(Agent.agent_id == "test_agent_2").first()
        assert agent.meta is not None
        assert "last_errors" in agent.meta
        assert len(agent.meta["last_errors"]) == 2


class TestSessionStats:
    """Тесты статистики сессий"""
    
    @pytest.mark.asyncio
    async def test_session_start_end_with_stats(self, db_session: Session):
        """Тест создания и завершения сессии со статистикой"""
        # Создаём сессию
        create_request = SessionCreate(
            session_id="test_session_1",
            limit_type="NL10"
        )
        start_response = await start_session(create_request, db_session)
        
        assert start_response["status"] == "started"
        assert start_response["session_id"] == "test_session_1"
        
        # Логируем несколько рук
        for i in range(5):
            hand_request = HandLogRequest(
                hand_id=f"hand_{i}",
                table_id="table_1",
                limit_type="NL10",
                players_count=6,
                hero_position=0,
                hero_cards="AsKh",
                board_cards="",
                pot_size=20.0,
                rake_amount=None,  # Будет вычислено
                hero_result=5.0,
                hand_history=None
            )
            await log_hand_endpoint(hand_request, db_session, True)
        
        # Завершаем сессию
        end_request = SessionEnd(session_id="test_session_1")
        end_response = await end_session(end_request, db_session)
        
        assert end_response["status"] == "ended"
        assert end_response["hands_played"] == 5
        assert end_response["total_rake"] > 0
        
        # Проверяем статистику
        session_response = await get_session("test_session_1", db_session)
        assert session_response.hands_played == 5
        assert session_response.rake_100 > 0
        assert session_response.hands_per_hour > 0
        assert session_response.profit_bb_100 > 0


class TestFullCycle:
    """Тест полного цикла: агент → сессия → решения → статистика"""
    
    @pytest.mark.asyncio
    async def test_full_agent_cycle(self, db_session: Session):
        """Тест полного цикла работы агента"""
        # 1. Агент отправляет heartbeat
        heartbeat_request = AgentHeartbeatRequest(
            agent_id="full_cycle_agent",
            status="online",
            version="1.0.0"
        )
        heartbeat_response = await agent_heartbeat_http(heartbeat_request, db_session)
        assert heartbeat_response.status == "ok"
        
        # 2. Начинаем сессию
        session_request = SessionCreate(
            session_id="full_cycle_session",
            limit_type="NL10"
        )
        session_start = await start_session(session_request, db_session)
        assert session_start["status"] == "started"
        
        # 3. Агент обновляет heartbeat с session_id
        heartbeat_request.session_id = "full_cycle_session"
        heartbeat_response = await agent_heartbeat_http(heartbeat_request, db_session)
        
        # Проверяем, что агент привязан к сессии
        agent = db_session.query(Agent).filter(Agent.agent_id == "full_cycle_agent").first()
        assert agent.assigned_session_id is not None
        
        # 4. Генерируем решения и логируем руки
        for i in range(3):
            # Решение
            decide_request = GameStateRequest(
                hand_id=f"cycle_hand_{i}",
                table_id="table_1",
                limit_type="NL10",
                street="preflop",
                hero_position=0,
                dealer=0,
                hero_cards="AsKh",
                board_cards="",
                stacks={"player_0": 100.0},
                bets={"player_0": 0.0},
                total_bets={"player_0": 0.0},
                active_players=[0],
                pot=10.0,
                current_player=0,
                last_raise_amount=0.0,
                small_blind=0.5,
                big_blind=1.0
            )
            decision = await decide_endpoint(decide_request, None, db_session, True, None, None, None)
            assert decision.action in ["fold", "call", "raise", "check", "all_in"]
            
            # Логируем руку
            hand_request = HandLogRequest(
                hand_id=f"cycle_hand_{i}",
                table_id="table_1",
                limit_type="NL10",
                players_count=6,
                hero_position=0,
                hero_cards="AsKh",
                board_cards="",
                pot_size=20.0,
                rake_amount=None,
                hero_result=2.0,
                hand_history=None
            )
            await log_hand_endpoint(hand_request, db_session, True)
        
        # 5. Проверяем статистику сессии
        session_stats = await get_session("full_cycle_session", db_session)
        assert session_stats.hands_played == 3
        assert session_stats.total_rake > 0
        assert session_stats.rake_100 > 0
        assert session_stats.hands_per_hour > 0
        
        # 6. Завершаем сессию
        end_request = SessionEnd(session_id="full_cycle_session")
        end_response = await end_session(end_request, db_session)
        assert end_response["status"] == "ended"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
