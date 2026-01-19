"""Валидатор состояния игры для защиты от некорректных данных"""

from typing import List, Dict, Set, Optional, Tuple
from engine.env_wrapper import GameState, Street


class GameStateValidator:
    """Валидатор для проверки корректности состояния игры"""

    @staticmethod
    def validate(state: GameState) -> Tuple[bool, Optional[str]]:
        """
        Валидирует состояние игры

        Args:
            state: Состояние игры

        Returns:
            (is_valid, error_message)
        """
        # 1. Проверка активных игроков
        if not hasattr(state, 'active_players') or not state.active_players:
            return False, "active_players пусто или отсутствует"

        if len(state.active_players) < 1:
            return False, f"Недостаточно активных игроков: {len(state.active_players)}"

        # 2. Проверка current_player
        if not hasattr(state, 'current_player'):
            return False, "current_player отсутствует"

        if state.current_player not in state.active_players:
            return False, f"current_player {state.current_player} не в active_players {state.active_players}"

        # 3. Проверка карт на дубликаты
        all_cards = []

        if hasattr(state, 'hero_cards') and state.hero_cards:
            all_cards.extend(state.hero_cards)

        if hasattr(state, 'board_cards') and state.board_cards:
            all_cards.extend(state.board_cards)

        if hasattr(state, 'player_cards') and state.player_cards:
            for player_id, cards in state.player_cards.items():
                if cards:
                    all_cards.extend(cards)

        # Проверка на дубликаты карт
        if len(all_cards) != len(set(all_cards)):
            duplicates = [card for card in all_cards if all_cards.count(card) > 1]
            return False, f"Обнаружены дубликаты карт: {duplicates}"

        # 4. Проверка валидности карт (rank 2-14, suit 0-3)
        for card in all_cards:
            if not isinstance(card, tuple) or len(card) != 2:
                return False, f"Некорректный формат карты: {card}"
            rank, suit = card
            if not (2 <= rank <= 14):
                return False, f"Некорректный ранг карты: {rank} (должен быть 2-14)"
            if not (0 <= suit <= 3):
                return False, f"Некорректная масть карты: {suit} (должна быть 0-3)"

        # 5. Проверка количества карт на борде в зависимости от улицы
        if hasattr(state, 'street') and hasattr(state, 'board_cards'):
            board_count = len(state.board_cards) if state.board_cards else 0

            if state.street == Street.PREFLOP and board_count != 0:
                return False, f"Preflop должен иметь 0 карт на борде, имеет {board_count}"
            elif state.street == Street.FLOP and board_count != 3:
                return False, f"Flop должен иметь 3 карты на борде, имеет {board_count}"
            elif state.street == Street.TURN and board_count != 4:
                return False, f"Turn должен иметь 4 карты на борде, имеет {board_count}"
            elif state.street == Street.RIVER and board_count != 5:
                return False, f"River должен иметь 5 карт на борде, имеет {board_count}"

        # 6. Проверка ставок
        if hasattr(state, 'bets') and state.bets:
            for player_id, bet in state.bets.items():
                if bet < 0:
                    return False, f"Отрицательная ставка для игрока {player_id}: {bet}"

        # 7. Проверка пота
        if hasattr(state, 'pot') and state.pot < 0:
            return False, f"Отрицательный пот: {state.pot}"

        # 8. Проверка стеков
        if hasattr(state, 'stacks') and state.stacks:
            for player_id, stack in state.stacks.items():
                if stack < 0:
                    return False, f"Отрицательный стек для игрока {player_id}: {stack}"

        # Все проверки пройдены
        return True, None

    @staticmethod
    def sanitize(state: GameState) -> GameState:
        """
        Очищает и исправляет состояние игры

        Args:
            state: Состояние игры

        Returns:
            Очищенное состояние
        """
        # Создаем копию состояния
        cleaned_state = GameState()
        cleaned_state.__dict__.update(state.__dict__)

        # Убираем дубликаты карт (оставляем первое вхождение)
        all_cards = []
        seen_cards = set()

        # Hero cards
        if hasattr(cleaned_state, 'hero_cards') and cleaned_state.hero_cards:
            unique_hero_cards = []
            for card in cleaned_state.hero_cards:
                if card not in seen_cards:
                    unique_hero_cards.append(card)
                    seen_cards.add(card)
            cleaned_state.hero_cards = unique_hero_cards

        # Board cards
        if hasattr(cleaned_state, 'board_cards') and cleaned_state.board_cards:
            unique_board_cards = []
            for card in cleaned_state.board_cards:
                if card not in seen_cards:
                    unique_board_cards.append(card)
                    seen_cards.add(card)
            cleaned_state.board_cards = unique_board_cards

        # Player cards
        if hasattr(cleaned_state, 'player_cards') and cleaned_state.player_cards:
            cleaned_player_cards = {}
            for player_id, cards in cleaned_state.player_cards.items():
                unique_cards = []
                if cards:
                    for card in cards:
                        if card not in seen_cards:
                            unique_cards.append(card)
                            seen_cards.add(card)
                cleaned_player_cards[player_id] = unique_cards
            cleaned_state.player_cards = cleaned_player_cards

        # Убираем отрицательные значения
        if hasattr(cleaned_state, 'pot') and cleaned_state.pot < 0:
            cleaned_state.pot = 0.0

        if hasattr(cleaned_state, 'bets') and cleaned_state.bets:
            cleaned_state.bets = {k: max(0, v) for k, v in cleaned_state.bets.items()}

        if hasattr(cleaned_state, 'stacks') and cleaned_state.stacks:
            cleaned_state.stacks = {k: max(0, v) for k, v in cleaned_state.stacks.items()}

        return cleaned_state


# Глобальный валидатор
game_state_validator = GameStateValidator()
