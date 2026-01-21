"""Главный модуль Table Agent"""

import asyncio
import time
import uuid
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

from .connection import BackendConnection, ConnectionConfig
from .game_state_parser import GameStateParser, JSONGameStateParser, ParsedGameState


class AgentState(Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    WAITING = "waiting"
    PLAYING = "playing"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AgentConfig:
    """Конфигурация агента"""
    bot_id: str = "bot_1"
    limit_type: str = "NL10"
    table_key: Optional[str] = None  # если задан, всегда подставляем как table_id в API
    default_action: str = "fold"  # действие при ошибке
    action_timeout_ms: int = 800  # макс время на решение
    min_delay_ms: int = 300  # мин задержка перед действием
    max_delay_ms: int = 800  # макс задержка


class TableAgent:
    """Table Agent - связывает покер-рум с backend"""

    def __init__(
        self,
        connection_config: ConnectionConfig,
        agent_config: AgentConfig,
        parser: Optional[GameStateParser] = None
    ):
        self.connection = BackendConnection(connection_config)
        self.config = agent_config
        self.parser = parser or JSONGameStateParser()

        self.state = AgentState.IDLE
        self.agent_id: str = f"agent_{self.config.bot_id}_{uuid.uuid4().hex[:8]}"
        self.session_id: Optional[str] = None
        self.hands_played = 0
        self.errors_count = 0
        self.paused = False
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Callbacks
        self._on_decision: Optional[Callable[[str, float], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_state_change: Optional[Callable[[AgentState], None]] = None

    def on_decision(self, callback: Callable[[str, float], None]):
        """Установить callback для решений"""
        self._on_decision = callback

    def on_error(self, callback: Callable[[str], None]):
        """Установить callback для ошибок"""
        self._on_error = callback

    def on_state_change(self, callback: Callable[[AgentState], None]):
        """Установить callback для смены состояния"""
        self._on_state_change = callback

    def _set_state(self, new_state: AgentState):
        """Изменить состояние агента"""
        if self.state != new_state:
            self.state = new_state
            if self._on_state_change:
                self._on_state_change(new_state)

    async def start(self) -> bool:
        """Запустить агента"""
        self._set_state(AgentState.CONNECTING)

        if not await self.connection.connect():
            self._set_state(AgentState.ERROR)
            return False

        # Создаём сессию
        self.session_id = f"{self.config.bot_id}_{int(time.time())}"
        if not await self.connection.start_session(self.session_id, self.config.limit_type):
            self._set_state(AgentState.ERROR)
            return False

        self._set_state(AgentState.WAITING)
        # Стартуем heartbeat loop (agent protocol)
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        print(f"Agent started. AgentID: {self.agent_id} Session: {self.session_id}")
        return True

    async def stop(self):
        """Остановить агента"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self.session_id:
            await self.connection.end_session(self.session_id)

        await self.connection.disconnect()
        self._set_state(AgentState.STOPPED)
        print(f"Agent stopped. Hands played: {self.hands_played}")

    async def process_game_state(self, raw_state: Any) -> Optional[Dict[str, Any]]:
        """Обработать состояние игры и получить решение"""
        if self.paused:
            return None
        if self.state not in [AgentState.WAITING, AgentState.PLAYING]:
            return None

        self._set_state(AgentState.PLAYING)
        start_time = time.time()

        try:
            # Парсим состояние
            parsed = self.parser.parse(raw_state)
            if not parsed:
                raise ValueError("Failed to parse game state")

            # Проверяем - наш ли ход
            if parsed.current_player != parsed.hero_position:
                self._set_state(AgentState.WAITING)
                return None

            # Получаем решение
            api_state = parsed.to_api_format()
            # Канонизируем table_id -> table_key (если задано конфигом)
            if self.config.table_key:
                api_state["table_id"] = self.config.table_key
            # Привязка к backend-сессии + лимиту (важно для логов/статистики)
            api_state["session_id"] = self.session_id
            api_state["limit_type"] = self.config.limit_type
            decision = await self.connection.decide(api_state)

            elapsed_ms = (time.time() - start_time) * 1000

            if not decision:
                # Fallback на дефолтное действие
                decision = {
                    "action": self.config.default_action,
                    "amount": None,
                    "reasoning": {"type": "fallback", "error": "no_response"}
                }
                self.errors_count += 1

            # Добавляем задержку для "человечности"
            await self._human_delay(elapsed_ms)

            # Callback
            if self._on_decision:
                self._on_decision(decision["action"], decision.get("amount"))

            self.hands_played += 1
            self._set_state(AgentState.WAITING)

            return decision

        except Exception as e:
            self.errors_count += 1
            error_msg = str(e)

            if self._on_error:
                self._on_error(error_msg)

            self._set_state(AgentState.WAITING)

            return {
                "action": self.config.default_action,
                "amount": None,
                "reasoning": {"type": "error", "message": error_msg}
            }

    async def _human_delay(self, elapsed_ms: float):
        """Добавить задержку для имитации человека"""
        remaining = self.config.min_delay_ms - elapsed_ms
        if remaining > 0:
            # Добавляем случайность
            import random
            delay = remaining + random.uniform(0, self.config.max_delay_ms - self.config.min_delay_ms)
            await asyncio.sleep(delay / 1000)

    async def log_hand_result(self, hand_data: Dict[str, Any]) -> bool:
        """Записать результат раздачи"""
        hand_data["session_id"] = self.session_id
        if self.config.table_key:
            hand_data["table_id"] = self.config.table_key
        return await self.connection.log_hand(hand_data)

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику агента"""
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "state": self.state.value,
            "paused": self.paused,
            "hands_played": self.hands_played,
            "errors_count": self.errors_count,
            "connected": self.connection.is_connected
        }

    async def _heartbeat_loop(self):
        """Периодический heartbeat + получение команд от backend."""
        while True:
            try:
                resp = await self.connection.heartbeat(
                    agent_id=self.agent_id,
                    session_id=self.session_id,
                    status=("paused" if self.paused else "online"),
                    version=None,
                    errors=None,
                )
                if resp and isinstance(resp, dict):
                    cmds = resp.get("commands") or []
                    for cmd in cmds:
                        await self._apply_command(cmd)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.errors_count += 1
                if self._on_error:
                    self._on_error(f"heartbeat_error: {e}")
            await asyncio.sleep(5)

    async def _apply_command(self, cmd: Dict[str, Any]):
        """Применить команду, пришедшую от backend."""
        name = (cmd.get("command") or "").lower()
        if name == "pause":
            self.paused = True
        elif name == "resume":
            self.paused = False
        elif name in ("sit_out",):
            self.paused = True
        elif name == "stop":
            # Останов асинхронно, чтобы не ломать loop
            asyncio.create_task(self.stop())


async def main():
    """Пример использования"""
    # Конфигурация
    conn_config = ConnectionConfig(
        api_url="http://localhost:8000",
        timeout=5.0
    )

    agent_config = AgentConfig(
        bot_id="test_bot",
        limit_type="NL10"
    )

    # Создаём агента
    agent = TableAgent(conn_config, agent_config)

    # Callbacks
    agent.on_decision(lambda action, amount: print(f"Decision: {action} {amount or ''}"))
    agent.on_error(lambda err: print(f"Error: {err}"))

    # Запускаем
    if await agent.start():
        # Тестовый game state
        test_state = {
            "hand_id": "test_hand_1",
            "table_id": "table_1",
            "hero_cards": "AsKh",
            "board_cards": "",
            "hero_position": 5,
            "dealer": 0,
            "stacks": {"0": 100, "1": 99.5, "2": 99, "3": 100, "4": 100, "5": 100},
            "bets": {"0": 0, "1": 0.5, "2": 1, "3": 0, "4": 0, "5": 0},
            "total_bets": {"0": 0, "1": 0.5, "2": 1, "3": 0, "4": 0, "5": 0},
            "active_players": [0, 1, 2, 5],
            "pot": 1.5,
            "current_player": 5,
            "street": "preflop"
        }

        decision = await agent.process_game_state(test_state)
        print(f"Got decision: {decision}")

        print(f"Stats: {agent.get_stats()}")

        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
