"""Оценка силы руки (hand evaluator)

Поддерживает работу с numba (если установлен) и без него.
"""

from typing import List, Tuple, Callable
from functools import wraps

# Попытка импорта numba (опционально)
try:
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    # Заглушка для @jit декоратора
    def jit(nopython=True):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

# Попытка импорта numpy (опционально для non-numba версии)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


def _evaluate_hand_pure_python(cards: List[Tuple[int, int]]) -> int:
    """
    Чистая Python версия без зависимостей от numpy/numba.
    Используется как fallback.
    """
    if len(cards) < 5:
        return 0

    ranks = [card[0] for card in cards]
    suits = [card[1] for card in cards]

    # Подсчет частот рангов
    rank_counts = [0] * 15
    for rank in ranks:
        rank_counts[rank] += 1

    # Проверка на флеш
    suit_counts = [0] * 4
    for suit in suits:
        suit_counts[suit] += 1
    is_flush = max(suit_counts) >= 5
    flush_suit = suit_counts.index(max(suit_counts)) if is_flush else -1

    # Проверка на стрит
    is_straight = False
    straight_high = 0

    for high in range(14, 5, -1):
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
        flush_ranks = sorted([r for i, r in enumerate(ranks) if suits[i] == flush_suit], reverse=True)[:5]
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


# Версия с numba (если доступен)
if NUMBA_AVAILABLE and NUMPY_AVAILABLE:
    import numpy as np

    @jit(nopython=True)
    def _evaluate_hand_numba(cards_arr) -> int:
        """Numba-оптимизированная версия"""
        n = len(cards_arr)
        if n < 5:
            return 0

        ranks = cards_arr[:, 0]
        suits = cards_arr[:, 1]

        # Подсчет частот рангов
        rank_counts = np.zeros(15, dtype=np.int32)
        for i in range(n):
            rank_counts[ranks[i]] += 1

        # Проверка на флеш
        suit_counts = np.zeros(4, dtype=np.int32)
        for i in range(n):
            suit_counts[suits[i]] += 1
        is_flush = np.max(suit_counts) >= 5
        flush_suit = np.argmax(suit_counts)

        # Проверка на стрит
        is_straight = False
        straight_high = 0

        for high in range(14, 5, -1):
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
        pairs = np.zeros(7, dtype=np.int32)
        trips = np.zeros(7, dtype=np.int32)
        quads = np.zeros(7, dtype=np.int32)
        n_pairs = 0
        n_trips = 0
        n_quads = 0

        for rank in range(14, 1, -1):
            count = rank_counts[rank]
            if count == 2:
                pairs[n_pairs] = rank
                n_pairs += 1
            elif count == 3:
                trips[n_trips] = rank
                n_trips += 1
            elif count == 4:
                quads[n_quads] = rank
                n_quads += 1

        # Стрит-флеш
        if is_flush and is_straight:
            return 8000000 + straight_high

        # Каре
        if n_quads > 0:
            kicker = 0
            for i in range(n):
                if ranks[i] != quads[0] and ranks[i] > kicker:
                    kicker = ranks[i]
            return 7000000 + quads[0] * 100 + kicker

        # Фулл-хаус
        if n_trips > 0 and n_pairs > 0:
            return 6000000 + trips[0] * 100 + pairs[0]
        if n_trips >= 2:
            return 6000000 + trips[0] * 100 + trips[1]

        # Флеш
        if is_flush:
            flush_ranks = np.zeros(7, dtype=np.int32)
            n_flush = 0
            for i in range(n):
                if suits[i] == flush_suit:
                    flush_ranks[n_flush] = ranks[i]
                    n_flush += 1
            # Сортировка (простая bubble sort для малого массива)
            for i in range(n_flush):
                for j in range(i + 1, n_flush):
                    if flush_ranks[j] > flush_ranks[i]:
                        flush_ranks[i], flush_ranks[j] = flush_ranks[j], flush_ranks[i]
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
        if n_trips > 0:
            kickers = np.zeros(4, dtype=np.int32)
            n_kick = 0
            for i in range(n):
                if ranks[i] != trips[0]:
                    kickers[n_kick] = ranks[i]
                    n_kick += 1
            for i in range(n_kick):
                for j in range(i + 1, n_kick):
                    if kickers[j] > kickers[i]:
                        kickers[i], kickers[j] = kickers[j], kickers[i]
            return 3000000 + trips[0] * (15 ** 2) + kickers[0] * 15 + kickers[1]

        # Две пары
        if n_pairs >= 2:
            kicker = 0
            for i in range(n):
                if ranks[i] != pairs[0] and ranks[i] != pairs[1] and ranks[i] > kicker:
                    kicker = ranks[i]
            return 2000000 + pairs[0] * (15 ** 2) + pairs[1] * 15 + kicker

        # Пара
        if n_pairs == 1:
            kickers = np.zeros(5, dtype=np.int32)
            n_kick = 0
            for i in range(n):
                if ranks[i] != pairs[0]:
                    kickers[n_kick] = ranks[i]
                    n_kick += 1
            for i in range(n_kick):
                for j in range(i + 1, n_kick):
                    if kickers[j] > kickers[i]:
                        kickers[i], kickers[j] = kickers[j], kickers[i]
            return 1000000 + pairs[0] * (15 ** 3) + kickers[0] * (15 ** 2) + kickers[1] * 15 + kickers[2]

        # Старшая карта
        high = np.zeros(7, dtype=np.int32)
        for i in range(n):
            high[i] = ranks[i]
        for i in range(n):
            for j in range(i + 1, n):
                if high[j] > high[i]:
                    high[i], high[j] = high[j], high[i]
        return (
            high[0] * (15 ** 4)
            + high[1] * (15 ** 3)
            + high[2] * (15 ** 2)
            + high[3] * 15
            + high[4]
        )


def evaluate_hand(cards: List[Tuple[int, int]]) -> int:
    """
    Оценивает силу руки (чем больше, тем сильнее).
    Возвращает: комбинация * 1000000 + kickers

    Автоматически выбирает оптимальную реализацию:
    - numba-версия если доступен numba+numpy (быстрее в ~10-50x)
    - pure python версия как fallback
    """
    # Используем numba версию если доступна
    if NUMBA_AVAILABLE and NUMPY_AVAILABLE:
        cards_arr = np.array(cards, dtype=np.int32)
        return _evaluate_hand_numba(cards_arr)

    # Fallback на чистый Python
    return _evaluate_hand_pure_python(cards)


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
