"""Принятие решений через Decision Router"""

import time
import hashlib
import json
from typing import Dict
from api.schemas import GameStateRequest
from brain.decision_router import decision_router
from data.database import SessionLocal
from data.redis_cache import redis_cache
from api.decision_logger import decision_logger


def make_decision(request: GameStateRequest) -> Dict:
    """
    Принимает решение через Decision Router (GTO + Exploit)
    
    Args:
        request: Запрос состояния игры
        
    Returns:
        Словарь с решением
    """
    start_time = time.time()
    
    # Преобразуем запрос в формат для Decision Router
    game_state = {
        "street": request.street,
        "hero_position": request.hero_position,
        "dealer": request.dealer,
        "hero_cards": request.hero_cards,
        "board_cards": request.board_cards or "",
        "stacks": request.stacks,
        "bets": request.bets,
        "total_bets": request.total_bets,
        "active_players": request.active_players,
        "pot": request.pot,
        "current_player": request.current_player,
        "last_raise_amount": request.last_raise_amount,
        "small_blind": request.small_blind,
        "big_blind": request.big_blind,
        "bet_sequence": _extract_bet_sequence(request),
        "current_bet": max(request.bets.values()) if request.bets else 0.0,
        "stack": request.stacks.get(str(request.hero_position), 100.0)
    }
    
    # Проверяем кэш (для частых спотов)
    state_hash = _hash_game_state(game_state)
    cached_decision = redis_cache.get_game_state_cache(state_hash)
    
    if cached_decision:
        latency_ms = int((time.time() - start_time) * 1000)
        cached_decision["latency_ms"] = latency_ms
        cached_decision["cached"] = True
        return cached_decision
    
    # Получаем ID оппонентов
    opponent_ids = request.opponent_ids or []
    
    # Принимаем решение через Decision Router
    db = SessionLocal()
    gto_strategy = None
    exploit_adjustments = None
    reasoning = {}
    
    try:
        decision = decision_router.decide(
            game_state=game_state,
            opponent_ids=opponent_ids,
            limit_type=request.limit_type,
            style="neutral",
            db_session=db
        )
        
        gto_strategy = decision.get("gto_strategy")
        exploit_adjustments = decision.get("exploit_adjustments")
        reasoning = decision.get("reasoning", {})
        
        # Преобразуем действие в формат API
        action = decision["action"]
        amount = decision.get("amount")
        
        # Нормализуем действие (check вместо call когда можно)
        if action == "call" and max(request.bets.values()) == 0:
            action = "check"
        
        # Добавляем timing delay для человечности (через anti-pattern router)
        from brain.anti_pattern_router import anti_pattern_router
        timing_delay = anti_pattern_router.add_timing_delay()
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        result = {
            "action": action,
            "amount": amount,
            "reasoning": reasoning,
            "latency_ms": latency_ms,
            "cached": False
        }
        
        # Кэшируем решение для частых спотов (только стандартные)
        if _is_standard_spot(game_state):
            redis_cache.set_game_state_cache(state_hash, result, ttl=300)
        
        # Логируем решение
        decision_logger.log_decision(
            hand_id=request.hand_id,
            street=request.street,
            game_state=game_state,
            gto_strategy=gto_strategy,
            exploit_adjustments=exploit_adjustments,
            final_action=action,
            action_amount=amount,
            reasoning=reasoning,
            latency_ms=latency_ms,
            db_session=db
        )
        
        return result
    
    except Exception as e:
        # Fallback на stub при ошибке
        print(f"Ошибка в Decision Router: {e}")
        return make_decision_stub(request)
    
    finally:
        db.close()


def _hash_game_state(game_state: Dict) -> str:
    """Создает хэш состояния игры для кэширования"""
    # Упрощенный хэш (только ключевые параметры)
    key_parts = [
        game_state.get("street", ""),
        str(game_state.get("hero_position", 0)),
        game_state.get("board_cards", ""),
        str(game_state.get("pot", 0)),
        str(len(game_state.get("active_players", [])))
    ]
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def _is_standard_spot(game_state: Dict) -> bool:
    """Проверяет, является ли спот стандартным (для кэширования)"""
    # Упрощенная проверка: стандартные споты - это частые комбинации
    # В реальной реализации нужно более точное определение
    street = game_state.get("street", "")
    pot = game_state.get("pot", 0)
    
    # Стандартные споты: префлоп и флоп с небольшим потом
    return street in ["preflop", "flop"] and pot < 50.0


def _extract_bet_sequence(request: GameStateRequest) -> str:
    """
    Извлекает последовательность ставок из запроса (упрощенно)
    
    В реальной реализации нужно анализировать hand_history
    """
    # Упрощенная реализация: возвращаем пустую строку
    # В будущем нужно парсить hand_history из request
    return ""


# Для обратной совместимости
def make_decision_stub(request: GameStateRequest) -> Dict:
    """Stub реализация (fallback)"""
    import random
    
    max_bet = max(request.bets.values()) if request.bets else 0.0
    hero_bet = request.bets.get(str(request.hero_position), 0.0)
    call_amount = max_bet - hero_bet
    
    if call_amount > 0 and call_amount <= request.big_blind * 2:
        return {
            "action": "call",
            "amount": None,
            "reasoning": {"type": "stub", "reason": "small_call"}
        }
    
    if call_amount == 0:
        return {
            "action": "check",
            "amount": None,
            "reasoning": {"type": "stub", "reason": "can_check"}
        }
    
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
