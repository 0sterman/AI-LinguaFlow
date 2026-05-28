from __future__ import annotations

import ctypes
from dataclasses import dataclass


VK_C = 0x43
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3


@dataclass
class DoubleCtrlCDetector:
    max_interval_seconds: float = 0.7
    _last_ctrl_c_at: float | None = None

    def register_key_press(self, key_name: str, ctrl_down: bool, now: float) -> bool:
        normalized = key_name.lower()
        if normalized not in {"c", "с"} or not ctrl_down:
            self._last_ctrl_c_at = None
            return False

        if self._last_ctrl_c_at is None:
            self._last_ctrl_c_at = now
            return False

        elapsed = now - self._last_ctrl_c_at
        self._last_ctrl_c_at = None
        return 0 <= elapsed <= self.max_interval_seconds

    def reset(self) -> None:
        self._last_ctrl_c_at = None


@dataclass
class CtrlCPollStateDetector:
    double_press_detector: DoubleCtrlCDetector
    _c_was_down: bool = False

    def update(self, ctrl_down: bool, c_down: bool, now: float) -> bool:
        if not ctrl_down:
            self.double_press_detector.reset()
            self._c_was_down = c_down
            return False

        c_pressed_now = c_down and not self._c_was_down
        self._c_was_down = c_down
        if not c_pressed_now:
            return False
        return self.double_press_detector.register_key_press("c", True, now)

    def reset(self) -> None:
        self.double_press_detector.reset()
        self._c_was_down = False


class WindowsKeyStateReader:
    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)

    def ctrl_down(self) -> bool:
        return any(self._key_down(key) for key in (VK_CONTROL, VK_LCONTROL, VK_RCONTROL))

    def c_down(self) -> bool:
        return self._key_down(VK_C)

    def _key_down(self, virtual_key: int) -> bool:
        return bool(self._user32.GetAsyncKeyState(virtual_key) & 0x8000)
