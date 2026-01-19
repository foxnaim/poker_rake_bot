"""Дерево игры для MCCFR"""

from typing import Dict, List, Optional, Tuple, Set
from enum import IntEnum
import numpy as np
from collections import defaultdict
from numba import jit


class NodeType(IntEnum):
    """Типы узлов в дереве игры"""
    DECISION = 0  # Узел принятия решения
    CHANCE = 1   # Узел случайного события (раздача карт)
    TERMINAL = 2  # Терминальный узел (конец раздачи)


class GameNode:
    """Узел в дереве игры"""
    
    def __init__(self, node_type: NodeType, infoset: str = ""):
        self.node_type = node_type
        self.infoset = infoset  # Информационное множество
        self.children: Dict[str, 'GameNode'] = {}
        self.regret_sum: Dict[str, float] = defaultdict(float)
        self.strategy_sum: Dict[str, float] = defaultdict(float)
        self.strategy: Dict[str, float] = {}
        self.reach_prob: float = 0.0
        self.player: Optional[int] = None  # Игрок, принимающий решение
        self.actions: List[str] = []  # Доступные действия
        
    def get_strategy(self, realization_prob: float) -> Dict[str, float]:
        """
        Вычисляет текущую стратегию через regret matching (оптимизировано)
        
        Args:
            realization_prob: Вероятность достижения этого узла
            
        Returns:
            Словарь {действие: вероятность}
        """
        # Используем numpy для быстрых вычислений
        actions_list = self.actions
        regrets = np.array([max(self.regret_sum[action], 0.0) for action in actions_list], dtype=np.float64)
        normalizing_sum = float(np.sum(regrets))
        
        # Нормализация
        if normalizing_sum > 0:
            strategy_values = regrets / normalizing_sum
        else:
            # Равномерная стратегия если нет положительных regret
            strategy_values = np.ones(len(actions_list), dtype=np.float64) / len(actions_list)
        
        # Обновляем strategy
        for i, action in enumerate(actions_list):
            self.strategy[action] = float(strategy_values[i])
            # Обновляем strategy_sum для усреднения
            self.strategy_sum[action] += realization_prob * self.strategy[action]
        
        return self.strategy
    
    def get_average_strategy(self) -> Dict[str, float]:
        """
        Возвращает усредненную стратегию
        
        Returns:
            Словарь {действие: вероятность}
        """
        normalizing_sum = sum(self.strategy_sum.values())
        
        if normalizing_sum > 0:
            return {action: self.strategy_sum[action] / normalizing_sum 
                   for action in self.actions}
        else:
            # Равномерная стратегия
            return {action: 1.0 / len(self.actions) for action in self.actions}


class GameTree:
    """Дерево игры для покера"""
    
    def __init__(self, max_raise_sizes: Dict[int, int] = None):
        """
        Args:
            max_raise_sizes: Максимальное количество размеров ставки на каждой улице
                           {Street.PREFLOP: 2, Street.FLOP: 2, ...}
        """
        self.root = GameNode(NodeType.DECISION)
        self.nodes: Dict[str, GameNode] = {}  # Кэш узлов по infoset
        self.max_raise_sizes = max_raise_sizes or {
            0: 2,  # PREFLOP: 2 размера
            1: 2,  # FLOP: 2 размера
            2: 3,  # TURN: 3 размера
            3: 3   # RIVER: 3 размера
        }
        
    def get_node(self, infoset: str, actions: List[str], player: int) -> GameNode:
        """
        Получает или создает узел по информационному множеству
        
        Args:
            infoset: Информационное множество (уникальный идентификатор состояния)
            actions: Доступные действия
            player: Игрок, принимающий решение
            
        Returns:
            Узел игры
        """
        if infoset not in self.nodes:
            node = GameNode(NodeType.DECISION, infoset)
            node.actions = actions
            node.player = player
            self.nodes[infoset] = node
        else:
            node = self.nodes[infoset]
            # Обновляем действия если нужно
            if not node.actions:
                node.actions = actions
        
        return node
    
    def get_infoset(self, street: int, player: int, cards: Tuple, board: Tuple, 
                   pot: float, bet_sequence: str) -> str:
        """
        Генерирует информационное множество
        
        Args:
            street: Улица (0=preflop, 1=flop, 2=turn, 3=river)
            player: Игрок
            cards: Карты игрока
            board: Карты на борде
            pot: Размер пота
            bet_sequence: Последовательность ставок (например, "rrc" для raise-raise-call)
            
        Returns:
            Строка-идентификатор информационного множества
        """
        # Информационное множество включает:
        # - Улицу
        # - Позицию игрока
        # - Карты на борде (публичная информация)
        # - Последовательность ставок
        # НЕ включает карты игрока (приватная информация)
        
        board_str = "".join([f"{r}{s}" for r, s in board]) if board else ""
        cards_str = "".join([f"{r}{s}" for r, s in cards]) if cards else ""
        
        # Для упрощения: используем только публичную информацию
        # В реальной реализации нужно учитывать эквивалентность рук
        infoset = f"{street}_{player}_{board_str}_{bet_sequence}"
        
        return infoset
    
    def get_available_actions(self, street: int, pot: float, current_bet: float, 
                            stack: float, last_raise: float, num_raises: int) -> List[str]:
        """
        Возвращает доступные действия с учетом ограничений дерева
        
        Args:
            street: Улица
            pot: Размер пота
            current_bet: Текущая ставка
            stack: Стек игрока
            last_raise: Размер последнего рейза
            num_raises: Количество рейзов в текущем раунде
            
        Returns:
            Список доступных действий
        """
        actions = []
        
        # Всегда доступны fold и call
        if current_bet > 0:
            actions.append("fold")
            if current_bet < stack:
                actions.append("call")
        else:
            actions.append("check")
        
        # Рейзы с ограничениями
        max_raises = self.max_raise_sizes.get(street, 2)
        
        if num_raises < max_raises and stack > current_bet:
            # Размеры рейзов: 2x, 3x от пота (упрощенно)
            raise_sizes = []
            
            if street == 0:  # Preflop
                raise_sizes = [2.0, 3.0]  # 2x и 3x BB
            elif street == 1:  # Flop
                raise_sizes = [0.5, 0.75]  # 50% и 75% пота
            else:  # Turn/River
                raise_sizes = [0.5, 0.75, 1.0]  # 50%, 75%, 100% пота
            
            for size in raise_sizes[:max_raises]:
                raise_amount = pot * size
                if raise_amount <= stack - current_bet:
                    actions.append(f"raise_{size}")
        
        # All-in
        if stack > current_bet:
            actions.append("all_in")
        
        return actions
