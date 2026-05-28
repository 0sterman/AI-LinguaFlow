from __future__ import annotations

from PySide6.QtCore import QDate, Qt, Signal
import ctypes

from PySide6.QtGui import QGuiApplication, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from translator_app.config import AppConfig, DEFAULT_MODELS, MODEL_OPTIONS
from translator_app.history import HistoryRecord
from translator_app.i18n import t
from translator_app.languages import LANGUAGES, Language


PROVIDERS = (
    ("openai", "OpenAI"),
    ("google", "Google Gemini"),
    ("anthropic", "Anthropic Claude"),
)


def provider_label_for_ui(provider: str) -> str:
    for provider_code, label in PROVIDERS:
        if provider_code == provider:
            return label
    return provider

MODEL_INFO = """Рекомендация для переводчика:

OpenAI: gpt-5-mini
Хороший баланс качества, скорости и цены для коротких переводов. Если экономия важнее качества, можно попробовать gpt-5-nano, gpt-4.1-mini или gpt-4.1-nano.

Google: gemini-2.5-flash-lite
Самый быстрый и экономичный вариант Gemini для массовых коротких задач. Для чуть лучшего качества можно поставить gemini-2.5-flash.

Anthropic: claude-3-5-haiku-latest
Быстрый и недорогой Claude для простых переводов. Sonnet обычно качественнее, но дороже и чаще избыточен для всплывающего переводчика.

Мой строгий совет: начните с OpenAI gpt-5-mini или Google gemini-2.5-flash-lite. Не ставьте самые дорогие модели для перевода выделенного текста, это обычно лишняя трата."""

APP_DISPLAY_NAME = "AI LinguaFlow"
VK_RCONTROL = 0xA3


def is_right_ctrl_down() -> bool:
    if not hasattr(ctypes, "windll"):
        return False
    return bool(ctypes.windll.user32.GetAsyncKeyState(VK_RCONTROL) & 0x8000)


def app_stylesheet(theme: str = "dark") -> str:
    if theme == "light":
        return LIGHT_STYLESHEET
    return DARK_STYLESHEET


DARK_STYLESHEET = """
QWidget {
    background: #0f131a;
    color: #eef3f8;
    font-family: "Segoe UI Variable", "Segoe UI";
    font-size: 13px;
}
QDialog {
    background: #0f131a;
}
QLabel {
    color: #d7dee8;
    background: transparent;
}
QLabel#AppTitle {
    color: #f7fbff;
    font-size: 15px;
    font-weight: 650;
}
QLabel#HeroTitle {
    color: #f7fbff;
    font-size: 24px;
    font-weight: 700;
}
QLabel#HeroSubtitle {
    color: #9caaba;
    font-size: 13px;
}
QLabel#SectionLabel {
    color: #8fd8ff;
    font-size: 12px;
    font-weight: 600;
}
QLabel#StatusLabel {
    color: #9caaba;
    font-size: 12px;
}
QLabel#KeyStatusOk {
    color: #5ef0a5;
    font-size: 18px;
    font-weight: 800;
}
QLabel#KeyStatusBad {
    color: #ff6b7a;
    font-size: 18px;
    font-weight: 800;
}
QLabel#KeyStatusNeutral {
    color: #8fd8ff;
    font-size: 18px;
    font-weight: 800;
}
QTextEdit, QLineEdit, QComboBox, QDateEdit, QListWidget {
    background: #151b24;
    border: 1px solid #2b3545;
    border-radius: 8px;
    color: #f2f6fb;
    padding: 7px 9px;
    selection-background-color: #2f86c8;
    selection-color: #ffffff;
}
QTextEdit {
    font-size: 14px;
}
QTextEdit:focus, QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QListWidget:focus {
    border: 1px solid #60c6ff;
}
QComboBox::drop-down, QDateEdit::drop-down {
    width: 24px;
    border: 0;
}
QTabWidget::pane {
    border: 1px solid #252f3f;
    border-radius: 8px;
    background: #111722;
    top: -1px;
}
QTabBar::tab {
    background: #151b24;
    border: 1px solid #252f3f;
    color: #aab7c7;
    padding: 8px 14px;
    min-width: 72px;
}
QTabBar::tab:selected {
    background: #1c2634;
    color: #ffffff;
    border-bottom-color: #60c6ff;
}
QPushButton {
    background: #1d2632;
    border: 1px solid #344154;
    border-radius: 8px;
    color: #eef3f8;
    padding: 5px 11px;
    min-height: 20px;
    font-weight: 650;
}
QPushButton:hover {
    background: #263244;
    border-color: #4f8fb6;
}
QPushButton:pressed {
    background: #18202b;
}
QPushButton:checked {
    background: #1e78ad;
    border-color: #65cfff;
    color: #ffffff;
}
QPushButton#HistoryButton {
    background: #132534;
    border: 1px solid #4bb8ed;
    color: #dff6ff;
    font-weight: 650;
}
QPushButton#HistoryButton:hover {
    background: #183247;
}
QPushButton#InfoButton {
    border-radius: 14px;
    border: 1px solid #74d2ff;
    background: #1f78ad;
    color: #ffffff;
    font-size: 16px;
    font-weight: 800;
    padding: 0;
    min-width: 28px;
    min-height: 28px;
}
QPushButton#InfoButton:hover {
    background: #2a91cf;
    border-color: #a4e5ff;
}
QPushButton#PrimaryButton {
    background: #1e78ad;
    border: 1px solid #65cfff;
    color: #ffffff;
    font-weight: 650;
}
QPushButton#PrimaryButton:hover {
    background: #2588c3;
}
QCheckBox {
    spacing: 8px;
    color: #d7dee8;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1px solid #526174;
    background: #151b24;
}
QCheckBox::indicator:checked {
    background: #1e78ad;
    border: 1px solid #65cfff;
}
QListWidget::item {
    border-radius: 7px;
    padding: 8px;
    margin: 2px;
}
QListWidget::item:selected {
    background: #1b415a;
    color: #ffffff;
}
QSplitter::handle {
    background: #202938;
}
QMenu {
    background: #121821;
    border: 1px solid #303b4d;
    color: #eef3f8;
}
QMenu::item {
    padding: 7px 28px 7px 20px;
}
QMenu::item:selected {
    background: #1b415a;
}
"""

LIGHT_STYLESHEET = DARK_STYLESHEET.replace("#0f131a", "#f6f8fb").replace("#eef3f8", "#16202c").replace("#d7dee8", "#263241").replace("#f7fbff", "#101720").replace("#9caaba", "#536173").replace("#151b24", "#ffffff").replace("#2b3545", "#cfd8e5").replace("#f2f6fb", "#111827").replace("#60c6ff", "#1686c4").replace("#111722", "#ffffff").replace("#252f3f", "#d8e0eb").replace("#1c2634", "#eaf4fb").replace("#aab7c7", "#46566a").replace("#1d2632", "#edf2f7").replace("#344154", "#c6d0dd").replace("#263244", "#e3edf7").replace("#4f8fb6", "#4a9eca").replace("#18202b", "#dce7f2").replace("#121821", "#ffffff").replace("#303b4d", "#cad5e2").replace("#1b415a", "#d8eefc")
APP_STYLESHEET = DARK_STYLESHEET


class SubmitTextEdit(QTextEdit):
    submitRequested = Signal()
    clearRequested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            if is_right_ctrl_down():
                self.submitRequested.emit()
                event.accept()
                return
        if event.key() == Qt.Key.Key_Escape:
            self.clear()
            self.clearRequested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class TranslationPopup(QWidget):
    languageSelected = Signal(str)
    copyRequested = Signal()
    historyRequested = Signal()

    def __init__(self, width: int, height: int, ui_language: str = "ru") -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.ui_language = ui_language
        self.setObjectName("TranslationPopup")
        self.resize(width, height)

        self.title_label = QLabel(APP_DISPLAY_NAME)
        self.title_label.setObjectName("AppTitle")

        self.status_label = QLabel()
        self.status_label.setObjectName("StatusLabel")

        self.language_buttons: dict[str, QPushButton] = {}
        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        header_row.addWidget(self.title_label)
        header_row.addStretch(1)
        for language in LANGUAGES:
            button = QPushButton(language.label)
            button.setCheckable(True)
            button.setFixedSize(46, 30)
            button.setToolTip(f"Перевести на {language.english_name}")
            button.clicked.connect(lambda _checked=False, code=language.code: self.languageSelected.emit(code))
            self.language_buttons[language.code] = button
            header_row.addWidget(button)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setAcceptRichText(False)

        self.copy_button = QPushButton()
        self.copy_button.setFixedWidth(82)
        self.copy_button.clicked.connect(self.copyRequested.emit)

        self.history_button = QPushButton()
        self.history_button.setObjectName("HistoryButton")
        self.history_button.setFixedWidth(94)
        self.history_button.clicked.connect(self.historyRequested.emit)

        self.close_button = QPushButton()
        self.close_button.setFixedWidth(82)
        self.close_button.clicked.connect(self.hide)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.status_label, 1)
        bottom_row.addWidget(self.history_button)
        bottom_row.addWidget(self.copy_button)
        bottom_row.addWidget(self.close_button)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)
        root.addLayout(header_row)
        root.addWidget(self.text_box, 1)
        root.addLayout(bottom_row)

        self.setStyleSheet(
            """
            QWidget#TranslationPopup {
                background: #101620;
                border: 1px solid #314055;
                border-radius: 8px;
            }
            """
        )
        self.apply_locale(ui_language)

    def apply_locale(self, language_code: str) -> None:
        self.ui_language = language_code
        self.status_label.setText(t(language_code, "ready"))
        self.copy_button.setText(t(language_code, "copy"))
        self.history_button.setText(t(language_code, "history"))
        self.history_button.setToolTip(t(language_code, "history"))
        self.close_button.setText(t(language_code, "close"))

    def show_loading(self, target_language: Language) -> None:
        self._mark_language(target_language.code)
        self.text_box.setPlainText(t(self.ui_language, "translating"))
        self.status_label.setText(t(self.ui_language, "target", language=target_language.english_name))
        self.copy_button.setEnabled(False)
        self._move_to_bottom_right()
        self.show()
        self.raise_()
        self.activateWindow()

    def show_translation(self, text: str, target_language: Language) -> None:
        self._mark_language(target_language.code)
        self.text_box.setPlainText(text)
        self.status_label.setText(t(self.ui_language, "translated_to", language=target_language.english_name))
        self.copy_button.setEnabled(bool(text.strip()))
        self._move_to_bottom_right()
        self.show()
        self.raise_()

    def show_error(self, message: str) -> None:
        self.text_box.setPlainText(message)
        self.status_label.setText(t(self.ui_language, "error"))
        self.copy_button.setEnabled(False)
        self._move_to_bottom_right()
        self.show()
        self.raise_()

    def current_text(self) -> str:
        return self.text_box.toPlainText()

    def _mark_language(self, code: str) -> None:
        for language_code, button in self.language_buttons.items():
            button.setChecked(language_code == code)

    def _move_to_bottom_right(self) -> None:
        screen = QGuiApplication.screenAt(QGuiApplication.cursor().pos()) or QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry()
        margin = 18
        self.move(
            geometry.right() - self.width() - margin,
            geometry.bottom() - self.height() - margin,
        )


class MainTranslatorWindow(QWidget):
    translateRequested = Signal(str, str, str)
    copyRequested = Signal()
    historyRequested = Signal()
    settingsRequested = Signal()

    def __init__(self, primary_language_code: str) -> None:
        super().__init__()
        self.ui_language = primary_language_code
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.setObjectName("MainTranslatorWindow")
        self.resize(860, 560)

        self.title_label = QLabel(APP_DISPLAY_NAME)
        self.title_label.setObjectName("HeroTitle")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("HeroSubtitle")
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(62, 62)
        self.logo_label.setScaledContents(True)

        self.source_language_input = QComboBox()
        self.source_language_input.addItem("Auto", "auto")
        for language in LANGUAGES:
            self.source_language_input.addItem(language.english_name, language.code)

        self.target_language_input = QComboBox()
        for language in LANGUAGES:
            self.target_language_input.addItem(language.english_name, language.code)
        target_index = max(0, self.target_language_input.findData(primary_language_code))
        self.target_language_input.setCurrentIndex(target_index)

        self.source_text = SubmitTextEdit()
        self.source_text.setAcceptRichText(False)
        self.source_text.submitRequested.connect(self.emit_translate_requested)
        self.source_text.clearRequested.connect(self.clear_source_text)

        self.translation_text = QTextEdit()
        self.translation_text.setReadOnly(True)
        self.translation_text.setAcceptRichText(False)

        self.translate_button = QPushButton()
        self.translate_button.setObjectName("PrimaryButton")
        self.translate_button.clicked.connect(self.emit_translate_requested)

        self.copy_button = QPushButton("⧉")
        self.copy_button.setFixedSize(34, 30)
        self.copy_button.setToolTip("Copy translation")
        self.copy_button.clicked.connect(self.copyRequested.emit)

        self.clear_source_button = QPushButton("×")
        self.clear_source_button.setFixedSize(30, 28)
        self.clear_source_button.setToolTip("Clear")
        self.clear_source_button.clicked.connect(self.clear_source_text)

        self.history_button = QPushButton()
        self.history_button.setObjectName("HistoryButton")
        self.history_button.clicked.connect(self.historyRequested.emit)

        self.settings_button = QPushButton()
        self.settings_button.clicked.connect(self.settingsRequested.emit)

        self.from_label = QLabel()
        self.to_label = QLabel()
        language_row = QHBoxLayout()
        language_row.addWidget(self.from_label)
        language_row.addWidget(self.source_language_input)
        language_row.addWidget(self.to_label)
        language_row.addWidget(self.target_language_input)

        action_row = QHBoxLayout()
        action_row.addWidget(self.translate_button)
        action_row.addStretch(1)
        action_row.addWidget(self.history_button)
        action_row.addWidget(self.settings_button)

        text_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.source_section_label = QLabel()
        self.source_section_label.setObjectName("SectionLabel")
        self.translation_section_label = QLabel()
        self.translation_section_label.setObjectName("SectionLabel")
        text_splitter.addWidget(self._labeled_text(self.source_section_label, self.source_text, self.clear_source_button))
        text_splitter.addWidget(self._labeled_text(self.translation_section_label, self.translation_text, self.copy_button))
        text_splitter.setSizes([430, 430])

        title_layout = QVBoxLayout()
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)
        header_layout = QHBoxLayout()
        header_layout.addLayout(title_layout, 1)
        header_layout.addWidget(self.logo_label)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)
        root.addLayout(header_layout)
        root.addLayout(language_row)
        root.addWidget(text_splitter, 1)
        root.addLayout(action_row)
        self.set_logo_path("assets/app_icon.png")
        self.apply_locale(primary_language_code)

    def set_logo_path(self, path: str) -> None:
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap)

    def apply_locale(self, language_code: str) -> None:
        self.ui_language = language_code
        self.subtitle_label.setText(t(language_code, "main_subtitle"))
        self.from_label.setText(t(language_code, "from"))
        self.to_label.setText(t(language_code, "to"))
        self.source_section_label.setText(t(language_code, "original"))
        self.translation_section_label.setText(t(language_code, "translation"))
        self.source_text.setPlaceholderText(t(language_code, "source_placeholder"))
        self.translation_text.setPlaceholderText(t(language_code, "translation_placeholder"))
        self.translate_button.setText(t(language_code, "translate"))
        self.copy_button.setToolTip(t(language_code, "copy"))
        self.history_button.setText(t(language_code, "history"))
        self.settings_button.setText(t(language_code, "settings"))

    def clear_source_text(self) -> None:
        self.source_text.clear()

    def emit_translate_requested(self) -> None:
        self.translateRequested.emit(
            str(self.source_language_input.currentData()),
            str(self.target_language_input.currentData()),
            self.source_text.toPlainText(),
        )

    def set_loading(self) -> None:
        self.translation_text.setPlainText(t(self.ui_language, "translating"))
        self.translate_button.setEnabled(False)

    def set_translation(self, text: str) -> None:
        self.translation_text.setPlainText(text)
        self.translate_button.setEnabled(True)

    def set_error(self, message: str) -> None:
        self.translation_text.setPlainText(message)
        self.translate_button.setEnabled(True)

    def current_translation(self) -> str:
        return self.translation_text.toPlainText()

    def _labeled_text(self, label: QLabel, text_edit: QTextEdit, action_button: QPushButton | None = None) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(label)
        header.addStretch(1)
        if action_button is not None:
            header.addWidget(action_button)
        layout.addLayout(header)
        layout.addWidget(text_edit, 1)
        return widget


class HistoryDialog(QDialog):
    filtersChanged = Signal(str, object, object)

    def __init__(self, records: list[HistoryRecord], ui_language: str = "ru", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui_language = ui_language
        self.setObjectName("SurfaceDialog")
        self.resize(900, 560)
        self.records_by_id: dict[int, HistoryRecord] = {}

        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.emit_filters_changed)

        self.date_from_input = QDateEdit()
        self.date_from_input.setCalendarPopup(True)
        self.date_from_input.setDisplayFormat("dd.MM.yyyy")
        self.date_from_input.setSpecialValueText(t(ui_language, "date_from"))
        self.date_from_input.setMinimumDate(QDate(2000, 1, 1))
        self.date_from_input.setDate(self.date_from_input.minimumDate())
        self.date_from_input.dateChanged.connect(self.emit_filters_changed)

        self.date_to_input = QDateEdit()
        self.date_to_input.setCalendarPopup(True)
        self.date_to_input.setDisplayFormat("dd.MM.yyyy")
        self.date_to_input.setSpecialValueText(t(ui_language, "date_to"))
        self.date_to_input.setMinimumDate(QDate(2000, 1, 1))
        self.date_to_input.setMaximumDate(QDate.currentDate().addYears(5))
        self.date_to_input.setDate(self.date_to_input.minimumDate())
        self.date_to_input.dateChanged.connect(self.emit_filters_changed)

        self.reset_filters_button = QPushButton()
        self.reset_filters_button.clicked.connect(self.reset_filters)

        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(260)
        self.list_widget.currentItemChanged.connect(lambda _current, _previous: self.show_selected_record())

        self.source_box = QTextEdit()
        self.source_box.setReadOnly(True)
        self.source_box.setAcceptRichText(False)
        self.translation_box = QTextEdit()
        self.translation_box.setReadOnly(True)
        self.translation_box.setAcceptRichText(False)

        self.source_section_label = QLabel()
        self.translation_section_label = QLabel()
        text_splitter = QSplitter(Qt.Orientation.Vertical)
        text_splitter.addWidget(self._labeled_text(self.source_section_label, self.source_box))
        text_splitter.addWidget(self._labeled_text(self.translation_section_label, self.translation_box))
        text_splitter.setSizes([220, 260])

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.list_widget)
        splitter.addWidget(text_splitter)
        splitter.setSizes([280, 540])

        self.copy_source_button = QPushButton()
        self.copy_translation_button = QPushButton()
        self.clear_button = QPushButton()
        self.close_button = QPushButton()
        self.close_button.clicked.connect(self.accept)

        self.date_from_label = QLabel()
        self.date_to_label = QLabel()
        filter_row = QHBoxLayout()
        filter_row.addWidget(self.search_input, 1)
        filter_row.addWidget(self.date_from_label)
        filter_row.addWidget(self.date_from_input)
        filter_row.addWidget(self.date_to_label)
        filter_row.addWidget(self.date_to_input)
        filter_row.addWidget(self.reset_filters_button)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.copy_source_button)
        bottom_row.addWidget(self.copy_translation_button)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.clear_button)
        bottom_row.addWidget(self.close_button)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        root.addLayout(filter_row)
        root.addWidget(splitter, 1)
        root.addLayout(bottom_row)
        self.apply_locale(ui_language)
        self.set_records(records)

    def apply_locale(self, language_code: str) -> None:
        self.ui_language = language_code
        self.setWindowTitle(t(language_code, "history_title"))
        self.search_input.setPlaceholderText(t(language_code, "search"))
        self.date_from_label.setText(t(language_code, "date_from"))
        self.date_to_label.setText(t(language_code, "date_to"))
        self.reset_filters_button.setText(t(language_code, "reset"))
        self.source_section_label.setText(t(language_code, "original"))
        self.translation_section_label.setText(t(language_code, "translation"))
        self.copy_source_button.setText(t(language_code, "copy_original"))
        self.copy_translation_button.setText(t(language_code, "copy_translation"))
        self.clear_button.setText(t(language_code, "clear_history"))
        self.close_button.setText(t(language_code, "close"))

    def set_records(self, records: list[HistoryRecord]) -> None:
        self.records_by_id = {record.id: record for record in records}
        self.list_widget.clear()
        for record in records:
            item = QListWidgetItem(self._record_title(record))
            item.setData(Qt.ItemDataRole.UserRole, record.id)
            self.list_widget.addItem(item)

        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self.source_box.setPlainText(t(self.ui_language, "nothing_found"))
            self.translation_box.clear()

    def selected_record(self) -> HistoryRecord | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return self.records_by_id.get(int(item.data(Qt.ItemDataRole.UserRole)))

    def show_selected_record(self) -> None:
        record = self.selected_record()
        if record is None:
            return
        self.source_box.setPlainText(record.source_text)
        self.translation_box.setPlainText(record.translated_text)

    def emit_filters_changed(self) -> None:
        self.filtersChanged.emit(
            self.search_input.text(),
            self.selected_date_from(),
            self.selected_date_to(),
        )

    def reset_filters(self) -> None:
        self.search_input.clear()
        self.date_from_input.setDate(self.date_from_input.minimumDate())
        self.date_to_input.setDate(self.date_to_input.minimumDate())
        self.emit_filters_changed()

    def selected_date_from(self) -> str | None:
        if self.date_from_input.date() == self.date_from_input.minimumDate():
            return None
        return self.date_from_input.date().toString("yyyy-MM-dd")

    def selected_date_to(self) -> str | None:
        if self.date_to_input.date() == self.date_to_input.minimumDate():
            return None
        return self.date_to_input.date().toString("yyyy-MM-dd")

    def _record_title(self, record: HistoryRecord) -> str:
        preview = " ".join(record.translated_text.split())
        if len(preview) > 58:
            preview = f"{preview[:55]}..."
        return f"{record.local_date_label}  |  {record.target_language.upper()}  |  {preview}"

    def _labeled_text(self, label: QLabel, text_edit: QTextEdit) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        layout.addWidget(text_edit, 1)
        return widget


class SettingsDialog(QDialog):
    apiKeyCheckRequested = Signal(str, str, str)
    apiKeyDeleteRequested = Signal(str)
    applyRequested = Signal()

    def __init__(
        self,
        config: AppConfig,
        saved_key_status: dict[str, bool],
        key_valid_status: dict[str, bool | None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.ui_language = config.primary_language
        self.saved_key_status = dict(saved_key_status)
        self.key_valid_status = key_valid_status or {}
        self.setObjectName("SurfaceDialog")
        self.setModal(True)
        self.resize(690, 500)

        self.provider_input = QComboBox()
        for provider, label in PROVIDERS:
            self.provider_input.addItem(label, provider)
        selected_index = max(0, self.provider_input.findData(config.provider))
        self.provider_input.setCurrentIndex(selected_index)

        self.primary_language_input = QComboBox()
        for language in LANGUAGES:
            self.primary_language_input.addItem(language.english_name, language.code)
        language_index = max(0, self.primary_language_input.findData(config.primary_language))
        self.primary_language_input.setCurrentIndex(language_index)
        self.primary_language_input.currentIndexChanged.connect(self._on_primary_language_changed)

        self.key_inputs: dict[str, QLineEdit] = {}
        self.model_inputs: dict[str, QComboBox] = {}
        self.key_status_labels: dict[str, QLabel] = {}
        self.key_check_buttons: dict[str, QPushButton] = {}
        self.key_delete_buttons: dict[str, QPushButton] = {}
        self.key_row_labels: dict[str, QLabel] = {}
        self.model_row_labels: dict[str, QLabel] = {}
        for provider, label in PROVIDERS:
            key_input = QLineEdit()
            key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.key_inputs[provider] = key_input
            key_input.textChanged.connect(lambda _text="", p=provider: self._on_key_text_changed(p))

            status_label = QLabel()
            status_label.setFixedWidth(28)
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.key_status_labels[provider] = status_label

            check_button = QPushButton()
            check_button.clicked.connect(lambda _checked=False, p=provider: self.request_api_key_check(p))
            self.key_check_buttons[provider] = check_button

            delete_button = QPushButton()
            delete_button.clicked.connect(lambda _checked=False, p=provider: self.confirm_delete_api_key(p))
            self.key_delete_buttons[provider] = delete_button

            model_input = QComboBox()
            model_input.setEditable(True)
            for model_name in MODEL_OPTIONS[provider]:
                model_input.addItem(model_name)
            selected_model = config.model_for_provider(provider) or DEFAULT_MODELS[provider]
            model_index = model_input.findText(selected_model)
            if model_index < 0:
                model_input.insertItem(0, selected_model)
                model_index = 0
            model_input.setCurrentIndex(model_index)
            self.model_inputs[provider] = model_input
            if not saved_key_status.get(provider):
                initial_status = "missing"
            elif self.key_valid_status.get(provider) is True:
                initial_status = "valid"
            elif self.key_valid_status.get(provider) is False:
                initial_status = "invalid"
            else:
                initial_status = "saved"
            self.update_api_key_status(provider, initial_status)

        self.autostart_checkbox = QCheckBox()
        self.autostart_checkbox.setChecked(config.autostart)

        self.desktop_shortcut_checkbox = QCheckBox()
        self.desktop_shortcut_checkbox.setChecked(config.desktop_shortcut)

        self.theme_input = QComboBox()
        for theme_code in ("system", "dark", "light"):
            self.theme_input.addItem(theme_code, theme_code)
        theme_index = max(0, self.theme_input.findData(config.theme))
        self.theme_input.setCurrentIndex(theme_index)

        self.info_button = QPushButton("?")
        self.info_button.setObjectName("InfoButton")
        self.info_button.setFixedSize(28, 28)
        self.info_button.clicked.connect(self.show_model_info)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general_tab(), "")
        self.tabs.addTab(self._build_api_tab(), "")

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.apply_button = QPushButton()
        self.apply_button.clicked.connect(self.applyRequested.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self.tabs)
        layout.addWidget(self.apply_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.buttons)
        self.apply_locale(config.primary_language)

    def _build_general_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.provider_label = QLabel()
        self.primary_language_label = QLabel()
        self.theme_label = QLabel()
        form.addRow(self.provider_label, self.provider_input)
        form.addRow(self.primary_language_label, self.primary_language_input)
        form.addRow(self.theme_label, self.theme_input)
        form.addRow("", self.autostart_checkbox)
        form.addRow("", self.desktop_shortcut_checkbox)
        return widget

    def _build_api_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        header = QHBoxLayout()
        self.api_header_label = QLabel()
        header.addWidget(self.api_header_label)
        header.addStretch(1)
        header.addWidget(self.info_button)
        layout.addLayout(header)

        form = QFormLayout()
        for provider, label in PROVIDERS:
            key_row = QHBoxLayout()
            key_row.addWidget(self.key_inputs[provider], 1)
            key_row.addWidget(self.key_status_labels[provider])
            key_row.addWidget(self.key_check_buttons[provider])
            key_row.addWidget(self.key_delete_buttons[provider])
            key_label = QLabel()
            model_label = QLabel()
            self.key_row_labels[provider] = key_label
            self.model_row_labels[provider] = model_label
            form.addRow(key_label, key_row)
            form.addRow(model_label, self.model_inputs[provider])
        layout.addLayout(form)
        layout.addStretch(1)
        return widget

    def show_model_info(self) -> None:
        QMessageBox.information(self, t(self.ui_language, "recommended_models"), MODEL_INFO)

    def apply_locale(self, language_code: str) -> None:
        self.ui_language = language_code
        self.setWindowTitle(t(language_code, "settings_title"))
        self.tabs.setTabText(0, t(language_code, "general"))
        self.tabs.setTabText(1, t(language_code, "api"))
        self.provider_label.setText(t(language_code, "provider"))
        self.primary_language_label.setText(t(language_code, "primary_language"))
        self.theme_label.setText(t(language_code, "theme"))
        self.theme_input.setItemText(0, t(language_code, "theme_system"))
        self.theme_input.setItemText(1, t(language_code, "theme_dark"))
        self.theme_input.setItemText(2, t(language_code, "theme_light"))
        self.autostart_checkbox.setText(t(language_code, "autostart"))
        self.desktop_shortcut_checkbox.setText(t(language_code, "desktop_shortcut"))
        self.api_header_label.setText(t(language_code, "api_keys_models"))
        self.info_button.setToolTip(t(language_code, "info_tooltip"))
        save_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if save_button:
            save_button.setText(t(language_code, "save"))
        if cancel_button:
            cancel_button.setText(t(language_code, "cancel"))
        self.apply_button.setText(t(language_code, "apply"))
        for provider, label in PROVIDERS:
            self.key_row_labels[provider].setText(f"{label} {t(language_code, 'key')}")
            self.model_row_labels[provider].setText(f"{label} {t(language_code, 'model')}")
            self.key_check_buttons[provider].setText(t(language_code, "check"))
            self.key_delete_buttons[provider].setText(t(language_code, "delete"))
            placeholder = t(language_code, "saved_key_exists") if self.saved_key_status.get(provider) else t(
                language_code,
                "api_key_placeholder",
                provider=label,
            )
            self.key_inputs[provider].setPlaceholderText(placeholder)

    def request_api_key_check(self, provider: str) -> None:
        key_text = self.key_inputs[provider].text().strip()
        if not key_text and not self.saved_key_status.get(provider):
            self.update_api_key_status(provider, "missing")
            return
        self.update_api_key_status(provider, "checking")
        self.apiKeyCheckRequested.emit(provider, key_text, self.models[provider])

    def confirm_delete_api_key(self, provider: str) -> None:
        label = provider_label_for_ui(provider)
        answer = QMessageBox.question(
            self,
            t(self.ui_language, "key_delete_confirm_title"),
            t(self.ui_language, "key_delete_confirm", provider=label),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.key_inputs[provider].clear()
        self.saved_key_status[provider] = False
        self.update_api_key_status(provider, "missing")
        self.apiKeyDeleteRequested.emit(provider)

    def update_api_key_status(self, provider: str, status: str, message: str | None = None) -> None:
        label = self.key_status_labels[provider]
        if status == "valid":
            label.setText("✓")
            label.setObjectName("KeyStatusOk")
            label.setToolTip(message or t(self.ui_language, "key_valid"))
            self.saved_key_status[provider] = True
            self.key_valid_status[provider] = True
        elif status in {"missing", "invalid"}:
            label.setText("✕")
            label.setObjectName("KeyStatusBad")
            label.setToolTip(message or t(self.ui_language, "key_missing" if status == "missing" else "key_invalid"))
            if status == "missing":
                self.saved_key_status[provider] = False
                self.key_valid_status[provider] = None
            else:
                self.key_valid_status[provider] = False
        elif status == "checking":
            label.setText("…")
            label.setObjectName("KeyStatusNeutral")
            label.setToolTip(t(self.ui_language, "key_checking"))
        else:
            label.setText("•")
            label.setObjectName("KeyStatusNeutral")
            label.setToolTip(message or t(self.ui_language, "key_saved"))
        label.style().unpolish(label)
        label.style().polish(label)

    def _on_key_text_changed(self, provider: str) -> None:
        if self.key_inputs[provider].text().strip():
            self.update_api_key_status(provider, "saved", t(self.ui_language, "key_saved"))
        elif self.saved_key_status.get(provider):
            self.update_api_key_status(provider, "saved")
        else:
            self.update_api_key_status(provider, "missing")

    def _on_primary_language_changed(self) -> None:
        self.apply_locale(self.primary_language)

    @property
    def provider(self) -> str:
        return str(self.provider_input.currentData())

    @property
    def primary_language(self) -> str:
        return str(self.primary_language_input.currentData())

    @property
    def api_keys(self) -> dict[str, str]:
        return {provider: input_box.text().strip() for provider, input_box in self.key_inputs.items()}

    @property
    def models(self) -> dict[str, str]:
        return {
            provider: input_box.currentText().strip() or DEFAULT_MODELS[provider]
            for provider, input_box in self.model_inputs.items()
        }

    @property
    def theme(self) -> str:
        return str(self.theme_input.currentData())

    @property
    def autostart(self) -> bool:
        return self.autostart_checkbox.isChecked()

    @property
    def desktop_shortcut(self) -> bool:
        return self.desktop_shortcut_checkbox.isChecked()
