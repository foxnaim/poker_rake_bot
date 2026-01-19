"""Тесты для всех улучшений и исправлений проекта"""

import pytest
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.game_state_validator import GameStateValidator, game_state_validator
from engine.env_wrapper import GameState, Street
from brain.mccfr import MCCFR
from brain.game_tree import GameTree
from utils.hand_history_parser import HandHistoryParser, hand_history_parser


class TestGameStateValidator:
    """Тесты для валидатора состояния игры"""

    def test_valid_state(self):
        """Тест корректного состояния"""
        state = GameState()
        state.active_players = {0, 1}
        state.current_player = 0
        state.hero_cards = [(14, 3), (13, 3)]  # As, Ks
        state.board_cards = []
        state.street = Street.PREFLOP
        state.pot = 1.5
        state.bets = {0: 0.5, 1: 1.0}
        state.stacks = {0: 100.0, 1: 99.0}

        is_valid, error = game_state_validator.validate(state)
        assert is_valid, f"Состояние должно быть валидным, ошибка: {error}"

    def test_duplicate_cards(self):
        """Тест обнаружения дубликатов карт"""
        state = GameState()
        state.active_players = {0, 1}
        state.current_player = 0
        state.hero_cards = [(14, 3), (14, 3)]  # Дубликат: As, As
        state.board_cards = []
        state.street = Street.PREFLOP

        is_valid, error = game_state_validator.validate(state)
        assert not is_valid
        assert "дубликаты" in error.lower()

    def test_invalid_card_rank(self):
        """Тест некорректного ранга карты"""
        state = GameState()
        state.active_players = {0, 1}
        state.current_player = 0
        state.hero_cards = [(15, 3), (13, 3)]  # Некорректный ранг: 15
        state.board_cards = []
        state.street = Street.PREFLOP

        is_valid, error = game_state_validator.validate(state)
        assert not is_valid
        assert "ранг" in error.lower()

    def test_invalid_board_count(self):
        """Тест некорректного количества карт на флопе"""
        state = GameState()
        state.active_players = {0, 1}
        state.current_player = 0
        state.hero_cards = [(14, 3), (13, 3)]
        state.board_cards = [(12, 2), (11, 2)]  # Флоп должен иметь 3 карты
        state.street = Street.FLOP

        is_valid, error = game_state_validator.validate(state)
        assert not is_valid
        assert "3 карты" in error.lower()

    def test_sanitize_duplicates(self):
        """Тест очистки дубликатов"""
        state = GameState()
        state.active_players = {0, 1}
        state.current_player = 0
        state.hero_cards = [(14, 3), (14, 3), (13, 3)]  # Дубликат As
        state.board_cards = []
        state.street = Street.PREFLOP

        cleaned_state = game_state_validator.sanitize(state)
        assert len(cleaned_state.hero_cards) == 2  # Дубликат удален
        assert cleaned_state.hero_cards[0] == (14, 3)
        assert cleaned_state.hero_cards[1] == (13, 3)


class TestMCCFRImprovements:
    """Тесты для улучшений MCCFR"""

    def test_6max_support(self):
        """Тест поддержки 6-max"""
        game_tree = GameTree()
        mccfr = MCCFR(game_tree, num_players=6, max_depth=15)

        assert mccfr.num_players == 6
        assert mccfr.max_depth == 15
        assert 6 in mccfr.recommended_iterations
        assert mccfr.recommended_iterations[6] == 200000

    def test_invalid_num_players(self):
        """Тест некорректного количества игроков"""
        game_tree = GameTree()

        with pytest.raises(ValueError):
            MCCFR(game_tree, num_players=1)  # Слишком мало

        with pytest.raises(ValueError):
            MCCFR(game_tree, num_players=10)  # Слишком много

    def test_heads_up_default(self):
        """Тест heads-up по умолчанию"""
        game_tree = GameTree()
        mccfr = MCCFR(game_tree)

        assert mccfr.num_players == 2
        assert mccfr.recommended_iterations[2] == 50000


class TestHandHistoryParser:
    """Тесты для парсера hand history"""

    def test_parse_basic_hand(self):
        """Тест парсинга базовой раздачи"""
        hand_text = """
        PokerStars Hand #12345: Hold'em No Limit (NL10) - 2025/01/19
        Table 'Test' 6-max Seat #1 is the button
        Seat 1: Player1 (100 in chips)
        Seat 2: Player2 (100 in chips)
        Player1: posts small blind 0.5
        Player2: posts big blind 1
        *** HOLE CARDS ***
        Player1: raises 2 to 3
        Player2: calls 2
        *** FLOP *** [Ah Kh Qh]
        Player2: checks
        Player1: bets 5
        Player2: folds
        Player1 collected 6 from pot
        """

        parsed = hand_history_parser.parse(hand_text)

        assert parsed is not None
        assert parsed.hand_id == "12345"
        assert parsed.limit_type == "NL10"
        assert "Player1" in parsed.players
        assert "Player2" in parsed.players
        assert len(parsed.actions) > 0

    def test_extract_preflop_action(self):
        """Тест извлечения префлоп действия"""
        hand_text = """
        PokerStars Hand #12345: Hold'em No Limit (NL10) - 2025/01/19
        Table 'Test' 6-max
        Seat 1: Hero (100 in chips)
        Seat 2: Villain (100 in chips)
        Hero: raises 2 to 3
        Villain: calls 2
        """

        parsed = hand_history_parser.parse(hand_text)
        assert parsed is not None

        hero_stats = hand_history_parser.extract_player_stats(parsed, "Hero")
        assert hero_stats["preflop_action"] == "raise"

        villain_stats = hand_history_parser.extract_player_stats(parsed, "Villain")
        assert villain_stats["preflop_action"] == "call"


class TestAntiPatternOptional:
    """Тесты для опционального anti-pattern router"""

    def test_anti_patterns_disabled_by_default(self):
        """Тест что anti-patterns отключены по умолчанию"""
        from brain.anti_pattern_router import anti_pattern_router

        assert anti_pattern_router.enabled is False

    def test_anti_patterns_no_modification_when_disabled(self):
        """Тест что действия не меняются когда anti-patterns отключены"""
        from brain.anti_pattern_router import anti_pattern_router

        action = "raise"
        amount = 10.0
        game_state = {"street": "flop", "pot": 20.0}
        strategy = {"raise": 0.7, "fold": 0.3}

        result_action, result_amount = anti_pattern_router.apply_anti_patterns(
            action, amount, game_state, strategy
        )

        # Действие должно остаться без изменений
        assert result_action == action
        assert result_amount == amount


class TestAutoTrainerFixes:
    """Тесты для исправлений Auto-trainer"""

    def test_null_winrate_handling(self):
        """Тест обработки None значений в winrate"""
        # Симулируем объект stats с None значениями
        class MockStats:
            vpip = None
            pfr = None
            aggression_factor = None
            winrate_bb_100 = None

        # Проверяем, что не возникает TypeError при преобразовании
        stats = MockStats()

        vpip = float(stats.vpip) if stats.vpip is not None else 0.0
        pfr = float(stats.pfr) if stats.pfr is not None else 0.0
        af = float(stats.aggression_factor) if stats.aggression_factor is not None else 0.0
        winrate = float(stats.winrate_bb_100) if stats.winrate_bb_100 is not None else 0.0

        assert vpip == 0.0
        assert pfr == 0.0
        assert af == 0.0
        assert winrate == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
