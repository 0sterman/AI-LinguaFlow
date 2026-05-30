from __future__ import annotations

import threading
import time
from collections.abc import Callable

from translator_app.hotkey import DoubleCtrlCDetector


class MacCommandCHotkeyListener:
    def __init__(self, on_trigger: Callable[[], None]) -> None:
        self._on_trigger = on_trigger
        self._detector = DoubleCtrlCDetector()
        self._listener = None
        self._modifier_down = False
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._listener is not None:
            return
        from pynput import keyboard

        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None
        self._detector.reset()
        self._modifier_down = False

    def _on_press(self, key: object) -> None:
        if self._is_supported_modifier_key(key):
            with self._lock:
                self._modifier_down = True
            return
        if not self._is_c_key(key):
            return
        with self._lock:
            modifier_down = self._modifier_down
        if self._detector.register_key_press("c", modifier_down, time.monotonic()):
            self._on_trigger()

    def _on_release(self, key: object) -> None:
        if self._is_supported_modifier_key(key):
            with self._lock:
                self._modifier_down = False
            self._detector.reset()

    @staticmethod
    def _is_supported_modifier_key(key: object) -> bool:
        name = str(key).lower()
        return name in {"key.cmd", "key.cmd_l", "key.cmd_r", "key.ctrl", "key.ctrl_l", "key.ctrl_r"}

    @staticmethod
    def _is_c_key(key: object) -> bool:
        char = getattr(key, "char", None)
        return isinstance(char, str) and char.lower() == "c"
