"""
Hand History Parser для парсинга hand history из покер-румов

Поддерживаемые форматы:
- PokerStars
- 888poker
- PartyPoker

Использование:
    from utils.hand_history_parser import HandHistoryParser

    parser = HandHistoryParser()
    hands = parser.parse_file('hands.txt', room='pokerstars')

    # Или загрузить напрямую через API
    from utils.hand_history_parser import parse_and_upload
    parse_and_upload('hands.txt', api_url='http://localhost:8080', api_key='your-key')
"""

import re
from typing import List, Dict, Optional, Any
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass, field

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class HandHistoryParser:
    """Парсер hand history файлов из различных покер-румов"""

    def __init__(self):
        self.parsers = {
            'pokerstars': self._parse_pokerstars,
            '888poker': self._parse_888poker,
            'partypoker': self._parse_partypoker
        }

    def parse_file(self, file_path: str, room: str = 'pokerstars') -> List[Dict[str, Any]]:
        """
        Парсит hand history файл

        Args:
            file_path: путь к файлу
            room: покер-рум (pokerstars, 888poker, partypoker)

        Returns:
            Список раздач в формате API
        """
        if room not in self.parsers:
            raise ValueError(f"Неподдерживаемый покер-рум: {room}. Доступны: {', '.join(self.parsers.keys())}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return self.parsers[room](content)

    # ---------------------------------------------------------------------
    # Упрощённый объектный интерфейс (используется тестами)
    # ---------------------------------------------------------------------
    def parse(self, hand_text: str, room: str = "pokerstars") -> Optional["ParsedHand"]:
        """
        Парсит один hand history текст и возвращает ParsedHand.

        Это лёгкий (не полный) парсер, который покрывает тесты и базовые кейсы.
        Для массового импорта используйте parse_file()/parse_and_upload().
        """
        if not hand_text or not hand_text.strip():
            return None

        # Hand id
        m = re.search(r"Hand\s+#(\d+):", hand_text)
        hand_id = m.group(1) if m else ""

        # Limit type
        m = re.search(r"\((NL\d+)\)", hand_text)
        limit_type = m.group(1) if m else ""

        # Players (Seat lines)
        players: Dict[str, Any] = {}
        for seat_m in re.finditer(r"^\s*Seat\s+\d+:\s*([^\(\n\r]+)\s*\(", hand_text, re.MULTILINE):
            name = seat_m.group(1).strip()
            if name:
                players[name] = {}

        # Actions
        actions: List[Dict[str, Any]] = []
        street = "preflop"
        for raw_line in hand_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("*** FLOP ***"):
                street = "flop"
                continue
            if line.startswith("*** TURN ***"):
                street = "turn"
                continue
            if line.startswith("*** RIVER ***"):
                street = "river"
                continue

            # Игнорируем блайнды и служебные строки
            if "posts small blind" in line or "posts big blind" in line:
                continue
            if line.startswith("***"):
                continue

            am = re.match(r"^([^:]+):\s+(raises|calls|bets|checks|folds)\s*(.*)$", line, re.IGNORECASE)
            if not am:
                continue

            player = am.group(1).strip()
            action = am.group(2).lower().strip()
            # Нормализация под тесты (raise/call/bet/check/fold)
            action = {
                "raises": "raise",
                "calls": "call",
                "bets": "bet",
                "checks": "check",
                "folds": "fold",
            }.get(action, action)
            tail = am.group(3).strip()

            amount: Optional[float] = None
            # raises 2 to 3 / calls 2 / bets 5
            m_to = re.search(r"to\s+([0-9]+(?:\.[0-9]+)?)", tail)
            if m_to:
                amount = float(m_to.group(1))
            else:
                m_amt = re.search(r"([0-9]+(?:\.[0-9]+)?)", tail)
                if m_amt and action in ("calls", "bets"):
                    amount = float(m_amt.group(1))

            actions.append({
                "street": street,
                "player": player,
                "action": action,
                "amount": amount,
                "raw": line,
            })

        return ParsedHand(
            hand_id=hand_id,
            limit_type=limit_type,
            players=players,
            actions=actions,
            raw_text=hand_text,
        )

    def extract_player_stats(self, parsed_hand: "ParsedHand", player_name: str) -> Dict[str, Any]:
        """
        Упрощённая экстракция статов игрока из ParsedHand (для тестов/заглушек).
        """
        preflop_action = None
        for a in parsed_hand.actions:
            if a.get("street") != "preflop":
                continue
            if a.get("player") != player_name:
                continue
            preflop_action = a.get("action")
            break

        return {
            "preflop_action": preflop_action or "none",
        }

    def _parse_pokerstars(self, content: str) -> List[Dict[str, Any]]:
        """
        Парсит PokerStars hand history

        Формат PokerStars:
        PokerStars Hand #123456789: Hold'em No Limit ($0.05/$0.10 USD) - 2024/01/15 12:34:56 ET
        Table 'TableName' 6-max Seat #1 is the button
        Seat 1: Player1 ($10.00 in chips)
        Seat 2: Hero ($10.00 in chips)
        ...
        """
        hands = []

        # Разбиваем на отдельные раздачи
        hand_blocks = re.split(r'\n\n\n', content)

        for block in hand_blocks:
            if not block.strip():
                continue

            try:
                hand_data = self._parse_pokerstars_hand(block)
                if hand_data:
                    hands.append(hand_data)
            except Exception as e:
                print(f"Ошибка парсинга раздачи: {e}")
                continue

        return hands

    def _parse_pokerstars_hand(self, block: str) -> Optional[Dict[str, Any]]:
        """Парсит одну раздачу PokerStars"""

        # Hand ID
        hand_id_match = re.search(r'PokerStars Hand #(\d+):', block)
        if not hand_id_match:
            return None
        hand_id = f"PS_{hand_id_match.group(1)}"

        # Table ID
        table_match = re.search(r"Table '([^']+)'", block)
        table_id = table_match.group(1) if table_match else "Unknown"

        # Limit type (например: $0.05/$0.10 -> NL10)
        limit_match = re.search(r'\$(\d+\.?\d*)/\$(\d+\.?\d*)', block)
        if limit_match:
            bb = float(limit_match.group(2))
            # Конвертируем в формат NL2, NL5, NL10 и т.д.
            bb_cents = int(bb * 100)
            if bb_cents <= 2:
                limit_type = "NL2"
            elif bb_cents <= 5:
                limit_type = "NL5"
            elif bb_cents <= 10:
                limit_type = "NL10"
            elif bb_cents <= 25:
                limit_type = "NL25"
            elif bb_cents <= 50:
                limit_type = "NL50"
            elif bb_cents <= 100:
                limit_type = "NL100"
            else:
                limit_type = "NL200"
        else:
            limit_type = "NL10"  # По умолчанию

        # Players count - считаем только из начала раздачи, до *** HOLE CARDS ***
        header = block.split('*** HOLE CARDS ***')[0]
        players = re.findall(r'Seat \d+: \w+ \(\$', header)
        players_count = len(players)

        # Hero cards
        hero_cards_match = re.search(r'Dealt to (\w+) \[([^\]]+)\]', block)
        hero_cards = ""
        hero_name = None
        if hero_cards_match:
            hero_name = hero_cards_match.group(1)
            hero_cards = hero_cards_match.group(2).replace(' ', '')

        # Hero position
        hero_position = "Unknown"
        if hero_name:
            # Ищем seat героя
            hero_seat_match = re.search(rf'Seat (\d+): {re.escape(hero_name)}', block)
            if hero_seat_match:
                seat = int(hero_seat_match.group(1))
                # Определяем позицию относительно баттона
                button_match = re.search(r'Seat #(\d+) is the button', block)
                if button_match:
                    button_seat = int(button_match.group(1))
                    positions = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO']
                    offset = (seat - button_seat) % players_count
                    hero_position = positions[min(offset, len(positions)-1)]

        # Board cards
        board_cards = ""
        flop_match = re.search(r'\*\*\* FLOP \*\*\* \[([^\]]+)\]', block)
        turn_match = re.search(r'\*\*\* TURN \*\*\* \[[^\]]+\] \[([^\]]+)\]', block)
        river_match = re.search(r'\*\*\* RIVER \*\*\* \[[^\]]+\] \[([^\]]+)\]', block)

        if flop_match:
            board_cards = flop_match.group(1).replace(' ', '')
        if turn_match:
            board_cards += turn_match.group(1)
        if river_match:
            board_cards += river_match.group(1)

        # Pot size
        pot_match = re.search(r'Total pot \$?(\d+\.?\d*)', block)
        pot_size = float(pot_match.group(1)) if pot_match else 0.0

        # Rake
        rake_match = re.search(r'Rake \$?(\d+\.?\d*)', block)
        rake_amount = float(rake_match.group(1)) if rake_match else 0.0

        # Hero result
        hero_result = 0.0
        if hero_name:
            # Ищем "collected" для выигрыша
            collected_match = re.search(rf'{re.escape(hero_name)} collected \$?(\d+\.?\d*)', block)
            if collected_match:
                collected = float(collected_match.group(1))
                # Вычитаем вложенное
                invested = self._calculate_invested(block, hero_name)
                hero_result = collected - invested
            else:
                # Если не выиграл, то только потери
                hero_result = -self._calculate_invested(block, hero_name)

        # Hand history (сохраняем весь блок для анализа)
        hand_history = self._extract_opponent_data(block, hero_name)

        return {
            "hand_id": hand_id,
            "table_id": table_id,
            "limit_type": limit_type,
            "players_count": players_count,
            "hero_position": hero_position,
            "hero_cards": hero_cards,
            "board_cards": board_cards,
            "pot_size": pot_size,
            "rake_amount": rake_amount,
            "hero_result": hero_result,
            "hand_history": hand_history
        }

    def _calculate_invested(self, block: str, player_name: str) -> float:
        """Вычисляет сколько игрок вложил в пот"""
        total_put_in = 0.0

        # Блайнды
        sb_match = re.search(rf'{re.escape(player_name)}: posts small blind \$?(\d+\.?\d*)', block)
        bb_match = re.search(rf'{re.escape(player_name)}: posts big blind \$?(\d+\.?\d*)', block)

        if sb_match:
            total_put_in += float(sb_match.group(1))
        if bb_match:
            total_put_in += float(bb_match.group(1))

        # Действия по улицам - учитываем текущую ставку на каждой улице
        streets = ['HOLE CARDS', 'FLOP', 'TURN', 'RIVER']
        street_blocks = []

        # Разбиваем на улицы
        current_block = block
        for street in streets:
            if f'*** {street} ***' in current_block:
                parts = current_block.split(f'*** {street} ***', 1)
                if len(parts) == 2:
                    street_blocks.append((street, parts[1]))
                    current_block = parts[1]

        # Для каждой улицы считаем вложения
        for street_name, street_content in street_blocks:
            # Останавливаемся на следующей улице
            next_street = None
            for s in streets:
                if f'*** {s} ***' in street_content:
                    street_content = street_content.split(f'*** {s} ***')[0]
                    break

            # Ищем действия на этой улице
            # calls X - добавляет X
            calls = re.findall(rf'{re.escape(player_name)}: calls \$?(\d+\.?\d*)', street_content)
            for call in calls:
                total_put_in += float(call)

            # bets X - добавляет X
            bets = re.findall(rf'{re.escape(player_name)}: bets \$?(\d+\.?\d*)', street_content)
            for bet in bets:
                total_put_in += float(bet)

            # raises X to Y - добавляет (Y - уже_вложено_на_улице)
            # Но проще: если raises $0.70 to $1.00 - значит добавил $0.70
            raises = re.findall(rf'{re.escape(player_name)}: raises \$?(\d+\.?\d*) to \$?(\d+\.?\d*)', street_content)
            for raise_amt, _ in raises:
                total_put_in += float(raise_amt)

        # Вычитаем uncalled bet (возвращенные ставки)
        uncalled_match = re.search(rf'Uncalled bet \(\$?(\d+\.?\d*)\) returned to {re.escape(player_name)}', block)
        if uncalled_match:
            total_put_in -= float(uncalled_match.group(1))

        return total_put_in

    def _extract_opponent_data(self, block: str, hero_name: Optional[str]) -> Dict[str, Any]:
        """Извлекает данные об оппонентах для профилирования"""
        opponents = {}

        # Находим всех игроков
        players = re.findall(r'Seat \d+: (\w+)', block)

        for player in players:
            if player == hero_name:
                continue

            opponent_data = {
                "actions": [],
                "showdown": False,
                "cards": None
            }

            # Действия игрока
            actions = re.findall(
                rf'{re.escape(player)}: (folds|checks|calls|bets|raises)',
                block
            )
            opponent_data["actions"] = actions

            # Показал карты на шоудауне?
            showdown_match = re.search(rf'{re.escape(player)}: shows \[([^\]]+)\]', block)
            if showdown_match:
                opponent_data["showdown"] = True
                opponent_data["cards"] = showdown_match.group(1)

            opponents[player] = opponent_data

        return opponents

    def _parse_888poker(self, content: str) -> List[Dict[str, Any]]:
        """
        Парсит 888poker hand history

        Формат 888poker:
        ***** 888poker Hand History for Game 1234567890 *****
        $0.05/$0.10 Blinds No Limit Holdem - *** 15 01 2024 12:34:56
        Table TableName 6 Max (Real Money)
        Seat 1 is the button
        Total number of players : 6
        Seat 1: Player1 ( $10.00 )
        Seat 2: Hero ( $10.00 )
        ...
        """
        hands = []

        # Разбиваем на отдельные раздачи (двойной перенос строки или новая раздача)
        hand_blocks = re.split(r'\*{5}\s*888poker Hand History', content)

        for block in hand_blocks:
            if not block.strip():
                continue

            # Восстанавливаем заголовок
            block = "***** 888poker Hand History" + block

            try:
                hand_data = self._parse_888poker_hand(block)
                if hand_data:
                    hands.append(hand_data)
            except Exception as e:
                print(f"Ошибка парсинга 888poker раздачи: {e}")
                continue

        return hands

    def _parse_888poker_hand(self, block: str) -> Optional[Dict[str, Any]]:
        """Парсит одну раздачу 888poker"""

        # Hand ID
        hand_id_match = re.search(r'Game\s+(\d+)', block)
        if not hand_id_match:
            return None
        hand_id = f"888_{hand_id_match.group(1)}"

        # Table ID
        table_match = re.search(r"Table\s+(\S+)", block)
        table_id = table_match.group(1) if table_match else "Unknown"

        # Blinds и limit type (например: $0.05/$0.10 -> NL10)
        limit_match = re.search(r'\$(\d+\.?\d*)/\$(\d+\.?\d*)\s+Blinds', block)
        if limit_match:
            bb = float(limit_match.group(2))
            bb_cents = int(bb * 100)
            if bb_cents <= 2:
                limit_type = "NL2"
            elif bb_cents <= 5:
                limit_type = "NL5"
            elif bb_cents <= 10:
                limit_type = "NL10"
            elif bb_cents <= 25:
                limit_type = "NL25"
            elif bb_cents <= 50:
                limit_type = "NL50"
            else:
                limit_type = "NL100"
        else:
            limit_type = "NL10"

        # Players count
        players_match = re.search(r'Total number of players\s*:\s*(\d+)', block)
        players_count = int(players_match.group(1)) if players_match else 6

        # Hero cards - в 888 формат: "Dealt to Hero [ Ks, Qh ]"
        hero_cards_match = re.search(r'Dealt to (\w+)\s*\[\s*([^\]]+)\s*\]', block)
        hero_cards = ""
        hero_name = None
        if hero_cards_match:
            hero_name = hero_cards_match.group(1)
            cards_raw = hero_cards_match.group(2)
            # Убираем запятые и пробелы: "Ks, Qh" -> "KsQh"
            hero_cards = cards_raw.replace(',', '').replace(' ', '')

        # Hero position
        hero_position = "Unknown"
        if hero_name:
            # Ищем seat героя
            hero_seat_match = re.search(rf'Seat\s+(\d+):\s+{re.escape(hero_name)}', block)
            if hero_seat_match:
                seat = int(hero_seat_match.group(1))
                button_match = re.search(r'Seat\s+(\d+)\s+is the button', block)
                if button_match:
                    button_seat = int(button_match.group(1))
                    positions = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO']
                    offset = (seat - button_seat) % players_count
                    hero_position = positions[min(offset, len(positions) - 1)]

        # Board cards
        board_cards = ""
        flop_match = re.search(r'\*\*\s*Dealing Flop\s*\*\*\s*\[\s*([^\]]+)\s*\]', block)
        turn_match = re.search(r'\*\*\s*Dealing Turn\s*\*\*\s*\[\s*([^\]]+)\s*\]', block)
        river_match = re.search(r'\*\*\s*Dealing River\s*\*\*\s*\[\s*([^\]]+)\s*\]', block)

        if flop_match:
            board_cards = flop_match.group(1).replace(',', '').replace(' ', '')
        if turn_match:
            board_cards += turn_match.group(1).replace(',', '').replace(' ', '')
        if river_match:
            board_cards += river_match.group(1).replace(',', '').replace(' ', '')

        # Pot size
        pot_match = re.search(r'Total\s+pot\s*\(?\$?(\d+\.?\d*)', block, re.IGNORECASE)
        pot_size = float(pot_match.group(1)) if pot_match else 0.0

        # Rake
        rake_match = re.search(r'Rake\s*\$?(\d+\.?\d*)', block, re.IGNORECASE)
        rake_amount = float(rake_match.group(1)) if rake_match else 0.0

        # Hero result
        hero_result = 0.0
        if hero_name:
            # Выигрыш: "Hero collected [ $X ]" или "Hero wins $X"
            win_match = re.search(rf'{re.escape(hero_name)}\s+(?:collected|wins)\s*\[?\s*\$?(\d+\.?\d*)', block)
            if win_match:
                collected = float(win_match.group(1))
                invested = self._calculate_invested_888(block, hero_name)
                hero_result = collected - invested
            else:
                hero_result = -self._calculate_invested_888(block, hero_name)

        # Hand history
        hand_history = self._extract_opponent_data_888(block, hero_name)

        return {
            "hand_id": hand_id,
            "table_id": table_id,
            "limit_type": limit_type,
            "players_count": players_count,
            "hero_position": hero_position,
            "hero_cards": hero_cards,
            "board_cards": board_cards,
            "pot_size": pot_size,
            "rake_amount": rake_amount,
            "hero_result": hero_result,
            "hand_history": hand_history
        }

    def _calculate_invested_888(self, block: str, player_name: str) -> float:
        """Вычисляет сколько игрок вложил в пот (888poker формат)"""
        total = 0.0

        # Blinds: "Player posts small blind [$0.05]"
        sb_match = re.search(rf'{re.escape(player_name)}\s+posts small blind\s*\[\s*\$?(\d+\.?\d*)\s*\]', block)
        bb_match = re.search(rf'{re.escape(player_name)}\s+posts big blind\s*\[\s*\$?(\d+\.?\d*)\s*\]', block)

        if sb_match:
            total += float(sb_match.group(1))
        if bb_match:
            total += float(bb_match.group(1))

        # Actions: "Player calls [$X]", "Player raises [$X]", "Player bets [$X]"
        calls = re.findall(rf'{re.escape(player_name)}\s+calls\s*\[\s*\$?(\d+\.?\d*)\s*\]', block)
        for call in calls:
            total += float(call)

        bets = re.findall(rf'{re.escape(player_name)}\s+bets\s*\[\s*\$?(\d+\.?\d*)\s*\]', block)
        for bet in bets:
            total += float(bet)

        raises = re.findall(rf'{re.escape(player_name)}\s+raises\s*\[\s*\$?(\d+\.?\d*)\s*\]', block)
        for r in raises:
            total += float(r)

        return total

    def _extract_opponent_data_888(self, block: str, hero_name: Optional[str]) -> Dict[str, Any]:
        """Извлекает данные об оппонентах (888poker)"""
        opponents = {}

        players = re.findall(r'Seat\s+\d+:\s+(\w+)', block)

        for player in players:
            if player == hero_name:
                continue

            opponent_data = {
                "actions": [],
                "showdown": False,
                "cards": None
            }

            # Actions
            actions = re.findall(
                rf'{re.escape(player)}\s+(folds|checks|calls|bets|raises)',
                block, re.IGNORECASE
            )
            opponent_data["actions"] = [a.lower() for a in actions]

            # Showdown
            showdown_match = re.search(rf'{re.escape(player)}\s+shows\s*\[\s*([^\]]+)\s*\]', block)
            if showdown_match:
                opponent_data["showdown"] = True
                opponent_data["cards"] = showdown_match.group(1).replace(',', '').replace(' ', '')

            opponents[player] = opponent_data

        return opponents

    def _parse_partypoker(self, content: str) -> List[Dict[str, Any]]:
        """
        Парсит PartyPoker hand history

        Формат PartyPoker:
        ***** Hand History for Game 1234567890 *****
        $0.05/$0.10 USD NL Texas Hold'em - Monday, January 15, 12:34:56 CET 2024
        Table TableName (Real Money)
        Seat 1 is the button
        Total number of players : 6
        Seat 1: Player1 ( $10 USD )
        ...
        """
        hands = []

        # Разбиваем на раздачи
        hand_blocks = re.split(r'\*{5}\s*Hand History for Game', content)

        for block in hand_blocks:
            if not block.strip():
                continue

            block = "***** Hand History for Game" + block

            try:
                hand_data = self._parse_partypoker_hand(block)
                if hand_data:
                    hands.append(hand_data)
            except Exception as e:
                print(f"Ошибка парсинга PartyPoker раздачи: {e}")
                continue

        return hands

    def _parse_partypoker_hand(self, block: str) -> Optional[Dict[str, Any]]:
        """Парсит одну раздачу PartyPoker"""

        # Hand ID
        hand_id_match = re.search(r'Game\s+(\d+)', block)
        if not hand_id_match:
            return None
        hand_id = f"PP_{hand_id_match.group(1)}"

        # Table ID
        table_match = re.search(r"Table\s+(\S+)", block)
        table_id = table_match.group(1) if table_match else "Unknown"

        # Limit type
        limit_match = re.search(r'\$(\d+\.?\d*)/\$(\d+\.?\d*)\s+USD', block)
        if limit_match:
            bb = float(limit_match.group(2))
            bb_cents = int(bb * 100)
            if bb_cents <= 2:
                limit_type = "NL2"
            elif bb_cents <= 5:
                limit_type = "NL5"
            elif bb_cents <= 10:
                limit_type = "NL10"
            elif bb_cents <= 25:
                limit_type = "NL25"
            elif bb_cents <= 50:
                limit_type = "NL50"
            else:
                limit_type = "NL100"
        else:
            limit_type = "NL10"

        # Players count
        players_match = re.search(r'Total number of players\s*:\s*(\d+)', block)
        players_count = int(players_match.group(1)) if players_match else 6

        # Hero cards - PartyPoker: "Dealt to Hero [  Ks Qh ]"
        hero_cards_match = re.search(r'Dealt to (\w+)\s*\[\s*([^\]]+)\s*\]', block)
        hero_cards = ""
        hero_name = None
        if hero_cards_match:
            hero_name = hero_cards_match.group(1)
            hero_cards = hero_cards_match.group(2).replace(' ', '')

        # Hero position
        hero_position = "Unknown"
        if hero_name:
            hero_seat_match = re.search(rf'Seat\s+(\d+):\s+{re.escape(hero_name)}', block)
            if hero_seat_match:
                seat = int(hero_seat_match.group(1))
                button_match = re.search(r'Seat\s+(\d+)\s+is the button', block)
                if button_match:
                    button_seat = int(button_match.group(1))
                    positions = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO']
                    offset = (seat - button_seat) % players_count
                    hero_position = positions[min(offset, len(positions) - 1)]

        # Board cards
        board_cards = ""
        flop_match = re.search(r'\*\*\s*Dealing Flop\s*\*\*\s*\[\s*([^\]]+)\s*\]', block)
        turn_match = re.search(r'\*\*\s*Dealing Turn\s*\*\*\s*\[\s*([^\]]+)\s*\]', block)
        river_match = re.search(r'\*\*\s*Dealing River\s*\*\*\s*\[\s*([^\]]+)\s*\]', block)

        if flop_match:
            board_cards = flop_match.group(1).replace(' ', '')
        if turn_match:
            board_cards += turn_match.group(1).replace(' ', '')
        if river_match:
            board_cards += river_match.group(1).replace(' ', '')

        # Pot size
        pot_match = re.search(r'Total\s+pot\s*\$?(\d+\.?\d*)', block, re.IGNORECASE)
        pot_size = float(pot_match.group(1)) if pot_match else 0.0

        # Rake
        rake_match = re.search(r'Rake\s*\$?(\d+\.?\d*)', block, re.IGNORECASE)
        rake_amount = float(rake_match.group(1)) if rake_match else 0.0

        # Hero result
        hero_result = 0.0
        if hero_name:
            win_match = re.search(rf'{re.escape(hero_name)}\s+wins\s+\$?(\d+\.?\d*)', block)
            if win_match:
                collected = float(win_match.group(1))
                invested = self._calculate_invested_partypoker(block, hero_name)
                hero_result = collected - invested
            else:
                hero_result = -self._calculate_invested_partypoker(block, hero_name)

        hand_history = self._extract_opponent_data_partypoker(block, hero_name)

        return {
            "hand_id": hand_id,
            "table_id": table_id,
            "limit_type": limit_type,
            "players_count": players_count,
            "hero_position": hero_position,
            "hero_cards": hero_cards,
            "board_cards": board_cards,
            "pot_size": pot_size,
            "rake_amount": rake_amount,
            "hero_result": hero_result,
            "hand_history": hand_history
        }

    def _calculate_invested_partypoker(self, block: str, player_name: str) -> float:
        """Вычисляет вложения игрока (PartyPoker формат)"""
        total = 0.0

        # Blinds
        sb_match = re.search(rf'{re.escape(player_name)}\s+posts small blind\s*\[\s*\$?(\d+\.?\d*)', block)
        bb_match = re.search(rf'{re.escape(player_name)}\s+posts big blind\s*\[\s*\$?(\d+\.?\d*)', block)

        if sb_match:
            total += float(sb_match.group(1))
        if bb_match:
            total += float(bb_match.group(1))

        # Actions
        calls = re.findall(rf'{re.escape(player_name)}\s+calls\s*\[\s*\$?(\d+\.?\d*)\s*\]', block)
        for call in calls:
            total += float(call)

        bets = re.findall(rf'{re.escape(player_name)}\s+bets\s*\[\s*\$?(\d+\.?\d*)\s*\]', block)
        for bet in bets:
            total += float(bet)

        raises = re.findall(rf'{re.escape(player_name)}\s+raises\s*\[\s*\$?(\d+\.?\d*)\s*\]', block)
        for r in raises:
            total += float(r)

        return total

    def _extract_opponent_data_partypoker(self, block: str, hero_name: Optional[str]) -> Dict[str, Any]:
        """Извлекает данные об оппонентах (PartyPoker)"""
        opponents = {}

        players = re.findall(r'Seat\s+\d+:\s+(\w+)', block)

        for player in players:
            if player == hero_name:
                continue

            opponent_data = {
                "actions": [],
                "showdown": False,
                "cards": None
            }

            actions = re.findall(
                rf'{re.escape(player)}\s+(folds|checks|calls|bets|raises)',
                block, re.IGNORECASE
            )
            opponent_data["actions"] = [a.lower() for a in actions]

            showdown_match = re.search(rf'{re.escape(player)}\s+shows\s*\[\s*([^\]]+)\s*\]', block)
            if showdown_match:
                opponent_data["showdown"] = True
                opponent_data["cards"] = showdown_match.group(1).replace(' ', '')

            opponents[player] = opponent_data

        return opponents


def parse_and_upload(
    file_path: str,
    api_url: str = "http://localhost:8080",
    api_key: Optional[str] = None,
    room: str = "pokerstars",
    skip_existing: bool = True
) -> Dict[str, Any]:
    """
    Парсит hand history файл и загружает в API

    Args:
        file_path: путь к файлу
        api_url: URL API
        api_key: API ключ (опционально)
        room: покер-рум
        skip_existing: пропускать существующие раздачи

    Returns:
        Результат bulk операции
    """
    if not HAS_REQUESTS:
        return {
            "status": "error",
            "message": "requests library not installed. Install with: pip install requests"
        }

    parser = HandHistoryParser()
    hands = parser.parse_file(file_path, room=room)

    if not hands:
        return {
            "status": "error",
            "message": "Не удалось распарсить раздачи"
        }

    # Загружаем через bulk API
    url = f"{api_url}/api/v1/hands/bulk"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    payload = {
        "hands": hands,
        "skip_existing": skip_existing
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Ошибка загрузки: {str(e)}"
        }


@dataclass
class ParsedHand:
    """
    Упрощённое представление раздачи (интерфейс под тесты).
    """
    hand_id: str
    limit_type: str
    players: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""


# Глобальный экземпляр (для обратной совместимости с тестами/старым импортом)
hand_history_parser = HandHistoryParser()


# CLI интерфейс
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Hand History Parser")
    parser.add_argument("file", help="Путь к hand history файлу")
    parser.add_argument("--room", default="pokerstars", choices=["pokerstars", "888poker", "partypoker"],
                       help="Покер-рум")
    parser.add_argument("--api-url", default="http://localhost:8080", help="URL API")
    parser.add_argument("--api-key", help="API ключ")
    parser.add_argument("--upload", action="store_true", help="Загрузить в API после парсинга")
    parser.add_argument("--no-skip-existing", action="store_true", help="Не пропускать существующие раздачи")

    args = parser.parse_args()

    if args.upload:
        print(f"Парсинг и загрузка {args.file}...")
        result = parse_and_upload(
            args.file,
            api_url=args.api_url,
            api_key=args.api_key,
            room=args.room,
            skip_existing=not args.no_skip_existing
        )
        print(f"Результат: {result}")
    else:
        print(f"Парсинг {args.file}...")
        hh_parser = HandHistoryParser()
        hands = hh_parser.parse_file(args.file, room=args.room)
        print(f"Распарсено раздач: {len(hands)}")

        if hands:
            print("\nПример первой раздачи:")
            import json
            print(json.dumps(hands[0], indent=2, ensure_ascii=False))
