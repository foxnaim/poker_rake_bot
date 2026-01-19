"""Утилиты для работы с картами"""

from typing import List, Tuple
from enum import IntEnum


class Suit(IntEnum):
    """Масти"""
    CLUBS = 0
    DIAMONDS = 1
    HEARTS = 2
    SPADES = 3


class Rank(IntEnum):
    """Достоинства"""
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


SUIT_NAMES = ['c', 'd', 'h', 's']
RANK_NAMES = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']


def card_to_string(rank: int, suit: int) -> str:
    """Конвертирует карту в строку (например, 'As', 'Kh')"""
    return f"{RANK_NAMES[rank - 2]}{SUIT_NAMES[suit]}"


def string_to_card(card_str: str) -> Tuple[int, int]:
    """Конвертирует строку в карту (rank, suit)"""
    rank_char = card_str[0].upper()
    suit_char = card_str[1].lower()
    
    rank = RANK_NAMES.index(rank_char) + 2
    suit = SUIT_NAMES.index(suit_char)
    
    return rank, suit


def parse_cards(cards_str: str) -> List[Tuple[int, int]]:
    """Парсит строку карт (например, 'AsKh' -> [(14, 3), (13, 2)])"""
    cards = []
    for i in range(0, len(cards_str), 2):
        card_str = cards_str[i:i+2]
        cards.append(string_to_card(card_str))
    return cards


def cards_to_string(cards: List[Tuple[int, int]]) -> str:
    """Конвертирует список карт в строку"""
    return ''.join(card_to_string(rank, suit) for rank, suit in cards)
