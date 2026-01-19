"""Opponent Profiler - анализ и классификация оппонентов"""

from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func
import yaml
from pathlib import Path

from data.database import SessionLocal
from data.models import OpponentProfile, Hand, DecisionLog


class PlayerType:
    """Типы игроков"""
    FISH_LOOSE = "fish_loose"  # VPIP 40%+
    NIT = "nit"  # VPIP <18%
    TAG = "tag"  # Tight-Aggressive, VPIP 18-25%, высокий PFR
    LAG = "lag"  # Loose-Aggressive, VPIP 28-35%, высокий PFR
    CALLING_STATION = "calling_station"  # Низкий AF, много коллов
    UNKNOWN = "unknown"


class OpponentProfiler:
    """Профайлер оппонентов - анализ статистики и классификация"""
    
    def __init__(self):
        self.profiles_cache: Dict[str, OpponentProfile] = {}
        self.min_hands_for_classification = 20  # Минимум раздач для классификации
    
    def update_profile(self, opponent_id: str, hand_data: Dict, db: Session) -> OpponentProfile:
        """
        Обновляет профиль оппонента на основе новой раздачи
        
        Args:
            opponent_id: ID оппонента
            hand_data: Данные раздачи (из hand_history)
            db: Сессия БД
            
        Returns:
            Обновленный профиль
        """
        # Получаем или создаем профиль
        profile = db.query(OpponentProfile).filter(
            OpponentProfile.opponent_id == opponent_id
        ).first()
        
        if not profile:
            profile = OpponentProfile(opponent_id=opponent_id)
            db.add(profile)
        
        # Извлекаем статистику из hand_data
        # hand_data должен содержать:
        # - preflop_action: "fold", "call", "raise", "3bet"
        # - postflop_actions: список действий по улицам
        # - position: позиция игрока
        
        preflop_action = hand_data.get("preflop_action", "")
        postflop_actions = hand_data.get("postflop_actions", [])
        
        # Обновляем счетчики
        profile.hands_played += 1
        
        # VPIP: Voluntarily Put $ In Pot (вложил деньги добровольно)
        if preflop_action in ["call", "raise", "3bet"]:
            profile.vpip = self._update_percentage(
                profile.vpip, profile.hands_played, True
            )
        else:
            profile.vpip = self._update_percentage(
                profile.vpip, profile.hands_played, False
            )
        
        # PFR: Pre-Flop Raise (рейз префлоп)
        if preflop_action in ["raise", "3bet"]:
            profile.pfr = self._update_percentage(
                profile.pfr, profile.hands_played, True
            )
        else:
            profile.pfr = self._update_percentage(
                profile.pfr, profile.hands_played, False
            )
        
        # 3-bet процент
        if preflop_action == "3bet":
            profile.three_bet_pct = self._update_percentage(
                profile.three_bet_pct, profile.hands_played, True
            )
        else:
            profile.three_bet_pct = self._update_percentage(
                profile.three_bet_pct, profile.hands_played, False
            )
        
        # Aggression Factor (AF) = (bets + raises) / calls
        # Упрощенно: считаем агрессивные действия постфлоп
        if postflop_actions:
            bets_raises = sum(1 for a in postflop_actions if a in ["bet", "raise"])
            calls = sum(1 for a in postflop_actions if a == "call")
            
            if calls > 0:
                profile.aggression_factor = bets_raises / calls
            elif bets_raises > 0:
                profile.aggression_factor = bets_raises  # Только агрессия
            else:
                profile.aggression_factor = 0.0
        
        # C-bet процент (упрощенно)
        # fold_to_cbet (упрощенно)
        
        # Классифицируем
        if profile.hands_played >= self.min_hands_for_classification:
            profile.classification = self._classify_player(profile)
        
        db.commit()
        self.profiles_cache[opponent_id] = profile
        
        return profile
    
    def _update_percentage(self, current_pct: float, total_hands: int, 
                          is_true: bool) -> float:
        """Обновляет процентное значение"""
        if total_hands == 0:
            return 100.0 if is_true else 0.0
        
        # Взвешенное среднее
        new_value = 1.0 if is_true else 0.0
        return (current_pct * (total_hands - 1) + new_value * 100) / total_hands
    
    def _classify_player(self, profile: OpponentProfile) -> str:
        """
        Классифицирует игрока по типу
        
        Args:
            profile: Профиль оппонента
            
        Returns:
            Тип игрока
        """
        vpip = float(profile.vpip)
        pfr = float(profile.pfr)
        af = float(profile.aggression_factor)
        
        # Фиш (лузовый)
        if vpip >= 40:
            return PlayerType.FISH_LOOSE
        
        # Нит (титовый)
        if vpip < 18:
            return PlayerType.NIT
        
        # Calling Station (много коллов, мало агрессии)
        if af < 1.0 and vpip > 20:
            return PlayerType.CALLING_STATION
        
        # TAG (Tight-Aggressive)
        if 18 <= vpip <= 25 and pfr >= vpip * 0.8 and af >= 2.0:
            return PlayerType.TAG
        
        # LAG (Loose-Aggressive)
        if 28 <= vpip <= 35 and pfr >= vpip * 0.7 and af >= 2.5:
            return PlayerType.LAG
        
        return PlayerType.UNKNOWN
    
    def get_profile(self, opponent_id: str, db: Session) -> Optional[OpponentProfile]:
        """
        Получает профиль оппонента
        
        Args:
            opponent_id: ID оппонента
            db: Сессия БД
            
        Returns:
            Профиль или None
        """
        # Проверяем кэш
        if opponent_id in self.profiles_cache:
            return self.profiles_cache[opponent_id]
        
        # Загружаем из БД
        profile = db.query(OpponentProfile).filter(
            OpponentProfile.opponent_id == opponent_id
        ).first()
        
        if profile:
            # Обновляем кэш
            self.profiles_cache[opponent_id] = profile
            # Обновляем классификацию если нужно
            if not profile.classification or profile.hands_played >= self.min_hands_for_classification:
                profile.classification = self._classify_player(profile)
                db.commit()
        
        return profile
    
    def get_tendency(self, opponent_id: str, db: Session) -> Dict[str, any]:
        """
        Получает тенденции оппонента
        
        Args:
            opponent_id: ID оппонента
            db: Сессия БД
            
        Returns:
            Словарь с тенденциями
        """
        profile = self.get_profile(opponent_id, db)
        
        if not profile:
            return {
                "type": PlayerType.UNKNOWN,
                "confidence": 0.0,
                "tendencies": {}
            }
        
        classification = profile.classification or PlayerType.UNKNOWN
        confidence = min(profile.hands_played / 50.0, 1.0)  # Максимальная уверенность при 50+ руках
        
        tendencies = {
            "vpip": float(profile.vpip),
            "pfr": float(profile.pfr),
            "three_bet_pct": float(profile.three_bet_pct),
            "aggression_factor": float(profile.aggression_factor),
            "cbet_pct": float(profile.cbet_pct),
            "fold_to_cbet_pct": float(profile.fold_to_cbet_pct),
            "hands_played": profile.hands_played
        }
        
        return {
            "type": classification,
            "confidence": confidence,
            "tendencies": tendencies
        }
    
    def suggest_exploit(self, opponent_id: str, street: str, 
                       game_state: Dict, db: Session) -> Dict[str, any]:
        """
        Предлагает эксплойт-стратегию против оппонента
        
        Args:
            opponent_id: ID оппонента
            street: Улица (preflop, flop, turn, river)
            game_state: Состояние игры
            db: Сессия БД
            
        Returns:
            Словарь с эксплойт-советами
        """
        tendency = self.get_tendency(opponent_id, db)
        player_type = tendency["type"]
        confidence = tendency["confidence"]
        
        exploit = {
            "type": "gto",  # По умолчанию GTO
            "adjustments": {},
            "confidence": confidence
        }
        
        if confidence < 0.3:
            # Недостаточно данных
            return exploit
        
        # Эксплойт-коррекции по типу игрока
        if player_type == PlayerType.FISH_LOOSE:
            # Против фиша: больше value-бетов, меньше блефов
            exploit["type"] = "value_heavy"
            exploit["adjustments"] = {
                "bluff_frequency": -0.2,  # Уменьшить блефы на 20%
                "value_bet_frequency": 0.1,  # Увеличить value-беты на 10%
                "call_frequency": 0.15  # Больше коллов против агрессии
            }
        
        elif player_type == PlayerType.NIT:
            # Против нита: больше блефов, больше рейзов
            exploit["type"] = "bluff_heavy"
            exploit["adjustments"] = {
                "bluff_frequency": 0.15,
                "raise_frequency": 0.1,
                "fold_frequency": -0.1  # Меньше фолдов
            }
        
        elif player_type == PlayerType.CALLING_STATION:
            # Против calling station: только value, никаких блефов
            exploit["type"] = "value_only"
            exploit["adjustments"] = {
                "bluff_frequency": -0.5,  # Сильно уменьшить блефы
                "value_bet_frequency": 0.2,
                "call_frequency": -0.1  # Меньше коллов, больше рейзов
            }
        
        elif player_type == PlayerType.TAG:
            # Против TAG: играть ближе к GTO, но немного больше блефов
            exploit["type"] = "gto_plus"
            exploit["adjustments"] = {
                "bluff_frequency": 0.05,
                "fold_frequency": 0.05  # Больше фолдов в маргинальных спотах
            }
        
        elif player_type == PlayerType.LAG:
            # Против LAG: больше value, меньше блефов, больше коллов
            exploit["type"] = "value_heavy"
            exploit["adjustments"] = {
                "bluff_frequency": -0.1,
                "value_bet_frequency": 0.1,
                "call_frequency": 0.1
            }
        
        return exploit


# Глобальный профайлер
opponent_profiler = OpponentProfiler()
