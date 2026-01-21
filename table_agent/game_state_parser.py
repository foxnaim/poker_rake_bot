"""Парсер состояния игры из различных источников"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class Street(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


@dataclass
class PlayerInfo:
    """Информация об игроке за столом"""
    seat: int
    stack: float
    is_active: bool = True
    is_sitting_out: bool = False
    name: Optional[str] = None
    bet: float = 0.0
    total_bet: float = 0.0


@dataclass
class ParsedGameState:
    """Распарсенное состояние игры"""
    hand_id: str
    table_id: str

    # Карты
    hero_cards: str  # "AsKh"
    board_cards: str  # "QdJcTs" или ""

    # Позиции
    hero_position: int  # 0-5
    dealer_position: int  # 0-5
    current_player: int  # чей ход

    # Деньги
    pot: float
    small_blind: float = 0.5
    big_blind: float = 1.0

    # Игроки
    players: List[PlayerInfo] = field(default_factory=list)

    # Улица
    street: Street = Street.PREFLOP

    # Дополнительно
    last_raise_amount: float = 0.0
    action_deadline_ms: Optional[int] = None

    def to_api_format(self) -> Dict[str, Any]:
        """Конвертация в формат API /decide"""
        stacks = {str(p.seat): p.stack for p in self.players}
        bets = {str(p.seat): p.bet for p in self.players}
        total_bets = {str(p.seat): p.total_bet for p in self.players}
        active_players = [p.seat for p in self.players if p.is_active and not p.is_sitting_out]

        return {
            "hand_id": self.hand_id,
            "table_id": self.table_id,
            "hero_cards": self.hero_cards,
            "board_cards": self.board_cards,
            "hero_position": self.hero_position,
            "dealer": self.dealer_position,
            "stacks": stacks,
            "bets": bets,
            "total_bets": total_bets,
            "active_players": active_players,
            "pot": self.pot,
            "current_player": self.current_player,
            "street": self.street.value,
            "last_raise_amount": self.last_raise_amount,
            "small_blind": self.small_blind,
            "big_blind": self.big_blind
        }


class GameStateParser:
    """Базовый парсер состояния игры"""

    def parse(self, raw_data: Any) -> Optional[ParsedGameState]:
        """Распарсить сырые данные в GameState"""
        raise NotImplementedError

    def parse_cards(self, cards_str: str) -> str:
        """Нормализация формата карт -> AsKh"""
        if not cards_str:
            return ""

        # Убираем пробелы и приводим к стандартному формату
        cards_str = cards_str.replace(" ", "").replace(",", "")

        # Маппинг мастей
        suit_map = {
            's': 's', 'S': 's', '♠': 's', 'spades': 's',
            'h': 'h', 'H': 'h', '♥': 'h', 'hearts': 'h',
            'd': 'd', 'D': 'd', '♦': 'd', 'diamonds': 'd',
            'c': 'c', 'C': 'c', '♣': 'c', 'clubs': 'c'
        }

        # Маппинг номиналов
        rank_map = {
            'a': 'A', 'A': 'A', '14': 'A',
            'k': 'K', 'K': 'K', '13': 'K',
            'q': 'Q', 'Q': 'Q', '12': 'Q',
            'j': 'J', 'J': 'J', '11': 'J',
            't': 'T', 'T': 'T', '10': 'T',
            '9': '9', '8': '8', '7': '7', '6': '6',
            '5': '5', '4': '4', '3': '3', '2': '2'
        }

        result = []
        i = 0
        while i < len(cards_str):
            # Пробуем двухсимвольный номинал (10)
            if i + 2 < len(cards_str) and cards_str[i:i+2] == '10':
                rank = 'T'
                i += 2
            else:
                rank = rank_map.get(cards_str[i], cards_str[i])
                i += 1

            if i < len(cards_str):
                suit = suit_map.get(cards_str[i], cards_str[i])
                i += 1
                result.append(f"{rank}{suit}")

        return "".join(result)

    def parse_position(self, position_str: str, num_players: int = 6) -> int:
        """Конвертация позиции в число 0-5"""
        position_map = {
            'btn': 0, 'button': 0, 'bu': 0,
            'sb': 1, 'small': 1,
            'bb': 2, 'big': 2,
            'utg': 3, 'ep': 3,
            'mp': 4, 'middle': 4,
            'co': 5, 'cutoff': 5
        }

        if isinstance(position_str, int):
            return position_str % num_players

        return position_map.get(position_str.lower(), 0)


class JSONGameStateParser(GameStateParser):
    """Парсер JSON формата (для тестирования и API)"""

    def parse(self, raw_data: Dict[str, Any]) -> Optional[ParsedGameState]:
        try:
            players = []
            for i, (seat, stack) in enumerate(raw_data.get("stacks", {}).items()):
                players.append(PlayerInfo(
                    seat=int(seat),
                    stack=float(stack),
                    is_active=int(seat) in raw_data.get("active_players", []),
                    bet=raw_data.get("bets", {}).get(seat, 0),
                    total_bet=raw_data.get("total_bets", {}).get(seat, 0)
                ))

            return ParsedGameState(
                hand_id=raw_data.get("hand_id", f"hand_{int(__import__('time').time())}"),
                table_id=raw_data.get("table_id", "table_1"),
                hero_cards=self.parse_cards(raw_data.get("hero_cards", "")),
                board_cards=self.parse_cards(raw_data.get("board_cards", "")),
                hero_position=raw_data.get("hero_position", 0),
                dealer_position=raw_data.get("dealer", 0),
                current_player=raw_data.get("current_player", 0),
                pot=float(raw_data.get("pot", 0)),
                small_blind=float(raw_data.get("small_blind", 0.5)),
                big_blind=float(raw_data.get("big_blind", 1.0)),
                players=players,
                street=Street(raw_data.get("street", "preflop")),
                last_raise_amount=float(raw_data.get("last_raise_amount", 0))
            )
        except Exception as e:
            print(f"Parse error: {e}")
            return None
