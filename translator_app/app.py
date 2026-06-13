from __future__ import annotations

import sys
import ctypes
import threading
import time
from pathlib import Path

import pyperclip
from PySide6.QtCore import QObject, QProcess, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QPainter, QPixmap, QColor
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from translator_app.config import AppConfig, load_config, save_config
from translator_app.history import HistoryStore
from translator_app.hotkey import (
    CtrlCPollStateDetector,
    DoubleCtrlCDetector,
    WindowsCtrlCHook,
    WindowsKeyStateReader,
)
from translator_app.i18n import t
from translator_app.languages import Language, detect_language_code, get_language, preferred_target_language
from translator_app.openai_client import MissingApiKeyError, ProviderTranslator, TextTooLongError, TranslationError, provider_label
from translator_app.platform_text import popup_shortcut
from translator_app.secure_store import ApiKeyStore
from translator_app.startup import (
    is_desktop_shortcut_enabled,
    is_start_with_windows_enabled,
    set_desktop_shortcut,
    set_start_with_windows,
)
from translator_app.ui import APP_DISPLAY_NAME, HistoryDialog, MainTranslatorWindow, SettingsDialog, TranslationPopup, app_stylesheet
from translator_app.update_checker import UpdateInfo, download_installer, fetch_required_update
from translator_app import __version__

SINGLE_INSTANCE_NAME = "OsterLinguaFlowAITranslator"
WINDOWS_APP_USER_MODEL_ID = "Oster.LinguaFlowAI.PopupTranslator"


class AppSignals(QObject):
    hotkeyTriggered = Signal()
    translationReady = Signal(int, str, object)
    translationFailed = Signal(int, str, bool)
    manualTranslationReady = Signal(int, str)
    manualTranslationFailed = Signal(int, str, bool)
    apiKeyCheckFinished = Signal(str, bool, str)


class TranslatorApplication(QObject):
    def __init__(self, qt_app: QApplication) -> None:
        super().__init__()
        self.qt_app = qt_app
        self.config = load_config()
        self.config.autostart = is_start_with_windows_enabled()
        self.key_store = ApiKeyStore()
        self.history_store = HistoryStore()
        self.detector = DoubleCtrlCDetector()
        self.hotkey_listener: WindowsCtrlCHook | None = None
        self.hotkey_poll_timer: QTimer | None = None
        self.hotkey_poll_detector = CtrlCPollStateDetector(DoubleCtrlCDetector())
        self.key_state_reader: WindowsKeyStateReader | None = None
        self.last_ctrl_down_at = 0.0
        self.last_hotkey_at = 0.0
        self.mac_hotkey_listener = None
        self.signals = AppSignals()
        self.keyboard_hook = None
        self.original_text = ""
        self.request_id = 0
        self.manual_request_id = 0
        self.pending_requests: dict[int, tuple[str, str, str, str]] = {}
        self.raise_main_window_on_next_manual_result = False

        self.main_window = MainTranslatorWindow(self.config.primary_language, self.config.target_language)
        self.main_window.set_logo_path(str(resource_path("assets/app_icon.png")))
        self.main_window.translateRequested.connect(self.translate_manual_text)
        self.main_window.copyRequested.connect(self.copy_manual_translation)
        self.main_window.historyRequested.connect(self.open_history)
        self.main_window.settingsRequested.connect(self.open_settings)
        self.main_window.targetLanguageChanged.connect(self.save_target_language)

        self.popup = TranslationPopup(self.config.popup_width, self.config.popup_height, self.config.primary_language)
        self.popup.languageSelected.connect(self.retranslate)
        self.popup.copyRequested.connect(self.copy_translation)
        self.popup.historyRequested.connect(self.open_history)

        self.tray = QSystemTrayIcon(self._build_icon(), self.qt_app)
        self.tray.setToolTip(APP_DISPLAY_NAME)
        self.tray.setContextMenu(self._build_menu())
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

        self.signals.hotkeyTriggered.connect(self.on_hotkey_triggered)
        self.signals.translationReady.connect(self.on_translation_ready)
        self.signals.translationFailed.connect(self.on_translation_failed)
        self.signals.manualTranslationReady.connect(self.on_manual_translation_ready)
        self.signals.manualTranslationFailed.connect(self.on_manual_translation_failed)
        self.signals.apiKeyCheckFinished.connect(self.on_api_key_check_finished)

        if self.config.enabled:
            self.start_hotkey_listener()
        if self.config.desktop_shortcut:
            self.config.desktop_shortcut = is_desktop_shortcut_enabled()
        self.missing_api_key_notice_shown = False

    def _hotkey_permission_message(self) -> str:
        if sys.platform == "darwin":
            return (
                "Не удалось включить macOS hotkey listener. "
                "Разрешите LinguaFlow AI доступ в System Settings -> Privacy & Security -> Accessibility."
            )
        return "Не удалось включить Windows hotkey listener."

    def _build_menu(self) -> QMenu:
        menu = QMenu()

        self.enabled_action = QAction(t(self.config.primary_language, "enabled"), self)
        self.enabled_action.setCheckable(True)
        self.enabled_action.setChecked(self.config.enabled)
        self.enabled_action.triggered.connect(self.set_enabled)
        menu.addAction(self.enabled_action)

        settings_action = QAction(t(self.config.primary_language, "settings"), self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        open_action = QAction(t(self.config.primary_language, "open_translator"), self)
        open_action.triggered.connect(self.open_main_window)
        menu.addAction(open_action)

        history_action = QAction(t(self.config.primary_language, "history"), self)
        history_action.triggered.connect(self.open_history)
        menu.addAction(history_action)

        menu.addSeparator()

        quit_action = QAction(t(self.config.primary_language, "quit"), self)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        return menu

    def _build_icon(self) -> QIcon:
        icon_path = resource_path("assets/app_icon.ico")
        if icon_path.exists():
            return QIcon(str(icon_path))
        png_icon_path = resource_path("assets/app_icon.png")
        if png_icon_path.exists():
            return QIcon(str(png_icon_path))

        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#2f6f73"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        painter.drawText(pixmap.rect(), 0x84, "T")
        painter.end()
        return QIcon(pixmap)

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.open_main_window()

    def open_main_window(self, stay_on_top: bool = False) -> None:
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()
        if stay_on_top:
            self._force_main_window_to_front()
            QTimer.singleShot(80, self._force_main_window_to_front)
            QTimer.singleShot(220, self._force_main_window_to_front)

    def release_main_window_top_hint(self) -> None:
        return

    def _force_main_window_to_front(self) -> None:
        if sys.platform == "darwin":
            try:
                self.main_window.raise_()
                self.main_window.activateWindow()
                QProcess.startDetached(
                    "osascript",
                    [
                        "-e",
                        (
                            'tell application "System Events" to set frontmost of '
                            f"(first process whose unix id is {QApplication.applicationPid()}) to true"
                        ),
                    ],
                )
            except Exception:
                pass
            return
        if not sys.platform.startswith("win"):
            return
        try:
            hwnd = int(self.main_window.winId())
            if not hwnd:
                return
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            sw_restore = 9
            hwnd_topmost = -1
            hwnd_notopmost = -2
            swp_nosize = 0x0001
            swp_nomove = 0x0002
            swp_showwindow = 0x0040
            flags = swp_nomove | swp_nosize | swp_showwindow
            current_thread = kernel32.GetCurrentThreadId()
            foreground_hwnd = user32.GetForegroundWindow()
            foreground_thread = user32.GetWindowThreadProcessId(foreground_hwnd, None) if foreground_hwnd else 0
            target_thread = user32.GetWindowThreadProcessId(hwnd, None)
            attached_threads: list[int] = []
            for thread_id in {foreground_thread, target_thread}:
                if thread_id and thread_id != current_thread:
                    if user32.AttachThreadInput(current_thread, thread_id, True):
                        attached_threads.append(thread_id)
            try:
                user32.ShowWindow(hwnd, sw_restore)
                user32.SetWindowPos(hwnd, hwnd_topmost, 0, 0, 0, 0, flags)
                user32.SetWindowPos(hwnd, hwnd_notopmost, 0, 0, 0, 0, flags)
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
                user32.SetActiveWindow(hwnd)
                user32.SetFocus(hwnd)
                self.main_window.raise_()
                self.main_window.activateWindow()
            finally:
                for thread_id in attached_threads:
                    user32.AttachThreadInput(current_thread, thread_id, False)
        except Exception:
            return

    def save_target_language(self, language_code: str) -> None:
        if language_code not in {"ru", "en", "de", "es", "zh"}:
            return
        self.config.target_language = language_code
        save_config(self.config)

    def start_hotkey_listener(self) -> None:
        if sys.platform.startswith("win"):
            if self.hotkey_listener is None:
                try:
                    self.hotkey_listener = WindowsCtrlCHook(lambda: self.signals.hotkeyTriggered.emit())
                    self.hotkey_listener.start()
                except Exception:
                    self.hotkey_listener = None
            if self.hotkey_poll_timer is None:
                try:
                    self.key_state_reader = WindowsKeyStateReader()
                    self.hotkey_poll_detector.reset()
                    self.hotkey_poll_timer = QTimer(self)
                    self.hotkey_poll_timer.setInterval(8)
                    self.hotkey_poll_timer.timeout.connect(self.poll_hotkey_state)
                    self.hotkey_poll_timer.start()
                except Exception:
                    self.key_state_reader = None
                    self.hotkey_poll_timer = None
            if (
                self.hotkey_listener is None
                and self.hotkey_poll_timer is None
            ):
                self.popup.show_error(self._hotkey_permission_message())
            return

        if sys.platform == "darwin":
            if self.mac_hotkey_listener is not None:
                return
            try:
                from translator_app.hotkey_macos import MacCommandCHotkeyListener

                self.mac_hotkey_listener = MacCommandCHotkeyListener(lambda: self.signals.hotkeyTriggered.emit())
                self.mac_hotkey_listener.start()
            except ImportError:
                self.mac_hotkey_listener = None
                self.popup.show_error("Не установлен модуль pynput. Установите macOS-зависимости из requirements-macos.txt.")
            except Exception:
                self.mac_hotkey_listener = None
                self.popup.show_error(self._hotkey_permission_message())
            return

        try:
            import keyboard
        except ImportError:
            self.popup.show_error("Не установлен модуль keyboard. Установите зависимости из requirements.txt.")
            return

        if self.keyboard_hook is not None:
            return

        def on_press(event: object) -> None:
            name = getattr(event, "name", "")
            ctrl_down = keyboard.is_pressed("ctrl")
            if self.detector.register_key_press(name, ctrl_down, time.monotonic()):
                self.signals.hotkeyTriggered.emit()

        try:
            self.keyboard_hook = keyboard.on_press(on_press)
        except Exception:
            self.keyboard_hook = None
            self.popup.show_error("Не удалось включить глобальный хоткей. Попробуйте запустить приложение от администратора.")

    def poll_hotkey_state(self) -> None:
        if self.key_state_reader is None:
            return
        ctrl_down = self.key_state_reader.ctrl_down()
        if ctrl_down:
            self.last_ctrl_down_at = time.monotonic()
        if self.hotkey_poll_detector.update(
            ctrl_down,
            self.key_state_reader.c_down(),
            time.monotonic(),
        ):
            self.signals.hotkeyTriggered.emit()

    def stop_hotkey_listener(self) -> None:
        if self.mac_hotkey_listener is not None:
            try:
                self.mac_hotkey_listener.stop()
            except Exception:
                pass
            self.mac_hotkey_listener = None
        if self.hotkey_listener is not None:
            self.hotkey_listener.stop()
            self.hotkey_listener = None
        if self.hotkey_poll_timer is not None:
            self.hotkey_poll_timer.stop()
            self.hotkey_poll_timer.deleteLater()
            self.hotkey_poll_timer = None
        self.key_state_reader = None
        self.hotkey_poll_detector.reset()
        self.detector.reset()
        if self.keyboard_hook is None:
            return
        try:
            import keyboard

            keyboard.unhook(self.keyboard_hook)
        except Exception:
            pass
        self.keyboard_hook = None
        self.detector.reset()

    def set_enabled(self, enabled: bool) -> None:
        self.config.enabled = enabled
        save_config(self.config)
        if enabled:
            self.start_hotkey_listener()
        else:
            self.stop_hotkey_listener()

    def on_hotkey_triggered(self) -> None:
        if not self.config.enabled:
            return
        now = time.monotonic()
        if now - self.last_hotkey_at < 0.5:
            return
        self.last_hotkey_at = now
        if sys.platform == "darwin":
            self.copy_selection_on_macos()
        QTimer.singleShot(320, self.open_clipboard_in_main_window)

    def copy_selection_on_macos(self) -> None:
        try:
            QProcess.startDetached(
                "osascript",
                ["-e", 'tell application "System Events" to keystroke "c" using command down'],
            )
        except Exception:
            pass

    def open_clipboard_in_main_window(self) -> None:
        try:
            text = pyperclip.paste()
        except pyperclip.PyperclipException:
            self.open_main_window(stay_on_top=True)
            self.main_window.set_error("Не удалось прочитать буфер обмена")
            return

        if not text or not text.strip():
            self.open_main_window(stay_on_top=True)
            self.main_window.set_error(t(self.config.primary_language, "no_text"))
            return

        self.original_text = text
        target_language = preferred_target_language(text, self.config.primary_language, self.config.target_language)
        self.raise_main_window_on_next_manual_result = True
        self.main_window.load_source_text(text, target_language.code)
        self.open_main_window(stay_on_top=True)

    def translate_clipboard(self) -> None:
        try:
            text = pyperclip.paste()
        except pyperclip.PyperclipException:
            self.popup.show_error("Не удалось прочитать буфер обмена")
            return

        if not text or not text.strip():
            self.popup.show_error(t(self.config.primary_language, "no_text"))
            return

        self.original_text = text
        target_language = preferred_target_language(text, self.config.primary_language, self.config.target_language)
        self.translate_text(text, target_language)

    def retranslate(self, language_code: str) -> None:
        if not self.original_text.strip():
            self.popup.show_error(f"Сначала скопируйте текст через {popup_shortcut()}")
            return
        self.save_target_language(language_code)
        self.translate_text(self.original_text, get_language(language_code))

    def translate_text(self, text: str, target_language: Language) -> None:
        self.request_id += 1
        current_request_id = self.request_id
        self.pending_requests[current_request_id] = (
            text,
            detect_language_code(text) or "auto",
            target_language.code,
            self.config.provider,
            self.config.model_for_provider(),
        )
        self.popup.show_loading(target_language)

        def run() -> None:
            try:
                translator = ProviderTranslator(
                    self.config.provider,
                    self.key_store.get_api_key(self.config.provider),
                    model=self.config.model_for_provider(),
                )
                translated = translator.translate(text, target_language)
            except MissingApiKeyError:
                provider = provider_label(self.config.provider)
                self.signals.translationFailed.emit(current_request_id, f"Нужен {provider} API key. Открою настройки.", True)
            except TextTooLongError as exc:
                self.signals.translationFailed.emit(current_request_id, str(exc), False)
            except TranslationError as exc:
                self.signals.translationFailed.emit(current_request_id, str(exc), False)
            except Exception:
                self.signals.translationFailed.emit(current_request_id, "Неожиданная ошибка перевода", False)
            else:
                self.signals.translationReady.emit(current_request_id, translated, target_language)

        threading.Thread(target=run, daemon=True).start()

    def translate_manual_text(self, source_language_code: str, target_language_code: str, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            self.main_window.set_error(t(self.config.primary_language, "no_text"))
            return

        target_language = get_language(target_language_code)
        source_language = None if source_language_code == "auto" else get_language(source_language_code)
        history_source_language_code = source_language.code if source_language else detect_language_code(cleaned) or "auto"
        self.manual_request_id += 1
        current_request_id = self.manual_request_id
        provider = self.config.provider
        model = self.config.model_for_provider()
        self.main_window.set_loading()

        def run() -> None:
            try:
                translator = ProviderTranslator(
                    provider,
                    self.key_store.get_api_key(provider),
                    model=model,
                )
                translated = translator.translate(cleaned, target_language, source_language)
            except MissingApiKeyError:
                provider_name = provider_label(provider)
                self.signals.manualTranslationFailed.emit(current_request_id, f"Нужен {provider_name} API key. Открою настройки.", True)
            except TextTooLongError as exc:
                self.signals.manualTranslationFailed.emit(current_request_id, str(exc), False)
            except TranslationError as exc:
                self.signals.manualTranslationFailed.emit(current_request_id, str(exc), False)
            except Exception:
                self.signals.manualTranslationFailed.emit(current_request_id, "Неожиданная ошибка перевода", False)
            else:
                self.history_store.add(
                    cleaned,
                    translated,
                    target_language.code,
                    provider,
                    model,
                    source_language=history_source_language_code,
                )
                self.signals.manualTranslationReady.emit(current_request_id, translated)

        threading.Thread(target=run, daemon=True).start()

    def on_manual_translation_ready(self, request_id: int, translated: str) -> None:
        if request_id != self.manual_request_id:
            return
        self.main_window.set_translation(translated)
        if self.raise_main_window_on_next_manual_result:
            self.raise_main_window_on_next_manual_result = False
            self.open_main_window(stay_on_top=True)

    def on_manual_translation_failed(self, request_id: int, message: str, open_settings: bool) -> None:
        if request_id != self.manual_request_id:
            return
        self.main_window.set_error(message)
        if self.raise_main_window_on_next_manual_result:
            self.raise_main_window_on_next_manual_result = False
            self.open_main_window(stay_on_top=True)
        if open_settings:
            QTimer.singleShot(250, self.open_settings)

    def on_translation_ready(self, request_id: int, translated: str, target_language: object) -> None:
        if request_id != self.request_id:
            self.pending_requests.pop(request_id, None)
            return
        request_context = self.pending_requests.pop(request_id, None)
        if request_context is not None:
            source_text, source_language_code, target_language_code, provider, model = request_context
            self.history_store.add(
                source_text,
                translated,
                target_language_code,
                provider,
                model,
                source_language=source_language_code,
            )
        self.popup.show_translation(translated, target_language)  # type: ignore[arg-type]

    def on_translation_failed(self, request_id: int, message: str, open_settings: bool) -> None:
        if request_id != self.request_id:
            self.pending_requests.pop(request_id, None)
            return
        self.pending_requests.pop(request_id, None)
        self.popup.show_error(message)
        if open_settings:
            QTimer.singleShot(250, self.open_settings)

    def copy_translation(self) -> None:
        text = self.popup.current_text()
        if text.strip():
            pyperclip.copy(text)
            self.popup.status_label.setText(t(self.config.primary_language, "copied"))

    def copy_manual_translation(self) -> None:
        text = self.main_window.current_translation()
        if text.strip():
            pyperclip.copy(text)

    def open_history(self) -> None:
        dialog = HistoryDialog(self.history_store.recent(), self.config.primary_language)
        dialog.filtersChanged.connect(lambda query, date_from, date_to: self.filter_history(dialog, query, date_from, date_to))
        dialog.copy_source_button.clicked.connect(
            lambda: self.copy_history_text(dialog, copy_translation=False)
        )
        dialog.copy_translation_button.clicked.connect(
            lambda: self.copy_history_text(dialog, copy_translation=True)
        )
        dialog.clear_button.clicked.connect(lambda: self.clear_history(dialog))
        dialog.exec()

    def filter_history(
        self,
        dialog: HistoryDialog,
        query: str,
        date_from: str | None,
        date_to: str | None,
    ) -> None:
        dialog.set_records(self.history_store.search(query=query, date_from=date_from, date_to=date_to))

    def copy_history_text(self, dialog: HistoryDialog, copy_translation: bool) -> None:
        record = dialog.selected_record()
        if record is None:
            return
        pyperclip.copy(record.translated_text if copy_translation else record.source_text)

    def clear_history(self, dialog: HistoryDialog) -> None:
        answer = QMessageBox.question(
            dialog,
            "Очистить историю",
            "Удалить всю локальную историю переводов? Это действие нельзя отменить.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.history_store.clear()
        dialog.accept()

    def open_settings(self) -> None:
        saved_key_status = {
            "openai": bool(self.key_store.get_api_key("openai")),
            "google": bool(self.key_store.get_api_key("google")),
            "anthropic": bool(self.key_store.get_api_key("anthropic")),
        }
        key_valid_status = {
            "openai": self.config.key_status_for_provider("openai"),
            "google": self.config.key_status_for_provider("google"),
            "anthropic": self.config.key_status_for_provider("anthropic"),
        }
        dialog = SettingsDialog(self.config, saved_key_status=saved_key_status, key_valid_status=key_valid_status)
        self.active_settings_dialog = dialog
        dialog.apiKeyCheckRequested.connect(self.check_api_key)
        dialog.apiKeyDeleteRequested.connect(self.delete_api_key)
        dialog.applyRequested.connect(lambda: self.apply_settings(dialog, close_dialog=False))
        for provider, has_key in saved_key_status.items():
            if has_key and key_valid_status.get(provider) is not True:
                dialog.update_api_key_status(provider, "checking")
                QTimer.singleShot(
                    150,
                    lambda provider_name=provider: self.check_api_key(
                        provider_name,
                        "",
                        dialog.models[provider_name],
                    ),
                )
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            self.active_settings_dialog = None
            return
        self.active_settings_dialog = None
        self.apply_settings(dialog, close_dialog=True)

    def apply_settings(self, dialog: SettingsDialog, close_dialog: bool) -> None:
        for provider, api_key in dialog.api_keys.items():
            if not api_key:
                continue
            try:
                self.key_store.save_api_key(provider, api_key)
                self.config.set_key_status_for_provider(provider, dialog.key_valid_status.get(provider))
            except Exception as exc:
                QMessageBox.warning(None, "Settings", f"Не удалось сохранить {provider_label(provider)} API key: {exc}")
                return

        self.config.provider = dialog.provider
        self.config.primary_language = dialog.primary_language
        self.config.openai_model = dialog.models["openai"]
        self.config.google_model = dialog.models["google"]
        self.config.anthropic_model = dialog.models["anthropic"]
        self.config.autostart = dialog.autostart
        self.config.desktop_shortcut = dialog.desktop_shortcut
        self.config.theme = dialog.theme
        try:
            set_start_with_windows(self.config.autostart)
        except Exception as exc:
            QMessageBox.warning(None, "Settings", f"Не удалось изменить автозапуск: {exc}")
        try:
            set_desktop_shortcut(self.config.desktop_shortcut)
        except Exception as exc:
            QMessageBox.warning(None, "Settings", f"Не удалось изменить ярлык на рабочем столе: {exc}")
        save_config(self.config)
        self.main_window.apply_locale(self.config.primary_language)
        self.popup.apply_locale(self.config.primary_language)
        self.tray.setContextMenu(self._build_menu())
        self.qt_app.setStyleSheet(app_stylesheet(self.resolved_theme()))
        if close_dialog:
            return

    def check_api_key(self, provider: str, api_key: str, model: str) -> None:
        key_to_check = api_key.strip() or self.key_store.get_api_key(provider)
        if not key_to_check:
            self.signals.apiKeyCheckFinished.emit(provider, False, "API key is missing")
            return

        def run() -> None:
            try:
                translator = ProviderTranslator(provider, key_to_check, model=model, timeout_seconds=20)
                translator.translate("Hello", get_language("ru"))
            except Exception as exc:
                self.signals.apiKeyCheckFinished.emit(provider, False, str(exc))
            else:
                self.signals.apiKeyCheckFinished.emit(provider, True, "")

        threading.Thread(target=run, daemon=True).start()

    def on_api_key_check_finished(self, provider: str, is_valid: bool, message: str) -> None:
        dialog = getattr(self, "active_settings_dialog", None)
        if dialog is None:
            return
        dialog.update_api_key_status(provider, "valid" if is_valid else "invalid", message or None)
        if dialog.api_keys.get(provider) or self.key_store.get_api_key(provider):
            self.config.set_key_status_for_provider(provider, is_valid)
            save_config(self.config)

    def delete_api_key(self, provider: str) -> None:
        self.key_store.delete_api_key(provider)
        self.config.set_key_status_for_provider(provider, False)
        save_config(self.config)

    def quit(self) -> None:
        self.shutdown()
        self.qt_app.quit()

    def shutdown(self) -> None:
        self.stop_hotkey_listener()
        self.tray.hide()
        save_config(self.config)

    def resolved_theme(self) -> str:
        return resolve_theme(self.config)


def main() -> int:
    set_windows_app_user_model_id()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationDisplayName("")
    app.setApplicationName(APP_DISPLAY_NAME)
    icon = QIcon(str(resource_path("assets/app_icon.ico")))
    if icon.isNull():
        icon = QIcon(str(resource_path("assets/app_icon.png")))
    app.setWindowIcon(icon)
    single_instance_server = create_single_instance_server()
    if single_instance_server is None:
        return 0
    update = fetch_required_update(__version__) if getattr(sys, "frozen", False) else None
    if update is not None:
        return show_required_update(app, update)
    config = load_config()
    app.setStyleSheet(app_stylesheet(resolve_theme(config)))
    controller = TranslatorApplication(app)
    single_instance_server.newConnection.connect(lambda: handle_second_instance(single_instance_server, controller))
    controller.open_main_window()
    app.aboutToQuit.connect(controller.shutdown)
    return app.exec()


def create_single_instance_server() -> QLocalServer | None:
    probe = QLocalSocket()
    probe.connectToServer(SINGLE_INSTANCE_NAME)
    if probe.waitForConnected(250):
        probe.write(b"show")
        probe.flush()
        probe.waitForBytesWritten(250)
        probe.disconnectFromServer()
        return None

    QLocalServer.removeServer(SINGLE_INSTANCE_NAME)
    server = QLocalServer()
    if not server.listen(SINGLE_INSTANCE_NAME):
        return None
    return server


def handle_second_instance(server: QLocalServer, controller: TranslatorApplication) -> None:
    while server.hasPendingConnections():
        socket = server.nextPendingConnection()
        if socket is not None:
            socket.readAll()
            socket.disconnectFromServer()
    controller.open_main_window(stay_on_top=True)


def resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base_path / relative_path


def resolve_theme(config: AppConfig) -> str:
    if config.theme in {"dark", "light"}:
        return config.theme
    if sys.platform != "win32":
        return "dark"
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            apps_use_light_theme, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if int(apps_use_light_theme) else "dark"
    except Exception:
        return "dark"


def show_required_update(app: QApplication, update: UpdateInfo) -> int:
    answer = QMessageBox.warning(
        None,
        "LinguaFlow AI update required",
        (
            f"This LinguaFlow AI version is outdated.\n\n"
            f"Installed version: {__version__}\n"
            f"Required version: {update.version}\n\n"
            "The app will download the newest installer and open the release page."
        ),
        QMessageBox.StandardButton.Ok,
    )
    if answer == QMessageBox.StandardButton.Ok:
        QDesktopServices.openUrl(QUrl(update.release_url))
        try:
            QMessageBox.information(
                None,
                "LinguaFlow AI update",
                "The release page has been opened. The installer download will start now.",
            )
            installer_path = download_installer(update)
            QProcess.startDetached(str(installer_path), [])
        except Exception:
            QMessageBox.warning(
                None,
                "LinguaFlow AI update",
                "Could not download the installer automatically. Please use the opened GitHub release page.",
            )
    return 0


def set_windows_app_user_model_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_USER_MODEL_ID)
    except Exception:
        pass
