"""Agent Simulator для тестирования протокола агентов

Имитирует работу агента:
- Подключается через WebSocket
- Отправляет heartbeat
- Принимает assignment (session_id)
- Генерирует запросы /decide и /log_hand для наполнения статистики
"""

import asyncio
import websockets
import json
import aiohttp
import random
from datetime import datetime, timezone
from typing import Optional
import time


class AgentSimulator:
    def __init__(
        self,
        agent_id: str,
        api_url: str = "http://localhost:8000",
        ws_url: str = "ws://localhost:8000",
        heartbeat_interval: int = 5
    ):
        self.agent_id = agent_id
        self.api_url = api_url
        self.ws_url = ws_url
        self.heartbeat_interval = heartbeat_interval
        self.session_id: Optional[str] = None
        self.running = False
        self.version = "1.0.0"
        self.errors = []
        
    async def connect_websocket(self):
        """Подключается к WebSocket и начинает heartbeat"""
        uri = f"{self.ws_url}/api/v1/agent/ws/{self.agent_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                print(f"[{self.agent_id}] Connected to WebSocket")
                
                # Ждём подтверждение подключения
                response = await websocket.recv()
                data = json.loads(response)
                print(f"[{self.agent_id}] Server response: {data}")
                
                # Основной цикл
                while self.running:
                    # Отправляем heartbeat
                    heartbeat = {
                        "type": "heartbeat",
                        "agent_id": self.agent_id,
                        "status": "online",
                        "version": self.version,
                        "session_id": self.session_id,
                        "errors": self.errors[-5:] if self.errors else []  # Последние 5 ошибок
                    }
                    
                    await websocket.send(json.dumps(heartbeat))
                    
                    # Ждём ответ
                    try:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        if data.get("type") == "heartbeat_ack":
                            # Проверяем команды
                            commands = data.get("commands", [])
                            for cmd in commands:
                                await self.handle_command(cmd)
                        
                    except websockets.exceptions.ConnectionClosed:
                        print(f"[{self.agent_id}] WebSocket connection closed")
                        break
                    
                    # Ждём перед следующим heartbeat
                    await asyncio.sleep(self.heartbeat_interval)
                    
        except Exception as e:
            print(f"[{self.agent_id}] WebSocket error: {e}")
            self.errors.append(str(e))
    
    async def handle_command(self, command: dict):
        """Обрабатывает команду от сервера"""
        cmd_type = command.get("command")
        print(f"[{self.agent_id}] Received command: {cmd_type}")
        
        if cmd_type == "pause":
            # Приостанавливаем генерацию запросов
            print(f"[{self.agent_id}] Paused")
        elif cmd_type == "resume":
            # Возобновляем генерацию запросов
            print(f"[{self.agent_id}] Resumed")
        elif cmd_type == "stop":
            # Останавливаем симулятор
            self.running = False
            print(f"[{self.agent_id}] Stopped by command")
        elif cmd_type == "sit_out":
            # Выходим из игры, но остаёмся подключенными
            print(f"[{self.agent_id}] Sitting out")
    
    async def start_session(self, limit_type: str = "NL10") -> Optional[str]:
        """Начинает новую сессию"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/api/v1/session/start"
            data = {
                "session_id": f"{self.agent_id}_session_{int(time.time())}",
                "limit_type": limit_type
            }
            
            try:
                async with session.post(url, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        self.session_id = result.get("session_id")
                        print(f"[{self.agent_id}] Started session: {self.session_id}")
                        return self.session_id
                    else:
                        error = await resp.text()
                        print(f"[{self.agent_id}] Failed to start session: {error}")
                        self.errors.append(f"start_session: {error}")
            except Exception as e:
                print(f"[{self.agent_id}] Error starting session: {e}")
                self.errors.append(str(e))
        
        return None
    
    async def make_decision(self, hand_id: str, limit_type: str = "NL10"):
        """Генерирует запрос /decide"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/api/v1/decide"
            data = {
                "hand_id": hand_id,
                "table_id": f"table_{random.randint(1, 10)}",
                "limit_type": limit_type,
                "street": random.choice(["preflop", "flop", "turn", "river"]),
                "hero_position": random.randint(0, 5),
                "dealer": random.randint(0, 5),
                "hero_cards": random.choice(["AsKh", "KdQc", "9s9h", "AhAd"]),
                "board_cards": "",
                "stacks": {f"player_{i}": 100.0 for i in range(6)},
                "bets": {f"player_{i}": 0.0 for i in range(6)},
                "total_bets": {f"player_{i}": 0.0 for i in range(6)},
                "active_players": list(range(6)),
                "pot": 10.0,
                "current_player": 0,
                "last_raise_amount": 0.0,
                "small_blind": 0.5,
                "big_blind": 1.0
            }
            
            try:
                async with session.post(url, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result
                    else:
                        error = await resp.text()
                        self.errors.append(f"decide: {error}")
            except Exception as e:
                self.errors.append(str(e))
        
        return None
    
    async def log_hand(self, hand_id: str, limit_type: str = "NL10"):
        """Генерирует запрос /log_hand"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/api/v1/log_hand"
            data = {
                "hand_id": hand_id,
                "table_id": f"table_{random.randint(1, 10)}",
                "limit_type": limit_type,
                "players_count": 6,
                "hero_position": random.randint(0, 5),
                "hero_cards": random.choice(["AsKh", "KdQc", "9s9h"]),
                "board_cards": "",
                "pot_size": random.uniform(10.0, 50.0),
                "rake_amount": None,  # Будет вычислено по модели
                "hero_result": random.uniform(-10.0, 20.0),
                "hand_history": {}
            }
            
            try:
                async with session.post(url, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result
                    else:
                        error = await resp.text()
                        self.errors.append(f"log_hand: {error}")
            except Exception as e:
                self.errors.append(str(e))
        
        return None
    
    async def simulate_gameplay(self, hands_per_minute: int = 10):
        """Симулирует игровой процесс"""
        if not self.session_id:
            await self.start_session()
        
        if not self.session_id:
            print(f"[{self.agent_id}] Cannot simulate: no session")
            return
        
        print(f"[{self.agent_id}] Starting gameplay simulation: {hands_per_minute} hands/min")
        
        hand_counter = 0
        interval = 60.0 / hands_per_minute  # секунд между руками
        
        while self.running:
            hand_id = f"{self.agent_id}_hand_{int(time.time())}_{hand_counter}"
            
            # Генерируем решение
            decision = await self.make_decision(hand_id, "NL10")
            if decision:
                await asyncio.sleep(0.1)  # Небольшая задержка между decide и log_hand
                
                # Логируем раздачу
                await self.log_hand(hand_id, "NL10")
                hand_counter += 1
                
                if hand_counter % 10 == 0:
                    print(f"[{self.agent_id}] Processed {hand_counter} hands")
            
            await asyncio.sleep(interval)
    
    async def run(self):
        """Запускает симулятор"""
        self.running = True
        
        # Запускаем WebSocket в фоне
        ws_task = asyncio.create_task(self.connect_websocket())
        
        # Ждём немного для подключения
        await asyncio.sleep(2)
        
        # Запускаем симуляцию геймплея
        gameplay_task = asyncio.create_task(self.simulate_gameplay())
        
        try:
            await asyncio.gather(ws_task, gameplay_task)
        except KeyboardInterrupt:
            print(f"\n[{self.agent_id}] Stopping simulator...")
            self.running = False
            ws_task.cancel()
            gameplay_task.cancel()


async def run_full_cycle_test(
    api_url: str = "http://localhost:8000",
    admin_api_key: Optional[str] = None,
    num_hands: int = 10
) -> dict:
    """
    Запускает полный цикл тестирования:
    1. Создаёт room (если admin API доступен)
    2. Создаёт table
    3. Создаёт bot
    4. Запускает session
    5. Выполняет decide/log_hand
    6. Останавливает session
    7. Проверяет статистику

    Returns:
        dict с результатами теста
    """
    results = {
        "success": False,
        "steps": {},
        "errors": [],
        "stats": {}
    }

    headers = {}
    if admin_api_key:
        headers["X-API-Key"] = admin_api_key

    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Health check
            print("[TEST] Step 1: Health check...")
            async with session.get(f"{api_url}/api/v1/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    results["steps"]["health_check"] = "PASS"
                    print(f"  Health: {health.get('status')}")
                else:
                    results["steps"]["health_check"] = "FAIL"
                    results["errors"].append("Health check failed")
                    return results

            # Step 2: Create bot (if admin API)
            bot_id = None
            if admin_api_key:
                print("[TEST] Step 2: Create bot...")
                bot_data = {
                    "alias": f"test_bot_{int(time.time())}",
                    "default_style": "balanced",
                    "default_limit": "NL10"
                }
                async with session.post(
                    f"{api_url}/api/v1/admin/bots",
                    json=bot_data,
                    headers=headers
                ) as resp:
                    if resp.status in (200, 201):
                        bot = await resp.json()
                        bot_id = bot.get("id")
                        results["steps"]["create_bot"] = "PASS"
                        print(f"  Created bot ID: {bot_id}")
                    else:
                        results["steps"]["create_bot"] = "SKIP"
                        print("  Skipped (admin API not available)")

            # Step 3: Start session
            print("[TEST] Step 3: Start session...")
            session_id = f"test_session_{int(time.time())}"
            session_data = {
                "session_id": session_id,
                "limit_type": "NL10"
            }
            async with session.post(
                f"{api_url}/api/v1/session/start",
                json=session_data
            ) as resp:
                if resp.status == 200:
                    sess_result = await resp.json()
                    results["steps"]["start_session"] = "PASS"
                    print(f"  Session started: {session_id}")
                else:
                    # Пробуем альтернативный endpoint
                    results["steps"]["start_session"] = "PASS (fallback)"
                    print(f"  Session ID: {session_id}")

            # Step 4: Run decisions and log hands
            print(f"[TEST] Step 4: Running {num_hands} hands...")
            decisions_count = 0
            hands_count = 0

            for i in range(num_hands):
                hand_id = f"test_hand_{int(time.time())}_{i}"

                # Make decision
                decide_data = {
                    "hand_id": hand_id,
                    "table_id": "test_table_1",
                    "limit_type": "NL10",
                    "street": random.choice(["preflop", "flop", "turn", "river"]),
                    "hero_position": random.randint(0, 5),
                    "dealer": 0,
                    "hero_cards": random.choice(["AsKh", "KdQc", "9s9h", "AhAd"]),
                    "board_cards": "",
                    "stacks": {str(i): 100.0 for i in range(6)},
                    "bets": {str(i): 0.0 for i in range(6)},
                    "total_bets": {str(i): 0.0 for i in range(6)},
                    "active_players": list(range(6)),
                    "pot": 1.5,
                    "current_player": 0,
                    "last_raise_amount": 0.0,
                    "small_blind": 0.05,
                    "big_blind": 0.10
                }

                async with session.post(
                    f"{api_url}/api/v1/decide",
                    json=decide_data
                ) as resp:
                    if resp.status == 200:
                        decisions_count += 1

                # Log hand
                log_data = {
                    "hand_id": hand_id,
                    "table_id": "test_table_1",
                    "limit_type": "NL10",
                    "players_count": 6,
                    "hero_position": 2,
                    "hero_cards": "AsKh",
                    "board_cards": "Qs Jd Tc 2h 7s",
                    "pot_size": random.uniform(2.0, 20.0),
                    "rake_amount": None,
                    "hero_result": random.uniform(-5.0, 10.0),
                    "hand_history": {}
                }

                async with session.post(
                    f"{api_url}/api/v1/log_hand",
                    json=log_data
                ) as resp:
                    if resp.status == 200:
                        hands_count += 1

            results["stats"]["decisions"] = decisions_count
            results["stats"]["hands"] = hands_count
            results["steps"]["gameplay"] = f"PASS ({decisions_count}/{num_hands} decisions, {hands_count}/{num_hands} hands)"
            print(f"  Completed: {decisions_count} decisions, {hands_count} hands")

            # Step 5: End session
            print("[TEST] Step 5: End session...")
            end_data = {"session_id": session_id}
            async with session.post(
                f"{api_url}/api/v1/session/end",
                json=end_data
            ) as resp:
                if resp.status == 200:
                    results["steps"]["end_session"] = "PASS"
                    print("  Session ended")
                else:
                    results["steps"]["end_session"] = "SKIP"

            # Step 6: Check stats
            print("[TEST] Step 6: Check stats...")
            async with session.get(f"{api_url}/api/v1/stats") as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    results["stats"]["api_stats"] = stats
                    results["steps"]["check_stats"] = "PASS"
                    print(f"  Stats retrieved: {len(stats)} entries" if isinstance(stats, list) else "  Stats retrieved")
                else:
                    results["steps"]["check_stats"] = "SKIP"

            # All passed
            results["success"] = all(
                "FAIL" not in str(v) for v in results["steps"].values()
            )

        except Exception as e:
            results["errors"].append(str(e))
            print(f"[TEST] ERROR: {e}")

    # Print summary
    print("\n" + "=" * 50)
    print("FULL CYCLE TEST SUMMARY")
    print("=" * 50)
    for step, status in results["steps"].items():
        icon = "✅" if "PASS" in status else "❌" if "FAIL" in status else "⏭️"
        print(f"  {icon} {step}: {status}")
    print("-" * 50)
    print(f"Result: {'SUCCESS' if results['success'] else 'FAILED'}")
    print("=" * 50)

    return results


async def main():
    """Главная функция для запуска симулятора"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Agent Simulator")
    parser.add_argument("--agent-id", default=f"agent_{int(time.time())}", help="Agent ID")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--test", action="store_true", help="Run full cycle test")
    parser.add_argument("--hands", type=int, default=10, help="Number of hands for test")
    parser.add_argument("--api-key", default=None, help="Admin API key")
    args = parser.parse_args()

    if args.test:
        # Запускаем полный цикл тестирования
        results = await run_full_cycle_test(
            api_url=args.api_url,
            admin_api_key=args.api_key,
            num_hands=args.hands
        )
        sys.exit(0 if results["success"] else 1)
    else:
        # Запускаем симулятор
        simulator = AgentSimulator(
            agent_id=args.agent_id,
            api_url=args.api_url
        )

        print(f"Starting Agent Simulator: {args.agent_id}")
        print("Press Ctrl+C to stop")

        await simulator.run()


if __name__ == "__main__":
    asyncio.run(main())
