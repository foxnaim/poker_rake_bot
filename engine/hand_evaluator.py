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
    
    # Проверка на стрит (Numba-friendly: через rank_counts)
    is_straight = False
    straight_high = 0

    # Обычные стриты: от A-high (14) до 6-high (6)
    # (5-high обрабатываем отдельно как wheel A2345)
    for high in range(14, 5, -1):  # 14..6
        ok = True
        for r in range(high, high - 5, -1):
            if rank_counts[r] == 0:
                ok = False
                break
        if ok:
            is_straight = True
            straight_high = high
            break

    # Wheel: A-2-3-4-5
    if not is_straight:
        if (rank_counts[14] > 0 and rank_counts[5] > 0 and rank_counts[4] > 0
                and rank_counts[3] > 0 and rank_counts[2] > 0):
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
        # pack5 в base-15, чтобы kickers < 1e6
        kickers = (
            flush_ranks[0] * (15 ** 4)
            + flush_ranks[1] * (15 ** 3)
            + flush_ranks[2] * (15 ** 2)
            + flush_ranks[3] * 15
            + flush_ranks[4]
        )
        return 5000000 + kickers
    
    # Стрит
    if is_straight:
        return 4000000 + straight_high
    
    # Тройка
    if len(trips) > 0:
        kickers = sorted([r for r in ranks if r != trips[0]], reverse=True)[:2]
        return 3000000 + trips[0] * (15 ** 2) + kickers[0] * 15 + kickers[1]
    
    # Две пары
    if len(pairs) >= 2:
        kicker = max([r for r in ranks if r not in pairs[:2]])
        return 2000000 + pairs[0] * (15 ** 2) + pairs[1] * 15 + kicker
    
    # Пара
    if len(pairs) == 1:
        kickers = sorted([r for r in ranks if r != pairs[0]], reverse=True)[:3]
        return 1000000 + pairs[0] * (15 ** 3) + kickers[0] * (15 ** 2) + kickers[1] * 15 + kickers[2]
    
    # Старшая карта
    high_cards = sorted(ranks, reverse=True)[:5]
    return (
        high_cards[0] * (15 ** 4)
        + high_cards[1] * (15 ** 3)
        + high_cards[2] * (15 ** 2)
        + high_cards[3] * 15
        + high_cards[4]
    )


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
