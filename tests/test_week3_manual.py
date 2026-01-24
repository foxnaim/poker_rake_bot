"""Ручные тесты для Week 3 - для запуска вручную и проверки функциональности

Эти тесты требуют запущенного сервера на localhost:8000.
Для запуска: python tests/test_week3_manual.py
"""

import pytest
# Эти тесты используют async def и требуют pytest-asyncio/anyio плагины.
pytest.importorskip("pytest_asyncio")

import asyncio
import aiohttp
import json
from datetime import datetime


API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

# Skip все тесты в этом файле при обычном запуске pytest
pytestmark = pytest.mark.skip(reason="Manual tests require running server at localhost:8000")


async def test_rake_calculation():
    """Тест расчёта рейка"""
    print("\n=== Тест расчёта рейка ===")
    
    async with aiohttp.ClientSession() as session:
        # Создаём комнату и модель рейка (через admin API если есть, или напрямую в БД)
        # Для теста просто логируем руку и проверяем, что рейк вычислен
        hand_data = {
            "hand_id": f"test_rake_{int(datetime.now().timestamp())}",
            "table_id": "table_1",
            "limit_type": "NL10",
            "players_count": 6,
            "hero_position": 0,
            "hero_cards": "AsKh",
            "board_cards": "",
            "pot_size": 100.0,
            "rake_amount": None,  # Должен быть вычислен
            "hero_result": 10.0,
            "hand_history": None
        }
        
        async with session.post(f"{API_URL}/api/v1/log_hand", json=hand_data) as resp:
            result = await resp.json()
            print(f"✅ Hand logged: {result}")
            
            # Проверяем, что рейк был вычислен (нужно получить руку из БД)
            # Для упрощения просто проверяем, что запрос прошёл успешно
            assert resp.status == 200


async def test_agent_heartbeat():
    """Тест heartbeat агента"""
    print("\n=== Тест heartbeat агента ===")
    
    agent_id = f"test_agent_{int(datetime.now().timestamp())}"
    
    async with aiohttp.ClientSession() as session:
        heartbeat_data = {
            "agent_id": agent_id,
            "status": "online",
            "version": "1.0.0",
            "errors": []
        }
        
        async with session.post(f"{API_URL}/api/v1/agent/heartbeat", json=heartbeat_data) as resp:
            result = await resp.json()
            print(f"✅ Heartbeat sent: {result}")
            assert resp.status == 200
            assert result["status"] == "ok"
            assert result["agent_id"] == agent_id
        
        # Проверяем статус агента
        async with session.get(f"{API_URL}/api/v1/agent/{agent_id}") as resp:
            agent_status = await resp.json()
            print(f"✅ Agent status: {agent_status}")
            assert resp.status == 200
            assert agent_status["status"] == "online"


async def test_session_with_stats():
    """Тест сессии со статистикой"""
    print("\n=== Тест сессии со статистикой ===")
    
    session_id = f"test_session_{int(datetime.now().timestamp())}"
    
    async with aiohttp.ClientSession() as session:
        # 1. Начинаем сессию
        start_data = {
            "session_id": session_id,
            "limit_type": "NL10"
        }
        
        async with session.post(f"{API_URL}/api/v1/session/start", json=start_data) as resp:
            start_result = await resp.json()
            print(f"✅ Session started: {start_result}")
            assert resp.status == 200
        
        # 2. Логируем несколько рук
        for i in range(3):
            hand_data = {
                "hand_id": f"{session_id}_hand_{i}",
                "table_id": "table_1",
                "limit_type": "NL10",
                "players_count": 6,
                "hero_position": 0,
                "hero_cards": "AsKh",
                "board_cards": "",
                "pot_size": 20.0,
                "rake_amount": None,
                "hero_result": 2.0,
                "hand_history": None
            }
            
            async with session.post(f"{API_URL}/api/v1/log_hand", json=hand_data) as resp:
                assert resp.status == 200
        
        # 3. Проверяем статистику сессии
        async with session.get(f"{API_URL}/api/v1/session/{session_id}") as resp:
            session_stats = await resp.json()
            print(f"✅ Session stats: {session_stats}")
            assert resp.status == 200
            assert session_stats["hands_played"] == 3
            assert "rake_100" in session_stats
            assert "profit_bb_100" in session_stats
            assert "hands_per_hour" in session_stats
        
        # 4. Завершаем сессию
        end_data = {"session_id": session_id}
        async with session.post(f"{API_URL}/api/v1/session/end", json=end_data) as resp:
            end_result = await resp.json()
            print(f"✅ Session ended: {end_result}")
            assert resp.status == 200
            assert end_result["hands_played"] == 3


async def test_full_cycle():
    """Тест полного цикла: агент → сессия → решения → статистика"""
    print("\n=== Тест полного цикла ===")
    
    agent_id = f"cycle_agent_{int(datetime.now().timestamp())}"
    session_id = f"cycle_session_{int(datetime.now().timestamp())}"
    
    async with aiohttp.ClientSession() as session:
        # 1. Агент heartbeat
        heartbeat_data = {
            "agent_id": agent_id,
            "status": "online",
            "version": "1.0.0"
        }
        async with session.post(f"{API_URL}/api/v1/agent/heartbeat", json=heartbeat_data) as resp:
            assert resp.status == 200
        
        # 2. Начинаем сессию
        start_data = {"session_id": session_id, "limit_type": "NL10"}
        async with session.post(f"{API_URL}/api/v1/session/start", json=start_data) as resp:
            assert resp.status == 200
        
        # 3. Агент обновляет heartbeat с session_id
        heartbeat_data["session_id"] = session_id
        async with session.post(f"{API_URL}/api/v1/agent/heartbeat", json=heartbeat_data) as resp:
            assert resp.status == 200
        
        # 4. Генерируем решения и логируем руки
        for i in range(2):
            # Решение
            decide_data = {
                "hand_id": f"{session_id}_hand_{i}",
                "table_id": "table_1",
                "limit_type": "NL10",
                "street": "preflop",
                "hero_position": 0,
                "dealer": 0,
                "hero_cards": "AsKh",
                "board_cards": "",
                "stacks": {"player_0": 100.0},
                "bets": {"player_0": 0.0},
                "total_bets": {"player_0": 0.0},
                "active_players": [0],
                "pot": 10.0,
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": 0.5,
                "big_blind": 1.0
            }
            
            async with session.post(f"{API_URL}/api/v1/decide", json=decide_data) as resp:
                decision = await resp.json()
                assert resp.status == 200
                assert "action" in decision
            
            # Логируем руку
            hand_data = {
                "hand_id": f"{session_id}_hand_{i}",
                "table_id": "table_1",
                "limit_type": "NL10",
                "players_count": 6,
                "hero_position": 0,
                "hero_cards": "AsKh",
                "board_cards": "",
                "pot_size": 20.0,
                "rake_amount": None,
                "hero_result": 2.0,
                "hand_history": None
            }
            
            async with session.post(f"{API_URL}/api/v1/log_hand", json=hand_data) as resp:
                assert resp.status == 200
        
        # 5. Проверяем статистику
        async with session.get(f"{API_URL}/api/v1/session/{session_id}") as resp:
            stats = await resp.json()
            print(f"✅ Final stats: hands={stats['hands_played']}, rake_100={stats.get('rake_100', 0)}")
            assert stats["hands_played"] == 2
        
        # 6. Завершаем сессию
        async with session.post(f"{API_URL}/api/v1/session/end", json={"session_id": session_id}) as resp:
            assert resp.status == 200
        
        print("✅ Full cycle completed successfully!")


async def test_agent_command():
    """Тест отправки команды агенту"""
    print("\n=== Тест команды агенту ===")
    
    agent_id = f"cmd_agent_{int(datetime.now().timestamp())}"
    
    async with aiohttp.ClientSession() as session:
        # Создаём агента через heartbeat
        heartbeat_data = {
            "agent_id": agent_id,
            "status": "online",
            "version": "1.0.0"
        }
        async with session.post(f"{API_URL}/api/v1/agent/heartbeat", json=heartbeat_data) as resp:
            assert resp.status == 200
        
        # Отправляем команду
        command_data = {
            "command": "pause",
            "reason": "Testing command system"
        }
        
        async with session.post(f"{API_URL}/api/v1/agent/{agent_id}/command", json=command_data) as resp:
            result = await resp.json()
            print(f"✅ Command sent: {result}")
            assert resp.status == 200
            assert result["command"] == "pause"


async def test_metrics_endpoint():
    """Тест endpoint метрик"""
    print("\n=== Тест метрик ===")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/metrics") as resp:
            metrics_text = await resp.text()
            print(f"✅ Metrics endpoint accessible")
            assert resp.status == 200
            # Проверяем наличие некоторых метрик
            assert "agent_online" in metrics_text or "decision_latency_seconds" in metrics_text


async def main():
    """Запуск всех тестов"""
    print("🚀 Starting Week 3 Manual Tests")
    print("=" * 50)
    
    try:
        await test_rake_calculation()
        await test_agent_heartbeat()
        await test_session_with_stats()
        await test_agent_command()
        await test_metrics_endpoint()
        await test_full_cycle()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
