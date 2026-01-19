"""Тесты для hand evaluator"""

import pytest
from engine.hand_evaluator import evaluate_hand, compare_hands
from engine.cards import parse_cards


def test_royal_flush():
    """Тест роял-флеша"""
    cards = parse_cards("AsKsQsJsTs")
    score = evaluate_hand(cards)
    assert score >= 8000000  # Стрит-флеш


def test_straight_flush():
    """Тест стрит-флеша"""
    cards = parse_cards("9s8s7s6s5s")
    score = evaluate_hand(cards)
    assert score >= 8000000


def test_four_of_a_kind():
    """Тест каре"""
    cards = parse_cards("AsAcAdAhKh")
    score = evaluate_hand(cards)
    assert 7000000 <= score < 8000000


def test_full_house():
    """Тест фулл-хауса"""
    cards = parse_cards("AsAcAdKhKc")
    score = evaluate_hand(cards)
    assert 6000000 <= score < 7000000


def test_flush():
    """Тест флеша"""
    cards = parse_cards("AsKs9s7s5s")
    score = evaluate_hand(cards)
    assert 5000000 <= score < 6000000


def test_straight():
    """Тест стрита"""
    cards = parse_cards("9s8h7c6d5s")
    score = evaluate_hand(cards)
    assert 4000000 <= score < 5000000


def test_three_of_a_kind():
    """Тест тройки"""
    cards = parse_cards("AsAcAdKhQc")
    score = evaluate_hand(cards)
    assert 3000000 <= score < 4000000


def test_two_pair():
    """Тест двух пар"""
    cards = parse_cards("AsAcKhKdQc")
    score = evaluate_hand(cards)
    assert 2000000 <= score < 3000000


def test_pair():
    """Тест пары"""
    cards = parse_cards("AsAcKhQdJc")
    score = evaluate_hand(cards)
    assert 1000000 <= score < 2000000


def test_high_card():
    """Тест старшей карты"""
    cards = parse_cards("AsKhQdJc9s")
    score = evaluate_hand(cards)
    assert score < 1000000


def test_compare_hands():
    """Тест сравнения рук"""
    royal_flush = parse_cards("AsKsQsJsTs")
    pair = parse_cards("AsAcKhQdJc")
    
    result = compare_hands(royal_flush, pair)
    assert result == 1  # royal_flush > pair
    
    result = compare_hands(pair, royal_flush)
    assert result == -1  # pair < royal_flush
