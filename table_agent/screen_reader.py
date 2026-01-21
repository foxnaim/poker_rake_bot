"""Screen Reader для чтения состояния покерного стола

Поддерживает:
- Скриншот окна покерного клиента
- OCR для распознавания карт, стеков, ставок
- Определение позиций кнопок (fold, call, raise)
- Работа с различными покер-клиентами
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import re
import time

logger = logging.getLogger(__name__)

# Опциональные импорты для работы с изображениями
try:
    from PIL import Image, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL not installed. Install with: pip install Pillow")

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False
    logger.warning("pytesseract not installed. Install with: pip install pytesseract")

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False
    logger.warning("pyautogui not installed. Install with: pip install pyautogui")


@dataclass
class CardRegion:
    """Регион для распознавания карты"""
    x: int
    y: int
    width: int
    height: int
    name: str = ""


@dataclass
class ButtonRegion:
    """Регион кнопки действия"""
    x: int
    y: int
    width: int
    height: int
    action: str  # fold, call, check, raise, all_in

    @property
    def center(self) -> Tuple[int, int]:
        """Центр кнопки для клика"""
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class TableLayout:
    """Разметка стола для конкретного покер-клиента"""
    name: str
    window_title_pattern: str

    # Регионы карт героя
    hero_cards: List[CardRegion] = field(default_factory=list)

    # Регионы борда
    board_cards: List[CardRegion] = field(default_factory=list)

    # Регионы стеков игроков (по позициям 0-5)
    player_stacks: Dict[int, CardRegion] = field(default_factory=dict)

    # Регионы ставок игроков
    player_bets: Dict[int, CardRegion] = field(default_factory=dict)

    # Регион пота
    pot_region: Optional[CardRegion] = None

    # Кнопки действий
    buttons: List[ButtonRegion] = field(default_factory=list)

    # Регион для ввода размера ставки
    bet_input_region: Optional[CardRegion] = None

    # Регион таймера (для определения чей ход)
    timer_regions: Dict[int, CardRegion] = field(default_factory=dict)


class ScreenReader(ABC):
    """Базовый класс для чтения экрана покерного стола"""

    def __init__(self, layout: TableLayout):
        self.layout = layout
        self.last_screenshot: Optional[Any] = None
        self.last_read_time: float = 0

        # Кэш распознанных данных
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: float = 0.5  # Время жизни кэша в секундах

    @abstractmethod
    def capture_window(self) -> Optional[Any]:
        """Захватывает скриншот окна покерного клиента"""
        pass

    @abstractmethod
    def find_window(self) -> Optional[Tuple[int, int, int, int]]:
        """Находит окно покерного клиента, возвращает (x, y, width, height)"""
        pass

    def read_table_state(self) -> Dict[str, Any]:
        """
        Читает полное состояние стола

        Returns:
            Словарь с состоянием стола
        """
        # Проверяем кэш
        now = time.time()
        if now - self.last_read_time < self._cache_ttl and self._cache:
            return self._cache

        screenshot = self.capture_window()
        if screenshot is None:
            return {"error": "Failed to capture window"}

        self.last_screenshot = screenshot
        self.last_read_time = now

        state = {
            "hero_cards": self._read_hero_cards(screenshot),
            "board_cards": self._read_board_cards(screenshot),
            "pot": self._read_pot(screenshot),
            "player_stacks": self._read_player_stacks(screenshot),
            "player_bets": self._read_player_bets(screenshot),
            "current_player": self._detect_current_player(screenshot),
            "available_buttons": self._detect_available_buttons(screenshot),
            "timestamp": now
        }

        self._cache = state
        return state

    def _read_hero_cards(self, screenshot: Any) -> str:
        """Читает карты героя"""
        cards = []
        for region in self.layout.hero_cards:
            card = self._ocr_card(screenshot, region)
            if card:
                cards.append(card)
        return "".join(cards)

    def _read_board_cards(self, screenshot: Any) -> str:
        """Читает карты борда"""
        cards = []
        for region in self.layout.board_cards:
            card = self._ocr_card(screenshot, region)
            if card:
                cards.append(card)
        return "".join(cards)

    def _read_pot(self, screenshot: Any) -> float:
        """Читает размер пота"""
        if not self.layout.pot_region:
            return 0.0
        return self._ocr_number(screenshot, self.layout.pot_region)

    def _read_player_stacks(self, screenshot: Any) -> Dict[int, float]:
        """Читает стеки игроков"""
        stacks = {}
        for position, region in self.layout.player_stacks.items():
            stack = self._ocr_number(screenshot, region)
            if stack > 0:
                stacks[position] = stack
        return stacks

    def _read_player_bets(self, screenshot: Any) -> Dict[int, float]:
        """Читает ставки игроков"""
        bets = {}
        for position, region in self.layout.player_bets.items():
            bet = self._ocr_number(screenshot, region)
            if bet > 0:
                bets[position] = bet
        return bets

    def _detect_current_player(self, screenshot: Any) -> int:
        """Определяет чей сейчас ход по таймеру/подсветке"""
        # Базовая реализация - ищем активный таймер
        for position, region in self.layout.timer_regions.items():
            if self._is_region_active(screenshot, region):
                return position
        return -1

    def _detect_available_buttons(self, screenshot: Any) -> List[str]:
        """Определяет доступные кнопки действий"""
        available = []
        for button in self.layout.buttons:
            if self._is_button_visible(screenshot, button):
                available.append(button.action)
        return available

    @abstractmethod
    def _ocr_card(self, screenshot: Any, region: CardRegion) -> Optional[str]:
        """OCR для распознавания карты (например 'As', 'Kh')"""
        pass

    @abstractmethod
    def _ocr_number(self, screenshot: Any, region: CardRegion) -> float:
        """OCR для распознавания числа (стек, ставка, пот)"""
        pass

    @abstractmethod
    def _is_region_active(self, screenshot: Any, region: CardRegion) -> bool:
        """Проверяет, активен ли регион (например, горит таймер)"""
        pass

    @abstractmethod
    def _is_button_visible(self, screenshot: Any, button: ButtonRegion) -> bool:
        """Проверяет, видна ли кнопка"""
        pass

    def get_button_position(self, action: str) -> Optional[Tuple[int, int]]:
        """Возвращает позицию кнопки для клика"""
        for button in self.layout.buttons:
            if button.action == action:
                return button.center
        return None


class PILScreenReader(ScreenReader):
    """Screen Reader на базе PIL + Tesseract"""

    def __init__(self, layout: TableLayout):
        super().__init__(layout)

        if not HAS_PIL:
            raise RuntimeError("PIL not available. Install with: pip install Pillow")
        if not HAS_TESSERACT:
            raise RuntimeError("pytesseract not available. Install with: pip install pytesseract")

        # Настройки Tesseract
        self.tesseract_config = '--psm 7 -c tessedit_char_whitelist=0123456789.$,AKQJTakqjt23456789shdc♠♥♦♣'

        # Карта символов карт
        self.card_rank_map = {
            'A': 'A', 'a': 'A',
            'K': 'K', 'k': 'K',
            'Q': 'Q', 'q': 'Q',
            'J': 'J', 'j': 'J',
            'T': 'T', 't': 'T', '10': 'T',
            '9': '9', '8': '8', '7': '7', '6': '6',
            '5': '5', '4': '4', '3': '3', '2': '2'
        }

        self.card_suit_map = {
            's': 's', 'S': 's', '♠': 's',
            'h': 'h', 'H': 'h', '♥': 'h',
            'd': 'd', 'D': 'd', '♦': 'd',
            'c': 'c', 'C': 'c', '♣': 'c'
        }

        self._window_bounds: Optional[Tuple[int, int, int, int]] = None

    def find_window(self) -> Optional[Tuple[int, int, int, int]]:
        """Находит окно покерного клиента"""
        if not HAS_PYAUTOGUI:
            logger.error("pyautogui not available for window finding")
            return None

        try:
            # Ищем окно по паттерну заголовка
            import subprocess

            # macOS
            result = subprocess.run(
                ['osascript', '-e',
                 f'tell application "System Events" to get bounds of first window of '
                 f'(first process whose name contains "{self.layout.window_title_pattern}")'],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                bounds = result.stdout.strip().split(', ')
                if len(bounds) == 4:
                    x1, y1, x2, y2 = map(int, bounds)
                    self._window_bounds = (x1, y1, x2 - x1, y2 - y1)
                    return self._window_bounds
        except Exception as e:
            logger.error(f"Error finding window: {e}")

        return None

    def capture_window(self) -> Optional[Image.Image]:
        """Захватывает скриншот окна"""
        if not HAS_PIL:
            return None

        try:
            if self._window_bounds:
                x, y, w, h = self._window_bounds
                screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            else:
                # Пробуем найти окно
                bounds = self.find_window()
                if bounds:
                    x, y, w, h = bounds
                    screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                else:
                    # Полный скриншот как fallback
                    screenshot = ImageGrab.grab()

            return screenshot
        except Exception as e:
            logger.error(f"Error capturing window: {e}")
            return None

    def _ocr_card(self, screenshot: Image.Image, region: CardRegion) -> Optional[str]:
        """OCR для распознавания карты"""
        try:
            # Вырезаем регион
            crop = screenshot.crop((
                region.x, region.y,
                region.x + region.width,
                region.y + region.height
            ))

            # Увеличиваем для лучшего распознавания
            crop = crop.resize((crop.width * 3, crop.height * 3), Image.Resampling.LANCZOS)

            # Конвертируем в grayscale
            crop = crop.convert('L')

            # OCR
            text = pytesseract.image_to_string(crop, config=self.tesseract_config).strip()

            if len(text) >= 2:
                rank = self.card_rank_map.get(text[0], None)
                suit = self.card_suit_map.get(text[-1], None)

                if rank and suit:
                    return f"{rank}{suit}"

            return None
        except Exception as e:
            logger.debug(f"OCR card error: {e}")
            return None

    def _ocr_number(self, screenshot: Image.Image, region: CardRegion) -> float:
        """OCR для распознавания числа"""
        try:
            crop = screenshot.crop((
                region.x, region.y,
                region.x + region.width,
                region.y + region.height
            ))

            # Увеличиваем
            crop = crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS)
            crop = crop.convert('L')

            # OCR только для цифр
            config = '--psm 7 -c tessedit_char_whitelist=0123456789.$,'
            text = pytesseract.image_to_string(crop, config=config).strip()

            # Парсим число
            text = text.replace('$', '').replace(',', '').replace(' ', '')

            if text:
                return float(text)
            return 0.0
        except Exception as e:
            logger.debug(f"OCR number error: {e}")
            return 0.0

    def _is_region_active(self, screenshot: Image.Image, region: CardRegion) -> bool:
        """Проверяет активность региона по яркости/цвету"""
        try:
            crop = screenshot.crop((
                region.x, region.y,
                region.x + region.width,
                region.y + region.height
            ))

            # Проверяем среднюю яркость
            pixels = list(crop.getdata())
            if not pixels:
                return False

            # Если это RGB
            if isinstance(pixels[0], tuple):
                avg_brightness = sum(sum(p[:3]) / 3 for p in pixels) / len(pixels)
            else:
                avg_brightness = sum(pixels) / len(pixels)

            # Активный регион обычно ярче
            return avg_brightness > 150
        except Exception:
            return False

    def _is_button_visible(self, screenshot: Image.Image, button: ButtonRegion) -> bool:
        """Проверяет видимость кнопки"""
        try:
            crop = screenshot.crop((
                button.x, button.y,
                button.x + button.width,
                button.y + button.height
            ))

            # Проверяем, что кнопка не серая (disabled)
            pixels = list(crop.getdata())
            if not pixels or not isinstance(pixels[0], tuple):
                return False

            # Считаем цветные пиксели (не серые)
            colored = 0
            for p in pixels:
                r, g, b = p[:3]
                # Если разница между каналами значительная - кнопка цветная
                if abs(r - g) > 30 or abs(g - b) > 30 or abs(r - b) > 30:
                    colored += 1

            # Если больше 30% пикселей цветные - кнопка активна
            return colored / len(pixels) > 0.3
        except Exception:
            return False


class MockScreenReader(ScreenReader):
    """Mock Screen Reader для тестирования"""

    def __init__(self, layout: TableLayout):
        super().__init__(layout)
        self.mock_state: Dict[str, Any] = {
            "hero_cards": "AsKh",
            "board_cards": "",
            "pot": 3.0,
            "player_stacks": {0: 100.0, 1: 95.0, 2: 110.0},
            "player_bets": {1: 0.5, 2: 1.0},
            "current_player": 0,
            "available_buttons": ["fold", "call", "raise"]
        }

    def set_mock_state(self, state: Dict[str, Any]):
        """Устанавливает mock состояние для тестов"""
        self.mock_state.update(state)

    def find_window(self) -> Optional[Tuple[int, int, int, int]]:
        return (0, 0, 800, 600)

    def capture_window(self) -> Optional[Any]:
        return "mock_screenshot"

    def read_table_state(self) -> Dict[str, Any]:
        return {**self.mock_state, "timestamp": time.time()}

    def _ocr_card(self, screenshot: Any, region: CardRegion) -> Optional[str]:
        return None

    def _ocr_number(self, screenshot: Any, region: CardRegion) -> float:
        return 0.0

    def _is_region_active(self, screenshot: Any, region: CardRegion) -> bool:
        return False

    def _is_button_visible(self, screenshot: Any, button: ButtonRegion) -> bool:
        return True


# ============================================
# Предустановленные layouts для покер-румов
# ============================================

def get_pokerking_layout() -> TableLayout:
    """Layout для PokerKing/WPN"""
    return TableLayout(
        name="PokerKing",
        window_title_pattern="PokerKing",
        hero_cards=[
            CardRegion(x=350, y=450, width=40, height=55, name="card1"),
            CardRegion(x=395, y=450, width=40, height=55, name="card2"),
        ],
        board_cards=[
            CardRegion(x=280, y=250, width=40, height=55, name="flop1"),
            CardRegion(x=325, y=250, width=40, height=55, name="flop2"),
            CardRegion(x=370, y=250, width=40, height=55, name="flop3"),
            CardRegion(x=415, y=250, width=40, height=55, name="turn"),
            CardRegion(x=460, y=250, width=40, height=55, name="river"),
        ],
        player_stacks={
            0: CardRegion(x=350, y=520, width=80, height=20, name="hero_stack"),
            1: CardRegion(x=150, y=400, width=80, height=20, name="sb_stack"),
            2: CardRegion(x=150, y=200, width=80, height=20, name="bb_stack"),
            3: CardRegion(x=350, y=100, width=80, height=20, name="utg_stack"),
            4: CardRegion(x=550, y=200, width=80, height=20, name="mp_stack"),
            5: CardRegion(x=550, y=400, width=80, height=20, name="co_stack"),
        },
        player_bets={
            0: CardRegion(x=360, y=400, width=60, height=20, name="hero_bet"),
            1: CardRegion(x=200, y=350, width=60, height=20, name="sb_bet"),
            2: CardRegion(x=200, y=250, width=60, height=20, name="bb_bet"),
            3: CardRegion(x=360, y=180, width=60, height=20, name="utg_bet"),
            4: CardRegion(x=500, y=250, width=60, height=20, name="mp_bet"),
            5: CardRegion(x=500, y=350, width=60, height=20, name="co_bet"),
        },
        pot_region=CardRegion(x=350, y=200, width=100, height=30, name="pot"),
        buttons=[
            ButtonRegion(x=250, y=550, width=80, height=35, action="fold"),
            ButtonRegion(x=340, y=550, width=80, height=35, action="call"),
            ButtonRegion(x=430, y=550, width=80, height=35, action="raise"),
        ],
        bet_input_region=CardRegion(x=520, y=550, width=80, height=30, name="bet_input"),
    )


def get_pokerstars_layout() -> TableLayout:
    """Layout для PokerStars"""
    return TableLayout(
        name="PokerStars",
        window_title_pattern="PokerStars",
        hero_cards=[
            CardRegion(x=370, y=440, width=45, height=60, name="card1"),
            CardRegion(x=420, y=440, width=45, height=60, name="card2"),
        ],
        board_cards=[
            CardRegion(x=265, y=230, width=45, height=60, name="flop1"),
            CardRegion(x=315, y=230, width=45, height=60, name="flop2"),
            CardRegion(x=365, y=230, width=45, height=60, name="flop3"),
            CardRegion(x=415, y=230, width=45, height=60, name="turn"),
            CardRegion(x=465, y=230, width=45, height=60, name="river"),
        ],
        player_stacks={
            0: CardRegion(x=370, y=510, width=80, height=20, name="hero_stack"),
            1: CardRegion(x=140, y=380, width=80, height=20, name="sb_stack"),
            2: CardRegion(x=140, y=180, width=80, height=20, name="bb_stack"),
            3: CardRegion(x=370, y=80, width=80, height=20, name="utg_stack"),
            4: CardRegion(x=580, y=180, width=80, height=20, name="mp_stack"),
            5: CardRegion(x=580, y=380, width=80, height=20, name="co_stack"),
        },
        pot_region=CardRegion(x=360, y=190, width=100, height=25, name="pot"),
        buttons=[
            ButtonRegion(x=270, y=560, width=90, height=40, action="fold"),
            ButtonRegion(x=370, y=560, width=90, height=40, action="call"),
            ButtonRegion(x=470, y=560, width=90, height=40, action="raise"),
        ],
    )


def get_888poker_layout() -> TableLayout:
    """Layout для 888poker"""
    return TableLayout(
        name="888poker",
        window_title_pattern="888poker",
        hero_cards=[
            CardRegion(x=360, y=430, width=42, height=58, name="card1"),
            CardRegion(x=405, y=430, width=42, height=58, name="card2"),
        ],
        board_cards=[
            CardRegion(x=270, y=220, width=42, height=58, name="flop1"),
            CardRegion(x=318, y=220, width=42, height=58, name="flop2"),
            CardRegion(x=366, y=220, width=42, height=58, name="flop3"),
            CardRegion(x=414, y=220, width=42, height=58, name="turn"),
            CardRegion(x=462, y=220, width=42, height=58, name="river"),
        ],
        pot_region=CardRegion(x=350, y=180, width=100, height=25, name="pot"),
        buttons=[
            ButtonRegion(x=260, y=550, width=85, height=38, action="fold"),
            ButtonRegion(x=355, y=550, width=85, height=38, action="call"),
            ButtonRegion(x=450, y=550, width=85, height=38, action="raise"),
        ],
    )


# Реестр layouts
LAYOUTS = {
    "pokerking": get_pokerking_layout,
    "pokerstars": get_pokerstars_layout,
    "888poker": get_888poker_layout,
}


def create_screen_reader(room: str, mock: bool = False) -> ScreenReader:
    """
    Фабричный метод для создания Screen Reader

    Args:
        room: Название покер-рума (pokerking, pokerstars, 888poker)
        mock: Использовать mock reader для тестов

    Returns:
        ScreenReader instance
    """
    layout_factory = LAYOUTS.get(room.lower())
    if not layout_factory:
        raise ValueError(f"Unknown room: {room}. Available: {', '.join(LAYOUTS.keys())}")

    layout = layout_factory()

    if mock:
        return MockScreenReader(layout)

    return PILScreenReader(layout)
