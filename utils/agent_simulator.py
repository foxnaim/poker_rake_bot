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


async def main():
    """Главная функция для запуска симулятора"""
    import sys
    
    agent_id = sys.argv[1] if len(sys.argv) > 1 else f"agent_{int(time.time())}"
    
    simulator = AgentSimulator(agent_id=agent_id)
    
    print(f"Starting Agent Simulator: {agent_id}")
    print("Press Ctrl+C to stop")
    
    await simulator.run()


if __name__ == "__main__":
    asyncio.run(main())
