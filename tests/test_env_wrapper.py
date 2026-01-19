"""Тесты для env_wrapper"""

import pytest
from engine.env_wrapper import PokerEnv, Street


def test_env_initialization():
    """Тест инициализации среды"""
    env = PokerEnv(num_players=6, small_blind=0.5, big_blind=1.0, stack_size=100.0)
    assert env.num_players == 6
    assert env.big_blind == 1.0
    assert env.stack_size == 100.0


def test_reset():
    """Тест сброса раздачи"""
    env = PokerEnv(num_players=6)
    state = env.reset(hand_id="test_hand_1")
    
    assert state is not None
    assert len(state.hero_cards) == 2
    assert state.street == Street.PREFLOP
    assert state.pot > 0  # Блайнды
    assert len(state.active_players) == 6


def test_step_fold():
    """Тест действия fold"""
    env = PokerEnv(num_players=6)
    state = env.reset()
    
    # Первый игрок фолдит
    state, done, info = env.step("fold")
    
    assert state.current_player in state.active_players
    assert len(state.active_players) == 5


def test_step_call():
    """Тест действия call"""
    env = PokerEnv(num_players=6)
    state = env.reset()
    
    # Игрок коллирует блайнд
    call_amount = state.big_blind - state.bets.get(state.current_player, 0)
    if call_amount > 0:
        state, done, info = env.step("call")
        assert not done


def test_step_check():
    """Тест действия check"""
    env = PokerEnv(num_players=6)
    state = env.reset()
    
    # После колла всех, можно чекнуть
    # (упрощенный тест)
    pass


def test_side_pots():
    """Тест side pots (упрощенный)"""
    # В будущем: тест с алл-инами разных размеров
    pass
