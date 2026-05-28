from __future__ import annotations

from dataclasses import dataclass


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
