"""Тесты для Decision Router"""

import pytest
from brain.decision_router import DecisionRouter
from pathlib import Path


def test_router_initialization():
    """Тест инициализации роутера"""
    router = DecisionRouter()
    assert router.decision_weights is not None
    assert "preflop" in router.decision_weights


def test_mix_strategies():
    """Тест смешивания стратегий"""
    router = DecisionRouter()
    
    gto_strategy = {
        "fold": 0.2,
        "call": 0.5,
        "raise": 0.3
    }
    
    exploit_adjustments = {
        "type": "value_heavy",
        "adjustments": {
            "bluff_frequency": -0.2,  # Уменьшить блефы
            "value_bet_frequency": 0.1  # Увеличить value
        }
    }
    
    mixed = router._mix_strategies(gto_strategy, exploit_adjustments, "flop")
    
    # Проверяем, что вероятности суммируются в 1
    assert abs(sum(mixed.values()) - 1.0) < 0.01
    
    # Проверяем, что raise (блеф) уменьшился
    assert mixed["raise"] < gto_strategy["raise"]


def test_get_available_actions():
    """Тест получения доступных действий"""
    router = DecisionRouter()
    
    game_state = {
        "current_bet": 1.0,
        "stack": 100.0
    }
    
    actions = router._get_available_actions(game_state)
    assert "fold" in actions
    assert "call" in actions
    
    game_state["current_bet"] = 0.0
    actions = router._get_available_actions(game_state)
    assert "check" in actions


def test_sample_action():
    """Тест выбора действия"""
    router = DecisionRouter()
    
    strategy = {
        "fold": 0.1,
        "call": 0.6,
        "raise": 0.3
    }
    
    game_state = {
        "pot": 10.0,
        "stack": 100.0
    }
    
    action, amount = router._sample_action(strategy, game_state)
    
    assert action in ["fold", "call", "raise"]
    if action == "raise":
        assert amount is not None


def test_adjust_to_style_targets():
    """Тест корректировки под целевые параметры"""
    router = DecisionRouter()
    
    strategy = {
        "fold": 0.3,
        "call": 0.4,
        "raise": 0.3
    }
    
    # Устанавливаем низкий VPIP
    router.current_stats["vpip"] = 20.0
    
    adjusted = router._adjust_to_style_targets(strategy, "preflop", "NL10", "neutral")
    
    # Проверяем нормализацию
    assert abs(sum(adjusted.values()) - 1.0) < 0.01
