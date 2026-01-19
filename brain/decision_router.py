"""Decision Router - смешивание GTO и exploit стратегий"""

from typing import Dict, List, Optional, Tuple
import random
import yaml
from pathlib import Path

from .opponent_profiler import opponent_profiler, PlayerType
from .strategy_loader import strategy_loader
from .game_tree import GameTree
from .anti_pattern_router import anti_pattern_router
from data.database import SessionLocal
from engine.env_wrapper import Street


class DecisionRouter:
    """Роутер решений - смешивает GTO и exploit стратегии"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: Путь к конфигурации стиля
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "bot_styles.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.decision_weights = self.config.get("decision_weights", {
            "preflop": {"gto_weight": 0.7, "exploit_weight": 0.3},
            "postflop": {"gto_weight": 0.4, "exploit_weight": 0.6}
        })
        
        self.style_targets = self._load_style_targets()
        self.current_stats = {
            "vpip": 0.0,
            "pfr": 0.0,
            "three_bet_pct": 0.0,
            "aggression_factor": 0.0,
            "hands_played": 0
        }
    
    def _load_style_targets(self) -> Dict:
        """Загружает целевые параметры стиля"""
        # По умолчанию NL10 neutral
        styles = self.config.get("styles", {})
        nl10 = styles.get("NL10", {})
        return nl10.get("neutral", {})
    
    def decide(self, game_state: Dict, opponent_ids: List[str], 
              limit_type: str = "NL10", style: str = "neutral",
              db_session=None) -> Dict[str, any]:
        """
        Принимает решение на основе GTO + exploit
        
        Args:
            game_state: Состояние игры
            opponent_ids: ID оппонентов
            limit_type: Лимит (NL10, NL50)
            style: Стиль (gentle, neutral)
            db_session: Сессия БД
            
        Returns:
            Словарь с решением
        """
        if db_session is None:
            db = SessionLocal()
        else:
            db = db_session
        
        try:
            street = game_state.get("street", "preflop")
            hero_position = game_state.get("hero_position", 0)
            
            # 1. Получаем GTO стратегию
            gto_strategy = self._get_gto_strategy(game_state, limit_type)
            
            # 2. Получаем exploit коррекции
            exploit_adjustments = self._get_exploit_adjustments(
                opponent_ids, street, game_state, db
            )
            
            # 3. Смешиваем стратегии
            final_strategy = self._mix_strategies(
                gto_strategy, exploit_adjustments, street
            )
            
            # 4. Корректируем под целевой стиль
            final_strategy = self._adjust_to_style_targets(
                final_strategy, street, limit_type, style
            )
            
            # 5. Выбираем действие
            action, amount = self._sample_action(final_strategy, game_state)
            
            # 6. Применяем anti-pattern коррекции (человеческие ошибки)
            action, amount = anti_pattern_router.apply_anti_patterns(
                action, amount, game_state, final_strategy
            )
            
            return {
                "action": action,
                "amount": amount,
                "strategy": final_strategy,
                "gto_strategy": gto_strategy,
                "exploit_adjustments": exploit_adjustments,
                "reasoning": {
                    "type": "gto_exploit_mix",
                    "street": street,
                    "gto_weight": self.decision_weights.get(street, {}).get("gto_weight", 0.5),
                    "exploit_weight": self.decision_weights.get(street, {}).get("exploit_weight", 0.5),
                    "anti_pattern_applied": True
                }
            }
        
        finally:
            if db_session is None:
                db.close()
    
    def _get_gto_strategy(self, game_state: Dict, limit_type: str) -> Dict[str, float]:
        """
        Получает GTO стратегию из MCCFR
        
        Args:
            game_state: Состояние игры
            limit_type: Лимит
            
        Returns:
            Словарь {действие: вероятность}
        """
        # Генерируем информационное множество
        street = game_state.get("street", "preflop")
        hero_position = game_state.get("hero_position", 0)
        board_cards = game_state.get("board_cards", "")
        bet_sequence = game_state.get("bet_sequence", "")
        
        # Упрощенное информационное множество
        infoset = f"{street}_{hero_position}_{board_cards}_{bet_sequence}"
        
        # Загружаем стратегию
        strategy = strategy_loader.get_action_probabilities(limit_type, infoset)
        
        if not strategy:
            # Fallback: равномерная стратегия
            available_actions = self._get_available_actions(game_state)
            return {action: 1.0 / len(available_actions) for action in available_actions}
        
        return strategy
    
    def _get_exploit_adjustments(self, opponent_ids: List[str], street: str,
                                game_state: Dict, db) -> Dict[str, any]:
        """
        Получает эксплойт-коррекции для оппонентов
        
        Args:
            opponent_ids: ID оппонентов
            street: Улица
            game_state: Состояние игры
            db: Сессия БД
            
        Returns:
            Словарь с коррекциями
        """
        if not opponent_ids:
            return {"type": "gto", "adjustments": {}}
        
        # Берем главного оппонента (первого в списке или по стеку)
        main_opponent = opponent_ids[0]
        
        exploit = opponent_profiler.suggest_exploit(
            main_opponent, street, game_state, db
        )
        
        return exploit
    
    def _mix_strategies(self, gto_strategy: Dict[str, float],
                       exploit_adjustments: Dict, street: str) -> Dict[str, float]:
        """
        Смешивает GTO и exploit стратегии
        
        Args:
            gto_strategy: GTO стратегия
            exploit_adjustments: Эксплойт-коррекции
            street: Улица
            
        Returns:
            Смешанная стратегия
        """
        weights = self.decision_weights.get(street, {})
        gto_weight = weights.get("gto_weight", 0.5)
        exploit_weight = weights.get("exploit_weight", 0.5)
        
        # Начинаем с GTO стратегии
        mixed_strategy = gto_strategy.copy()
        
        # Применяем эксплойт-коррекции
        adjustments = exploit_adjustments.get("adjustments", {})
        
        for action in mixed_strategy:
            # Корректируем вероятности действий
            if "bluff_frequency" in adjustments and action in ["raise", "bet"]:
                # Увеличиваем/уменьшаем блефовые действия
                mixed_strategy[action] *= (1.0 + adjustments["bluff_frequency"])
            
            if "value_bet_frequency" in adjustments and action in ["raise", "bet"]:
                # Увеличиваем value-беты
                mixed_strategy[action] *= (1.0 + adjustments["value_bet_frequency"])
            
            if "call_frequency" in adjustments and action == "call":
                # Корректируем коллы
                mixed_strategy[action] *= (1.0 + adjustments["call_frequency"])
            
            if "fold_frequency" in adjustments and action == "fold":
                # Корректируем фолды
                mixed_strategy[action] *= (1.0 + adjustments["fold_frequency"])
        
        # Нормализуем
        total = sum(mixed_strategy.values())
        if total > 0:
            mixed_strategy = {k: v / total for k, v in mixed_strategy.items()}
        
        return mixed_strategy
    
    def _adjust_to_style_targets(self, strategy: Dict[str, float], street: str,
                                limit_type: str, style: str) -> Dict[str, float]:
        """
        Корректирует стратегию под целевые параметры стиля
        
        Args:
            strategy: Текущая стратегия
            street: Улица
            limit_type: Лимит
            style: Стиль
            
        Returns:
            Скорректированная стратегия
        """
        # Загружаем целевые параметры
        styles = self.config.get("styles", {})
        limit_config = styles.get(limit_type, {})
        style_config = limit_config.get(style, {})
        
        if not style_config:
            return strategy
        
        # Проверяем текущие статы бота
        # Если VPIP слишком низкий - увеличиваем частоту входов
        # Если PFR слишком высокий - уменьшаем рейзы
        # Если AF слишком высокий - уменьшаем агрессию
        
        # Упрощенная реализация: корректируем только префлоп
        if street == "preflop":
            target_vpip = (style_config.get("vpip_min", 26) + style_config.get("vpip_max", 30)) / 2
            current_vpip = self.current_stats.get("vpip", 0)
            
            if current_vpip < target_vpip - 2:
                # Увеличиваем частоту входов (call, raise)
                if "call" in strategy:
                    strategy["call"] *= 1.1
                if "raise" in strategy:
                    strategy["raise"] *= 1.1
            
            elif current_vpip > target_vpip + 2:
                # Уменьшаем частоту входов
                if "call" in strategy:
                    strategy["call"] *= 0.9
                if "raise" in strategy:
                    strategy["raise"] *= 0.9
        
        # Нормализуем
        total = sum(strategy.values())
        if total > 0:
            strategy = {k: v / total for k, v in strategy.items()}
        
        return strategy
    
    def _get_available_actions(self, game_state: Dict) -> List[str]:
        """Получает доступные действия"""
        current_bet = game_state.get("current_bet", 0.0)
        stack = game_state.get("stack", 100.0)
        
        actions = []
        
        if current_bet > 0:
            actions.append("fold")
            if current_bet < stack:
                actions.append("call")
        else:
            actions.append("check")
        
        if stack > current_bet:
            actions.append("raise")
            actions.append("all_in")
        
        return actions
    
    def _sample_action(self, strategy: Dict[str, float], 
                      game_state: Dict) -> Tuple[str, Optional[float]]:
        """
        Выбирает действие на основе стратегии
        
        Args:
            strategy: Стратегия {действие: вероятность}
            game_state: Состояние игры
            
        Returns:
            (действие, размер ставки)
        """
        if not strategy:
            # Fallback
            actions = self._get_available_actions(game_state)
            return random.choice(actions), None
        
        # Сэмплируем действие
        actions = list(strategy.keys())
        probabilities = list(strategy.values())
        
        action = random.choices(actions, weights=probabilities)[0]
        
        # Определяем размер ставки для raise
        amount = None
        if action == "raise":
            pot = game_state.get("pot", 10.0)
            amount = pot * 0.75  # 75% пота (можно сделать умнее)
        elif action == "all_in":
            amount = game_state.get("stack", 100.0)
        
        return action, amount
    
    def update_stats(self, stats: Dict):
        """Обновляет текущую статистику бота"""
        self.current_stats.update(stats)


# Глобальный роутер
decision_router = DecisionRouter()
