"""Anti-Pattern Router - вставляет человеческие ошибки для анти-палевности"""

from typing import Dict, List, Optional, Tuple
import random
import time
import yaml
from pathlib import Path


class AntiPatternRouter:
    """
    Роутер для вставки "человеческих" ошибок и паттернов

    Вставляет:
    - Донк-беты (donk bets)
    - Min-raise вместо оптимальных размеров
    - Периодические чек-бихайнды там, где солвер ставит
    - Хаотичность timing'а
    - Стилистические смещения

    ВАЖНО: Anti-patterns можно отключить через конфигурацию или параметр enabled.
    По умолчанию ОТКЛЮЧЕН для максимизации винрейта.
    """

    def __init__(self, config_path: Optional[Path] = None, enabled: bool = False):
        """
        Args:
            config_path: Путь к конфигурации
            enabled: Включить anti-patterns (по умолчанию False)
        """
        self.enabled = enabled

        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "bot_styles.yaml"

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        anti_pattern_config = self.config.get("anti_pattern", {})

        # Проверяем, включены ли anti-patterns в конфигурации
        self.enabled = anti_pattern_config.get("enabled", self.enabled)

        self.max_bluff_ratio = anti_pattern_config.get("max_bluff_ratio_per_street", {})
        self.min_fold_equity = anti_pattern_config.get("min_fold_equity_target", 0.20)
        self.max_3bet_streak = anti_pattern_config.get("max_3bet_streak", 3)
        self.timing_delay_min = anti_pattern_config.get("timing_delay_min_ms", 30)
        self.timing_delay_max = anti_pattern_config.get("timing_delay_max_ms", 150)
        self.randomizer_seed = anti_pattern_config.get("randomizer_noise_seed", 42)

        # Счетчики для отслеживания паттернов
        self.consecutive_3bets = 0
        self.last_3bet_hand = None
        self.donk_bet_count = 0
        self.min_raise_count = 0

        # Инициализируем random seed для воспроизводимости
        random.seed(self.randomizer_seed)
    
    def apply_anti_patterns(self, action: str, amount: Optional[float],
                          game_state: Dict, strategy: Dict[str, float]) -> Tuple[str, Optional[float]]:
        """
        Применяет anti-pattern коррекции к решению

        Args:
            action: Исходное действие
            amount: Размер ставки
            game_state: Состояние игры
            strategy: Стратегия действий

        Returns:
            Корректированное действие и размер
        """
        # Если anti-patterns отключены, возвращаем исходное решение
        if not self.enabled:
            return action, amount

        street = game_state.get("street", "preflop")
        hero_position = game_state.get("hero_position", 0)
        pot = game_state.get("pot", 0.0)
        board_cards = game_state.get("board_cards", "")
        
        # 1. Донк-бет (donk bet) - ставка OOP после чек-бихайнда
        if self._should_donk_bet(street, hero_position, game_state):
            action, amount = self._apply_donk_bet(action, pot)
            self.donk_bet_count += 1
        
        # 2. Min-raise вместо оптимального размера
        elif action == "raise" and self._should_min_raise(street, game_state):
            amount = self._get_min_raise_amount(game_state)
            self.min_raise_count += 1
        
        # 3. Чек-бихайнд там, где солвер часто ставит
        elif self._should_check_behind(action, street, game_state, strategy):
            action = "check"
            amount = None
        
        # 4. Ограничение 3-bet streak
        if action == "raise" and street == "preflop":
            if self.consecutive_3bets >= self.max_3bet_streak:
                # Превращаем 3-bet в call
                if self._is_3bet_situation(game_state):
                    action = "call"
                    amount = None
                    self.consecutive_3bets = 0
            elif self._is_3bet_situation(game_state):
                self.consecutive_3bets += 1
            else:
                self.consecutive_3bets = 0
        
        # 5. Ограничение bluff ratio
        if action == "raise" and street != "preflop":
            max_bluff = self.max_bluff_ratio.get(street, 0.30)
            if self._is_bluff_situation(game_state, strategy) and random.random() > max_bluff:
                # Превращаем блеф в чек/фолд
                if random.random() < 0.5:
                    action = "check"
                    amount = None
                else:
                    action = "fold"
                    amount = None
        
        return action, amount
    
    def _should_donk_bet(self, street: str, hero_position: int, game_state: Dict) -> bool:
        """Проверяет, нужно ли сделать донк-бет"""
        # Донк-бет: ставка OOP после чек-бихайнда на предыдущей улице
        if street == "preflop":
            return False
        
        # Вероятность донк-бета: 5-10% на флопе, 3-5% на терне
        donk_prob = 0.08 if street == "flop" else 0.04
        
        # Донк-бет чаще OOP
        is_oop = hero_position < 3  # Упрощенно
        
        return is_oop and random.random() < donk_prob
    
    def _apply_donk_bet(self, action: str, pot: float) -> Tuple[str, Optional[float]]:
        """Применяет донк-бет"""
        # Донк-бет обычно 30-50% пота
        bet_size = pot * random.uniform(0.3, 0.5)
        return "raise", bet_size
    
    def _should_min_raise(self, street: str, game_state: Dict) -> bool:
        """Проверяет, нужно ли сделать min-raise"""
        # Min-raise вместо оптимального размера: 10-15% случаев
        return random.random() < 0.12
    
    def _get_min_raise_amount(self, game_state: Dict) -> float:
        """Вычисляет минимальный размер рейза"""
        last_raise = game_state.get("last_raise_amount", 0.0)
        big_blind = game_state.get("big_blind", 1.0)
        
        # Min-raise = последний рейз + минимум (обычно 2x BB)
        min_raise = max(last_raise * 2, big_blind * 2)
        return min_raise
    
    def _should_check_behind(self, action: str, street: str, 
                            game_state: Dict, strategy: Dict[str, float]) -> bool:
        """Проверяет, нужно ли сделать чек-бихайнд вместо ставки"""
        # Если солвер часто ставит (высокая вероятность raise/bet в стратегии)
        bet_prob = strategy.get("raise", 0.0) + strategy.get("bet", 0.0)
        
        # В 5-8% случаев делаем чек-бихайнд вместо ставки
        if bet_prob > 0.7 and random.random() < 0.06:
            return True
        
        return False
    
    def _is_3bet_situation(self, game_state: Dict) -> bool:
        """Проверяет, является ли это 3-bet ситуацией"""
        bet_sequence = game_state.get("bet_sequence", "")
        street = game_state.get("street", "preflop")
        # Упрощенно: если есть рейз префлоп и мы рейзим - это 3-bet
        return "r" in bet_sequence and street == "preflop"
    
    def _is_bluff_situation(self, game_state: Dict, strategy: Dict[str, float]) -> bool:
        """Проверяет, является ли это блефовой ситуацией"""
        # Упрощенно: если вероятность raise высока, но нет сильной руки
        # В реальной реализации нужно анализировать силу руки
        raise_prob = strategy.get("raise", 0.0)
        return raise_prob > 0.5
    
    def add_timing_delay(self) -> float:
        """
        Добавляет человеческую задержку тайминга
        
        Returns:
            Задержка в миллисекундах
        """
        delay_ms = random.uniform(self.timing_delay_min, self.timing_delay_max)
        time.sleep(delay_ms / 1000.0)
        return delay_ms
    
    def reset_counters(self):
        """Сбрасывает счетчики (вызывать в начале новой раздачи)"""
        self.consecutive_3bets = 0
        self.last_3bet_hand = None
    
    def get_statistics(self) -> Dict:
        """Возвращает статистику anti-pattern использования"""
        return {
            "donk_bets": self.donk_bet_count,
            "min_raises": self.min_raise_count,
            "consecutive_3bets": self.consecutive_3bets
        }


# Глобальный экземпляр
anti_pattern_router = AntiPatternRouter()
