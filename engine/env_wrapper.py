"""Обёртка над NLHE средой для 6-max cash игры"""

import random
from typing import List, Dict, Optional, Tuple
from enum import IntEnum
# numpy используется в некоторых ветках/экспериментах, но не обязателен для базовой логики.
try:
    import numpy as np  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    np = None

from .cards import Suit, Rank, card_to_string, parse_cards, cards_to_string
from .hand_evaluator import evaluate_hand, compare_hands


class ActionType(IntEnum):
    """Типы действий"""
    FOLD = 0
    CHECK = 1
    CALL = 2
    RAISE = 3
    ALL_IN = 4


class Street(IntEnum):
    """Улицы"""
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3


class GameState:
    """Состояние игры"""
    def __init__(self):
        self.street = Street.PREFLOP
        self.players = []  # Список игроков
        self.hero_position = 0
        self.hero_cards = []
        self.board_cards = []
        self.pot = 0.0
        self.bets = {}  # Ставки игроков в текущем раунде
        self.total_bets = {}  # Общие ставки игроков
        self.active_players = set()  # Активные игроки
        self.dealer = 0
        self.small_blind = 0.5
        self.big_blind = 1.0
        self.stacks = {}  # Стеки игроков
        self.last_raise_amount = 0.0
        self.current_player = 0
        self.hand_history = []


class PokerEnv:
    """Обёртка над покерной средой для 6-max NLHE"""
    
    def __init__(self, num_players: int = 6, small_blind: float = 0.5, big_blind: float = 1.0, stack_size: float = 100.0):
        """
        Args:
            num_players: Количество игроков (максимум 6)
            small_blind: Маленький блайнд
            big_blind: Большой блайнд
            stack_size: Начальный стек в BB (100 = 100bb)
        """
        self.num_players = min(num_players, 6)
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.stack_size_bb = stack_size
        self.stack_size = stack_size * big_blind
        
        self.deck = self._create_deck()
        self.state = GameState()
        self.hand_id = None
        
    def _create_deck(self) -> List[Tuple[int, int]]:
        """Создает колоду из 52 карт"""
        deck = []
        for suit in range(4):
            for rank in range(2, 15):  # 2-14 (Ace)
                deck.append((rank, suit))
        return deck
    
    def reset(self, hand_id: Optional[str] = None) -> GameState:
        """
        Начинает новую раздачу
        
        Returns:
            Начальное состояние игры
        """
        self.hand_id = hand_id or f"hand_{random.randint(100000, 999999)}"
        self.deck = self._create_deck()
        random.shuffle(self.deck)
        
        self.state = GameState()
        self.state.small_blind = self.small_blind
        self.state.big_blind = self.big_blind
        self.state.dealer = random.randint(0, self.num_players - 1)
        
        # Инициализация игроков
        self.state.players = list(range(self.num_players))
        self.state.active_players = set(range(self.num_players))
        self.state.stacks = {i: self.stack_size for i in range(self.num_players)}
        self.state.total_bets = {i: 0.0 for i in range(self.num_players)}
        self.state.bets = {i: 0.0 for i in range(self.num_players)}
        
        # Раздача карт
        self.state.hero_cards = [self.deck.pop(), self.deck.pop()]
        # Для других игроков карты не раскрываются (скрытая информация)
        
        # Блайнды
        sb_pos = (self.state.dealer + 1) % self.num_players
        bb_pos = (self.state.dealer + 2) % self.num_players
        
        self.state.stacks[sb_pos] -= self.small_blind
        self.state.stacks[bb_pos] -= self.big_blind
        self.state.bets[sb_pos] = self.small_blind
        self.state.bets[bb_pos] = self.big_blind
        self.state.total_bets[sb_pos] = self.small_blind
        self.state.total_bets[bb_pos] = self.big_blind
        self.state.pot = self.small_blind + self.big_blind
        
        self.state.last_raise_amount = self.big_blind
        self.state.current_player = (bb_pos + 1) % self.num_players
        self.state.street = Street.PREFLOP
        
        return self.state
    
    def step(self, action: str, amount: Optional[float] = None) -> Tuple[GameState, bool, Dict]:
        """
        Выполняет действие
        
        Args:
            action: 'fold', 'check', 'call', 'raise', 'all_in'
            amount: Размер рейза (для 'raise')
        
        Returns:
            (новое состояние, завершена ли раздача, информация)
        """
        info = {}
        
        if action == 'fold':
            self.state.active_players.discard(self.state.current_player)
            if len(self.state.active_players) == 1:
                return self._end_hand(), True, info
            
        elif action == 'check':
            if self.state.bets[self.state.current_player] < max(self.state.bets.values()):
                raise ValueError("Cannot check when bet is required")
        
        elif action == 'call':
            call_amount = max(self.state.bets.values()) - self.state.bets[self.state.current_player]
            if call_amount >= self.state.stacks[self.state.current_player]:
                action = 'all_in'
            else:
                self.state.stacks[self.state.current_player] -= call_amount
                self.state.bets[self.state.current_player] += call_amount
                self.state.total_bets[self.state.current_player] += call_amount
                self.state.pot += call_amount
        
        elif action == 'raise':
            if amount is None:
                raise ValueError("Raise amount required")
            min_raise = self.state.last_raise_amount
            total_bet = max(self.state.bets.values()) + amount
            current_bet = self.state.bets[self.state.current_player]
            raise_amount = total_bet - current_bet
            
            if raise_amount < min_raise:
                raise ValueError(f"Raise too small, minimum: {min_raise}")
            
            if raise_amount >= self.state.stacks[self.state.current_player]:
                action = 'all_in'
            else:
                self.state.stacks[self.state.current_player] -= raise_amount
                self.state.bets[self.state.current_player] += raise_amount
                self.state.total_bets[self.state.current_player] += raise_amount
                self.state.pot += raise_amount
                self.state.last_raise_amount = raise_amount
        
        elif action == 'all_in':
            all_in_amount = self.state.stacks[self.state.current_player]
            self.state.bets[self.state.current_player] += all_in_amount
            self.state.total_bets[self.state.current_player] += all_in_amount
            self.state.pot += all_in_amount
            self.state.stacks[self.state.current_player] = 0
        
        # Переход к следующему игроку
        if not self._is_round_complete():
            self.state.current_player = self._next_active_player()
        else:
            # Раунд ставок завершен, переход к следующей улице
            if self.state.street == Street.PREFLOP:
                self._deal_flop()
            elif self.state.street == Street.FLOP:
                self._deal_turn()
            elif self.state.street == Street.TURN:
                self._deal_river()
            else:
                return self._end_hand(), True, info
            
            # Сброс ставок для нового раунда
            self.state.bets = {i: 0.0 for i in self.state.active_players}
            self.state.last_raise_amount = 0.0
            self.state.current_player = self._first_active_player()
        
        return self.state, False, info
    
    def _deal_flop(self):
        """Раздает флоп"""
        self.state.street = Street.FLOP
        self.state.board_cards = [self.deck.pop(), self.deck.pop(), self.deck.pop()]
    
    def _deal_turn(self):
        """Раздает терн"""
        self.state.street = Street.TURN
        self.state.board_cards.append(self.deck.pop())
    
    def _deal_river(self):
        """Раздает ривер"""
        self.state.street = Street.RIVER
        self.state.board_cards.append(self.deck.pop())
    
    def _is_round_complete(self) -> bool:
        """Проверяет, завершен ли раунд ставок"""
        if len(self.state.active_players) <= 1:
            return True
        
        active_bets = [self.state.bets[p] for p in self.state.active_players]
        if len(set(active_bets)) == 1:  # Все ставки равны
            # Проверяем, что последний рейзер уже походил
            return True
        return False
    
    def _next_active_player(self) -> int:
        """Следующий активный игрок"""
        current = self.state.current_player
        for _ in range(self.num_players):
            current = (current + 1) % self.num_players
            if current in self.state.active_players:
                return current
        return current
    
    def _first_active_player(self) -> int:
        """Первый активный игрок (после дилера)"""
        start = (self.state.dealer + 1) % self.num_players
        for _ in range(self.num_players):
            if start in self.state.active_players:
                return start
            start = (start + 1) % self.num_players
        return start
    
    def _end_hand(self) -> GameState:
        """Завершает раздачу и определяет победителя"""
        # Упрощенная логика: если остался один игрок - он выигрывает
        # В реальной реализации нужно сравнить руки всех активных игроков
        if len(self.state.active_players) == 1:
            winner = list(self.state.active_players)[0]
            self.state.stacks[winner] += self.state.pot
        
        return self.state
