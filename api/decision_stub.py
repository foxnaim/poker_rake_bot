"""Stub реализация для принятия решений (временная)"""

import random
from typing import Dict
from api.schemas import GameStateRequest


def make_decision_stub(request: GameStateRequest) -> Dict:
    """
    Stub функция для принятия решений
    В будущем будет заменена на DecisionRouter + MCCFR + Exploit
    
    Returns:
        Словарь с решением
    """
    # Простая логика: если нужно коллить - колл, иначе случайное действие
    max_bet = max(request.bets.values()) if request.bets else 0.0
    hero_bet = request.bets.get(str(request.hero_position), 0.0)
    call_amount = max_bet - hero_bet
    
    # Если нужно коллить и сумма небольшая - колл
    if call_amount > 0 and call_amount <= request.big_blind * 2:
        return {
            "action": "call",
            "amount": None,
            "reasoning": {"type": "stub", "reason": "small_call"}
        }
    
    # Если можно чекнуть - чек
    if call_amount == 0:
        return {
            "action": "check",
            "amount": None,
            "reasoning": {"type": "stub", "reason": "can_check"}
        }
    
    # Иначе случайное действие
    actions = ["fold", "call"]
    if call_amount < request.big_blind * 5:
        actions.append("call")
    
    action = random.choice(actions)
    
    if action == "raise":
        raise_amount = request.big_blind * random.uniform(2.0, 3.0)
        return {
            "action": "raise",
            "amount": raise_amount,
            "reasoning": {"type": "stub", "reason": "random_raise"}
        }
    
    return {
        "action": action,
        "amount": None,
        "reasoning": {"type": "stub", "reason": f"random_{action}"}
    }
