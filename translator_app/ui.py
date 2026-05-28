from __future__ import annotations

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QGuiApplication
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

from translator_app.config import AppConfig, DEFAULT_MODELS
from translator_app.history import HistoryRecord
from translator_app.languages import LANGUAGES, Language


PROVIDERS = (
    ("openai", "OpenAI"),
    ("google", "Google Gemini"),
    ("anthropic", "Anthropic Claude"),
)

MODEL_INFO = """Рекомендация для переводчика:

OpenAI: gpt-5-mini
Хороший баланс качества, скорости и цены для коротких переводов. Если экономия важнее качества, можно попробовать gpt-5-nano.

Google: gemini-2.5-flash-lite
Самый быстрый и экономичный вариант Gemini для массовых коротких задач. Для чуть лучшего качества можно поставить gemini-2.5-flash.

Anthropic: claude-3-5-haiku-latest
Быстрый и недорогой Claude для простых переводов. Sonnet обычно качественнее, но дороже и чаще избыточен для всплывающего переводчика.

Мой строгий совет: начните с OpenAI gpt-5-mini или Google gemini-2.5-flash-lite. Не ставьте самые дорогие модели для перевода выделенного текста, это обычно лишняя трата."""


class TranslationPopup(QWidget):
    languageSelected = Signal(str)
    copyRequested = Signal()
    historyRequested = Signal()

    def __init__(self, width: int, height: int) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setObjectName("TranslationPopup")
        self.resize(width, height)

        self.status_label = QLabel("Готово")
        self.status_label.setObjectName("StatusLabel")

        self.language_buttons: dict[str, QPushButton] = {}
        language_row = QHBoxLayout()
        language_row.setSpacing(6)
        for language in LANGUAGES:
            button = QPushButton(language.label)
            button.setCheckable(True)
            button.setFixedSize(46, 30)
            button.setToolTip(f"Перевести на {language.english_name}")
            button.clicked.connect(lambda _checked=False, code=language.code: self.languageSelected.emit(code))
            self.language_buttons[language.code] = button
            language_row.addWidget(button)
        language_row.addStretch(1)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setAcceptRichText(False)

        self.copy_button = QPushButton("Copy")
        self.copy_button.setFixedWidth(82)
        self.copy_button.clicked.connect(self.copyRequested.emit)

        self.history_button = QPushButton("История")
        self.history_button.setObjectName("HistoryButton")
        self.history_button.setFixedWidth(94)
        self.history_button.setToolTip("Открыть локальную историю переводов")
        self.history_button.clicked.connect(self.historyRequested.emit)

        self.close_button = QPushButton("Close")
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
        root.addLayout(language_row)
        root.addWidget(self.text_box, 1)
        root.addLayout(bottom_row)

        self.setStyleSheet(
            """
            QWidget#TranslationPopup {
                background: #fcfcfb;
                border: 1px solid #b8bbb7;
                border-radius: 8px;
            }
            QLabel#StatusLabel {
                color: #4d5358;
                font-size: 12px;
            }
            QTextEdit {
                background: #ffffff;
                border: 1px solid #d7d9d4;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                color: #1f2328;
            }
            QPushButton {
                background: #edf0ec;
                border: 1px solid #c8ccc6;
                border-radius: 6px;
                padding: 5px 8px;
                color: #1f2328;
            }
            QPushButton:hover {
                background: #e2e7e1;
            }
            QPushButton:checked {
                background: #2f6f73;
                color: white;
                border-color: #285f62;
            }
            QPushButton#HistoryButton {
                background: #f7fbfb;
                border: 1px solid #6b9ca0;
                color: #235d61;
                font-weight: 600;
            }
            QPushButton#HistoryButton:hover {
                background: #e7f3f2;
            }
            """
        )

    def show_loading(self, target_language: Language) -> None:
        self._mark_language(target_language.code)
        self.text_box.setPlainText("Перевожу...")
        self.status_label.setText(f"Цель: {target_language.english_name}")
        self.copy_button.setEnabled(False)
        self._move_to_bottom_right()
        self.show()
        self.raise_()
        self.activateWindow()

    def show_translation(self, text: str, target_language: Language) -> None:
        self._mark_language(target_language.code)
        self.text_box.setPlainText(text)
        self.status_label.setText(f"Переведено на {target_language.english_name}")
        self.copy_button.setEnabled(bool(text.strip()))
        self._move_to_bottom_right()
        self.show()
        self.raise_()

    def show_error(self, message: str) -> None:
        self.text_box.setPlainText(message)
        self.status_label.setText("Ошибка")
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


class HistoryDialog(QDialog):
    filtersChanged = Signal(str, object, object)

    def __init__(self, records: list[HistoryRecord], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("История переводов")
        self.resize(900, 560)
        self.records_by_id: dict[int, HistoryRecord] = {}

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск")
        self.search_input.textChanged.connect(self.emit_filters_changed)

        self.date_from_input = QDateEdit()
        self.date_from_input.setCalendarPopup(True)
        self.date_from_input.setDisplayFormat("dd.MM.yyyy")
        self.date_from_input.setSpecialValueText("С")
        self.date_from_input.setMinimumDate(QDate(2000, 1, 1))
        self.date_from_input.setDate(self.date_from_input.minimumDate())
        self.date_from_input.dateChanged.connect(self.emit_filters_changed)

        self.date_to_input = QDateEdit()
        self.date_to_input.setCalendarPopup(True)
        self.date_to_input.setDisplayFormat("dd.MM.yyyy")
        self.date_to_input.setSpecialValueText("По")
        self.date_to_input.setMinimumDate(QDate(2000, 1, 1))
        self.date_to_input.setMaximumDate(QDate.currentDate().addYears(5))
        self.date_to_input.setDate(self.date_to_input.minimumDate())
        self.date_to_input.dateChanged.connect(self.emit_filters_changed)

        self.reset_filters_button = QPushButton("Сброс")
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

        text_splitter = QSplitter(Qt.Orientation.Vertical)
        text_splitter.addWidget(self._labeled_text("Оригинал", self.source_box))
        text_splitter.addWidget(self._labeled_text("Перевод", self.translation_box))
        text_splitter.setSizes([220, 260])

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.list_widget)
        splitter.addWidget(text_splitter)
        splitter.setSizes([280, 540])

        self.copy_source_button = QPushButton("Копировать оригинал")
        self.copy_translation_button = QPushButton("Копировать перевод")
        self.clear_button = QPushButton("Очистить историю")
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.accept)

        filter_row = QHBoxLayout()
        filter_row.addWidget(self.search_input, 1)
        filter_row.addWidget(QLabel("С"))
        filter_row.addWidget(self.date_from_input)
        filter_row.addWidget(QLabel("По"))
        filter_row.addWidget(self.date_to_input)
        filter_row.addWidget(self.reset_filters_button)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.copy_source_button)
        bottom_row.addWidget(self.copy_translation_button)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.clear_button)
        bottom_row.addWidget(self.close_button)

        root = QVBoxLayout(self)
        root.addLayout(filter_row)
        root.addWidget(splitter, 1)
        root.addLayout(bottom_row)
        self.set_records(records)

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
            self.source_box.setPlainText("Ничего не найдено.")
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

    def _labeled_text(self, label: str, text_edit: QTextEdit) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(label))
        layout.addWidget(text_edit, 1)
        return widget


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, saved_key_status: dict[str, bool], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Translator Settings")
        self.setModal(True)
        self.resize(540, 430)

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

        self.key_inputs: dict[str, QLineEdit] = {}
        self.model_inputs: dict[str, QLineEdit] = {}
        for provider, label in PROVIDERS:
            key_input = QLineEdit()
            key_input.setEchoMode(QLineEdit.EchoMode.Password)
            key_input.setPlaceholderText("Saved key exists" if saved_key_status.get(provider) else f"{label} API key")
            self.key_inputs[provider] = key_input

            model_input = QLineEdit(config.model_for_provider(provider) or DEFAULT_MODELS[provider])
            self.model_inputs[provider] = model_input

        self.autostart_checkbox = QCheckBox("Start with Windows")
        self.autostart_checkbox.setChecked(config.autostart)

        self.info_button = QPushButton("i")
        self.info_button.setFixedSize(26, 26)
        self.info_button.setToolTip("Recommended models")
        self.info_button.clicked.connect(self.show_model_info)
        self.info_button.setStyleSheet(
            """
            QPushButton {
                border-radius: 13px;
                border: 1px solid #7f8b8c;
                background: #f4f6f5;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #e7ecea;
            }
            """
        )

        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_api_tab(), "API")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _build_general_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.addRow("Provider", self.provider_input)
        form.addRow("Primary language", self.primary_language_input)
        form.addRow("", self.autostart_checkbox)
        return widget

    def _build_api_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        header = QHBoxLayout()
        header.addWidget(QLabel("API keys and models"))
        header.addStretch(1)
        header.addWidget(self.info_button)
        layout.addLayout(header)

        form = QFormLayout()
        for provider, label in PROVIDERS:
            form.addRow(f"{label} key", self.key_inputs[provider])
            form.addRow(f"{label} model", self.model_inputs[provider])
        layout.addLayout(form)
        layout.addStretch(1)
        return widget

    def show_model_info(self) -> None:
        QMessageBox.information(self, "Recommended models", MODEL_INFO)

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
            provider: input_box.text().strip() or DEFAULT_MODELS[provider]
            for provider, input_box in self.model_inputs.items()
        }

    @property
    def autostart(self) -> bool:
        return self.autostart_checkbox.isChecked()
