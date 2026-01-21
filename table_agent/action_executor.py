"""Исполнитель действий - эмуляция кликов"""

import asyncio
import random
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod


class ActionType(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass
class ClickPosition:
    """Позиция клика на экране"""
    x: int
    y: int
    width: int = 10
    height: int = 10

    def randomized(self) -> Tuple[int, int]:
        """Вернуть случайную точку в области"""
        rx = self.x + random.randint(-self.width // 2, self.width // 2)
        ry = self.y + random.randint(-self.height // 2, self.height // 2)
        return rx, ry


@dataclass
class TableLayout:
    """Расположение элементов на столе"""
    fold_button: Optional[ClickPosition] = None
    check_button: Optional[ClickPosition] = None
    call_button: Optional[ClickPosition] = None
    bet_button: Optional[ClickPosition] = None
    raise_button: Optional[ClickPosition] = None
    all_in_button: Optional[ClickPosition] = None

    bet_slider: Optional[ClickPosition] = None
    bet_input: Optional[ClickPosition] = None
    confirm_button: Optional[ClickPosition] = None

    def get_button(self, action: ActionType) -> Optional[ClickPosition]:
        """Получить позицию кнопки"""
        mapping = {
            ActionType.FOLD: self.fold_button,
            ActionType.CHECK: self.check_button,
            ActionType.CALL: self.call_button,
            ActionType.BET: self.bet_button,
            ActionType.RAISE: self.raise_button,
            ActionType.ALL_IN: self.all_in_button
        }
        return mapping.get(action)


class ActionExecutor(ABC):
    """Базовый класс для исполнения действий"""

    def __init__(self, layout: TableLayout):
        self.layout = layout
        self.last_action_time = 0

    @abstractmethod
    async def click(self, x: int, y: int):
        """Выполнить клик по координатам"""
        pass

    @abstractmethod
    async def type_text(self, text: str):
        """Ввести текст"""
        pass

    async def execute(self, action: str, amount: Optional[float] = None) -> bool:
        """Выполнить покерное действие"""
        try:
            action_type = ActionType(action.lower())
        except ValueError:
            # Маппинг альтернативных названий
            action_map = {
                "bet": ActionType.BET,
                "raise": ActionType.RAISE,
            }
            action_type = action_map.get(action.lower())
            if not action_type:
                print(f"Unknown action: {action}")
                return False

        # Получаем позицию кнопки
        button = self.layout.get_button(action_type)

        if not button:
            print(f"No button configured for: {action}")
            return False

        # Для bet/raise нужно ввести сумму
        if action_type in [ActionType.BET, ActionType.RAISE] and amount:
            success = await self._execute_sized_action(action_type, amount)
        else:
            # Простой клик
            x, y = button.randomized()
            await self.click(x, y)
            success = True

        return success

    async def _execute_sized_action(self, action_type: ActionType, amount: float) -> bool:
        """Выполнить действие с размером (bet/raise)"""
        # 1. Сначала кликаем на кнопку bet/raise
        button = self.layout.get_button(action_type)
        if button:
            x, y = button.randomized()
            await self.click(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.2))

        # 2. Вводим сумму
        if self.layout.bet_input:
            x, y = self.layout.bet_input.randomized()
            await self.click(x, y)
            await asyncio.sleep(random.uniform(0.05, 0.1))
            await self.type_text(str(amount))
            await asyncio.sleep(random.uniform(0.1, 0.2))

        # 3. Подтверждаем
        if self.layout.confirm_button:
            x, y = self.layout.confirm_button.randomized()
            await self.click(x, y)

        return True


class DummyExecutor(ActionExecutor):
    """Заглушка для тестирования"""

    def __init__(self, layout: Optional[TableLayout] = None):
        super().__init__(layout or TableLayout())
        self.action_log = []

    async def click(self, x: int, y: int):
        print(f"[DUMMY] Click at ({x}, {y})")
        self.action_log.append(("click", x, y))

    async def type_text(self, text: str):
        print(f"[DUMMY] Type: {text}")
        self.action_log.append(("type", text))

    async def execute(self, action: str, amount: Optional[float] = None) -> bool:
        print(f"[DUMMY] Execute: {action} {amount or ''}")
        self.action_log.append(("execute", action, amount))
        return True


class PyAutoGUIExecutor(ActionExecutor):
    """Исполнитель через PyAutoGUI (для Windows/Mac)"""

    def __init__(self, layout: TableLayout):
        super().__init__(layout)
        try:
            import pyautogui
            self.pyautogui = pyautogui
            pyautogui.PAUSE = 0.05
            pyautogui.FAILSAFE = True
        except ImportError:
            raise ImportError("pyautogui required: pip install pyautogui")

    async def click(self, x: int, y: int):
        # Плавное движение мыши
        duration = random.uniform(0.1, 0.25)
        self.pyautogui.moveTo(x, y, duration=duration)
        await asyncio.sleep(random.uniform(0.02, 0.05))
        self.pyautogui.click()

    async def type_text(self, text: str):
        # Имитация печати с задержкой между символами
        for char in text:
            self.pyautogui.press(char)
            await asyncio.sleep(random.uniform(0.03, 0.08))


class ADBExecutor(ActionExecutor):
    """Исполнитель через ADB (для Android эмулятора)"""

    def __init__(self, layout: TableLayout, device_id: Optional[str] = None):
        super().__init__(layout)
        self.device_id = device_id
        self.adb_prefix = f"adb -s {device_id}" if device_id else "adb"

    async def _run_adb(self, command: str):
        """Выполнить ADB команду"""
        full_cmd = f"{self.adb_prefix} {command}"
        proc = await asyncio.create_subprocess_shell(
            full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

    async def click(self, x: int, y: int):
        await self._run_adb(f"shell input tap {x} {y}")

    async def type_text(self, text: str):
        # Экранируем специальные символы
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        await self._run_adb(f"shell input text '{escaped}'")

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """Свайп (для слайдера размера ставки)"""
        await self._run_adb(f"shell input swipe {x1} {y1} {x2} {y2} {duration_ms}")
