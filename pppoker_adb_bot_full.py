#!/usr/bin/env python3
"""
PPPoker ADB Bot - Полная автоматическая игра через ADB

Возможности:
- Автоматическое подключение к Android устройству через ADB
- Распознавание всех элементов игры (карты, стеки, ставки, баттон)
- Определение позиций игроков относительно дилера
- Интеграция с backend API для принятия решений
- Автоматическое выполнение действий (fold, call, raise)

Установка зависимостей:
    pip install opencv-python pillow pytesseract numpy requests

Для macOS также установите tesseract:
    brew install tesseract

Для работы с Android:
    brew install android-platform-tools  # macOS
    sudo apt install adb  # Linux

Использование:
    1. Подключите Android устройство или эмулятор
    2. Включите USB отладку в настройках Android
    3. Проверьте подключение: adb devices
    4. Запустите PPPoker на устройстве
    5. Запустите этот скрипт: python pppoker_adb_bot_full.py

ВАЖНО: По умолчанию DRY_RUN = True (только показывает что будет делать)
        Для реальной игры измените DRY_RUN = False
"""

import subprocess
import time
import cv2
import numpy as np
from PIL import Image
import pytesseract
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import re
import requests
import json


# ==================== НАСТРОЙКИ ====================

# БЕЗОПАСНОСТЬ: Пока True - бот только ПОКАЗЫВАЕТ что будет делать, но НЕ кликает
DRY_RUN = True

# Режим отладки - сохраняет debug screenshots
DEBUG_MODE = True
SAVE_DEBUG_IMAGES = True

# Backend API
API_BASE_URL = "http://localhost:8000/api/v1"
API_KEY = "dev_admin_key"

# Параметры игры
LIMIT_TYPE = "NL10"  # или NL50
SESSION_ID = "pppoker_adb_session"
POLL_INTERVAL = 1.0  # Как часто проверять состояние (секунды)

# Позиции игроков на столе (6-max)
# Координаты в процентах от размера экрана
PLAYER_SCREEN_POSITIONS = {
    0: (0.50, 0.75),  # Hero (внизу по центру)
    1: (0.15, 0.65),  # Лево-низ
    2: (0.10, 0.35),  # Лево-верх
    3: (0.50, 0.20),  # Верх по центру
    4: (0.90, 0.35),  # Право-верх
    5: (0.85, 0.65),  # Право-низ
}


# ==================== DATA CLASSES ====================

@dataclass
class PlayerInfo:
    """Информация об игроке"""
    position: int
    stack: float
    current_bet: float
    is_active: bool
    is_dealer: bool
    screen_position: Tuple[int, int]  # x, y в пикселях


@dataclass
class GameState:
    """Полное состояние игры"""
    hero_cards: str
    board_cards: str
    pot: float
    players: Dict[int, PlayerInfo]
    dealer_position: int
    hero_position: int  # Относительная позиция героя от дилера
    street: str
    active_players: List[int]
    last_raise: float
    min_raise: float
    hero_stack: float


# ==================== ADB CONTROL ====================

class ADBController:
    """Контроллер для работы с Android через ADB"""

    def __init__(self):
        self.device_id = None
        self.screen_width = 0
        self.screen_height = 0
        self._connect()

    def _connect(self):
        """Подключается к устройству"""
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')[1:]  # Пропускаем заголовок

            devices = [line.split()[0] for line in lines if line.strip() and 'device' in line]

            if not devices:
                raise Exception("Не найдено подключенных Android устройств. Выполните: adb devices")

            self.device_id = devices[0]
            print(f"✅ Подключено к устройству: {self.device_id}")

            # Получаем размер экрана
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'wm', 'size'],
                capture_output=True, text=True
            )

            match = re.search(r'(\d+)x(\d+)', result.stdout)
            if match:
                self.screen_width = int(match.group(1))
                self.screen_height = int(match.group(2))
                print(f"📱 Размер экрана: {self.screen_width}x{self.screen_height}")

        except Exception as e:
            raise Exception(f"Ошибка подключения к ADB: {e}")

    def screenshot(self) -> np.ndarray:
        """Делает скриншот экрана"""
        try:
            # ADB screencap -> PNG -> numpy array
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'exec-out', 'screencap', '-p'],
                capture_output=True
            )

            # Конвертируем в numpy array через PIL
            img = Image.open(io.BytesIO(result.stdout))
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        except Exception as e:
            print(f"❌ Ошибка скриншота: {e}")
            return None

    def tap(self, x: int, y: int, dry_run: bool = DRY_RUN):
        """Кликает по координатам"""
        if dry_run:
            print(f"🔷 [DRY RUN] Клик по ({x}, {y})")
            return

        try:
            subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'input', 'tap', str(x), str(y)],
                check=True
            )
            print(f"✅ Клик: ({x}, {y})")
        except Exception as e:
            print(f"❌ Ошибка клика: {e}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300):
        """Свайп (для слайдеров raise)"""
        if DRY_RUN:
            print(f"🔷 [DRY RUN] Свайп от ({x1}, {y1}) до ({x2}, {y2})")
            return

        try:
            subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'input', 'swipe',
                 str(x1), str(y1), str(x2), str(y2), str(duration)],
                check=True
            )
            print(f"✅ Свайп: ({x1}, {y1}) → ({x2}, {y2})")
        except Exception as e:
            print(f"❌ Ошибка свайпа: {e}")

    def input_text(self, text: str):
        """Вводит текст (для ввода суммы raise)"""
        if DRY_RUN:
            print(f"🔷 [DRY RUN] Ввод текста: {text}")
            return

        try:
            subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'input', 'text', text],
                check=True
            )
            print(f"✅ Текст введён: {text}")
        except Exception as e:
            print(f"❌ Ошибка ввода текста: {e}")


# ==================== ENHANCED SCREEN PARSER ====================

class EnhancedPokerParser:
    """Продвинутый парсер экрана PPPoker с полным распознаванием"""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Позиции игроков (в процентах экрана)
        self.player_positions = PLAYER_SCREEN_POSITIONS

        # Вычисляем абсолютные координаты
        self.player_coords = {
            pos: (int(x * screen_width), int(y * screen_height))
            for pos, (x, y) in self.player_positions.items()
        }

        # Регионы для распознавания
        self.hero_cards_region = self._get_region(0.40, 0.70, 0.20, 0.08)
        self.board_region = self._get_region(0.30, 0.35, 0.40, 0.10)
        self.pot_region = self._get_region(0.40, 0.30, 0.20, 0.05)

        # Кнопки действий (внизу экрана)
        self.fold_button = self._get_region(0.10, 0.85, 0.15, 0.08)
        self.call_button = self._get_region(0.42, 0.85, 0.15, 0.08)
        self.raise_button = self._get_region(0.75, 0.85, 0.15, 0.08)

        print(f"🎯 Parser инициализирован для {screen_width}x{screen_height}")

    def _get_region(self, x_pct: float, y_pct: float, w_pct: float, h_pct: float) -> Tuple[int, int, int, int]:
        """Конвертирует проценты в пиксели"""
        return (
            int(x_pct * self.screen_width),
            int(y_pct * self.screen_height),
            int(w_pct * self.screen_width),
            int(h_pct * self.screen_height)
        )

    def parse_full_game_state(self, img: np.ndarray) -> Optional[GameState]:
        """
        Полностью парсит состояние игры

        Returns:
            GameState или None если не удалось распознать
        """
        try:
            # 1. Карты героя
            hero_cards = self._parse_hero_cards(img)
            if not hero_cards or len(hero_cards) < 4:
                print("⚠️ Не удалось распознать карты героя")
                return None

            # 2. Борд
            board_cards = self._parse_board(img)

            # 3. Пот
            pot = self._parse_pot(img)

            # 4. Все игроки (стеки, ставки, баттон)
            players = self._find_all_players(img)
            if not players:
                print("⚠️ Не найдено игроков")
                return None

            # 5. Находим дилера
            dealer_pos = self._find_dealer_button(img, players)

            # 6. Определяем активных игроков
            active_players = [pos for pos, p in players.items() if p.is_active]

            # 7. Определяем улицу
            street = self._determine_street(board_cards)

            # 8. Последний рейз
            last_raise = self._calculate_last_raise(players)

            # 9. Относительная позиция героя
            hero_position = self._calculate_relative_position(0, dealer_pos, len(active_players))

            game_state = GameState(
                hero_cards=hero_cards,
                board_cards=board_cards,
                pot=pot,
                players=players,
                dealer_position=dealer_pos,
                hero_position=hero_position,
                street=street,
                active_players=active_players,
                last_raise=last_raise,
                min_raise=last_raise * 2 if last_raise > 0 else 2.0,
                hero_stack=players[0].stack if 0 in players else 100.0
            )

            if DEBUG_MODE:
                self._print_game_state(game_state)

            return game_state

        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_hero_cards(self, img: np.ndarray) -> str:
        """Распознаёт карты героя"""
        x, y, w, h = self.hero_cards_region
        crop = img[y:y+h, x:x+w]

        if SAVE_DEBUG_IMAGES:
            cv2.imwrite('debug_hero_cards.png', crop)

        text = self._ocr_cards(crop)
        return text

    def _parse_board(self, img: np.ndarray) -> str:
        """Распознаёт карты борда"""
        x, y, w, h = self.board_region
        crop = img[y:y+h, x:x+w]

        if SAVE_DEBUG_IMAGES:
            cv2.imwrite('debug_board.png', crop)

        text = self._ocr_cards(crop)
        return text

    def _parse_pot(self, img: np.ndarray) -> float:
        """Распознаёт размер пота"""
        x, y, w, h = self.pot_region
        crop = img[y:y+h, x:x+w]

        if SAVE_DEBUG_IMAGES:
            cv2.imwrite('debug_pot.png', crop)

        return self._ocr_number(crop)

    def _find_all_players(self, img: np.ndarray) -> Dict[int, PlayerInfo]:
        """
        Находит всех игроков и их данные

        Проверяет каждую из 6 позиций на наличие игрока
        Для каждого игрока распознаёт стек и ставку
        """
        players = {}
        debug_img = img.copy() if SAVE_DEBUG_IMAGES else None

        for position, (x, y) in self.player_coords.items():
            # Проверяем есть ли игрок на этой позиции
            is_present = self._is_player_present(img, x, y, position)

            if is_present:
                # Распознаём стек
                stack = self._parse_player_stack(img, x, y, position)

                # Распознаём текущую ставку
                current_bet = self._parse_player_bet(img, x, y, position)

                # Проверяем баттон дилера
                is_dealer = self._check_dealer_button_near(img, x, y)

                players[position] = PlayerInfo(
                    position=position,
                    stack=stack,
                    current_bet=current_bet,
                    is_active=stack > 0,
                    is_dealer=is_dealer,
                    screen_position=(x, y)
                )

                if DEBUG_MODE:
                    print(f"👤 Позиция {position}: Stack={stack:.2f}, Bet={current_bet:.2f}, Dealer={is_dealer}")

                # Рисуем на debug изображении
                if SAVE_DEBUG_IMAGES:
                    color = (0, 255, 0) if is_dealer else (255, 255, 0)
                    cv2.circle(debug_img, (x, y), 30, color, 3)
                    cv2.putText(debug_img, f"P{position}", (x-20, y-40),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if SAVE_DEBUG_IMAGES and debug_img is not None:
            cv2.imwrite('debug_players.png', debug_img)

        return players

    def _is_player_present(self, img: np.ndarray, x: int, y: int, position: int) -> bool:
        """
        Проверяет есть ли игрок на позиции

        Ищет яркие пиксели в области аватара игрока
        """
        # Регион вокруг позиции игрока
        region_size = 80
        x1 = max(0, x - region_size // 2)
        y1 = max(0, y - region_size // 2)
        x2 = min(img.shape[1], x + region_size // 2)
        y2 = min(img.shape[0], y + region_size // 2)

        crop = img[y1:y2, x1:x2]

        # Конвертируем в grayscale
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        # Считаем яркие пиксели (аватар обычно яркий)
        bright_pixels = np.sum(gray > 100)
        total_pixels = gray.size

        brightness_ratio = bright_pixels / total_pixels if total_pixels > 0 else 0

        # Если больше 20% ярких пикселей - игрок присутствует
        return brightness_ratio > 0.20

    def _parse_player_stack(self, img: np.ndarray, x: int, y: int, position: int) -> float:
        """
        Распознаёт стек игрока через OCR

        Стек обычно находится под аватаром игрока
        """
        # Регион стека (под аватаром)
        offset_y = 60 if position == 0 else 40
        stack_region_w = 120
        stack_region_h = 30

        x1 = max(0, x - stack_region_w // 2)
        y1 = min(img.shape[0] - stack_region_h, y + offset_y)
        x2 = min(img.shape[1], x1 + stack_region_w)
        y2 = min(img.shape[0], y1 + stack_region_h)

        crop = img[y1:y2, x1:x2]

        if SAVE_DEBUG_IMAGES:
            cv2.imwrite(f'debug_stack_{position}.png', crop)

        return self._ocr_number(crop)

    def _parse_player_bet(self, img: np.ndarray, x: int, y: int, position: int) -> float:
        """
        Распознаёт текущую ставку игрока

        Ставка обычно между игроком и центром стола
        """
        # Смещаем в сторону центра стола
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2

        # Ставка на 1/3 пути от игрока к центру
        bet_x = int(x + (center_x - x) * 0.3)
        bet_y = int(y + (center_y - y) * 0.3)

        bet_region_w = 100
        bet_region_h = 25

        x1 = max(0, bet_x - bet_region_w // 2)
        y1 = max(0, bet_y - bet_region_h // 2)
        x2 = min(img.shape[1], x1 + bet_region_w)
        y2 = min(img.shape[0], y1 + bet_region_h)

        crop = img[y1:y2, x1:x2]

        if SAVE_DEBUG_IMAGES:
            cv2.imwrite(f'debug_bet_{position}.png', crop)

        return self._ocr_number(crop)

    def _check_dealer_button_near(self, img: np.ndarray, x: int, y: int) -> bool:
        """
        Проверяет есть ли кнопка дилера рядом с игроком

        Кнопка дилера - обычно белый круглый значок с буквой D
        """
        # Область поиска баттона
        search_radius = 70
        x1 = max(0, x - search_radius)
        y1 = max(0, y - search_radius)
        x2 = min(img.shape[1], x + search_radius)
        y2 = min(img.shape[0], y + search_radius)

        search_area = img[y1:y2, x1:x2]

        # Конвертируем в HSV для поиска белого цвета
        hsv = cv2.cvtColor(search_area, cv2.COLOR_BGR2HSV)

        # Маска для белого цвета (кнопка дилера обычно белая)
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # Ищем контуры
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            # Баттон имеет площадь примерно 400-1200 пикселей
            if 300 < area < 1500:
                # Проверяем что контур примерно круглый
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    if circularity > 0.6:  # Достаточно круглый
                        return True

        return False

    def _find_dealer_button(self, img: np.ndarray, players: Dict[int, PlayerInfo]) -> int:
        """Находит позицию дилера"""
        for position, player in players.items():
            if player.is_dealer:
                return position

        # Если не нашли - возвращаем позицию 3 (default)
        return 3

    def _calculate_last_raise(self, players: Dict[int, PlayerInfo]) -> float:
        """Вычисляет размер последнего рейза"""
        bets = [p.current_bet for p in players.values() if p.current_bet > 0]
        if len(bets) < 2:
            return max(bets) if bets else 0.0

        bets.sort()
        return bets[-1] - bets[-2] if len(bets) >= 2 else bets[-1]

    def _determine_street(self, board: str) -> str:
        """Определяет улицу по количеству карт борда"""
        board_cards = len(board) // 2
        if board_cards == 0:
            return "preflop"
        elif board_cards == 3:
            return "flop"
        elif board_cards == 4:
            return "turn"
        elif board_cards == 5:
            return "river"
        return "preflop"

    def _calculate_relative_position(self, hero_pos: int, dealer_pos: int, num_players: int) -> int:
        """Вычисляет относительную позицию героя от дилера"""
        return (hero_pos - dealer_pos - 1) % num_players

    def _ocr_cards(self, img: np.ndarray) -> str:
        """
        OCR для распознавания карт

        Returns:
            Строка вида "AsKh" или "As Kh 9d"
        """
        # Препроцессинг
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Увеличиваем контраст
        gray = cv2.equalizeHist(gray)

        # Бинаризация
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Увеличиваем для лучшего распознавания
        scale = 3
        binary = cv2.resize(binary, (img.shape[1] * scale, img.shape[0] * scale))

        # OCR
        config = '--psm 6 -c tessedit_char_whitelist=AKQJTakqjt23456789shdc♠♥♦♣ '
        text = pytesseract.image_to_string(binary, config=config)

        # Парсим карты
        cards = self._parse_cards_from_text(text)
        return cards

    def _parse_cards_from_text(self, text: str) -> str:
        """Извлекает карты из OCR текста"""
        text = text.strip().upper()

        # Карты формата: ранг + масть
        # Ранги: A K Q J T 9 8 7 6 5 4 3 2
        # Масти: s h d c (или символы)

        rank_map = {'A': 'A', 'K': 'K', 'Q': 'Q', 'J': 'J', 'T': 'T', '10': 'T',
                   '9': '9', '8': '8', '7': '7', '6': '6', '5': '5', '4': '4', '3': '3', '2': '2'}
        suit_map = {'S': 's', 'H': 'h', 'D': 'd', 'C': 'c',
                   '♠': 's', '♥': 'h', '♦': 'd', '♣': 'c'}

        cards = []
        i = 0
        while i < len(text):
            # Ищем ранг
            if text[i] in rank_map:
                rank = rank_map[text[i]]
                i += 1

                # Ищем масть
                if i < len(text) and text[i] in suit_map:
                    suit = suit_map[text[i]]
                    cards.append(f"{rank}{suit}")
                    i += 1
                else:
                    i += 1
            else:
                i += 1

        return "".join(cards)

    def _ocr_number(self, img: np.ndarray) -> float:
        """
        OCR для распознавания чисел (стек, ставка, пот)

        Returns:
            float значение или 0.0 если не удалось распознать
        """
        # Препроцессинг
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Увеличиваем
        binary = cv2.resize(binary, (img.shape[1] * 2, img.shape[0] * 2))

        # OCR только цифры
        config = '--psm 7 -c tessedit_char_whitelist=0123456789.,$'
        text = pytesseract.image_to_string(binary, config=config)

        # Парсим число
        text = text.strip().replace('$', '').replace(',', '').replace(' ', '')

        try:
            return float(text) if text else 0.0
        except ValueError:
            return 0.0

    def _print_game_state(self, state: GameState):
        """Выводит состояние игры в консоль"""
        print("\n" + "="*60)
        print(f"🎴 Карты героя: {state.hero_cards}")
        print(f"🎴 Борд: {state.board_cards if state.board_cards else '---'}")
        print(f"💰 Пот: ${state.pot:.2f}")
        print(f"🎯 Улица: {state.street}")
        print(f"🎲 Дилер: позиция {state.dealer_position}")
        print(f"📍 Позиция героя: {state.hero_position} от дилера")
        print(f"👥 Активных игроков: {len(state.active_players)}")
        print(f"💵 Последний рейз: ${state.last_raise:.2f}")
        print(f"💵 Стек героя: ${state.hero_stack:.2f}")
        print("="*60 + "\n")

    def find_button(self, img: np.ndarray, button_name: str) -> Optional[Tuple[int, int]]:
        """
        Находит кнопку действия на экране

        Args:
            button_name: "fold", "call", "raise"

        Returns:
            (x, y) координаты центра кнопки или None
        """
        button_regions = {
            "fold": self.fold_button,
            "call": self.call_button,
            "raise": self.raise_button
        }

        if button_name not in button_regions:
            return None

        x, y, w, h = button_regions[button_name]

        # Возвращаем центр кнопки
        return (x + w // 2, y + h // 2)


# ==================== API CLIENT ====================

class BackendAPIClient:
    """Клиент для работы с backend API"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def get_decision(self, game_state: GameState) -> Dict:
        """
        Запрашивает решение у backend

        Returns:
            {"action": "fold"|"call"|"raise", "amount": float}
        """
        try:
            # Формируем запрос
            payload = {
                "hero_cards": game_state.hero_cards,
                "board_cards": game_state.board_cards,
                "pot": game_state.pot,
                "stacks": {str(k): v.stack for k, v in game_state.players.items()},
                "bets": {str(k): v.current_bet for k, v in game_state.players.items()},
                "position": game_state.hero_position,
                "street": game_state.street,
                "dealer_position": game_state.dealer_position,
                "active_players": game_state.active_players,
                "limit_type": LIMIT_TYPE,
                "session_id": SESSION_ID
            }

            response = requests.post(
                f"{self.base_url}/decision",
                json=payload,
                headers=self.headers,
                timeout=5
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                # Fallback - всегда fold
                return {"action": "fold", "amount": 0}

        except Exception as e:
            print(f"❌ Ошибка запроса к API: {e}")
            return {"action": "fold", "amount": 0}

    def log_hand(self, game_state: GameState, decision: Dict, result: str):
        """Логирует раздачу в backend"""
        try:
            payload = {
                "hand_id": f"pppoker_{int(time.time())}",
                "session_id": SESSION_ID,
                "limit_type": LIMIT_TYPE,
                "hero_cards": game_state.hero_cards,
                "board_cards": game_state.board_cards,
                "position": game_state.hero_position,
                "dealer_position": game_state.dealer_position,
                "pot": game_state.pot,
                "action_taken": decision["action"],
                "amount": decision.get("amount", 0),
                "result": result,
                "rake_amount": 0.0
            }

            requests.post(
                f"{self.base_url}/hands/log",
                json=payload,
                headers=self.headers,
                timeout=5
            )
        except Exception as e:
            print(f"⚠️ Не удалось залогировать руку: {e}")


# ==================== MAIN BOT ====================

class PPPokerBot:
    """Главный класс бота"""

    def __init__(self):
        print("🤖 Инициализация PPPoker Bot...")

        # ADB контроллер
        self.adb = ADBController()

        # Парсер экрана
        self.parser = EnhancedPokerParser(
            self.adb.screen_width,
            self.adb.screen_height
        )

        # API клиент
        self.api = BackendAPIClient(API_BASE_URL, API_KEY)

        # Состояние
        self.last_game_state = None
        self.hands_played = 0

        print("✅ Бот готов к работе!")

        if DRY_RUN:
            print("\n⚠️  РЕЖИМ DRY_RUN АКТИВЕН")
            print("⚠️  Бот НЕ будет кликать по кнопкам")
            print("⚠️  Для реальной игры измените DRY_RUN = False\n")

    def run(self):
        """Основной цикл бота"""
        print("🎮 Запуск основного цикла...\n")

        try:
            while True:
                # 1. Делаем скриншот
                img = self.adb.screenshot()
                if img is None:
                    print("⚠️ Не удалось получить скриншот")
                    time.sleep(POLL_INTERVAL)
                    continue

                # 2. Парсим состояние игры
                game_state = self.parser.parse_full_game_state(img)
                if game_state is None:
                    print("⚠️ Не удалось распознать состояние игры")
                    time.sleep(POLL_INTERVAL)
                    continue

                # 3. Проверяем нужно ли действовать
                if not self._is_hero_turn(img):
                    time.sleep(POLL_INTERVAL)
                    continue

                print("🎯 Наш ход!")

                # 4. Получаем решение от AI
                decision = self.api.get_decision(game_state)
                print(f"🤖 Решение AI: {decision['action'].upper()}")
                if decision.get("amount"):
                    print(f"   Сумма: ${decision['amount']:.2f}")

                # 5. Выполняем действие
                self._execute_action(img, decision)

                # 6. Логируем руку
                self.hands_played += 1
                print(f"📊 Сыграно рук: {self.hands_played}")

                # Пауза перед следующей проверкой
                time.sleep(POLL_INTERVAL * 2)

        except KeyboardInterrupt:
            print("\n\n👋 Бот остановлен пользователем")
            print(f"📊 Всего сыграно рук: {self.hands_played}")

    def _is_hero_turn(self, img: np.ndarray) -> bool:
        """
        Проверяет наш ли сейчас ход

        Ищет активные кнопки действий (Fold/Call/Raise)
        """
        # Проверяем наличие кнопок действий
        fold_pos = self.parser.find_button(img, "fold")
        call_pos = self.parser.find_button(img, "call")

        if not fold_pos or not call_pos:
            return False

        # Проверяем что кнопки видны (не серые)
        x, y, w, h = self.parser.fold_button
        fold_region = img[y:y+h, x:x+w]

        # Считаем цветные пиксели
        hsv = cv2.cvtColor(fold_region, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]

        # Если много насыщенных цветов - кнопки активны
        active_pixels = np.sum(saturation > 50)
        total_pixels = saturation.size

        return (active_pixels / total_pixels) > 0.15

    def _execute_action(self, img: np.ndarray, decision: Dict):
        """Выполняет действие на экране"""
        action = decision["action"].lower()

        if action == "fold":
            self._click_fold(img)
        elif action == "call":
            self._click_call(img)
        elif action == "raise":
            self._click_raise(img, decision.get("amount", 0))
        else:
            print(f"⚠️ Неизвестное действие: {action}")
            self._click_fold(img)

    def _click_fold(self, img: np.ndarray):
        """Кликает Fold"""
        pos = self.parser.find_button(img, "fold")
        if pos:
            print("❌ Fold")
            self.adb.tap(pos[0], pos[1])

    def _click_call(self, img: np.ndarray):
        """Кликает Call/Check"""
        pos = self.parser.find_button(img, "call")
        if pos:
            print("✅ Call")
            self.adb.tap(pos[0], pos[1])

    def _click_raise(self, img: np.ndarray, amount: float):
        """Кликает Raise с указанной суммой"""
        pos = self.parser.find_button(img, "raise")
        if pos:
            print(f"📈 Raise ${amount:.2f}")
            self.adb.tap(pos[0], pos[1])

            # TODO: Ввод суммы через слайдер или текстовое поле
            # Это зависит от UI PPPoker
            time.sleep(0.5)

            # Подтверждение raise (обычно ещё один клик)
            self.adb.tap(pos[0], pos[1])


# ==================== ENTRY POINT ====================

def main():
    """Точка входа"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              🎰 PPPoker ADB Bot v2.0 🎰                   ║
║                                                           ║
║  Полностью автоматический покерный бот для PPPoker       ║
║  через Android Debug Bridge (ADB)                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # Проверяем зависимости
    try:
        import io  # для скриншотов
        print("✅ Все зависимости установлены")
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("Установите: pip install opencv-python pillow pytesseract numpy requests")
        return

    # Создаём и запускаем бота
    try:
        bot = PPPokerBot()
        bot.run()
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Добавляем импорт io для работы со скриншотами
    import io
    main()
