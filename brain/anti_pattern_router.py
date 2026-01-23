"""Anti-Pattern Router - вставляет человеческие ошибки для анти-палевности

Включает Fingerprint Control для:
- Анализа паттернов действий
- Детекции редких линий
- Маскировки ботовых паттернов
"""

from typing import Dict, List, Optional, Tuple
import random
import time
import yaml
import json
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class FingerprintController:
    """
    Контроллер отпечатков - анализирует и маскирует ботовые паттерны

    Отслеживает:
    - Частоту действий по улицам
    - Размеры ставок
    - Тайминги решений
    - Редкие линии игры
    - Подозрительные паттерны
    """

    # Референсные человеческие паттерны (из hand history анализа)
    HUMAN_REFERENCE = {
        "action_distribution": {
            "preflop": {"fold": 0.55, "call": 0.25, "raise": 0.20},
            "flop": {"fold": 0.35, "check": 0.30, "call": 0.20, "raise": 0.15},
            "turn": {"fold": 0.30, "check": 0.35, "call": 0.20, "raise": 0.15},
            "river": {"fold": 0.25, "check": 0.40, "call": 0.20, "raise": 0.15},
        },
        "bet_sizing": {
            "min_bet_frequency": 0.08,  # 8% min-bets у людей
            "pot_bet_frequency": 0.15,  # 15% pot-size bets
            "overbet_frequency": 0.05,  # 5% overbets
        },
        "timing": {
            "instant_action_pct": 0.10,  # 10% мгновенных решений
            "long_tank_pct": 0.05,  # 5% долгих размышлений
            "avg_decision_ms": 2500,  # Среднее время решения
            "std_decision_ms": 1500,  # Стандартное отклонение
        },
        "rare_lines": {
            "donk_bet_frequency": 0.06,  # 6% донк-бетов
            "check_raise_frequency": 0.04,  # 4% чек-рейзов
            "limp_reraise_frequency": 0.02,  # 2% limp-reraise
            "min_3bet_frequency": 0.03,  # 3% мин-3бетов
        }
    }

    # Подозрительные ботовые паттерны для детекции
    SUSPICIOUS_PATTERNS = {
        "too_consistent_timing": {
            "threshold": 0.05,  # Меньше 5% вариации во времени = подозрительно
            "description": "Слишком консистентное время решений"
        },
        "perfect_bet_sizing": {
            "threshold": 0.90,  # Больше 90% идеальных размеров = подозрительно
            "description": "Слишком точные размеры ставок"
        },
        "no_mistakes": {
            "threshold": 0.02,  # Меньше 2% ошибок = подозрительно
            "description": "Отсутствие человеческих ошибок"
        },
        "no_rare_lines": {
            "threshold": 0.01,  # Меньше 1% редких линий = подозрительно
            "description": "Отсутствие редких линий"
        },
    }

    def __init__(self, window_size: int = 1000):
        """
        Args:
            window_size: Размер окна для анализа (количество рук)
        """
        self.window_size = window_size

        # Статистика действий
        self.action_history: List[Dict] = []
        self.timing_history: List[float] = []
        self.bet_sizing_history: List[Dict] = []

        # Счетчики редких линий
        self.rare_line_counts = defaultdict(int)
        self.total_hands = 0

        # Текущий отпечаток
        self.current_fingerprint = {}

        # Флаги подозрений
        self.suspicion_flags = {}

    def record_action(self, action: str, amount: Optional[float],
                     game_state: Dict, decision_time_ms: float):
        """
        Записывает действие для анализа отпечатка

        Args:
            action: Выполненное действие
            amount: Размер ставки
            game_state: Состояние игры
            decision_time_ms: Время принятия решения в мс
        """
        street = game_state.get("street", "preflop")
        pot = game_state.get("pot", 1.0)
        hand_id = game_state.get("hand_id", "")

        # Запись действия
        action_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hand_id": hand_id,
            "street": street,
            "action": action,
            "amount": amount,
            "pot": pot,
            "decision_time_ms": decision_time_ms
        }
        self.action_history.append(action_record)

        # Запись тайминга
        self.timing_history.append(decision_time_ms)

        # Запись sizing
        if amount and pot > 0:
            bet_ratio = amount / pot
            self.bet_sizing_history.append({
                "street": street,
                "bet_ratio": bet_ratio,
                "is_min_bet": bet_ratio < 0.35,
                "is_pot_bet": 0.9 <= bet_ratio <= 1.1,
                "is_overbet": bet_ratio > 1.5
            })

        # Детекция редких линий
        self._detect_rare_line(action, game_state)

        # Ограничение размера истории
        if len(self.action_history) > self.window_size:
            self.action_history = self.action_history[-self.window_size:]
        if len(self.timing_history) > self.window_size:
            self.timing_history = self.timing_history[-self.window_size:]
        if len(self.bet_sizing_history) > self.window_size:
            self.bet_sizing_history = self.bet_sizing_history[-self.window_size:]

    def _detect_rare_line(self, action: str, game_state: Dict):
        """Детектирует редкую линию"""
        street = game_state.get("street", "preflop")
        bet_sequence = game_state.get("bet_sequence", "")
        hero_position = game_state.get("hero_position", 0)
        aggressor = game_state.get("last_aggressor", -1)

        # Донк-бет: ставка OOP когда не были агрессором
        if street != "preflop" and action in ["bet", "raise"]:
            is_oop = hero_position < 3
            was_not_aggressor = aggressor != hero_position
            if is_oop and was_not_aggressor:
                self.rare_line_counts["donk_bet"] += 1

        # Чек-рейз
        if "x" in bet_sequence and action == "raise":
            self.rare_line_counts["check_raise"] += 1

        # Limp-reraise на префлопе
        if street == "preflop" and "l" in bet_sequence and action == "raise":
            self.rare_line_counts["limp_reraise"] += 1

        # Min-3bet
        if street == "preflop" and "r" in bet_sequence and action == "raise":
            amount = game_state.get("raise_amount", 0)
            last_raise = game_state.get("last_raise_amount", 0)
            if amount > 0 and last_raise > 0:
                if amount <= last_raise * 2.5:  # Мин-рейз это примерно 2-2.5x
                    self.rare_line_counts["min_3bet"] += 1

        self.total_hands += 1

    def analyze_fingerprint(self) -> Dict:
        """
        Анализирует текущий отпечаток бота

        Returns:
            Словарь с анализом отпечатка
        """
        if len(self.action_history) < 100:
            return {"status": "insufficient_data", "hands": len(self.action_history)}

        fingerprint = {}

        # 1. Анализ распределения действий
        fingerprint["action_distribution"] = self._analyze_action_distribution()

        # 2. Анализ тайминга
        fingerprint["timing_analysis"] = self._analyze_timing()

        # 3. Анализ размеров ставок
        fingerprint["bet_sizing_analysis"] = self._analyze_bet_sizing()

        # 4. Анализ редких линий
        fingerprint["rare_lines_analysis"] = self._analyze_rare_lines()

        # 5. Детекция подозрительных паттернов
        fingerprint["suspicion_score"] = self._calculate_suspicion_score(fingerprint)

        # 6. Рекомендации
        fingerprint["recommendations"] = self._generate_recommendations(fingerprint)

        self.current_fingerprint = fingerprint
        return fingerprint

    def _analyze_action_distribution(self) -> Dict:
        """Анализирует распределение действий по улицам"""
        distribution = defaultdict(lambda: defaultdict(int))

        for record in self.action_history:
            street = record["street"]
            action = record["action"]
            distribution[street][action] += 1

        # Нормализуем в проценты
        result = {}
        for street, actions in distribution.items():
            total = sum(actions.values())
            if total > 0:
                result[street] = {
                    action: count / total
                    for action, count in actions.items()
                }

        # Сравниваем с референсом
        deviations = {}
        for street in result:
            if street in self.HUMAN_REFERENCE["action_distribution"]:
                ref = self.HUMAN_REFERENCE["action_distribution"][street]
                deviation = sum(
                    abs(result[street].get(action, 0) - ref.get(action, 0))
                    for action in set(list(result[street].keys()) + list(ref.keys()))
                )
                deviations[street] = deviation

        return {
            "distribution": result,
            "deviations_from_human": deviations,
            "is_suspicious": any(d > 0.3 for d in deviations.values())
        }

    def _analyze_timing(self) -> Dict:
        """Анализирует тайминг решений"""
        if len(self.timing_history) < 50:
            return {"status": "insufficient_data"}

        import statistics

        timings = self.timing_history[-500:]  # Последние 500 решений

        avg_time = statistics.mean(timings)
        std_time = statistics.stdev(timings) if len(timings) > 1 else 0
        cv = std_time / avg_time if avg_time > 0 else 0  # Коэффициент вариации

        instant_actions = sum(1 for t in timings if t < 500) / len(timings)
        long_tanks = sum(1 for t in timings if t > 5000) / len(timings)

        ref = self.HUMAN_REFERENCE["timing"]

        return {
            "avg_decision_ms": avg_time,
            "std_decision_ms": std_time,
            "coefficient_of_variation": cv,
            "instant_action_pct": instant_actions,
            "long_tank_pct": long_tanks,
            "is_suspicious": cv < self.SUSPICIOUS_PATTERNS["too_consistent_timing"]["threshold"],
            "deviation_from_human": {
                "avg_time_diff": abs(avg_time - ref["avg_decision_ms"]),
                "instant_diff": abs(instant_actions - ref["instant_action_pct"]),
            }
        }

    def _analyze_bet_sizing(self) -> Dict:
        """Анализирует размеры ставок"""
        if len(self.bet_sizing_history) < 50:
            return {"status": "insufficient_data"}

        sizing = self.bet_sizing_history[-500:]

        min_bet_freq = sum(1 for s in sizing if s["is_min_bet"]) / len(sizing)
        pot_bet_freq = sum(1 for s in sizing if s["is_pot_bet"]) / len(sizing)
        overbet_freq = sum(1 for s in sizing if s["is_overbet"]) / len(sizing)

        # Подозрительно если слишком много "идеальных" размеров (pot-size)
        ref = self.HUMAN_REFERENCE["bet_sizing"]

        return {
            "min_bet_frequency": min_bet_freq,
            "pot_bet_frequency": pot_bet_freq,
            "overbet_frequency": overbet_freq,
            "is_suspicious": pot_bet_freq > self.SUSPICIOUS_PATTERNS["perfect_bet_sizing"]["threshold"],
            "deviation_from_human": {
                "min_bet_diff": abs(min_bet_freq - ref["min_bet_frequency"]),
                "pot_bet_diff": abs(pot_bet_freq - ref["pot_bet_frequency"]),
                "overbet_diff": abs(overbet_freq - ref["overbet_frequency"]),
            }
        }

    def _analyze_rare_lines(self) -> Dict:
        """Анализирует частоту редких линий"""
        if self.total_hands < 100:
            return {"status": "insufficient_data"}

        ref = self.HUMAN_REFERENCE["rare_lines"]

        frequencies = {
            line: count / self.total_hands
            for line, count in self.rare_line_counts.items()
        }

        # Проверяем, есть ли редкие линии вообще
        total_rare_lines = sum(frequencies.values())
        expected_rare_lines = sum(ref.values())

        return {
            "frequencies": frequencies,
            "total_rare_lines_pct": total_rare_lines,
            "expected_rare_lines_pct": expected_rare_lines,
            "is_suspicious": total_rare_lines < self.SUSPICIOUS_PATTERNS["no_rare_lines"]["threshold"],
            "deviation_from_human": {
                line: abs(frequencies.get(line, 0) - ref.get(f"{line}_frequency", 0))
                for line in ["donk_bet", "check_raise", "limp_reraise", "min_3bet"]
            }
        }

    def _calculate_suspicion_score(self, fingerprint: Dict) -> float:
        """
        Вычисляет общий балл подозрительности (0-100)

        0-20: Выглядит как человек
        21-50: Небольшие отклонения
        51-80: Подозрительно
        81-100: Явно бот
        """
        score = 0

        # Тайминг (до 30 баллов)
        timing = fingerprint.get("timing_analysis", {})
        if timing.get("is_suspicious"):
            score += 30
        elif timing.get("coefficient_of_variation", 1) < 0.15:
            score += 15

        # Размеры ставок (до 25 баллов)
        sizing = fingerprint.get("bet_sizing_analysis", {})
        if sizing.get("is_suspicious"):
            score += 25
        elif sizing.get("pot_bet_frequency", 0) > 0.5:
            score += 10

        # Редкие линии (до 25 баллов)
        rare = fingerprint.get("rare_lines_analysis", {})
        if rare.get("is_suspicious"):
            score += 25
        elif rare.get("total_rare_lines_pct", 1) < 0.03:
            score += 10

        # Распределение действий (до 20 баллов)
        actions = fingerprint.get("action_distribution", {})
        if actions.get("is_suspicious"):
            score += 20

        return min(100, score)

    def _generate_recommendations(self, fingerprint: Dict) -> List[str]:
        """Генерирует рекомендации по улучшению fingerprint"""
        recommendations = []
        score = fingerprint.get("suspicion_score", 0)

        if score > 50:
            recommendations.append("CRITICAL: Fingerprint highly suspicious!")

        # Рекомендации по таймингу
        timing = fingerprint.get("timing_analysis", {})
        if timing.get("is_suspicious"):
            recommendations.append(
                "Add more timing variation (target CV > 0.3)"
            )
        if timing.get("instant_action_pct", 0) < 0.05:
            recommendations.append(
                "Add some instant actions (target 8-12%)"
            )
        if timing.get("long_tank_pct", 0) < 0.02:
            recommendations.append(
                "Add occasional long tanks (target 3-7%)"
            )

        # Рекомендации по sizing
        sizing = fingerprint.get("bet_sizing_analysis", {})
        if sizing.get("min_bet_frequency", 0) < 0.05:
            recommendations.append(
                "Add more min-bets (target 6-10%)"
            )
        if sizing.get("overbet_frequency", 0) < 0.02:
            recommendations.append(
                "Add occasional overbets (target 3-7%)"
            )

        # Рекомендации по редким линиям
        rare = fingerprint.get("rare_lines_analysis", {})
        freqs = rare.get("frequencies", {})
        if freqs.get("donk_bet", 0) < 0.03:
            recommendations.append(
                "Add more donk-bets (target 4-8%)"
            )
        if freqs.get("check_raise", 0) < 0.02:
            recommendations.append(
                "Add more check-raises (target 3-5%)"
            )

        if not recommendations:
            recommendations.append("Fingerprint looks human-like")

        return recommendations

    def get_adjustment_params(self) -> Dict:
        """
        Возвращает параметры для корректировки AntiPatternRouter

        Returns:
            Словарь с рекомендуемыми параметрами
        """
        fingerprint = self.analyze_fingerprint()

        adjustments = {
            "timing": {},
            "sizing": {},
            "rare_lines": {}
        }

        # Корректировка тайминга
        timing = fingerprint.get("timing_analysis", {})
        if timing.get("is_suspicious"):
            adjustments["timing"]["add_variance"] = True
            adjustments["timing"]["target_cv"] = 0.4
        if timing.get("instant_action_pct", 0) < 0.08:
            adjustments["timing"]["instant_action_boost"] = 0.05
        if timing.get("long_tank_pct", 0) < 0.03:
            adjustments["timing"]["long_tank_boost"] = 0.02

        # Корректировка sizing
        sizing = fingerprint.get("bet_sizing_analysis", {})
        if sizing.get("min_bet_frequency", 0) < 0.06:
            adjustments["sizing"]["min_bet_boost"] = 0.04
        if sizing.get("overbet_frequency", 0) < 0.03:
            adjustments["sizing"]["overbet_boost"] = 0.02

        # Корректировка редких линий
        rare = fingerprint.get("rare_lines_analysis", {})
        freqs = rare.get("frequencies", {})
        if freqs.get("donk_bet", 0) < 0.04:
            adjustments["rare_lines"]["donk_bet_boost"] = 0.03
        if freqs.get("check_raise", 0) < 0.03:
            adjustments["rare_lines"]["check_raise_boost"] = 0.02

        return adjustments

    def export_report(self, filepath: Path):
        """Экспортирует отчет fingerprint в файл"""
        fingerprint = self.analyze_fingerprint()

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_hands_analyzed": len(self.action_history),
            "fingerprint": fingerprint,
            "raw_counts": {
                "rare_lines": dict(self.rare_line_counts),
                "total_hands": self.total_hands
            }
        }

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Fingerprint report exported to {filepath}")


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

        # Fingerprint Controller для анализа паттернов
        self.fingerprint_controller = FingerprintController(window_size=1000)
        self.fingerprint_adjustments = {}
        self.last_fingerprint_check = 0
        self.fingerprint_check_interval = 100  # Проверять каждые 100 рук

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
        
        # 6. Периодические thin value bets (расширенный fingerprint)
        if action == "check" and self._should_thin_value_bet(street, game_state, strategy):
            action = "raise"
            amount = pot * random.uniform(0.25, 0.40)  # Thin value bet
        
        # 7. Случайные overbets (5% случаев)
        if action == "raise" and random.random() < 0.05:
            amount = pot * random.uniform(1.2, 2.0)  # Overbet 120-200% пота
        
        # 8. Периодические min-donks (редко, но важно)
        if street != "preflop" and action == "check" and self._should_min_donk(street, hero_position):
            action = "raise"
            amount = pot * 0.15  # Min donk bet
        
        # 9. Случайные slow-plays (чек с сильной рукой)
        if action == "raise" and self._should_slow_play(street, game_state, strategy):
            action = "check"
            amount = None
        
        # 10. Периодические float IP (call с целью блефа на следующей улице)
        if action == "fold" and self._should_float_ip(street, hero_position, game_state):
            action = "call"
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
    
    def _should_thin_value_bet(self, street: str, game_state: Dict, strategy: Dict[str, float]) -> bool:
        """Проверяет, нужно ли сделать thin value bet вместо чека"""
        # Thin value bet: ставка с маргинальной рукой для value
        # Чаще на терне/ривере IP против фишей
        hero_position = game_state.get("hero_position", 0)
        is_ip = hero_position >= 3
        
        if street in ["turn", "river"] and is_ip:
            # 8-12% случаев делаем thin value bet
            return random.random() < 0.10
        return False
    
    def _should_min_donk(self, street: str, hero_position: int) -> bool:
        """Проверяет, нужно ли сделать min donk bet"""
        # Min donk: очень маленькая ставка OOP (редко, но важно для fingerprint)
        is_oop = hero_position < 3
        if street == "flop" and is_oop:
            # 2-4% случаев на флопе
            return random.random() < 0.03
        return False
    
    def _should_slow_play(self, street: str, game_state: Dict, strategy: Dict[str, float]) -> bool:
        """Проверяет, нужно ли сделать slow-play (чек с сильной рукой)"""
        # Slow-play: чек с очень сильной рукой для постройки пота
        # Чаще на флопе/терне с монстрами
        if street in ["flop", "turn"]:
            # Если стратегия сильно склоняется к raise (сильная рука)
            raise_prob = strategy.get("raise", 0.0)
            if raise_prob > 0.85:
                # 5-8% случаев делаем slow-play
                return random.random() < 0.06
        return False
    
    def _should_float_ip(self, street: str, hero_position: int, game_state: Dict) -> bool:
        """Проверяет, нужно ли сделать float IP (call с целью блефа)"""
        # Float: call IP с целью блефа на следующей улице
        is_ip = hero_position >= 3
        pot = game_state.get("pot", 0.0)
        last_bet = game_state.get("last_raise_amount", 0.0)
        
        if street in ["flop", "turn"] and is_ip:
            # Float если ставка небольшая относительно пота (< 40%)
            if last_bet > 0 and pot > 0 and (last_bet / pot) < 0.4:
                # 10-15% случаев делаем float
                return random.random() < 0.12
        return False
    
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

    def record_decision(self, action: str, amount: Optional[float],
                       game_state: Dict, decision_time_ms: float):
        """
        Записывает решение для fingerprint анализа

        Args:
            action: Выполненное действие
            amount: Размер ставки
            game_state: Состояние игры
            decision_time_ms: Время принятия решения в мс
        """
        self.fingerprint_controller.record_action(
            action, amount, game_state, decision_time_ms
        )

        # Периодически проверяем fingerprint и обновляем корректировки
        self.fingerprint_controller.total_hands += 1
        if (self.fingerprint_controller.total_hands - self.last_fingerprint_check
                >= self.fingerprint_check_interval):
            self._update_fingerprint_adjustments()
            self.last_fingerprint_check = self.fingerprint_controller.total_hands

    def _update_fingerprint_adjustments(self):
        """Обновляет корректировки на основе fingerprint анализа"""
        try:
            self.fingerprint_adjustments = self.fingerprint_controller.get_adjustment_params()
            fingerprint = self.fingerprint_controller.current_fingerprint

            suspicion_score = fingerprint.get("suspicion_score", 0)

            if suspicion_score > 50:
                logger.warning(
                    f"Fingerprint suspicion score HIGH: {suspicion_score}. "
                    f"Recommendations: {fingerprint.get('recommendations', [])}"
                )

                # Автоматически включаем anti-patterns если score высокий
                if not self.enabled and suspicion_score > 70:
                    logger.warning("Auto-enabling anti-patterns due to high suspicion score")
                    self.enabled = True

            elif suspicion_score < 20:
                logger.info(f"Fingerprint looks human-like. Score: {suspicion_score}")

        except Exception as e:
            logger.error(f"Error updating fingerprint adjustments: {e}")

    def get_fingerprint_report(self) -> Dict:
        """
        Получает полный отчет fingerprint

        Returns:
            Словарь с анализом fingerprint
        """
        return self.fingerprint_controller.analyze_fingerprint()

    def export_fingerprint_report(self, filepath: Path):
        """
        Экспортирует отчет fingerprint в файл

        Args:
            filepath: Путь к файлу отчета
        """
        self.fingerprint_controller.export_report(filepath)

    def apply_fingerprint_corrections(self, action: str, amount: Optional[float],
                                     game_state: Dict) -> Tuple[str, Optional[float]]:
        """
        Применяет корректировки на основе fingerprint анализа

        Args:
            action: Исходное действие
            amount: Размер ставки
            game_state: Состояние игры

        Returns:
            Корректированное действие и размер
        """
        if not self.fingerprint_adjustments:
            return action, amount

        pot = game_state.get("pot", 1.0)
        street = game_state.get("street", "preflop")

        # Корректировка размеров ставок
        sizing_adj = self.fingerprint_adjustments.get("sizing", {})

        if action == "raise" and amount:
            # Добавляем min-bets если не хватает
            if sizing_adj.get("min_bet_boost", 0) > 0:
                if random.random() < sizing_adj["min_bet_boost"]:
                    amount = pot * random.uniform(0.25, 0.35)

            # Добавляем overbets если не хватает
            elif sizing_adj.get("overbet_boost", 0) > 0:
                if random.random() < sizing_adj["overbet_boost"]:
                    amount = pot * random.uniform(1.5, 2.5)

        # Корректировка редких линий
        rare_adj = self.fingerprint_adjustments.get("rare_lines", {})

        # Добавляем донк-беты
        if rare_adj.get("donk_bet_boost", 0) > 0:
            if street != "preflop" and action == "check":
                if random.random() < rare_adj["donk_bet_boost"]:
                    action = "raise"
                    amount = pot * random.uniform(0.3, 0.5)

        # Добавляем чек-рейзы
        if rare_adj.get("check_raise_boost", 0) > 0:
            if action == "call" and "x" in game_state.get("bet_sequence", ""):
                if random.random() < rare_adj["check_raise_boost"]:
                    action = "raise"
                    amount = pot * random.uniform(0.8, 1.2)

        return action, amount

    def get_timing_with_variation(self) -> float:
        """
        Возвращает задержку с учетом fingerprint корректировок

        Returns:
            Задержка в миллисекундах
        """
        timing_adj = self.fingerprint_adjustments.get("timing", {})

        # Базовая задержка
        base_delay = random.uniform(self.timing_delay_min, self.timing_delay_max)

        # Добавляем вариацию если нужно
        if timing_adj.get("add_variance"):
            target_cv = timing_adj.get("target_cv", 0.4)
            # Добавляем случайные выбросы
            if random.random() < 0.15:
                base_delay *= random.uniform(2.0, 4.0)

        # Instant actions
        if timing_adj.get("instant_action_boost", 0) > 0:
            if random.random() < timing_adj["instant_action_boost"]:
                base_delay = random.uniform(50, 200)

        # Long tanks
        if timing_adj.get("long_tank_boost", 0) > 0:
            if random.random() < timing_adj["long_tank_boost"]:
                base_delay = random.uniform(5000, 10000)

        return base_delay


# Глобальный экземпляр
anti_pattern_router = AntiPatternRouter()
