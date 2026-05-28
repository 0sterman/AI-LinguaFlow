from __future__ import annotations

import ctypes
import threading
import time
from dataclasses import dataclass
from typing import Callable


VK_C = 0x43
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_KEYUP = 0x0101
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012
WH_KEYBOARD_LL = 13
HC_ACTION = 0


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_ulong),
        ("scanCode", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_void_p),
        ("time", ctypes.c_ulong),
        ("pt", POINT),
    ]


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


class WindowsCtrlCHook:
    def __init__(self, on_double_ctrl_c: Callable[[], None], max_interval_seconds: float = 0.7) -> None:
        self._on_double_ctrl_c = on_double_ctrl_c
        self._detector = DoubleCtrlCDetector(max_interval_seconds=max_interval_seconds)
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._user32.SetWindowsHookExW.restype = ctypes.c_void_p
        self._user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        self._user32.CallNextHookEx.restype = ctypes.c_ssize_t
        self._user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p]
        self._user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        self._user32.PostThreadMessageW.argtypes = [ctypes.c_ulong, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p]
        self._user32.GetMessageW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
        self._user32.GetMessageW.restype = ctypes.c_int
        self._kernel32.GetModuleHandleW.restype = ctypes.c_void_p
        self._hook_handle: int | None = None
        self._thread: threading.Thread | None = None
        self._thread_id = 0
        self._c_is_down = False
        self._callback = None
        self._ready = threading.Event()
        self._last_error = 0
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._ready.clear()
            self._last_error = 0
            self._thread = threading.Thread(target=self._run, name="AI LinguaFlow hotkey", daemon=True)
            self._thread.start()
        self._ready.wait(timeout=1.5)

    def is_ready(self) -> bool:
        return bool(self._hook_handle)

    @property
    def last_error(self) -> int:
        return self._last_error

    def stop(self) -> None:
        with self._lock:
            thread_id = self._thread_id
        if thread_id:
            self._user32.PostThreadMessageW(thread_id, WM_QUIT, 0, 0)
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.5)
        with self._lock:
            self._thread = None
            self._thread_id = 0
            self._hook_handle = None
            self._callback = None
            self._c_is_down = False
            self._detector.reset()

    def _run(self) -> None:
        self._thread_id = self._kernel32.GetCurrentThreadId()
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p)
        self._callback = callback_type(self._keyboard_proc)
        self._hook_handle = self._user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._callback, None, 0)
        if not self._hook_handle:
            self._last_error = ctypes.get_last_error()
            self._ready.set()
            return
        self._ready.set()
        msg = MSG()
        try:
            while self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                self._user32.TranslateMessage(ctypes.byref(msg))
                self._user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            if self._hook_handle:
                self._user32.UnhookWindowsHookEx(self._hook_handle)

    def _keyboard_proc(self, n_code: int, w_param: int, l_param: int) -> int:
        if n_code == HC_ACTION:
            event = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if event.vkCode == VK_C:
                if w_param in {WM_KEYUP, WM_SYSKEYUP}:
                    self._c_is_down = False
                elif w_param in {WM_KEYDOWN, WM_SYSKEYDOWN} and not self._c_is_down:
                    self._c_is_down = True
                    if self._ctrl_down() and self._detector.register_key_press("c", True, time.monotonic()):
                        self._on_double_ctrl_c()
            elif event.vkCode in {VK_CONTROL, VK_LCONTROL, VK_RCONTROL} and w_param in {WM_KEYUP, WM_SYSKEYUP}:
                self._detector.reset()
        return self._user32.CallNextHookEx(self._hook_handle, n_code, w_param, l_param)

    def _ctrl_down(self) -> bool:
        return any(self._user32.GetAsyncKeyState(key) & 0x8000 for key in (VK_CONTROL, VK_LCONTROL, VK_RCONTROL))
