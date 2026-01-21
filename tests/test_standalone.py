"""
Standalone тесты, не требующие Docker/PostgreSQL

Тестируют:
- Hand History Parsers (PokerStars, 888poker, PartyPoker)
- Screen Reader (mock)
- Game State Parser
- Hand Evaluator
"""

import pytest
import sys
import os

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHandHistoryParser:
    """Тесты для парсеров hand history"""

    def test_pokerstars_parser_loads(self):
        """Проверяет что PokerStars парсер загружается"""
        from utils.hand_history_parser import HandHistoryParser
        parser = HandHistoryParser()
        assert 'pokerstars' in parser.parsers

    def test_888poker_parser_loads(self):
        """Проверяет что 888poker парсер загружается"""
        from utils.hand_history_parser import HandHistoryParser
        parser = HandHistoryParser()
        assert '888poker' in parser.parsers

    def test_partypoker_parser_loads(self):
        """Проверяет что PartyPoker парсер загружается"""
        from utils.hand_history_parser import HandHistoryParser
        parser = HandHistoryParser()
        assert 'partypoker' in parser.parsers

    def test_pokerstars_hand_parsing(self):
        """Тестирует парсинг PokerStars hand history"""
        from utils.hand_history_parser import HandHistoryParser

        sample_hand = """
PokerStars Hand #123456789: Hold'em No Limit ($0.05/$0.10 USD) - 2024/01/15 12:34:56 ET
Table 'TestTable' 6-max Seat #1 is the button
Seat 1: Player1 ($10.00 in chips)
Seat 2: Hero ($10.00 in chips)
Seat 3: Player3 ($10.00 in chips)
Player1: posts small blind $0.05
Hero: posts big blind $0.10
*** HOLE CARDS ***
Dealt to Hero [As Kh]
Player3: folds
Player1: raises $0.20 to $0.30
Hero: calls $0.20
*** FLOP *** [Qd Jc Ts]
Player1: bets $0.50
Hero: raises $1.00 to $1.50
Player1: calls $1.00
*** TURN *** [Qd Jc Ts] [9h]
Player1: checks
Hero: bets $2.00
Player1: folds
Uncalled bet ($2.00) returned to Hero
Hero collected $3.70 from pot
*** SUMMARY ***
Total pot $3.90 | Rake $0.20
        """

        parser = HandHistoryParser()
        hands = parser._parse_pokerstars(sample_hand)

        assert len(hands) == 1
        hand = hands[0]

        assert hand['hand_id'] == 'PS_123456789'
        assert hand['limit_type'] == 'NL10'
        assert hand['hero_cards'] == 'AsKh'
        assert 'QdJcTs' in hand['board_cards']
        assert hand['pot_size'] == 3.90
        assert hand['rake_amount'] == 0.20

    def test_888poker_hand_parsing(self):
        """Тестирует парсинг 888poker hand history"""
        from utils.hand_history_parser import HandHistoryParser

        sample_hand = """
***** 888poker Hand History for Game 9876543210 *****
$0.05/$0.10 Blinds No Limit Holdem - *** 15 01 2024 12:34:56
Table TestTable 6 Max (Real Money)
Seat 1 is the button
Total number of players : 3
Seat 1: Player1 ( $10.00 )
Seat 2: Hero ( $10.00 )
Seat 3: Player3 ( $10.00 )
Player1 posts small blind [$0.05]
Hero posts big blind [$0.10]
** Dealing down cards **
Dealt to Hero [ Ks, Qh ]
Player3 folds
Player1 calls [$0.05]
Hero checks
** Dealing Flop ** [ Jd, Tc, 9s ]
Hero bets [$0.20]
Player1 calls [$0.20]
** Dealing Turn ** [ 8h ]
Hero bets [$0.50]
Player1 folds
Hero wins $0.60
        """

        parser = HandHistoryParser()
        hands = parser._parse_888poker(sample_hand)

        assert len(hands) == 1
        hand = hands[0]

        assert hand['hand_id'] == '888_9876543210'
        assert hand['limit_type'] == 'NL10'
        assert hand['hero_cards'] == 'KsQh'

    def test_partypoker_hand_parsing(self):
        """Тестирует парсинг PartyPoker hand history"""
        from utils.hand_history_parser import HandHistoryParser

        sample_hand = """
***** Hand History for Game 5555555555 *****
$0.05/$0.10 USD NL Texas Hold'em - Monday, January 15, 12:34:56 CET 2024
Table TestTable (Real Money)
Seat 1 is the button
Total number of players : 3
Seat 1: Player1 ( $10 USD )
Seat 2: Hero ( $10 USD )
Seat 3: Player3 ( $10 USD )
** Dealing down cards **
Dealt to Hero [ Ah Kd ]
Player3 folds
Player1 raises [$0.30]
Hero calls [$0.30]
** Dealing Flop ** [ Qs Jh Tc ]
Player1 bets [$0.50]
Hero raises [$1.50]
Player1 folds
Hero wins $1.70
        """

        parser = HandHistoryParser()
        hands = parser._parse_partypoker(sample_hand)

        assert len(hands) == 1
        hand = hands[0]

        assert hand['hand_id'] == 'PP_5555555555'
        assert hand['limit_type'] == 'NL10'
        assert hand['hero_cards'] == 'AhKd'


class TestScreenReader:
    """Тесты для Screen Reader"""

    def test_layouts_available(self):
        """Проверяет доступность layouts"""
        # Импортируем напрямую без __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "screen_reader",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "table_agent/screen_reader.py")
        )
        screen_reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(screen_reader)

        assert 'pokerking' in screen_reader.LAYOUTS
        assert 'pokerstars' in screen_reader.LAYOUTS
        assert '888poker' in screen_reader.LAYOUTS

    def test_mock_screen_reader(self):
        """Тестирует mock screen reader"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "screen_reader",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "table_agent/screen_reader.py")
        )
        screen_reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(screen_reader)

        sr = screen_reader.create_screen_reader('pokerking', mock=True)
        state = sr.read_table_state()

        assert 'hero_cards' in state
        assert 'pot' in state
        assert 'player_stacks' in state
        assert 'available_buttons' in state
        assert state['hero_cards'] == 'AsKh'

    def test_mock_state_modification(self):
        """Тестирует изменение mock состояния"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "screen_reader",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "table_agent/screen_reader.py")
        )
        screen_reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(screen_reader)

        sr = screen_reader.create_screen_reader('pokerstars', mock=True)

        # Изменяем состояние
        sr.set_mock_state({
            'hero_cards': 'QdQs',
            'pot': 15.0,
            'board_cards': 'AsKhJc'
        })

        state = sr.read_table_state()
        assert state['hero_cards'] == 'QdQs'
        assert state['pot'] == 15.0
        assert state['board_cards'] == 'AsKhJc'


class TestGameStateParser:
    """Тесты для Game State Parser"""

    def test_json_parser(self):
        """Тестирует JSON парсер"""
        from table_agent.game_state_parser import JSONGameStateParser

        parser = JSONGameStateParser()

        raw_data = {
            "hand_id": "test_hand_1",
            "table_id": "test_table",
            "hero_cards": "As Kh",
            "board_cards": "Qd Jc Ts",
            "hero_position": 2,
            "dealer": 0,
            "current_player": 2,
            "pot": 10.0,
            "small_blind": 0.5,
            "big_blind": 1.0,
            "stacks": {"0": 100.0, "1": 95.0, "2": 110.0},
            "bets": {"0": 0.0, "1": 0.5, "2": 1.0},
            "total_bets": {"0": 0.0, "1": 0.5, "2": 1.0},
            "active_players": [0, 1, 2],
            "street": "preflop",
            "last_raise_amount": 0.5
        }

        state = parser.parse(raw_data)

        assert state is not None
        assert state.hand_id == "test_hand_1"
        assert state.hero_cards == "AsKh"
        assert state.board_cards == "QdJcTs"
        assert state.pot == 10.0
        assert len(state.players) == 3

    def test_card_normalization(self):
        """Тестирует нормализацию карт"""
        from table_agent.game_state_parser import GameStateParser

        parser = GameStateParser()

        # Тесты различных форматов
        assert parser.parse_cards("As Kh") == "AsKh"
        assert parser.parse_cards("as,kh") == "AsKh"
        assert parser.parse_cards("A♠K♥") == "AsKh"
        assert parser.parse_cards("10s 10h") == "TsTh"

    def test_position_parsing(self):
        """Тестирует парсинг позиций"""
        from table_agent.game_state_parser import GameStateParser

        parser = GameStateParser()

        assert parser.parse_position("btn") == 0
        assert parser.parse_position("sb") == 1
        assert parser.parse_position("bb") == 2
        assert parser.parse_position("utg") == 3
        assert parser.parse_position("co") == 5

    def test_to_api_format(self):
        """Тестирует конвертацию в API формат"""
        from table_agent.game_state_parser import JSONGameStateParser

        parser = JSONGameStateParser()

        raw_data = {
            "hand_id": "test_hand",
            "table_id": "table_1",
            "hero_cards": "AhKd",
            "board_cards": "",
            "hero_position": 0,
            "dealer": 0,
            "current_player": 1,
            "pot": 1.5,
            "small_blind": 0.5,
            "big_blind": 1.0,
            "stacks": {"0": 100.0, "1": 99.5},
            "bets": {"0": 0.0, "1": 0.5},
            "total_bets": {"0": 0.0, "1": 0.5},
            "active_players": [0, 1],
            "street": "preflop",
            "last_raise_amount": 0.0
        }

        state = parser.parse(raw_data)
        api_format = state.to_api_format()

        assert api_format['hand_id'] == 'test_hand'
        assert api_format['hero_cards'] == 'AhKd'
        assert api_format['street'] == 'preflop'
        assert api_format['pot'] == 1.5
        assert '0' in api_format['stacks']


class TestHandEvaluator:
    """Тесты для оценщика рук"""

    def test_hand_evaluator_import(self):
        """Проверяет импорт hand evaluator"""
        from engine.hand_evaluator import HandEvaluator
        evaluator = HandEvaluator()
        assert evaluator is not None

    def test_royal_flush(self):
        """Тестирует определение Royal Flush"""
        from engine.hand_evaluator import HandEvaluator

        evaluator = HandEvaluator()
        hand = ["As", "Ks", "Qs", "Js", "Ts"]
        result = evaluator.evaluate(hand)

        assert result is not None
        assert result['rank_name'] == 'Royal Flush'

    def test_straight_flush(self):
        """Тестирует определение Straight Flush"""
        from engine.hand_evaluator import HandEvaluator

        evaluator = HandEvaluator()
        hand = ["9h", "8h", "7h", "6h", "5h"]
        result = evaluator.evaluate(hand)

        assert result is not None
        assert result['rank_name'] == 'Straight Flush'

    def test_four_of_a_kind(self):
        """Тестирует определение Four of a Kind"""
        from engine.hand_evaluator import HandEvaluator

        evaluator = HandEvaluator()
        hand = ["Kh", "Kd", "Kc", "Ks", "2h"]
        result = evaluator.evaluate(hand)

        assert result is not None
        assert result['rank_name'] == 'Four of a Kind'

    def test_full_house(self):
        """Тестирует определение Full House"""
        from engine.hand_evaluator import HandEvaluator

        evaluator = HandEvaluator()
        hand = ["Ah", "Ad", "Ac", "Ks", "Kh"]
        result = evaluator.evaluate(hand)

        assert result is not None
        assert result['rank_name'] == 'Full House'

    def test_flush(self):
        """Тестирует определение Flush"""
        from engine.hand_evaluator import HandEvaluator

        evaluator = HandEvaluator()
        hand = ["Ah", "Kh", "Jh", "8h", "3h"]
        result = evaluator.evaluate(hand)

        assert result is not None
        assert result['rank_name'] == 'Flush'

    def test_straight(self):
        """Тестирует определение Straight"""
        from engine.hand_evaluator import HandEvaluator

        evaluator = HandEvaluator()
        hand = ["9h", "8d", "7c", "6s", "5h"]
        result = evaluator.evaluate(hand)

        assert result is not None
        assert result['rank_name'] == 'Straight'

    def test_three_of_a_kind(self):
        """Тестирует определение Three of a Kind"""
        from engine.hand_evaluator import HandEvaluator

        evaluator = HandEvaluator()
        hand = ["Qh", "Qd", "Qc", "8s", "3h"]
        result = evaluator.evaluate(hand)

        assert result is not None
        assert result['rank_name'] == 'Three of a Kind'

    def test_two_pair(self):
        """Тестирует определение Two Pair"""
        from engine.hand_evaluator import HandEvaluator

        evaluator = HandEvaluator()
        hand = ["Ah", "Ad", "Kc", "Ks", "3h"]
        result = evaluator.evaluate(hand)

        assert result is not None
        assert result['rank_name'] == 'Two Pair'

    def test_one_pair(self):
        """Тестирует определение One Pair"""
        from engine.hand_evaluator import HandEvaluator

        evaluator = HandEvaluator()
        hand = ["Ah", "Ad", "Kc", "Js", "3h"]
        result = evaluator.evaluate(hand)

        assert result is not None
        assert result['rank_name'] == 'Pair'

    def test_high_card(self):
        """Тестирует определение High Card"""
        from engine.hand_evaluator import HandEvaluator

        evaluator = HandEvaluator()
        hand = ["Ah", "Kd", "Jc", "8s", "3h"]
        result = evaluator.evaluate(hand)

        assert result is not None
        assert result['rank_name'] == 'High Card'


class TestAntiPatternRouter:
    """Тесты для Anti-Pattern Router"""

    def test_fingerprint_controller_init(self):
        """Тестирует инициализацию FingerprintController"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "anti_pattern_router",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "brain/anti_pattern_router.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        fc = module.FingerprintController(window_size=500)
        assert fc.window_size == 500
        assert len(fc.action_history) == 0

    def test_human_reference_patterns(self):
        """Проверяет наличие референсных паттернов"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "anti_pattern_router",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "brain/anti_pattern_router.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        ref = module.FingerprintController.HUMAN_REFERENCE

        assert 'action_distribution' in ref
        assert 'bet_sizing' in ref
        assert 'timing' in ref
        assert 'rare_lines' in ref

        # Проверяем конкретные значения
        assert ref['timing']['avg_decision_ms'] == 2500
        assert ref['rare_lines']['donk_bet_frequency'] == 0.06


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
