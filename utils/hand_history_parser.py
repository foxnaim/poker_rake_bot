"""Парсер hand history для автоматического обновления профилей оппонентов"""

from typing import Dict, List, Optional, Tuple
import re
from dataclasses import dataclass
from enum import Enum


class Action(Enum):
    """Типы действий"""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass
class PlayerAction:
    """Действие игрока"""
    player_id: str
    action: Action
    amount: Optional[float] = None
    street: str = "preflop"


@dataclass
class ParsedHand:
    """Распарсенная раздача"""
    hand_id: str
    table_id: str
    limit_type: str
    players: Dict[str, Dict]  # player_id -> {position, stack, cards}
    actions: List[PlayerAction]
    board_cards: List[str]
    pot: float
    winner: Optional[str] = None
    winnings: Optional[float] = None


class HandHistoryParser:
    """Парсер для hand history из различных покерных румов"""

    def __init__(self):
        # Паттерны для парсинга (поддержка PokerStars, 888poker, и т.д.)
        self.patterns = {
            'hand_id': r'Hand #(\w+)',
            'table': r'Table \'([^\']+)\'',
            'limit': r'(NL\d+)',
            'player': r'Seat \d+: ([^\(]+) \((\d+\.?\d*) in chips\)',
            'cards': r'\[([^\]]+)\]',
            'action_fold': r'(\w+): folds',
            'action_check': r'(\w+): checks',
            'action_call': r'(\w+): calls (\d+\.?\d*)',
            'action_bet': r'(\w+): bets (\d+\.?\d*)',
            'action_raise': r'(\w+): raises (\d+\.?\d*) to (\d+\.?\d*)',
            'action_all_in': r'(\w+): all-in',
            'board': r'Board \[([^\]]+)\]',
            'winner': r'(\w+) collected (\d+\.?\d*)'
        }

    def parse(self, hand_text: str) -> Optional[ParsedHand]:
        """
        Парсит текст hand history

        Args:
            hand_text: Текст раздачи

        Returns:
            Распарсенная раздача или None если не удалось распарсить
        """
        try:
            # Извлекаем hand ID
            hand_id_match = re.search(self.patterns['hand_id'], hand_text)
            if not hand_id_match:
                return None
            hand_id = hand_id_match.group(1)

            # Извлекаем table ID
            table_match = re.search(self.patterns['table'], hand_text)
            table_id = table_match.group(1) if table_match else "unknown"

            # Извлекаем limit
            limit_match = re.search(self.patterns['limit'], hand_text)
            limit_type = limit_match.group(1) if limit_match else "NL10"

            # Извлекаем игроков
            players = {}
            for match in re.finditer(self.patterns['player'], hand_text):
                player_name = match.group(1).strip()
                stack = float(match.group(2))
                players[player_name] = {
                    'stack': stack,
                    'position': len(players),  # Упрощенно
                    'cards': None
                }

            # Извлекаем действия
            actions = []

            # Парсим действия по улицам
            streets = self._split_by_streets(hand_text)

            for street_name, street_text in streets.items():
                # Fold
                for match in re.finditer(self.patterns['action_fold'], street_text):
                    player = match.group(1)
                    actions.append(PlayerAction(player, Action.FOLD, street=street_name))

                # Check
                for match in re.finditer(self.patterns['action_check'], street_text):
                    player = match.group(1)
                    actions.append(PlayerAction(player, Action.CHECK, street=street_name))

                # Call
                for match in re.finditer(self.patterns['action_call'], street_text):
                    player = match.group(1)
                    amount = float(match.group(2))
                    actions.append(PlayerAction(player, Action.CALL, amount, street_name))

                # Bet
                for match in re.finditer(self.patterns['action_bet'], street_text):
                    player = match.group(1)
                    amount = float(match.group(2))
                    actions.append(PlayerAction(player, Action.BET, amount, street_name))

                # Raise
                for match in re.finditer(self.patterns['action_raise'], street_text):
                    player = match.group(1)
                    amount = float(match.group(3))  # Total amount
                    actions.append(PlayerAction(player, Action.RAISE, amount, street_name))

                # All-in
                for match in re.finditer(self.patterns['action_all_in'], street_text):
                    player = match.group(1)
                    actions.append(PlayerAction(player, Action.ALL_IN, street=street_name))

            # Извлекаем board cards
            board_cards = []
            board_match = re.search(self.patterns['board'], hand_text)
            if board_match:
                board_str = board_match.group(1)
                board_cards = [c.strip() for c in board_str.split()]

            # Извлекаем победителя
            winner = None
            winnings = None
            winner_match = re.search(self.patterns['winner'], hand_text)
            if winner_match:
                winner = winner_match.group(1)
                winnings = float(winner_match.group(2))

            # Вычисляем pot (упрощенно)
            pot = winnings if winnings else 0.0

            return ParsedHand(
                hand_id=hand_id,
                table_id=table_id,
                limit_type=limit_type,
                players=players,
                actions=actions,
                board_cards=board_cards,
                pot=pot,
                winner=winner,
                winnings=winnings
            )

        except Exception as e:
            print(f"Ошибка при парсинге hand history: {e}")
            return None

    def _split_by_streets(self, hand_text: str) -> Dict[str, str]:
        """Разделяет hand history на улицы"""
        streets = {}

        # Ищем маркеры улиц
        preflop_end = hand_text.find('*** FLOP ***')
        flop_end = hand_text.find('*** TURN ***')
        turn_end = hand_text.find('*** RIVER ***')
        river_end = hand_text.find('*** SHOW DOWN ***')

        if preflop_end == -1:
            preflop_end = len(hand_text)

        streets['preflop'] = hand_text[:preflop_end]

        if preflop_end < len(hand_text) and flop_end > preflop_end:
            streets['flop'] = hand_text[preflop_end:flop_end]

        if flop_end > 0 and turn_end > flop_end:
            streets['turn'] = hand_text[flop_end:turn_end]

        if turn_end > 0 and river_end > turn_end:
            streets['river'] = hand_text[turn_end:river_end]
        elif turn_end > 0:
            streets['river'] = hand_text[turn_end:]

        return streets

    def extract_player_stats(self, parsed_hand: ParsedHand, player_id: str) -> Dict:
        """
        Извлекает статистику игрока из раздачи для обновления профиля

        Args:
            parsed_hand: Распарсенная раздача
            player_id: ID игрока

        Returns:
            Словарь со статистикой
        """
        # Находим действия игрока
        player_actions = [a for a in parsed_hand.actions if a.player_id == player_id]

        if not player_actions:
            return {}

        # Определяем префлоп действие
        preflop_actions = [a for a in player_actions if a.street == 'preflop']
        preflop_action = None

        if preflop_actions:
            # Берем последнее действие префлоп
            last_action = preflop_actions[-1]

            if last_action.action == Action.FOLD:
                preflop_action = "fold"
            elif last_action.action in [Action.CALL, Action.CHECK]:
                preflop_action = "call"
            elif last_action.action in [Action.RAISE, Action.BET]:
                # Определяем, это рейз или 3-bet
                num_raises = sum(1 for a in parsed_hand.actions
                               if a.street == 'preflop' and a.action == Action.RAISE)
                if num_raises >= 2:
                    preflop_action = "3bet"
                else:
                    preflop_action = "raise"

        # Собираем постфлоп действия
        postflop_actions = []
        for street in ['flop', 'turn', 'river']:
            street_actions = [a for a in player_actions if a.street == street]
            for action in street_actions:
                if action.action == Action.FOLD:
                    postflop_actions.append("fold")
                elif action.action == Action.CHECK:
                    postflop_actions.append("check")
                elif action.action == Action.CALL:
                    postflop_actions.append("call")
                elif action.action in [Action.RAISE, Action.BET]:
                    postflop_actions.append("raise")

        return {
            "preflop_action": preflop_action,
            "postflop_actions": postflop_actions
        }


# Глобальный парсер
hand_history_parser = HandHistoryParser()
