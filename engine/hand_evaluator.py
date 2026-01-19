"""Оценка силы руки (hand evaluator)"""

from typing import List, Tuple
from numba import jit
import numpy as np


@jit(nopython=True)
def evaluate_hand(cards: List[Tuple[int, int]]) -> int:
    """
    Оценивает силу руки (чем больше, тем сильнее)
    Возвращает: комбинация * 1000000 + kickers
    """
    if len(cards) < 5:
        return 0
    
    ranks = [card[0] for card in cards]
    suits = [card[1] for card in cards]
    
    # Подсчет частот рангов
    rank_counts = np.zeros(15, dtype=np.int32)
    for rank in ranks:
        rank_counts[rank] += 1
    
    # Проверка на флеш
    suit_counts = np.zeros(4, dtype=np.int32)
    for suit in suits:
        suit_counts[suit] += 1
    is_flush = np.max(suit_counts) >= 5
    
    # Проверка на стрит
    sorted_ranks = sorted(set(ranks), reverse=True)
    is_straight = False
    straight_high = 0
    
    if len(sorted_ranks) >= 5:
        for i in range(len(sorted_ranks) - 4):
            if sorted_ranks[i] - sorted_ranks[i+4] == 4:
                is_straight = True
                straight_high = sorted_ranks[i]
                break
        # A-2-3-4-5 стрит
        if not is_straight and 14 in sorted_ranks:
            low_straight = [14, 5, 4, 3, 2]
            if all(r in sorted_ranks for r in low_straight):
                is_straight = True
                straight_high = 5
    
    # Определение комбинации
    pairs = []
    trips = []
    quads = []
    
    for rank in range(2, 15):
        count = rank_counts[rank]
        if count == 2:
            pairs.append(rank)
        elif count == 3:
            trips.append(rank)
        elif count == 4:
            quads.append(rank)
    
    pairs.sort(reverse=True)
    trips.sort(reverse=True)
    
    # Стрит-флеш / Роял-флеш
    if is_flush and is_straight:
        return 8000000 + straight_high
    
    # Каре
    if len(quads) > 0:
        kicker = max([r for r in ranks if r != quads[0]])
        return 7000000 + quads[0] * 100 + kicker
    
    # Фулл-хаус
    if len(trips) > 0 and len(pairs) > 0:
        return 6000000 + trips[0] * 100 + pairs[0]
    if len(trips) >= 2:
        return 6000000 + trips[0] * 100 + trips[1]
    
    # Флеш
    if is_flush:
        flush_ranks = sorted([r for i, r in enumerate(ranks) if suits[i] == np.argmax(suit_counts)], reverse=True)[:5]
        score = 5000000
        for i, rank in enumerate(flush_ranks):
            score += rank * (100 ** (4 - i))
        return score
    
    # Стрит
    if is_straight:
        return 4000000 + straight_high
    
    # Тройка
    if len(trips) > 0:
        kickers = sorted([r for r in ranks if r != trips[0]], reverse=True)[:2]
        return 3000000 + trips[0] * 10000 + kickers[0] * 100 + kickers[1]
    
    # Две пары
    if len(pairs) >= 2:
        kicker = max([r for r in ranks if r not in pairs[:2]])
        return 2000000 + pairs[0] * 10000 + pairs[1] * 100 + kicker
    
    # Пара
    if len(pairs) == 1:
        kickers = sorted([r for r in ranks if r != pairs[0]], reverse=True)[:3]
        return 1000000 + pairs[0] * 1000000 + kickers[0] * 10000 + kickers[1] * 100 + kickers[2]
    
    # Старшая карта
    high_cards = sorted(ranks, reverse=True)[:5]
    score = 0
    for i, rank in enumerate(high_cards):
        score += rank * (100 ** (4 - i))
    return score


def compare_hands(hand1: List[Tuple[int, int]], hand2: List[Tuple[int, int]]) -> int:
    """
    Сравнивает две руки
    Возвращает: 1 если hand1 > hand2, -1 если hand1 < hand2, 0 если равны
    """
    score1 = evaluate_hand(hand1)
    score2 = evaluate_hand(hand2)
    
    if score1 > score2:
        return 1
    elif score1 < score2:
        return -1
    else:
        return 0
