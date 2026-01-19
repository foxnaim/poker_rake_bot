"""Кодирование состояния игры в вектор для ML"""

import numpy as np
from typing import List, Dict, Tuple

from .env_wrapper import GameState, Street
from .cards import parse_cards, string_to_card


class StateEncoder:
    """Кодирует состояние игры в числовой вектор"""
    
    def __init__(self, num_players: int = 6):
        self.num_players = num_players
        self.rank_size = 13  # 2-A
        self.suit_size = 4   # c, d, h, s
        
    def encode(self, state: GameState, hero_position: int) -> np.ndarray:
        """
        Кодирует состояние игры в вектор
        
        Returns:
            Вектор признаков состояния
        """
        features = []
        
        # Улица (one-hot)
        street_features = [0.0] * 4
        street_features[state.street] = 1.0
        features.extend(street_features)
        
        # Позиция героя
        position_features = [0.0] * self.num_players
        position_features[hero_position] = 1.0
        features.extend(position_features)
        
        # Позиция дилера
        dealer_features = [0.0] * self.num_players
        dealer_features[state.dealer] = 1.0
        features.extend(dealer_features)
        
        # Карты героя (one-hot для каждой карты)
        hero_card_features = self._encode_cards(state.hero_cards)
        features.extend(hero_card_features)
        
        # Борд (one-hot для каждой карты)
        board_features = self._encode_cards(state.board_cards)
        # Дополняем до 5 карт (флоп=3, терн=4, ривер=5)
        while len(board_features) < 5 * (self.rank_size + self.suit_size):
            board_features.extend([0.0] * (self.rank_size + self.suit_size))
        features.extend(board_features[:5 * (self.rank_size + self.suit_size)])
        
        # Стеки игроков (нормализованные)
        stack_features = []
        for i in range(self.num_players):
            stack_features.append(state.stacks.get(i, 0.0) / 100.0)  # Нормализация к 100bb
        features.extend(stack_features)
        
        # Ставки в текущем раунде (нормализованные)
        bet_features = []
        max_bet = max(state.bets.values()) if state.bets else 0.0
        for i in range(self.num_players):
            bet_features.append(state.bets.get(i, 0.0) / max(1.0, max_bet))
        features.extend(bet_features)
        
        # Общие ставки (нормализованные)
        total_bet_features = []
        max_total_bet = max(state.total_bets.values()) if state.total_bets else 0.0
        for i in range(self.num_players):
            total_bet_features.append(state.total_bets.get(i, 0.0) / max(1.0, max_total_bet))
        features.extend(total_bet_features)
        
        # Активные игроки (binary)
        active_features = []
        for i in range(self.num_players):
            active_features.append(1.0 if i in state.active_players else 0.0)
        features.extend(active_features)
        
        # Пот (нормализованный)
        features.append(state.pot / 100.0)
        
        # Текущий игрок
        current_player_features = [0.0] * self.num_players
        if state.current_player < self.num_players:
            current_player_features[state.current_player] = 1.0
        features.extend(current_player_features)
        
        # Размер последнего рейза (нормализованный)
        features.append(state.last_raise_amount / 10.0)
        
        return np.array(features, dtype=np.float32)
    
    def _encode_cards(self, cards: List[Tuple[int, int]]) -> List[float]:
        """Кодирует карты в one-hot представление"""
        features = []
        for rank, suit in cards:
            # One-hot для ранга (2-A)
            rank_features = [0.0] * self.rank_size
            rank_features[rank - 2] = 1.0
            features.extend(rank_features)
            
            # One-hot для масти
            suit_features = [0.0] * self.suit_size
            suit_features[suit] = 1.0
            features.extend(suit_features)
        
        return features
    
    def encode_compact(self, state: GameState, hero_position: int) -> Dict:
        """
        Компактное кодирование для API (JSON-совместимое)
        
        Returns:
            Словарь с закодированным состоянием
        """
        from .cards import cards_to_string
        
        return {
            "street": state.street,
            "hero_position": hero_position,
            "dealer": state.dealer,
            "hero_cards": cards_to_string(state.hero_cards) if state.hero_cards else "",
            "board_cards": cards_to_string(state.board_cards) if state.board_cards else "",
            "stacks": {str(k): float(v) for k, v in state.stacks.items()},
            "bets": {str(k): float(v) for k, v in state.bets.items()},
            "total_bets": {str(k): float(v) for k, v in state.total_bets.items()},
            "active_players": list(state.active_players),
            "pot": float(state.pot),
            "current_player": state.current_player,
            "last_raise_amount": float(state.last_raise_amount),
            "small_blind": float(state.small_blind),
            "big_blind": float(state.big_blind)
        }
