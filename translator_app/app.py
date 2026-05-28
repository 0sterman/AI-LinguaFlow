from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pyperclip
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QIcon, QPainter, QPixmap, QColor
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from translator_app.config import AppConfig, load_config, save_config
from translator_app.history import HistoryStore
from translator_app.hotkey import DoubleCtrlCDetector
from translator_app.i18n import t
from translator_app.languages import Language, default_target_language, get_language
from translator_app.openai_client import MissingApiKeyError, ProviderTranslator, TextTooLongError, TranslationError, provider_label
from translator_app.secure_store import ApiKeyStore
from translator_app.startup import (
    ensure_desktop_shortcut,
    is_desktop_shortcut_enabled,
    is_start_with_windows_enabled,
    set_desktop_shortcut,
    set_start_with_windows,
)
from translator_app.ui import APP_STYLESHEET, HistoryDialog, MainTranslatorWindow, SettingsDialog, TranslationPopup


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
        self.signals = AppSignals()
        self.keyboard_hook = None
        self.original_text = ""
        self.request_id = 0
        self.manual_request_id = 0
        self.pending_requests: dict[int, tuple[str, str, str, str]] = {}

        self.main_window = MainTranslatorWindow(self.config.primary_language)
        self.main_window.translateRequested.connect(self.translate_manual_text)
        self.main_window.copyRequested.connect(self.copy_manual_translation)
        self.main_window.historyRequested.connect(self.open_history)
        self.main_window.settingsRequested.connect(self.open_settings)

        self.popup = TranslationPopup(self.config.popup_width, self.config.popup_height, self.config.primary_language)
        self.popup.languageSelected.connect(self.retranslate)
        self.popup.copyRequested.connect(self.copy_translation)
        self.popup.historyRequested.connect(self.open_history)

        self.tray = QSystemTrayIcon(self._build_icon(), self.qt_app)
        self.tray.setToolTip("AI-LinguaFlow")
        self.tray.setContextMenu(self._build_menu())
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
            try:
                ensure_desktop_shortcut()
                self.config.desktop_shortcut = is_desktop_shortcut_enabled()
            except Exception:
                pass
        if not self.key_store.get_api_key(self.config.provider):
            QTimer.singleShot(350, self.open_settings)

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

        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#2f6f73"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        painter.drawText(pixmap.rect(), 0x84, "T")
        painter.end()
        return QIcon(pixmap)

    def open_main_window(self) -> None:
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def start_hotkey_listener(self) -> None:
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

    def stop_hotkey_listener(self) -> None:
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
        QTimer.singleShot(140, self.translate_clipboard)

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
        self.translate_text(text, default_target_language(text, self.config.primary_language))

    def retranslate(self, language_code: str) -> None:
        if not self.original_text.strip():
            self.popup.show_error("Сначала скопируйте текст через Ctrl+C+C")
            return
        self.translate_text(self.original_text, get_language(language_code))

    def translate_text(self, text: str, target_language: Language) -> None:
        self.request_id += 1
        current_request_id = self.request_id
        self.pending_requests[current_request_id] = (
            text,
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
                self.history_store.add(cleaned, translated, target_language.code, provider, model)
                self.signals.manualTranslationReady.emit(current_request_id, translated)

        threading.Thread(target=run, daemon=True).start()

    def on_manual_translation_ready(self, request_id: int, translated: str) -> None:
        if request_id != self.manual_request_id:
            return
        self.main_window.set_translation(translated)

    def on_manual_translation_failed(self, request_id: int, message: str, open_settings: bool) -> None:
        if request_id != self.manual_request_id:
            return
        self.main_window.set_error(message)
        if open_settings:
            QTimer.singleShot(250, self.open_settings)

    def on_translation_ready(self, request_id: int, translated: str, target_language: object) -> None:
        if request_id != self.request_id:
            self.pending_requests.pop(request_id, None)
            return
        request_context = self.pending_requests.pop(request_id, None)
        if request_context is not None:
            source_text, target_language_code, provider, model = request_context
            self.history_store.add(source_text, translated, target_language_code, provider, model)
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
            self.popup.status_label.setText("Скопировано")

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
        dialog = SettingsDialog(self.config, saved_key_status=saved_key_status)
        self.active_settings_dialog = dialog
        dialog.apiKeyCheckRequested.connect(self.check_api_key)
        dialog.apiKeyDeleteRequested.connect(self.delete_api_key)
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            self.active_settings_dialog = None
            return
        self.active_settings_dialog = None

        for provider, api_key in dialog.api_keys.items():
            if not api_key:
                continue
            try:
                self.key_store.save_api_key(provider, api_key)
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
        try:
            set_start_with_windows(self.config.autostart)
        except Exception as exc:
            QMessageBox.warning(None, "Settings", f"Не удалось изменить автозапуск: {exc}")
        try:
            set_desktop_shortcut(self.config.desktop_shortcut)
        except Exception as exc:
            QMessageBox.warning(None, "Settings", f"Не удалось изменить ярлык на рабочем столе: {exc}")
        save_config(self.config)
        target_index = self.main_window.target_language_input.findData(self.config.primary_language)
        if target_index >= 0:
            self.main_window.target_language_input.setCurrentIndex(target_index)
        self.main_window.apply_locale(self.config.primary_language)
        self.popup.apply_locale(self.config.primary_language)
        self.tray.setContextMenu(self._build_menu())

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

    def delete_api_key(self, provider: str) -> None:
        self.key_store.delete_api_key(provider)

    def quit(self) -> None:
        self.shutdown()
        self.qt_app.quit()

    def shutdown(self) -> None:
        self.stop_hotkey_listener()
        self.tray.hide()
        save_config(self.config)


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(resource_path("assets/app_icon.ico"))))
    app.setStyleSheet(APP_STYLESHEET)
    controller = TranslatorApplication(app)
    controller.open_main_window()
    app.aboutToQuit.connect(controller.shutdown)
    return app.exec()


def resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base_path / relative_path
