"""Тесты для MCCFR"""

import pytest
pytest.importorskip("numpy")
from brain.game_tree import GameTree, GameNode, NodeType
from brain.mccfr import MCCFR


def test_game_tree_initialization():
    """Тест инициализации дерева игры"""
    game_tree = GameTree()
    assert game_tree.root is not None
    assert len(game_tree.nodes) == 0


def test_game_node_strategy():
    """Тест вычисления стратегии узла"""
    node = GameNode(NodeType.DECISION, "test_infoset")
    node.actions = ["fold", "call", "raise"]
    
    # Инициализируем regret
    node.regret_sum["fold"] = 0.0
    node.regret_sum["call"] = 10.0
    node.regret_sum["raise"] = 5.0
    
    strategy = node.get_strategy(1.0)
    
    # Проверяем, что вероятности суммируются в 1
    assert abs(sum(strategy.values()) - 1.0) < 0.01
    
    # Проверяем, что call имеет большую вероятность (больший regret)
    assert strategy["call"] > strategy["fold"]


def test_game_node_average_strategy():
    """Тест усредненной стратегии"""
    node = GameNode(NodeType.DECISION, "test_infoset")
    node.actions = ["fold", "call"]
    
    # Симулируем несколько обновлений
    for i in range(10):
        node.get_strategy(1.0)
        node.strategy_sum["fold"] += 0.3
        node.strategy_sum["call"] += 0.7
    
    avg_strategy = node.get_average_strategy()
    
    # Проверяем, что усредненная стратегия близка к ожидаемой
    assert abs(sum(avg_strategy.values()) - 1.0) < 0.01


def test_infoset_generation():
    """Тест генерации информационных множеств"""
    game_tree = GameTree()
    
    infoset = game_tree.get_infoset(
        street=0,
        player=0,
        cards=((14, 3), (13, 2)),  # AsKh
        board=(),
        pot=10.0,
        bet_sequence="rc"
    )
    
    assert infoset is not None
    assert isinstance(infoset, str)
    assert "0_" in infoset  # Улица
    assert "rc" in infoset  # Последовательность ставок


def test_available_actions():
    """Тест получения доступных действий"""
    game_tree = GameTree()
    
    actions = game_tree.get_available_actions(
        street=0,  # Preflop
        pot=10.0,
        current_bet=1.0,
        stack=100.0,
        last_raise=1.0,
        num_raises=0
    )
    
    assert "fold" in actions
    assert "call" in actions
    assert len(actions) > 0


def test_mccfr_initialization():
    """Тест инициализации MCCFR"""
    game_tree = GameTree()
    mccfr = MCCFR(game_tree, num_players=2)
    
    assert mccfr.game_tree == game_tree
    assert mccfr.num_players == 2
    assert mccfr.iterations == 0


def test_mccfr_training_small():
    """Тест небольшого обучения MCCFR"""
    game_tree = GameTree()
    mccfr = MCCFR(game_tree, num_players=2)
    
    # Обучаем на небольшом количестве итераций
    mccfr.train(10, verbose=False)
    
    assert mccfr.iterations == 10
    assert len(game_tree.nodes) > 0  # Должны появиться узлы


def test_regret_computation():
    """Тест вычисления regret"""
    game_tree = GameTree()
    mccfr = MCCFR(game_tree, num_players=2)
    
    # Обучаем немного
    mccfr.train(100, verbose=False)
    
    # Проверяем, что regret вычисляется
    avg_regret = mccfr._compute_avg_regret()
    assert avg_regret >= 0.0  # Regret должен быть неотрицательным
