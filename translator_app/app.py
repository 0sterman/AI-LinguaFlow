from __future__ import annotations

import sys
import threading
import time

import pyperclip
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QIcon, QPainter, QPixmap, QColor
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from translator_app.config import AppConfig, load_config, save_config
from translator_app.history import HistoryStore
from translator_app.hotkey import DoubleCtrlCDetector
from translator_app.languages import Language, default_target_language, get_language
from translator_app.openai_client import MissingApiKeyError, ProviderTranslator, TextTooLongError, TranslationError, provider_label
from translator_app.secure_store import ApiKeyStore
from translator_app.startup import is_start_with_windows_enabled, set_start_with_windows
from translator_app.ui import HistoryDialog, SettingsDialog, TranslationPopup


class AppSignals(QObject):
    hotkeyTriggered = Signal()
    translationReady = Signal(int, str, object)
    translationFailed = Signal(int, str, bool)


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
        self.pending_requests: dict[int, tuple[str, str, str, str]] = {}

        self.popup = TranslationPopup(self.config.popup_width, self.config.popup_height)
        self.popup.languageSelected.connect(self.retranslate)
        self.popup.copyRequested.connect(self.copy_translation)
        self.popup.historyRequested.connect(self.open_history)

        self.tray = QSystemTrayIcon(self._build_icon(), self.qt_app)
        self.tray.setToolTip("Windows Translator")
        self.tray.setContextMenu(self._build_menu())
        self.tray.show()

        self.signals.hotkeyTriggered.connect(self.on_hotkey_triggered)
        self.signals.translationReady.connect(self.on_translation_ready)
        self.signals.translationFailed.connect(self.on_translation_failed)

        if self.config.enabled:
            self.start_hotkey_listener()
        if not self.key_store.get_api_key(self.config.provider):
            QTimer.singleShot(350, self.open_settings)

    def _build_menu(self) -> QMenu:
        menu = QMenu()

        self.enabled_action = QAction("Enabled", self)
        self.enabled_action.setCheckable(True)
        self.enabled_action.setChecked(self.config.enabled)
        self.enabled_action.triggered.connect(self.set_enabled)
        menu.addAction(self.enabled_action)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        history_action = QAction("История", self)
        history_action.triggered.connect(self.open_history)
        menu.addAction(history_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        return menu

    def _build_icon(self) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#2f6f73"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        painter.drawText(pixmap.rect(), 0x84, "T")
        painter.end()
        return QIcon(pixmap)

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
            self.popup.show_error("Нет текста для перевода")
            return

        self.original_text = text
        self.translate_text(text, default_target_language(text))

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

    def open_history(self) -> None:
        dialog = HistoryDialog(self.history_store.recent())
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
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            return

        for provider, api_key in dialog.api_keys.items():
            if not api_key:
                continue
            try:
                self.key_store.save_api_key(provider, api_key)
            except Exception as exc:
                QMessageBox.warning(None, "Settings", f"Не удалось сохранить {provider_label(provider)} API key: {exc}")
                return

        self.config.provider = dialog.provider
        self.config.openai_model = dialog.models["openai"]
        self.config.google_model = dialog.models["google"]
        self.config.anthropic_model = dialog.models["anthropic"]
        self.config.autostart = dialog.autostart
        try:
            set_start_with_windows(self.config.autostart)
        except Exception as exc:
            QMessageBox.warning(None, "Settings", f"Не удалось изменить автозапуск: {exc}")
        save_config(self.config)

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
    controller = TranslatorApplication(app)
    app.aboutToQuit.connect(controller.shutdown)
    return app.exec()
