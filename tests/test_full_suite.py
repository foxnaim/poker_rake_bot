#!/usr/bin/env python3
"""
Полноценный тест-сьют для Poker Rake Bot.

Запуск:
    python -m tests.test_full_suite
    python -m tests.test_full_suite --verbose
    python -m tests.test_full_suite --module hand_evaluator
"""

import sys
import os
import argparse
import traceback
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Tuple, Dict, Any

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResult:
    """Результат теста"""
    __test__ = False  # Tell pytest not to collect this as a test class
    
    def __init__(self, name: str, passed: bool, message: str = "", duration_ms: float = 0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration_ms = duration_ms


class TestSuite:
    """Базовый класс для тестов"""
    __test__ = False  # Tell pytest not to collect this as a test class

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []

    def log(self, msg: str):
        if self.verbose:
            print(f"    {msg}")

    def assert_equal(self, actual, expected, msg: str = ""):
        if actual != expected:
            raise AssertionError(f"{msg}: expected {expected}, got {actual}")

    def assert_true(self, condition, msg: str = ""):
        if not condition:
            raise AssertionError(f"Assertion failed: {msg}")

    def assert_in(self, item, container, msg: str = ""):
        if item not in container:
            raise AssertionError(f"{msg}: {item} not in {container}")

    def assert_greater(self, a, b, msg: str = ""):
        if not a > b:
            raise AssertionError(f"{msg}: {a} not greater than {b}")

    def run_test(self, test_func, name: str) -> TestResult:
        """Запустить один тест"""
        import time
        start = time.time()
        try:
            test_func()
            duration = (time.time() - start) * 1000
            return TestResult(name, True, "OK", duration)
        except Exception as e:
            duration = (time.time() - start) * 1000
            return TestResult(name, False, str(e), duration)

    def run_all(self) -> List[TestResult]:
        """Запустить все тесты"""
        raise NotImplementedError


# ============================================
# Hand Evaluator Tests
# ============================================

class HandEvaluatorTests(TestSuite):
    """Тесты для Hand Evaluator"""

    def run_all(self) -> List[TestResult]:
        from engine.hand_evaluator import evaluate_hand, compare_hands, HandEvaluator

        tests = [
            (self.test_high_card, "High Card"),
            (self.test_pair, "Pair"),
            (self.test_two_pair, "Two Pair"),
            (self.test_three_of_a_kind, "Three of a Kind"),
            (self.test_straight, "Straight"),
            (self.test_flush, "Flush"),
            (self.test_full_house, "Full House"),
            (self.test_four_of_a_kind, "Four of a Kind"),
            (self.test_straight_flush, "Straight Flush"),
            (self.test_royal_flush, "Royal Flush"),
            (self.test_wheel_straight, "Wheel Straight (A-2-3-4-5)"),
            (self.test_compare_hands, "Compare Hands"),
            (self.test_hand_evaluator_class, "HandEvaluator Class"),
            (self.test_seven_card_hand, "7-Card Hand Selection"),
        ]

        results = []
        for test_func, name in tests:
            result = self.run_test(test_func, name)
            results.append(result)

        return results

    def test_high_card(self):
        from engine.hand_evaluator import evaluate_hand
        # Ah Kd Qc Js 9h (high card)
        cards = [(14, 0), (13, 1), (12, 2), (11, 0), (9, 3)]
        score = evaluate_hand(cards)
        self.assert_true(score < 1000000, "High card should be < 1M")
        self.log(f"High card score: {score}")

    def test_pair(self):
        from engine.hand_evaluator import evaluate_hand
        # AA + K Q J
        cards = [(14, 0), (14, 1), (13, 2), (12, 0), (11, 3)]
        score = evaluate_hand(cards)
        self.assert_true(1000000 <= score < 2000000, f"Pair should be 1M-2M, got {score}")
        self.log(f"Pair score: {score}")

    def test_two_pair(self):
        from engine.hand_evaluator import evaluate_hand
        # AA KK + Q
        cards = [(14, 0), (14, 1), (13, 2), (13, 0), (12, 3)]
        score = evaluate_hand(cards)
        self.assert_true(2000000 <= score < 3000000, f"Two pair should be 2M-3M, got {score}")
        self.log(f"Two pair score: {score}")

    def test_three_of_a_kind(self):
        from engine.hand_evaluator import evaluate_hand
        # AAA + K Q
        cards = [(14, 0), (14, 1), (14, 2), (13, 0), (12, 3)]
        score = evaluate_hand(cards)
        self.assert_true(3000000 <= score < 4000000, f"Trips should be 3M-4M, got {score}")
        self.log(f"Three of a kind score: {score}")

    def test_straight(self):
        from engine.hand_evaluator import evaluate_hand
        # A K Q J T (broadway)
        cards = [(14, 0), (13, 1), (12, 2), (11, 3), (10, 0)]
        score = evaluate_hand(cards)
        self.assert_true(4000000 <= score < 5000000, f"Straight should be 4M-5M, got {score}")
        self.log(f"Straight score: {score}")

    def test_flush(self):
        from engine.hand_evaluator import evaluate_hand
        # All hearts: A K Q J 9
        cards = [(14, 0), (13, 0), (12, 0), (11, 0), (9, 0)]
        score = evaluate_hand(cards)
        self.assert_true(5000000 <= score < 6000000, f"Flush should be 5M-6M, got {score}")
        self.log(f"Flush score: {score}")

    def test_full_house(self):
        from engine.hand_evaluator import evaluate_hand
        # AAA KK
        cards = [(14, 0), (14, 1), (14, 2), (13, 0), (13, 1)]
        score = evaluate_hand(cards)
        self.assert_true(6000000 <= score < 7000000, f"Full house should be 6M-7M, got {score}")
        self.log(f"Full house score: {score}")

    def test_four_of_a_kind(self):
        from engine.hand_evaluator import evaluate_hand
        # AAAA K
        cards = [(14, 0), (14, 1), (14, 2), (14, 3), (13, 0)]
        score = evaluate_hand(cards)
        self.assert_true(7000000 <= score < 8000000, f"Quads should be 7M-8M, got {score}")
        self.log(f"Four of a kind score: {score}")

    def test_straight_flush(self):
        from engine.hand_evaluator import evaluate_hand
        # 9h 8h 7h 6h 5h
        cards = [(9, 0), (8, 0), (7, 0), (6, 0), (5, 0)]
        score = evaluate_hand(cards)
        self.assert_true(8000000 <= score < 9000000, f"Straight flush should be 8M-9M, got {score}")
        self.log(f"Straight flush score: {score}")

    def test_royal_flush(self):
        from engine.hand_evaluator import evaluate_hand
        # Ah Kh Qh Jh Th
        cards = [(14, 0), (13, 0), (12, 0), (11, 0), (10, 0)]
        score = evaluate_hand(cards)
        self.assert_equal(score, 8000014, "Royal flush should be 8000014")
        self.log(f"Royal flush score: {score}")

    def test_wheel_straight(self):
        from engine.hand_evaluator import evaluate_hand
        # A 2 3 4 5 (wheel)
        cards = [(14, 0), (2, 1), (3, 2), (4, 3), (5, 0)]
        score = evaluate_hand(cards)
        self.assert_true(4000000 <= score < 5000000, f"Wheel should be straight 4M-5M, got {score}")
        self.assert_equal(score, 4000005, "Wheel high card should be 5")
        self.log(f"Wheel score: {score}")

    def test_compare_hands(self):
        from engine.hand_evaluator import compare_hands
        # AA vs KK
        hand1 = [(14, 0), (14, 1), (10, 2), (9, 3), (8, 0)]  # AA
        hand2 = [(13, 0), (13, 1), (10, 2), (9, 3), (8, 0)]  # KK
        result = compare_hands(hand1, hand2)
        self.assert_equal(result, 1, "AA should beat KK")

        # Same hand
        result = compare_hands(hand1, hand1)
        self.assert_equal(result, 0, "Same hand should be equal")
        self.log("Compare hands OK")

    def test_hand_evaluator_class(self):
        from engine.hand_evaluator import HandEvaluator
        evaluator = HandEvaluator()

        # Test Royal Flush
        result = evaluator.evaluate(['As', 'Ks', 'Qs', 'Js', 'Ts'])
        self.assert_equal(result['rank_name'], 'Royal Flush')
        self.assert_equal(result['rank'], 8)

        # Test Pair
        result = evaluator.evaluate(['Ah', 'Ad', 'Kc', 'Qs', 'Jh'])
        self.assert_equal(result['rank_name'], 'Pair')
        self.assert_equal(result['rank'], 1)
        self.log(f"HandEvaluator class OK")

    def test_seven_card_hand(self):
        from engine.hand_evaluator import evaluate_hand
        # 7 cards - should pick best 5
        # AA + flush cards but flush wins
        cards = [
            (14, 0), (14, 1),  # AA
            (13, 0), (12, 0), (11, 0), (9, 0), (8, 0)  # flush in hearts
        ]
        score = evaluate_hand(cards)
        self.assert_true(5000000 <= score < 6000000, f"Should find flush in 7 cards, got {score}")
        self.log(f"7-card hand score: {score}")


# ============================================
# Table Agent Tests
# ============================================

class TableAgentTests(TestSuite):
    """Тесты для Table Agent"""

    def run_all(self) -> List[TestResult]:
        tests = [
            (self.test_agent_config, "AgentConfig"),
            (self.test_connection_config, "ConnectionConfig"),
            (self.test_agent_initialization, "Agent Initialization"),
            (self.test_agent_states, "Agent States"),
            (self.test_dummy_executor, "DummyExecutor"),
            (self.test_table_layout, "TableLayout"),
            (self.test_game_state_parser, "GameStateParser"),
        ]

        results = []
        for test_func, name in tests:
            result = self.run_test(test_func, name)
            results.append(result)

        return results

    def test_agent_config(self):
        from table_agent.agent import AgentConfig
        config = AgentConfig(
            bot_id="test_bot",
            limit_type="NL10",
            table_key="table_123"
        )
        self.assert_equal(config.bot_id, "test_bot")
        self.assert_equal(config.limit_type, "NL10")
        self.assert_equal(config.table_key, "table_123")
        self.assert_equal(config.default_action, "fold")
        self.log("AgentConfig OK")

    def test_connection_config(self):
        from table_agent.connection import ConnectionConfig
        config = ConnectionConfig(
            api_url="http://localhost:8000",
            api_key="test_key",
            timeout=10.0
        )
        self.assert_equal(config.api_url, "http://localhost:8000")
        self.assert_equal(config.api_key, "test_key")
        self.assert_equal(config.timeout, 10.0)
        self.log("ConnectionConfig OK")

    def test_agent_initialization(self):
        from table_agent.agent import TableAgent, AgentConfig, AgentState
        from table_agent.connection import ConnectionConfig

        conn_config = ConnectionConfig(api_url="http://localhost:8000")
        agent_config = AgentConfig(bot_id="test", limit_type="NL10")

        agent = TableAgent(conn_config, agent_config)

        self.assert_true(agent.agent_id.startswith("agent_test_"))
        self.assert_equal(agent.state, AgentState.IDLE)
        self.assert_equal(agent.paused, False)
        self.assert_equal(agent.hands_played, 0)
        self.log(f"Agent ID: {agent.agent_id}")

    def test_agent_states(self):
        from table_agent.agent import AgentState
        states = [AgentState.IDLE, AgentState.CONNECTING, AgentState.WAITING,
                  AgentState.PLAYING, AgentState.ERROR, AgentState.STOPPED]

        self.assert_equal(len(states), 6)
        self.assert_equal(AgentState.IDLE.value, "idle")
        self.assert_equal(AgentState.PLAYING.value, "playing")
        self.log("Agent states OK")

    def test_dummy_executor(self):
        from table_agent.action_executor import DummyExecutor, TableLayout

        executor = DummyExecutor(TableLayout())

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute("fold", None)
        )
        self.assert_true(result)
        self.assert_equal(len(executor.action_log), 1)
        self.assert_equal(executor.action_log[0], ("execute", "fold", None))
        self.log("DummyExecutor OK")

    def test_table_layout(self):
        from table_agent.action_executor import TableLayout, ClickPosition, ActionType

        layout = TableLayout(
            fold_button=ClickPosition(100, 200, 50, 30),
            call_button=ClickPosition(200, 200, 50, 30)
        )

        fold_btn = layout.get_button(ActionType.FOLD)
        self.assert_equal(fold_btn.x, 100)
        self.assert_equal(fold_btn.y, 200)

        call_btn = layout.get_button(ActionType.CALL)
        self.assert_equal(call_btn.x, 200)
        self.log("TableLayout OK")

    def test_game_state_parser(self):
        from table_agent.game_state_parser import JSONGameStateParser

        parser = JSONGameStateParser()

        raw_state = {
            "hand_id": "test_hand_1",
            "table_id": "table_1",
            "hero_cards": "AsKh",
            "board_cards": "Qd7c2s",
            "hero_position": 3,
            "dealer": 0,
            "stacks": {"0": 100, "1": 99, "2": 98, "3": 100},
            "bets": {"0": 0, "1": 0.5, "2": 1, "3": 0},
            "total_bets": {"0": 0, "1": 0.5, "2": 1, "3": 0},
            "active_players": [0, 1, 2, 3],
            "pot": 1.5,
            "current_player": 3,
            "street": "flop"
        }

        parsed = parser.parse(raw_state)
        self.assert_equal(parsed.hand_id, "test_hand_1")
        self.assert_equal(parsed.hero_cards, "AsKh")
        self.assert_equal(parsed.hero_position, 3)
        self.assert_equal(parsed.street, "flop")
        self.log("GameStateParser OK")


# ============================================
# Database Tests
# ============================================

class DatabaseTests(TestSuite):
    """Тесты для Database"""

    def run_all(self) -> List[TestResult]:
        tests = [
            (self.test_models_import, "Models Import"),
            (self.test_database_connection, "Database Connection"),
            (self.test_crud_operations, "CRUD Operations"),
            (self.test_relationships, "Model Relationships"),
            (self.test_api_key_model, "APIKey Model"),
        ]

        results = []
        for test_func, name in tests:
            result = self.run_test(test_func, name)
            results.append(result)

        return results

    def test_models_import(self):
        from data.models import (
            Bot, Room, Table, BotSession, Hand,
            BotConfig, RakeModel, Agent, APIKey, OpponentProfile
        )
        self.log("All models imported OK")

    def test_database_connection(self):
        from data.database import SessionLocal, init_db

        init_db()
        db = SessionLocal()

        # Simple query
        result = db.execute("SELECT 1").fetchone()
        self.assert_equal(result[0], 1)

        db.close()
        self.log("Database connection OK")

    def test_crud_operations(self):
        from data.database import SessionLocal
        from data.models import Bot, Room

        db = SessionLocal()

        # Count existing
        bot_count = db.query(Bot).count()
        room_count = db.query(Room).count()

        self.assert_greater(bot_count, 0, "Should have bots")
        self.assert_greater(room_count, 0, "Should have rooms")

        self.log(f"Bots: {bot_count}, Rooms: {room_count}")
        db.close()

    def test_relationships(self):
        from data.database import SessionLocal
        from data.models import Bot, BotConfig, BotSession

        db = SessionLocal()

        # Get bot with configs
        bot = db.query(Bot).first()
        if bot:
            self.log(f"Bot: {bot.alias}, configs: {len(bot.configs)}")

        # Get session with table
        session = db.query(BotSession).first()
        if session:
            self.assert_true(session.table is not None, "Session should have table")
            self.log(f"Session table: {session.table_key}")

        db.close()

    def test_api_key_model(self):
        from data.database import SessionLocal
        from data.models import APIKey

        db = SessionLocal()

        api_keys = db.query(APIKey).all()
        self.assert_greater(len(api_keys), 0, "Should have API keys")

        key = api_keys[0]
        self.assert_true(len(key.key) > 20, "Key should be long enough")
        self.assert_true(isinstance(key.permissions, list), "Permissions should be list")

        self.log(f"API Key: {key.name}, permissions: {key.permissions}")
        db.close()


# ============================================
# Engine Tests
# ============================================

class EngineTests(TestSuite):
    """Тесты для Engine модулей"""

    def run_all(self) -> List[TestResult]:
        tests = [
            (self.test_cards_module, "Cards Module"),
            (self.test_card_parsing, "Card Parsing"),
            (self.test_deck_operations, "Deck Operations"),
        ]

        results = []
        for test_func, name in tests:
            result = self.run_test(test_func, name)
            results.append(result)

        return results

    def test_cards_module(self):
        from engine.cards import string_to_card, card_to_string
        self.log("Cards module imported OK")

    def test_card_parsing(self):
        from engine.cards import string_to_card, card_to_string

        # Test parsing
        card = string_to_card("As")
        self.assert_equal(card[0], 14, "Ace should be 14")
        self.assert_equal(card[1], 0, "Spades should be 0")

        card = string_to_card("2h")
        self.assert_equal(card[0], 2, "Deuce should be 2")
        self.assert_equal(card[1], 1, "Hearts should be 1")

        card = string_to_card("Td")
        self.assert_equal(card[0], 10, "Ten should be 10")

        self.log("Card parsing OK")

    def test_deck_operations(self):
        from engine.cards import string_to_card

        # Parse full hand
        cards = ["As", "Kh", "Qd", "Jc", "Ts"]
        parsed = [string_to_card(c) for c in cards]

        self.assert_equal(len(parsed), 5)
        self.assert_equal(parsed[0], (14, 0))  # As
        self.assert_equal(parsed[1], (13, 1))  # Kh

        self.log("Deck operations OK")


# ============================================
# Integration Tests
# ============================================

class IntegrationTests(TestSuite):
    """Интеграционные тесты"""

    def run_all(self) -> List[TestResult]:
        tests = [
            (self.test_hand_evaluation_pipeline, "Hand Evaluation Pipeline"),
            (self.test_agent_config_to_runner, "Agent Config to Runner"),
            (self.test_database_to_agent, "Database to Agent Flow"),
            (self.test_full_game_flow, "Full Game Flow Simulation"),
        ]

        results = []
        for test_func, name in tests:
            result = self.run_test(test_func, name)
            results.append(result)

        return results

    def test_hand_evaluation_pipeline(self):
        from engine.cards import string_to_card
        from engine.hand_evaluator import evaluate_hand, HandEvaluator

        # String -> parsed -> evaluated
        hand_str = ["As", "Ks", "Qs", "Js", "Ts"]
        parsed = [string_to_card(c) for c in hand_str]
        score = evaluate_hand(parsed)

        # Also via class
        evaluator = HandEvaluator()
        result = evaluator.evaluate(hand_str)

        self.assert_equal(score, result['score'])
        self.assert_equal(result['rank_name'], 'Royal Flush')
        self.log("Hand evaluation pipeline OK")

    def test_agent_config_to_runner(self):
        from table_agent.main import TableAgentRunner

        runner = TableAgentRunner(
            api_url="http://localhost:8000",
            bot_id="test_bot",
            limit_type="NL10",
            table_key="table_1",
            executor_type="dummy",
            room="pokerking"
        )

        self.assert_equal(runner.agent_config.bot_id, "test_bot")
        self.assert_equal(runner.agent_config.table_key, "table_1")
        self.assert_true(runner.executor is not None)
        self.log("Agent runner config OK")

    def test_database_to_agent(self):
        from data.database import SessionLocal
        from data.models import Bot, Table, APIKey
        from table_agent.agent import AgentConfig

        db = SessionLocal()

        # Get data from DB
        bot = db.query(Bot).first()
        table = db.query(Table).first()
        api_key = db.query(APIKey).filter(APIKey.is_active == True).first()

        # Create agent config from DB data
        if bot and table:
            config = AgentConfig(
                bot_id=bot.alias,
                limit_type=table.limit_type,
                table_key=table.external_table_id
            )

            self.assert_equal(config.bot_id, bot.alias)
            self.assert_equal(config.limit_type, table.limit_type)
            self.log(f"DB -> Agent: bot={bot.alias}, table={table.external_table_id}")

        db.close()

    def test_full_game_flow(self):
        from table_agent.game_state_parser import JSONGameStateParser
        from engine.hand_evaluator import HandEvaluator

        # Simulate game flow
        parser = JSONGameStateParser()
        evaluator = HandEvaluator()

        # 1. Parse game state
        game_state = {
            "hand_id": "test_123",
            "table_id": "table_1",
            "hero_cards": "AsKh",
            "board_cards": "Qs7c2d",
            "hero_position": 3,
            "dealer": 0,
            "stacks": {"0": 100, "3": 100},
            "bets": {"0": 1, "3": 0},
            "total_bets": {"0": 1, "3": 0},
            "active_players": [0, 3],
            "pot": 1.5,
            "current_player": 3,
            "street": "flop"
        }

        parsed = parser.parse(game_state)
        self.assert_equal(parsed.hero_cards, "AsKh")

        # 2. Evaluate hand strength
        hero_cards = ["As", "Kh"]
        board = ["Qs", "7c", "2d"]
        all_cards = hero_cards + board

        result = evaluator.evaluate(all_cards)
        self.log(f"Hand: {result['rank_name']} (score: {result['score']})")

        # 3. Check decision would be made
        self.assert_true(parsed.current_player == parsed.hero_position, "Should be hero's turn")

        self.log("Full game flow OK")


# ============================================
# Main Runner
# ============================================

def run_all_tests(verbose: bool = False, module: str = None):
    """Запуск всех тестов"""

    print("\n" + "=" * 60)
    print("    POKER RAKE BOT - FULL TEST SUITE")
    print("=" * 60 + "\n")

    all_suites = {
        "hand_evaluator": ("Hand Evaluator", HandEvaluatorTests),
        "table_agent": ("Table Agent", TableAgentTests),
        "database": ("Database", DatabaseTests),
        "engine": ("Engine", EngineTests),
        "integration": ("Integration", IntegrationTests),
    }

    if module:
        if module in all_suites:
            all_suites = {module: all_suites[module]}
        else:
            print(f"Unknown module: {module}")
            print(f"Available: {list(all_suites.keys())}")
            return

    total_passed = 0
    total_failed = 0
    total_time = 0

    for key, (name, suite_class) in all_suites.items():
        print(f"\n{'─' * 50}")
        print(f"  {name} Tests")
        print(f"{'─' * 50}")

        suite = suite_class(verbose=verbose)

        try:
            results = suite.run_all()
        except Exception as e:
            print(f"  SUITE ERROR: {e}")
            traceback.print_exc()
            continue

        for result in results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            time_str = f"({result.duration_ms:.1f}ms)"

            print(f"  {status} {result.name} {time_str}")

            if not result.passed:
                print(f"       Error: {result.message}")

            if result.passed:
                total_passed += 1
            else:
                total_failed += 1

            total_time += result.duration_ms

    # Summary
    print("\n" + "=" * 60)
    print("    SUMMARY")
    print("=" * 60)
    print(f"  Total:  {total_passed + total_failed} tests")
    print(f"  Passed: {total_passed} ✅")
    print(f"  Failed: {total_failed} ❌")
    print(f"  Time:   {total_time:.1f}ms")
    print("=" * 60)

    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED!\n")
        return 0
    else:
        print(f"\n⚠️  {total_failed} TESTS FAILED\n")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run full test suite")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--module", "-m", help="Test specific module")

    args = parser.parse_args()

    exit_code = run_all_tests(verbose=args.verbose, module=args.module)
    sys.exit(exit_code)
