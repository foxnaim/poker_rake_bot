"""Monte Carlo Counterfactual Regret Minimization (MCCFR) with External Sampling

Реализация External Sampling MCCFR для эффективного обучения покерных стратегий.
Основано на подходе из Pluribus poker AI.

External Sampling:
- Traverser (текущий игрок) исследует ВСЕ действия
- Opponents сэмплируют ОДНО действие согласно стратегии
- Chance nodes сэмплируют ОДИН исход
- Это дает линейную сложность вместо экспоненциальной
"""

import random
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import time
from numba import jit, prange
from numba.types import float64, int32, DictType, unicode_type

from .game_tree import GameTree, GameNode, NodeType
from engine.env_wrapper import PokerEnv, Street, GameState
from engine.cards import parse_cards, cards_to_string
from engine.hand_evaluator import compare_hands
from engine.game_state_validator import game_state_validator


class MCCFR:
    """MCCFR алгоритм с External Sampling для обучения стратегий

    Поддерживает обучение от heads-up (2 игрока) до full-ring (6-9 игроков).
    Для 6-max рекомендуется минимум 100K итераций.
    """

    def __init__(self, game_tree: GameTree, num_players: int = 2, max_depth: int = 15):
        """
        Args:
            game_tree: Дерево игры
            num_players: Количество игроков (2-6, можно до 9)
            max_depth: Максимальная глубина рекурсии (15 для 6-max, 12 для heads-up)
        """
        if num_players < 2 or num_players > 9:
            raise ValueError(f"num_players должно быть от 2 до 9, получено: {num_players}")

        self.game_tree = game_tree
        self.num_players = num_players
        self.max_depth = max_depth
        self.iterations = 0
        self.regret_history: List[float] = []

        # Статистика по улицам
        self.street_visits: Dict[str, int] = {
            'preflop': 0,
            'flop': 0,
            'turn': 0,
            'river': 0
        }

        # Статистика InfoSets
        self.infosets_created = 0
        self.infosets_by_street: Dict[str, int] = defaultdict(int)

        # Рекомендации по итерациям в зависимости от числа игроков
        self.recommended_iterations = {
            2: 50000,   # Heads-up
            3: 75000,   # 3-way
            4: 100000,  # 4-way
            5: 150000,  # 5-way
            6: 200000,  # 6-max (рекомендуется)
            7: 300000,  # 7-way
            8: 400000,  # 8-way
            9: 500000   # Full ring
        }

        print(f"🎯 MCCFR инициализирован для {num_players} игроков")
        print(f"📊 Рекомендуемое количество итераций: {self.recommended_iterations.get(num_players, 100000):,}")
    
    def traverse_mccfr(self, state: GameState, reach_probs: Dict[int, float],
                       player: int, depth: int = 0) -> float:
        """
        External Sampling MCCFR traversal

        Args:
            state: Состояние игры
            reach_probs: Вероятности достижения для каждого игрока
            player: Текущий игрок (traverser)
            depth: Глубина рекурсии

        Returns:
            Утилита для текущего игрока
        """
        # Валидация состояния (в debug режиме)
        if depth == 0:  # Проверяем только на входе для производительности
            is_valid, error = game_state_validator.validate(state)
            if not is_valid:
                print(f"⚠️  Предупреждение: некорректное состояние игры: {error}")
                # Пытаемся исправить
                state = game_state_validator.sanitize(state)

        # Защита от бесконечной рекурсии
        if depth > self.max_depth:
            return 0.0
        
        # Терминальный узел - вычисляем выигрыш
        if state.street == Street.RIVER and self._is_round_complete(state):
            return self._get_payoff(state, player)
        
        # Chance node - раздача карт (сэмплируем ОДИН исход)
        if state.street < Street.RIVER and self._is_round_complete(state):
            return self._handle_chance_node(state, reach_probs, player, depth)
        
        # Decision node
        return self._handle_decision_node_external(state, reach_probs, player, depth)
    
    def _handle_decision_node_external(self, state: GameState, reach_probs: Dict[int, float],
                                      player: int, depth: int) -> float:
        """
        Обработка decision node с External Sampling
        
        External Sampling логика:
        - Если текущий игрок == traverser: исследуем ВСЕ действия
        - Если текущий игрок != traverser: сэмплируем ОДНО действие
        """
        current_player = state.current_player
        
        # Генерируем информационное множество
        infoset = self._get_infoset(state, current_player)
        
        # Получаем доступные действия
        actions = self._get_available_actions(state)
        
        if not actions:
            return self._get_payoff(state, player)
        
        # Получаем или создаем узел
        node = self.game_tree.get_node(infoset, actions, current_player)
        if infoset not in self.game_tree.nodes:
            self.infosets_created += 1
            street_name = self._get_street_name(state.street)
            self.infosets_by_street[street_name] += 1
        
        # Вычисляем стратегию
        realization_prob = reach_probs.get(current_player, 1.0)
        strategy = node.get_strategy(realization_prob)
        
        # ========== EXTERNAL SAMPLING LOGIC ==========
        
        if current_player == player:
            # ========== TRAVERSER: исследуем ВСЕ действия ==========
            action_utilities = {}
            node_utility = 0.0
            
            for action_str in actions:
                action, amount = self._parse_action(action_str, state)
                new_state = self._apply_action(state, action, amount)
                new_reach_probs = reach_probs.copy()
                new_reach_probs[current_player] *= strategy[action_str]
                
                action_utility = self.traverse_mccfr(new_state, new_reach_probs, player, depth + 1)
                action_utilities[action_str] = action_utility
                node_utility += strategy[action_str] * action_utility
            
            # Обновляем regret для traverser
            counterfactual_reach = 1.0
            for p in range(self.num_players):
                if p != player:
                    counterfactual_reach *= reach_probs.get(p, 1.0)
            
            for action_str in actions:
                regret = action_utilities[action_str] - node_utility
                node.regret_sum[action_str] += counterfactual_reach * regret
            
            return node_utility
        
        else:
            # ========== OPPONENT: сэмплируем ОДНО действие ==========
            # Выбираем действие согласно стратегии
            action_str = self._sample_action(strategy)
            action, amount = self._parse_action(action_str, state)
            
            new_state = self._apply_action(state, action, amount)
            new_reach_probs = reach_probs.copy()
            new_reach_probs[current_player] *= strategy[action_str]
            
            return self.traverse_mccfr(new_state, new_reach_probs, player, depth + 1)
    
    def _handle_chance_node(self, state: GameState, reach_probs: Dict[int, float],
                           player: int, depth: int) -> float:
        """
        Обработка chance node (раздача карт)
        
        External Sampling: сэмплируем ОДИН исход
        """
        # Определяем следующую улицу
        if state.street == Street.PREFLOP:
            new_street = Street.FLOP
            cards_to_deal = 3
        elif state.street == Street.FLOP:
            new_street = Street.TURN
            cards_to_deal = 1
        elif state.street == Street.TURN:
            new_street = Street.RIVER
            cards_to_deal = 1
        else:
            return self._get_payoff(state, player)
        
        # Сэмплируем карты (упрощенно - в реальной реализации нужно учитывать колоду)
        new_state = self._deal_street(state, new_street, cards_to_deal)
        
        # Обновляем статистику
        street_name = self._get_street_name(new_street)
        if depth == 0:  # Только на корневом уровне
            self.street_visits[street_name] += 1
        
        return self.traverse_mccfr(new_state, reach_probs, player, depth + 1)
    
    def _get_infoset(self, state: GameState, player: int) -> str:
        """Генерирует информационное множество"""
        hero_cards = state.hero_cards if player == 0 else []
        board = state.board_cards
        bet_sequence = self._get_bet_sequence(state)
        
        return self.game_tree.get_infoset(
            state.street,
            player,
            tuple(hero_cards),
            tuple(board),
            state.pot,
            bet_sequence
        )
    
    def _get_available_actions(self, state: GameState) -> List[str]:
        """Получает доступные действия"""
        num_raises = self._get_bet_sequence(state).count('r')
        
        return self.game_tree.get_available_actions(
            state.street,
            state.pot,
            state.bets.get(state.current_player, 0.0),
            state.stacks.get(state.current_player, 100.0),
            state.last_raise_amount,
            num_raises
        )
    
    def _sample_action(self, strategy: Dict[str, float]) -> str:
        """Сэмплирует действие согласно стратегии"""
        actions = list(strategy.keys())
        probs = [strategy[action] for action in actions]
        
        # Нормализуем вероятности (оптимизировано)
        total_prob = sum(probs)
        if total_prob == 0:
            return random.choice(actions)
        
        # Используем numpy для быстрого выбора
        probs_array = np.array(probs, dtype=np.float64) / total_prob
        return actions[np.random.choice(len(actions), p=probs_array)]
    
    def _deal_street(self, state: GameState, new_street: Street, num_cards: int) -> GameState:
        """Раздает следующую улицу с корректной колодой"""
        new_state = GameState()
        new_state.__dict__.update(state.__dict__)
        new_state.street = new_street

        # Создаем полную колоду
        deck = [(rank, suit) for rank in range(2, 15) for suit in range(4)]

        # Удаляем уже раздаянные карты
        used_cards = set()

        # Карты героя
        if hasattr(state, 'hero_cards') and state.hero_cards:
            for card in state.hero_cards:
                used_cards.add(card)

        # Карты на борде
        if hasattr(state, 'board_cards') and state.board_cards:
            for card in state.board_cards:
                used_cards.add(card)

        # Карты других игроков (если есть)
        if hasattr(state, 'player_cards') and state.player_cards:
            for player_id, cards in state.player_cards.items():
                for card in cards:
                    used_cards.add(card)

        # Фильтруем колоду
        available_deck = [card for card in deck if card not in used_cards]

        # Проверка на дубликаты (для безопасности)
        if len(available_deck) < num_cards:
            # Fallback: используем случайные карты из полной колоды
            random.shuffle(deck)
            cards_to_add = deck[:num_cards]
        else:
            # Сэмплируем карты
            random.shuffle(available_deck)
            cards_to_add = available_deck[:num_cards]

        # Раздаем карты на соответствующую улицу
        if new_street == Street.FLOP:
            new_state.board_cards = cards_to_add
        elif new_street in [Street.TURN, Street.RIVER]:
            new_state.board_cards = list(state.board_cards) + cards_to_add

        return new_state
    
    def _parse_action(self, action_str: str, state: GameState) -> Tuple[str, Optional[float]]:
        """Парсит строку действия"""
        if action_str.startswith("raise_"):
            size = float(action_str.split("_")[1])
            amount = state.pot * size
            return "raise", amount
        return action_str, None
    
    def _apply_action(self, state: GameState, action: str, amount: Optional[float]) -> GameState:
        """Применяет действие к состоянию"""
        new_state = GameState()
        new_state.__dict__.update(state.__dict__)
        
        if action == "fold":
            new_state.active_players.discard(new_state.current_player)
        elif action == "call":
            max_bet = max(new_state.bets.values()) if new_state.bets else 0.0
            new_state.bets[new_state.current_player] = max_bet
        elif action == "raise":
            max_bet = max(new_state.bets.values()) if new_state.bets else 0.0
            new_state.bets[new_state.current_player] = max_bet + (amount or 0)
            new_state.last_raise_amount = amount or 0
        
        # Обновляем total_bets
        if new_state.current_player not in new_state.total_bets:
            new_state.total_bets[new_state.current_player] = 0.0
        new_state.total_bets[new_state.current_player] += new_state.bets.get(new_state.current_player, 0.0)
        
        # Переход к следующему игроку
        if len(new_state.active_players) > 1:
            new_state.current_player = (new_state.current_player + 1) % self.num_players
            while new_state.current_player not in new_state.active_players:
                new_state.current_player = (new_state.current_player + 1) % self.num_players
        
        return new_state
    
    def _get_bet_sequence(self, state: GameState) -> str:
        """Получает последовательность ставок с улучшенной логикой"""
        # Проверяем наличие hand_history
        if hasattr(state, 'hand_history') and state.hand_history:
            sequence = []
            for action in state.hand_history:
                if isinstance(action, str):
                    # Простая строка действия
                    if action in ['fold', 'check', 'call', 'raise', 'bet', 'all_in']:
                        sequence.append(action[0])  # Первая буква: f, c, r, b, a
                elif isinstance(action, (list, tuple)) and len(action) > 0:
                    # Кортеж (действие, размер)
                    if action[0] in ['fold', 'check', 'call', 'raise', 'bet', 'all_in']:
                        sequence.append(action[0][0])
            return ''.join(sequence)

        # Fallback: анализируем текущие ставки для определения последовательности
        if hasattr(state, 'bets') and state.bets:
            bets = list(state.bets.values())
            unique_bets = len(set(bets))
            max_bet = max(bets) if bets else 0

            # Упрощенная эвристика
            if max_bet == 0:
                return ""  # Никто не ставил
            elif unique_bets == 1 and max_bet > 0:
                return "c"  # Все заколлили
            elif unique_bets > 1:
                return "r"  # Был рейз

        return ""
    
    def _is_round_complete(self, state: GameState) -> bool:
        """Проверяет, завершен ли раунд ставок"""
        if len(state.active_players) <= 1:
            return True
        active_bets = [state.bets.get(p, 0.0) for p in state.active_players]
        return len(set(active_bets)) == 1
    
    def _get_payoff(self, state: GameState, player: int) -> float:
        """Вычисляет выигрыш игрока с корректным сравнением рук"""
        # Если остался один игрок - он забирает весь пот
        if len(state.active_players) == 1:
            winner = list(state.active_players)[0]
            if winner == player:
                # Выигрыш = пот - свои вложения
                player_investment = state.total_bets.get(player, 0.0)
                return state.pot - player_investment
            else:
                # Проигрыш = потеря своих вложений
                return -state.total_bets.get(player, 0.0)

        # Showdown - сравниваем руки
        if state.street == Street.RIVER and len(state.active_players) > 1:
            # Собираем все руки активных игроков
            player_hands = {}

            for p in state.active_players:
                if p == 0:  # Предполагаем, что player 0 - это герой
                    if hasattr(state, 'hero_cards') and state.hero_cards and state.board_cards:
                        full_hand = list(state.hero_cards) + list(state.board_cards)
                        player_hands[p] = full_hand
                else:
                    # Для других игроков используем случайные карты (в обучении MCCFR)
                    # В реальной игре здесь будут известны карты из GameState
                    if hasattr(state, 'player_cards') and p in state.player_cards:
                        full_hand = list(state.player_cards[p]) + list(state.board_cards)
                        player_hands[p] = full_hand

            # Если у нашего игрока нет карт, возвращаем 0
            if player not in player_hands:
                return -state.total_bets.get(player, 0.0)

            # Сравниваем руки
            player_hand = player_hands[player]
            best_opponents = []

            for p, hand in player_hands.items():
                if p != player:
                    result = compare_hands(player_hand, hand)
                    if result < 0:  # Рука оппонента сильнее
                        best_opponents.append(p)
                    elif result == 0:  # Равные руки (split pot)
                        best_opponents.append(p)

            # Определяем победителей
            if len(best_opponents) == 0:
                # Наш игрок выиграл
                player_investment = state.total_bets.get(player, 0.0)
                return state.pot - player_investment
            else:
                # Проиграл или split pot
                # Для упрощения считаем, что проиграл
                # В полной реализации нужно делить пот между победителями
                return -state.total_bets.get(player, 0.0)

        # Fallback
        return 0.0
    
    def _get_street_name(self, street: Street) -> str:
        """Получает название улицы"""
        street_names = {
            Street.PREFLOP: 'preflop',
            Street.FLOP: 'flop',
            Street.TURN: 'turn',
            Street.RIVER: 'river'
        }
        return street_names.get(street, 'unknown')
    
    def train(self, num_iterations: int, verbose: bool = True):
        """
        Обучение MCCFR с External Sampling
        
        Args:
            num_iterations: Количество итераций
            verbose: Выводить прогресс
        """
        start_time = time.time()
        
        for i in range(num_iterations):
            # Сэмплируем начальное состояние
            env = PokerEnv(num_players=self.num_players)
            state = env.reset()
            
            # Начальные вероятности
            reach_probs = {p: 1.0 for p in range(self.num_players)}
            
            # Запускаем External Sampling MCCFR для каждого игрока
            for player in range(self.num_players):
                self.traverse_mccfr(state, reach_probs, player, depth=0)
            
            self.iterations += 1
            
            # Выводим прогресс
            if (i + 1) % 100 == 0:
                avg_regret = self._compute_avg_regret()
                self.regret_history.append(avg_regret)
                
                elapsed = time.time() - start_time
                iter_per_sec = (i + 1) / elapsed if elapsed > 0 else 0
                
                if verbose:
                    print(f"Iteration {i+1}/{num_iterations}, "
                          f"Avg regret: {avg_regret:.4f}, "
                          f"Speed: {iter_per_sec:.2f} iter/sec, "
                          f"InfoSets: {self.infosets_created}")
                    
                    # Статистика по улицам
                    if self.street_visits:
                        total_visits = sum(self.street_visits.values())
                        if total_visits > 0:
                            street_stats = ', '.join([
                                f"{street}: {count*100//total_visits}%"
                                for street, count in self.street_visits.items()
                                if count > 0
                            ])
                            print(f"  Streets: {street_stats}")
    
    def _compute_avg_regret(self) -> float:
        """Вычисляет средний regret по всем узлам (оптимизировано)"""
        if not self.game_tree.nodes:
            return 0.0
        
        # Используем numpy для быстрого вычисления
        regrets = []
        for node in self.game_tree.nodes.values():
            for action in node.actions:
                regret = max(node.regret_sum[action], 0.0)
                regrets.append(regret)
        
        if not regrets:
            return 0.0
        
        regrets_array = np.array(regrets, dtype=np.float64)
        return float(np.mean(regrets_array))
    
    def get_strategy(self, infoset: str) -> Dict[str, float]:
        """
        Получает стратегию для информационного множества
        
        Args:
            infoset: Информационное множество
            
        Returns:
            Словарь {действие: вероятность}
        """
        if infoset in self.game_tree.nodes:
            return self.game_tree.nodes[infoset].get_average_strategy()
        else:
            return {}
    
    def get_statistics(self) -> Dict:
        """Возвращает статистику обучения"""
        return {
            'iterations': self.iterations,
            'infosets_created': self.infosets_created,
            'infosets_by_street': dict(self.infosets_by_street),
            'street_visits': self.street_visits.copy(),
            'avg_regret': self.regret_history[-1] if self.regret_history else 0.0,
            'total_nodes': len(self.game_tree.nodes)
        }
    
    # Обратная совместимость со старым API
    def cfr(self, state: GameState, reach_probs: Dict[int, float], 
            player: int, depth: int = 0) -> float:
        """Старый метод CFR - теперь использует External Sampling"""
        return self.traverse_mccfr(state, reach_probs, player, depth)
