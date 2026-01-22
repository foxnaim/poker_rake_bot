#!/usr/bin/env python3
"""
Утилита калибровки кнопок для Table Agent.

Позволяет интерактивно определить координаты кнопок покер-клиента
путем кликов мышью и сохранить их в конфиг.

Использование:
    python -m tools.calibrate_buttons --room pokerking
    python -m tools.calibrate_buttons --room pokerstars --output layouts/pokerstars.json
"""

import argparse
import json
import sys
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, List

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from pynput import mouse
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


@dataclass
class ButtonPosition:
    """Позиция кнопки"""
    x: int
    y: int
    width: int = 80
    height: int = 30
    name: str = ""


@dataclass
class TableLayout:
    """Layout стола"""
    room: str
    resolution: Tuple[int, int]
    fold_button: Optional[ButtonPosition] = None
    check_button: Optional[ButtonPosition] = None
    call_button: Optional[ButtonPosition] = None
    bet_button: Optional[ButtonPosition] = None
    raise_button: Optional[ButtonPosition] = None
    all_in_button: Optional[ButtonPosition] = None
    bet_input: Optional[ButtonPosition] = None
    confirm_button: Optional[ButtonPosition] = None

    # Дополнительные области для Screen Reader
    hero_cards_region: Optional[Tuple[int, int, int, int]] = None
    board_region: Optional[Tuple[int, int, int, int]] = None
    pot_region: Optional[Tuple[int, int, int, int]] = None


class ButtonCalibrator:
    """Интерактивный калибратор кнопок"""

    BUTTONS_TO_CALIBRATE = [
        ("fold_button", "FOLD"),
        ("check_button", "CHECK"),
        ("call_button", "CALL"),
        ("bet_button", "BET"),
        ("raise_button", "RAISE"),
        ("all_in_button", "ALL-IN"),
        ("bet_input", "Bet Input Field"),
        ("confirm_button", "CONFIRM/OK"),
    ]

    REGIONS_TO_CALIBRATE = [
        ("hero_cards_region", "Hero Cards Area"),
        ("board_region", "Board Cards Area"),
        ("pot_region", "Pot Amount Area"),
    ]

    def __init__(self, room: str):
        self.room = room
        self.layout = TableLayout(
            room=room,
            resolution=pyautogui.size() if PYAUTOGUI_AVAILABLE else (1920, 1080)
        )
        self.click_positions: List[Tuple[int, int]] = []
        self.current_button = None
        self.waiting_for_click = False
        self.calibration_done = False

    def on_click(self, x, y, button, pressed):
        """Callback для клика мыши"""
        if pressed and self.waiting_for_click:
            self.click_positions.append((int(x), int(y)))
            self.waiting_for_click = False
            return False  # Stop listener

    def wait_for_click(self) -> Tuple[int, int]:
        """Ждать клика пользователя"""
        if not PYNPUT_AVAILABLE:
            # Fallback: ввод координат вручную
            coords = input("Enter coordinates (x,y): ").strip()
            x, y = map(int, coords.split(","))
            return (x, y)

        self.waiting_for_click = True
        self.click_positions = []

        with mouse.Listener(on_click=self.on_click) as listener:
            listener.join()

        if self.click_positions:
            return self.click_positions[0]
        return (0, 0)

    def wait_for_region(self) -> Tuple[int, int, int, int]:
        """Ждать два клика для определения региона (top-left, bottom-right)"""
        print("    Click TOP-LEFT corner...")
        x1, y1 = self.wait_for_click()
        print(f"    Got: ({x1}, {y1})")

        print("    Click BOTTOM-RIGHT corner...")
        x2, y2 = self.wait_for_click()
        print(f"    Got: ({x2}, {y2})")

        return (x1, y1, x2 - x1, y2 - y1)

    def calibrate_buttons(self):
        """Калибровка кнопок"""
        print(f"\n{'='*50}")
        print(f"Button Calibration for: {self.room}")
        print(f"{'='*50}")
        print("\nInstructions:")
        print("1. Open the poker client and sit at a table")
        print("2. Click on the CENTER of each button when prompted")
        print("3. Press Enter to skip a button if not visible")
        print()

        for attr_name, button_name in self.BUTTONS_TO_CALIBRATE:
            response = input(f"Calibrate {button_name}? [Y/n/skip]: ").strip().lower()

            if response == 'skip' or response == 's':
                print(f"  Skipped {button_name}")
                continue

            if response == 'n':
                continue

            print(f"  Click on {button_name} button...")
            x, y = self.wait_for_click()

            # Запрашиваем размер кнопки
            size_input = input(f"  Button size (width,height) [80,30]: ").strip()
            if size_input:
                w, h = map(int, size_input.split(","))
            else:
                w, h = 80, 30

            button = ButtonPosition(x=x, y=y, width=w, height=h, name=button_name)
            setattr(self.layout, attr_name, button)
            print(f"  Saved: {button_name} at ({x}, {y}) size {w}x{h}")

        print("\n" + "="*50)
        print("Region Calibration (for Screen Reader)")
        print("="*50)

        for attr_name, region_name in self.REGIONS_TO_CALIBRATE:
            response = input(f"Calibrate {region_name}? [y/N]: ").strip().lower()

            if response != 'y':
                continue

            print(f"  Defining region for {region_name}:")
            region = self.wait_for_region()
            setattr(self.layout, attr_name, region)
            print(f"  Saved: {region_name} = {region}")

        self.calibration_done = True

    def save_layout(self, output_path: Optional[str] = None):
        """Сохранить layout в файл"""
        if not output_path:
            output_dir = Path("config/layouts")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{self.room}.json"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Конвертируем в dict
        layout_dict = {
            "room": self.layout.room,
            "resolution": list(self.layout.resolution),
            "buttons": {},
            "regions": {}
        }

        for attr_name, _ in self.BUTTONS_TO_CALIBRATE:
            btn = getattr(self.layout, attr_name)
            if btn:
                layout_dict["buttons"][attr_name] = asdict(btn)

        for attr_name, _ in self.REGIONS_TO_CALIBRATE:
            region = getattr(self.layout, attr_name)
            if region:
                layout_dict["regions"][attr_name] = list(region)

        with open(output_path, 'w') as f:
            json.dump(layout_dict, f, indent=2)

        print(f"\nLayout saved to: {output_path}")
        return output_path

    def generate_code(self) -> str:
        """Генерирует Python код для table_agent/main.py"""
        code_lines = [
            f'"{self.room}": TableLayout(',
        ]

        for attr_name, _ in self.BUTTONS_TO_CALIBRATE:
            btn = getattr(self.layout, attr_name)
            if btn:
                code_lines.append(
                    f'    {attr_name}=ClickPosition({btn.x}, {btn.y}, {btn.width}, {btn.height}),'
                )

        code_lines.append('),')

        return '\n'.join(code_lines)


def test_calibration(layout_path: str):
    """Тестирует калибровку - показывает где будут клики"""
    if not PYAUTOGUI_AVAILABLE:
        print("PyAutoGUI required for testing")
        return

    with open(layout_path) as f:
        layout = json.load(f)

    print(f"\nTesting layout for: {layout['room']}")
    print("Moving mouse to each button position (not clicking)")
    print("Press Ctrl+C to stop\n")

    try:
        for name, btn in layout.get("buttons", {}).items():
            print(f"  {name}: ({btn['x']}, {btn['y']})")
            pyautogui.moveTo(btn['x'], btn['y'], duration=0.5)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTest stopped")


def main():
    parser = argparse.ArgumentParser(description="Button Calibration Utility")
    parser.add_argument("--room", required=True, help="Poker room name")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--test", help="Test existing layout file")
    parser.add_argument("--generate-code", action="store_true",
                       help="Generate Python code for main.py")

    args = parser.parse_args()

    if args.test:
        test_calibration(args.test)
        return

    if not PYNPUT_AVAILABLE and not PYAUTOGUI_AVAILABLE:
        print("ERROR: pynput or pyautogui required")
        print("Install with: pip install pynput pyautogui")
        sys.exit(1)

    calibrator = ButtonCalibrator(args.room)
    calibrator.calibrate_buttons()

    if calibrator.calibration_done:
        layout_path = calibrator.save_layout(args.output)

        if args.generate_code:
            print("\n" + "="*50)
            print("Generated code for table_agent/main.py:")
            print("="*50)
            print(calibrator.generate_code())

        # Предложить тест
        response = input("\nTest calibration? [y/N]: ").strip().lower()
        if response == 'y':
            test_calibration(str(layout_path))


if __name__ == "__main__":
    main()
