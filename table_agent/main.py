#!/usr/bin/env python3
"""Главный скрипт запуска Table Agent"""

import asyncio
import argparse
import signal
import sys
import time
from typing import Optional

from .connection import ConnectionConfig
from .agent import TableAgent, AgentConfig, AgentState
from .action_executor import DummyExecutor, PyAutoGUIExecutor, ADBExecutor, TableLayout

# Screen Reader (опционально)
try:
    from .screen_reader import PILScreenReader, MockScreenReader, LAYOUTS
    SCREEN_READER_AVAILABLE = True
except ImportError:
    SCREEN_READER_AVAILABLE = False
    PILScreenReader = None
    MockScreenReader = None
    LAYOUTS = {}


class TableAgentRunner:
    """Запускатор Table Agent"""

    def __init__(
        self,
        api_url: str,
        bot_id: str,
        limit_type: str,
        table_key: Optional[str] = None,
        api_key: Optional[str] = None,
        executor_type: str = "dummy",
        room: str = "pokerking",
        use_screen_reader: bool = False
    ):
        self.conn_config = ConnectionConfig(
            api_url=api_url,
            api_key=api_key,
            timeout=5.0
        )

        self.agent_config = AgentConfig(
            bot_id=bot_id,
            limit_type=limit_type,
            table_key=table_key,
        )

        self.agent: Optional[TableAgent] = None
        self.running = False
        self.room = room
        self.use_screen_reader = use_screen_reader

        # Создаём executor на основе типа
        layout = self._get_layout(room)
        self.executor = self._create_executor(executor_type, layout)

        # Screen reader (если включен)
        self.screen_reader = None
        if use_screen_reader and SCREEN_READER_AVAILABLE:
            room_layout = LAYOUTS.get(room, {})
            self.screen_reader = PILScreenReader(room_layout)
            print(f"Screen reader enabled for {room}")

    def _get_layout(self, room: str) -> TableLayout:
        """Получить layout кнопок для рума"""
        from .action_executor import ClickPosition

        # Примерные позиции кнопок для разных румов
        layouts = {
            "pokerking": TableLayout(
                fold_button=ClickPosition(500, 600, 80, 30),
                check_button=ClickPosition(620, 600, 80, 30),
                call_button=ClickPosition(620, 600, 80, 30),
                bet_button=ClickPosition(740, 600, 80, 30),
                raise_button=ClickPosition(740, 600, 80, 30),
                all_in_button=ClickPosition(860, 600, 80, 30),
                bet_input=ClickPosition(700, 550, 100, 25),
                confirm_button=ClickPosition(740, 600, 80, 30)
            ),
            "pokerstars": TableLayout(
                fold_button=ClickPosition(450, 650, 90, 35),
                check_button=ClickPosition(580, 650, 90, 35),
                call_button=ClickPosition(580, 650, 90, 35),
                bet_button=ClickPosition(710, 650, 90, 35),
                raise_button=ClickPosition(710, 650, 90, 35),
                all_in_button=ClickPosition(840, 650, 90, 35),
                bet_input=ClickPosition(680, 600, 110, 28),
                confirm_button=ClickPosition(710, 650, 90, 35)
            ),
            "888poker": TableLayout(
                fold_button=ClickPosition(480, 620, 85, 32),
                check_button=ClickPosition(600, 620, 85, 32),
                call_button=ClickPosition(600, 620, 85, 32),
                bet_button=ClickPosition(720, 620, 85, 32),
                raise_button=ClickPosition(720, 620, 85, 32),
                all_in_button=ClickPosition(840, 620, 85, 32),
                bet_input=ClickPosition(690, 570, 105, 26),
                confirm_button=ClickPosition(720, 620, 85, 32)
            )
        }
        return layouts.get(room, TableLayout())

    def _create_executor(self, executor_type: str, layout: TableLayout):
        """Создать executor нужного типа"""
        if executor_type == "pyautogui":
            try:
                return PyAutoGUIExecutor(layout)
            except ImportError:
                print("PyAutoGUI not installed, falling back to dummy")
                return DummyExecutor(layout)
        elif executor_type == "adb":
            return ADBExecutor(layout)
        else:
            return DummyExecutor(layout)

    async def start(self):
        """Запустить агента"""
        self.agent = TableAgent(self.conn_config, self.agent_config)

        # Настраиваем callbacks
        self.agent.on_decision(self._on_decision)
        self.agent.on_error(self._on_error)
        self.agent.on_state_change(self._on_state_change)

        if not await self.agent.start():
            print("Failed to start agent")
            return False

        self.running = True
        print(f"""
╔══════════════════════════════════════════╗
║         TABLE AGENT STARTED              ║
╠══════════════════════════════════════════╣
║  Bot ID: {self.agent_config.bot_id:<30} ║
║  Limit: {self.agent_config.limit_type:<31} ║
║  Session: {self.agent.session_id:<28} ║
║  API: {self.conn_config.api_url:<32} ║
╚══════════════════════════════════════════╝
        """)
        return True

    async def stop(self):
        """Остановить агента"""
        self.running = False
        if self.agent:
            await self.agent.stop()

        stats = self.agent.get_stats() if self.agent else {}
        print(f"""
╔══════════════════════════════════════════╗
║         TABLE AGENT STOPPED              ║
╠══════════════════════════════════════════╣
║  Hands played: {stats.get('hands_played', 0):<25} ║
║  Errors: {stats.get('errors_count', 0):<31} ║
╚══════════════════════════════════════════╝
        """)

    def _on_decision(self, action: str, amount: Optional[float]):
        """Callback при получении решения"""
        amount_str = f"${amount:.2f}" if amount else ""
        print(f"🎯 Decision: {action.upper()} {amount_str}")

        # Выполняем действие
        asyncio.create_task(self.executor.execute(action, amount))

    def _on_error(self, error: str):
        """Callback при ошибке"""
        print(f"❌ Error: {error}")

    def _on_state_change(self, state: AgentState):
        """Callback при смене состояния"""
        state_icons = {
            AgentState.IDLE: "⏸️",
            AgentState.CONNECTING: "🔄",
            AgentState.WAITING: "⏳",
            AgentState.PLAYING: "🎮",
            AgentState.ERROR: "❌",
            AgentState.STOPPED: "🛑"
        }
        icon = state_icons.get(state, "❓")
        print(f"{icon} State: {state.value}")

    async def run_interactive(self):
        """Интерактивный режим для тестирования"""
        print("\nInteractive mode. Commands:")
        print("  test - send test game state")
        print("  stats - show statistics")
        print("  quit - exit")
        print()

        while self.running:
            try:
                cmd = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("> ").strip().lower()
                )

                if cmd == "quit" or cmd == "q":
                    break
                elif cmd == "test":
                    await self._send_test_state()
                elif cmd == "stats":
                    print(self.agent.get_stats())
                elif cmd:
                    print(f"Unknown command: {cmd}")

            except EOFError:
                break
            except KeyboardInterrupt:
                break

    async def run_auto_play(self):
        """Автоматический режим игры - постоянно читает экран и отправляет решения"""
        if not self.screen_reader:
            print("❌ Screen reader not enabled. Use --screen-reader flag.")
            return

        print("\n🎮 Auto-play mode started")
        print("   Reading screen and making decisions automatically...")
        print("   Press Ctrl+C to stop\n")

        last_hand_id = None
        hand_start_time = None
        hand_counter = 0

        while self.running:
            try:
                # Читаем состояние стола с экрана
                table_state = await asyncio.get_event_loop().run_in_executor(
                    None, self.screen_reader.read_table_state
                )

                if not table_state or "error" in table_state:
                    # Нет активной игры или ошибка чтения
                    await asyncio.sleep(1)
                    continue

                # Генерируем hand_id если его нет (для новой раздачи)
                # Определяем новую раздачу по изменению карт или борда
                hero_cards = table_state.get("hero_cards", "")
                board_cards = table_state.get("board_cards", "")
                # Нормализуем в строки
                if isinstance(hero_cards, list):
                    hero_cards = "".join(hero_cards)
                if isinstance(board_cards, list):
                    board_cards = "".join(board_cards)
                state_hash = f"{hero_cards}_{board_cards}"

                # Если состояние изменилось, это новая раздача
                if not hasattr(self, "_last_state_hash") or self._last_state_hash != state_hash:
                    if hasattr(self, "_last_state_hash") and self._last_state_hash:
                        # Логируем предыдущую раздачу
                        if last_hand_id:
                            await self._log_completed_hand(last_hand_id, hand_start_time, table_state)
                    
                    # Новая раздача
                    hand_counter += 1
                    last_hand_id = f"hand_{int(time.time())}_{hand_counter}"
                    hand_start_time = time.time()
                    self._last_state_hash = state_hash
                    print(f"🃏 New hand: {last_hand_id}")

                # Формируем GameState для API
                game_state = self._table_state_to_game_state(table_state, last_hand_id)

                # Отправляем состояние в agent для получения решения
                decision = await self.agent.process_game_state(game_state)

                if decision:
                    print(f"✅ Decision: {decision.get('action')} "
                          f"(latency: {decision.get('latency_ms', 'N/A')}ms)")

                # Небольшая задержка перед следующим чтением
                await asyncio.sleep(0.5)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error in auto-play loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(2)

        # Логируем последнюю раздачу при остановке
        if last_hand_id and hand_start_time:
            table_state = await asyncio.get_event_loop().run_in_executor(
                None, self.screen_reader.read_table_state
            )
            await self._log_completed_hand(last_hand_id, hand_start_time, table_state or {})

    def _table_state_to_game_state(self, table_state: dict, hand_id: str) -> dict:
        """Конвертирует table_state из screen reader в GameState для API"""
        # hero_cards и board_cards могут быть строками или списками
        hero_cards = table_state.get("hero_cards", "")
        if isinstance(hero_cards, list):
            hero_cards = "".join(hero_cards)
        elif not isinstance(hero_cards, str):
            hero_cards = str(hero_cards)
        
        board_cards = table_state.get("board_cards", "")
        if isinstance(board_cards, list):
            board_cards = "".join(board_cards)
        elif not isinstance(board_cards, str):
            board_cards = str(board_cards)
        
        player_stacks = table_state.get("player_stacks", {})
        player_bets = table_state.get("player_bets", {})
        
        # Базовый GameState
        game_state = {
            "hand_id": hand_id,
            "table_id": self.agent_config.table_key or "table_1",
            "limit_type": self.agent_config.limit_type,
            "street": self._detect_street(table_state),
            "hero_position": table_state.get("hero_position", 0),
            "dealer": table_state.get("dealer", 0),
            "hero_cards": hero_cards,
            "board_cards": board_cards,
            "stacks": {str(i): float(player_stacks.get(i, 100.0)) for i in range(6)},
            "bets": {str(i): float(player_bets.get(i, 0.0)) for i in range(6)},
            "total_bets": {str(i): float(player_bets.get(i, 0.0)) for i in range(6)},
            "active_players": [i for i in range(6) if player_stacks.get(i, 0) > 0],
            "pot": float(table_state.get("pot", 0.0)),
            "current_player": table_state.get("current_player", 0),
            "last_raise_amount": 0.0,
            "small_blind": 0.5,
            "big_blind": 1.0
        }
        return game_state

    def _detect_street(self, table_state: dict) -> str:
        """Определяет улицу по количеству карт на борде"""
        board_cards = table_state.get("board_cards", "")
        # Нормализуем в строку если это список
        if isinstance(board_cards, list):
            board_cards = "".join(board_cards)
        elif not isinstance(board_cards, str):
            board_cards = str(board_cards)
        
        # Определяем улицу по длине строки (каждая карта = 2 символа)
        board_len = len(board_cards)
        if board_len == 0:
            return "preflop"
        elif board_len == 6:  # 3 карты * 2 символа
            return "flop"
        elif board_len == 8:  # 4 карты * 2 символа
            return "turn"
        elif board_len == 10:  # 5 карт * 2 символа
            return "river"
        return "preflop"

    async def _log_completed_hand(self, hand_id: str, start_time: float, table_state: dict):
        """Логировать завершённую раздачу"""
        try:
            # Нормализуем hero_cards и board_cards
            hero_cards = table_state.get("hero_cards", "")
            board_cards = table_state.get("board_cards", "")
            if isinstance(hero_cards, list):
                hero_cards = "".join(hero_cards)
            if isinstance(board_cards, list):
                board_cards = "".join(board_cards)
            
            active_players = table_state.get("active_players", [])
            if not isinstance(active_players, list):
                # Если это dict, берём ключи
                active_players = list(active_players.keys()) if isinstance(active_players, dict) else []
            
            hand_data = {
                "hand_id": hand_id,
                "table_id": self.agent_config.table_key or "table_1",
                "table_key": self.agent_config.table_key,
                "limit_type": self.agent_config.limit_type,
                "players_count": len(active_players) if active_players else 2,
                "hero_position": table_state.get("hero_position", 0),
                "hero_cards": hero_cards if isinstance(hero_cards, str) else str(hero_cards),
                "board_cards": board_cards if isinstance(board_cards, str) else str(board_cards),
                "pot_size": float(table_state.get("pot", 0.0)),
                "rake_amount": 0.0,  # Будет вычислен автоматически
                "hero_result": 0.0,  # Нужно определить из результата раздачи
                "hand_history": None
            }
            
            success = await self.agent.log_hand_result(hand_data)
            if success:
                print(f"📝 Logged hand {hand_id} (duration: {time.time() - start_time:.1f}s)")
        except Exception as e:
            print(f"⚠️ Failed to log hand {hand_id}: {e}")

    async def _send_test_state(self):
        """Отправить тестовое состояние"""
        import random

        hands = ["AsKh", "AhAd", "KsQs", "JdTd", "7s6s", "5h5c"]
        positions = [0, 1, 2, 3, 4, 5]
        streets = ["preflop", "flop", "turn", "river"]

        hero_cards = random.choice(hands)
        hero_pos = random.choice(positions)
        street = random.choice(streets)

        board = ""
        if street == "flop":
            board = "QdJc2s"
        elif street == "turn":
            board = "QdJc2s8h"
        elif street == "river":
            board = "QdJc2s8h4c"

        test_state = {
            "hand_id": f"test_{int(asyncio.get_event_loop().time())}",
            "table_id": (self.agent_config.table_key or "table_1"),
            "hero_cards": hero_cards,
            "board_cards": board,
            "hero_position": hero_pos,
            "dealer": 0,
            "stacks": {str(i): 100.0 - i * 0.5 for i in range(6)},
            "bets": {str(i): 0.5 if i == 1 else (1.0 if i == 2 else 0) for i in range(6)},
            "total_bets": {str(i): 0.5 if i == 1 else (1.0 if i == 2 else 0) for i in range(6)},
            "active_players": [0, 1, 2, hero_pos],
            "pot": 1.5 + random.uniform(0, 10),
            "current_player": hero_pos,
            "street": street
        }

        print(f"\n📤 Test state: {hero_cards} on {street}, pos={hero_pos}")
        decision = await self.agent.process_game_state(test_state)

        if decision:
            print(f"📥 Response: {decision['action']} "
                  f"(latency: {decision.get('latency_ms', 'N/A')}ms)")


def main():
    parser = argparse.ArgumentParser(description="Poker Table Agent")
    parser.add_argument("--api", default="http://localhost:8000", help="Backend API URL")
    parser.add_argument("--bot", default="bot_1", help="Bot ID")
    parser.add_argument("--limit", default="NL10", help="Limit type (NL10, NL50)")
    parser.add_argument("--table-key", default=None, help="Table key (Table.external_table_id). Overrides table_id in API calls.")
    parser.add_argument("--key", help="API key")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--executor", choices=["dummy", "pyautogui", "adb"], default="dummy",
                        help="Action executor type")
    parser.add_argument("--room", choices=["pokerking", "pokerstars", "888poker"], default="pokerking",
                        help="Poker room for screen reader layout")
    parser.add_argument("--screen-reader", action="store_true", help="Enable screen reader mode")

    args = parser.parse_args()

    runner = TableAgentRunner(
        api_url=args.api,
        bot_id=args.bot,
        limit_type=args.limit,
        table_key=args.table_key,
        api_key=args.key,
        executor_type=args.executor,
        room=args.room,
        use_screen_reader=args.screen_reader
    )

    async def run():
        # Обработка сигналов
        loop = asyncio.get_event_loop()

        def signal_handler():
            asyncio.create_task(runner.stop())

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        if await runner.start():
            if args.interactive:
                await runner.run_interactive()
            elif args.screen_reader:
                # Автоматический режим игры
                await runner.run_auto_play()
            else:
                # Просто держим соединение (для тестирования без screen reader)
                print("💡 Tip: Use --screen-reader for auto-play mode")
                print("   Or use --interactive for manual testing")
                while runner.running:
                    await asyncio.sleep(1)

        await runner.stop()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
