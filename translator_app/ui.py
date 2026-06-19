from __future__ import annotations

import ctypes
from html import escape
import sys
from pathlib import Path

from PySide6.QtCore import QDate, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication, QIcon, QKeyEvent, QKeySequence, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from translator_app import __version__
from translator_app.config import AppConfig, DEFAULT_MODELS, MODEL_OPTIONS
from translator_app.history import HistoryRecord
from translator_app.i18n import t
from translator_app.languages import LANGUAGES, Language
from translator_app.platform_text import is_macos, platform_text


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


def ui_resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base_path / relative_path


def app_icon() -> QIcon:
    icon = QIcon(str(ui_resource_path("assets/app_icon.ico")))
    if icon.isNull():
        icon = QIcon(str(ui_resource_path("assets/app_icon.png")))
    return icon


def apply_windows_title_bar_theme(widget: QWidget, dark: bool = True) -> None:
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        if not hwnd:
            return
        enabled = ctypes.c_int(1 if dark else 0)
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        for attribute in (20, 19):
            result = dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_uint(attribute),
                ctypes.byref(enabled),
                ctypes.sizeof(enabled),
            )
            if result == 0:
                break
    except Exception:
        return


def schedule_windows_title_bar_theme(widget: QWidget, dark: bool = True) -> None:
    for delay_ms in (0, 50, 250):
        QTimer.singleShot(delay_ms, lambda widget=widget, dark=dark: apply_windows_title_bar_theme(widget, dark))


class WindowsTitleBarMixin:
    _windows_dark_title_bar = True

    def set_windows_dark_title_bar(self, enabled: bool) -> None:
        self._windows_dark_title_bar = enabled
        schedule_windows_title_bar_theme(self, enabled)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override.
        super().showEvent(event)
        schedule_windows_title_bar_theme(self, self._windows_dark_title_bar)

MODEL_DESCRIPTIONS = {
    "ru": {
        "gpt-5-mini": ("Основной вариант для качественного быстрого перевода.", "Низкая"),
        "gpt-5-nano": ("Самый экономный OpenAI-вариант для короткого текста.", "Очень низкая"),
        "gpt-4.1-mini": ("Хороший запасной вариант, если нужен стабильный mini-класс.", "Низкая"),
        "gpt-4.1-nano": ("Очень экономный вариант для простых фраз.", "Очень низкая"),
        "gpt-4o-mini": ("Быстрый старый mini-вариант, полезен как fallback.", "Низкая"),
        "gemini-2.5-flash-lite": ("Самый экономный Gemini для массовых коротких переводов.", "Очень низкая"),
        "gemini-2.5-flash": ("Лучше качество Gemini без перехода в тяжёлые модели.", "Низкая"),
        "gemini-2.0-flash-lite": ("Лёгкий fallback для простых переводов.", "Очень низкая"),
        "gemini-2.0-flash": ("Быстрый универсальный Gemini-вариант.", "Низкая"),
        "gemini-1.5-flash": ("Старый совместимый fallback.", "Низкая"),
        "claude-3-5-haiku-latest": ("Основной экономный Claude для быстрых переводов.", "Низкая"),
        "claude-3-5-haiku-20241022": ("Фиксированная версия Haiku вместо latest.", "Низкая"),
        "claude-3-haiku-20240307": ("Старый быстрый Haiku fallback.", "Низкая"),
        "claude-3-7-sonnet-latest": ("Качественнее, но часто избыточен для popup-перевода.", "Средняя"),
        "claude-sonnet-4-20250514": ("Сильная модель для сложных текстов, не основной экономный выбор.", "Средняя/выше"),
    },
    "en": {
        "gpt-5-mini": ("Default balanced OpenAI choice for fast, good translations.", "Low"),
        "gpt-5-nano": ("Cheapest OpenAI option for short text.", "Very low"),
        "gpt-4.1-mini": ("Good stable mini-class fallback.", "Low"),
        "gpt-4.1-nano": ("Very cheap choice for simple phrases.", "Very low"),
        "gpt-4o-mini": ("Fast older mini option, useful as fallback.", "Low"),
        "gemini-2.5-flash-lite": ("Cheapest Gemini choice for many short translations.", "Very low"),
        "gemini-2.5-flash": ("Better Gemini quality without heavy models.", "Low"),
        "gemini-2.0-flash-lite": ("Light fallback for simple translations.", "Very low"),
        "gemini-2.0-flash": ("Fast general Gemini option.", "Low"),
        "gemini-1.5-flash": ("Older compatible fallback.", "Low"),
        "claude-3-5-haiku-latest": ("Default economical Claude for fast translation.", "Low"),
        "claude-3-5-haiku-20241022": ("Pinned Haiku version instead of latest.", "Low"),
        "claude-3-haiku-20240307": ("Older fast Haiku fallback.", "Low"),
        "claude-3-7-sonnet-latest": ("Higher quality, often excessive for popup translation.", "Medium"),
        "claude-sonnet-4-20250514": ("Strong model for difficult text, not the cheapest default.", "Medium/higher"),
    },
    "de": {
        "gpt-5-mini": ("Standardauswahl von OpenAI für schnelle, gute Übersetzungen.", "Niedrig"),
        "gpt-5-nano": ("Günstigste OpenAI-Option für kurze Texte.", "Sehr niedrig"),
        "gpt-4.1-mini": ("Stabile Mini-Alternative.", "Niedrig"),
        "gpt-4.1-nano": ("Sehr günstige Option für einfache Sätze.", "Sehr niedrig"),
        "gpt-4o-mini": ("Ältere schnelle Mini-Option als Fallback.", "Niedrig"),
        "gemini-2.5-flash-lite": ("Günstigste Gemini-Option für viele kurze Übersetzungen.", "Sehr niedrig"),
        "gemini-2.5-flash": ("Bessere Gemini-Qualität ohne schwere Modelle.", "Niedrig"),
        "gemini-2.0-flash-lite": ("Leichter Fallback für einfache Übersetzungen.", "Sehr niedrig"),
        "gemini-2.0-flash": ("Schnelle universelle Gemini-Option.", "Niedrig"),
        "gemini-1.5-flash": ("Älterer kompatibler Fallback.", "Niedrig"),
        "claude-3-5-haiku-latest": ("Günstiger Standard-Claude für schnelle Übersetzungen.", "Niedrig"),
        "claude-3-5-haiku-20241022": ("Fixierte Haiku-Version statt latest.", "Niedrig"),
        "claude-3-haiku-20240307": ("Älterer schneller Haiku-Fallback.", "Niedrig"),
        "claude-3-7-sonnet-latest": ("Bessere Qualität, oft zu viel für Popup-Übersetzung.", "Mittel"),
        "claude-sonnet-4-20250514": ("Starke Modellwahl für schwierige Texte, nicht der günstigste Standard.", "Mittel/höher"),
    },
    "es": {
        "gpt-5-mini": ("Opción OpenAI equilibrada para traducciones rápidas y buenas.", "Bajo"),
        "gpt-5-nano": ("Opción OpenAI más barata para textos cortos.", "Muy bajo"),
        "gpt-4.1-mini": ("Alternativa mini estable.", "Bajo"),
        "gpt-4.1-nano": ("Opción muy barata para frases simples.", "Muy bajo"),
        "gpt-4o-mini": ("Mini anterior rápido como respaldo.", "Bajo"),
        "gemini-2.5-flash-lite": ("Gemini más barato para muchas traducciones cortas.", "Muy bajo"),
        "gemini-2.5-flash": ("Mejor calidad Gemini sin modelos pesados.", "Bajo"),
        "gemini-2.0-flash-lite": ("Respaldo ligero para traducciones simples.", "Muy bajo"),
        "gemini-2.0-flash": ("Opción Gemini rápida y general.", "Bajo"),
        "gemini-1.5-flash": ("Respaldo compatible anterior.", "Bajo"),
        "claude-3-5-haiku-latest": ("Claude económico por defecto para traducción rápida.", "Bajo"),
        "claude-3-5-haiku-20241022": ("Versión fija de Haiku en vez de latest.", "Bajo"),
        "claude-3-haiku-20240307": ("Respaldo Haiku rápido anterior.", "Bajo"),
        "claude-3-7-sonnet-latest": ("Más calidad, a menudo excesivo para traducción popup.", "Medio"),
        "claude-sonnet-4-20250514": ("Modelo fuerte para texto difícil, no el predeterminado más barato.", "Medio/alto"),
    },
    "zh": {
        "gpt-5-mini": ("OpenAI 默认均衡选择，适合快速且质量好的翻译。", "低"),
        "gpt-5-nano": ("OpenAI 最省钱选项，适合短文本。", "很低"),
        "gpt-4.1-mini": ("稳定的 mini 级备用选择。", "低"),
        "gpt-4.1-nano": ("适合简单短句的超省钱选择。", "很低"),
        "gpt-4o-mini": ("较早的快速 mini 备用选项。", "低"),
        "gemini-2.5-flash-lite": ("Gemini 最省钱选择，适合大量短翻译。", "很低"),
        "gemini-2.5-flash": ("质量更好的 Gemini 选择，不算重型模型。", "低"),
        "gemini-2.0-flash-lite": ("适合简单翻译的轻量备用。", "很低"),
        "gemini-2.0-flash": ("快速通用 Gemini 选择。", "低"),
        "gemini-1.5-flash": ("较早的兼容备用模型。", "低"),
        "claude-3-5-haiku-latest": ("默认经济 Claude，适合快速翻译。", "低"),
        "claude-3-5-haiku-20241022": ("固定 Haiku 版本，不使用 latest。", "低"),
        "claude-3-haiku-20240307": ("较早的快速 Haiku 备用。", "低"),
        "claude-3-7-sonnet-latest": ("质量更高，但对弹窗翻译通常过强。", "中"),
        "claude-sonnet-4-20250514": ("适合复杂文本的强模型，不是最省钱默认。", "中/较高"),
    },
}

MODEL_SPEED_RATINGS = {
    "gpt-5-mini": 4,
    "gpt-5-nano": 5,
    "gpt-4.1-mini": 4,
    "gpt-4.1-nano": 5,
    "gpt-4o-mini": 4,
    "gemini-2.5-flash-lite": 5,
    "gemini-2.5-flash": 4,
    "gemini-2.0-flash-lite": 5,
    "gemini-2.0-flash": 4,
    "gemini-1.5-flash": 4,
    "claude-3-5-haiku-latest": 4,
    "claude-3-5-haiku-20241022": 4,
    "claude-3-haiku-20240307": 5,
    "claude-3-7-sonnet-latest": 3,
    "claude-sonnet-4-20250514": 3,
}

MODEL_COST_RATINGS = {
    "gpt-5-mini": 2,
    "gpt-5-nano": 1,
    "gpt-4.1-mini": 2,
    "gpt-4.1-nano": 1,
    "gpt-4o-mini": 2,
    "gemini-2.5-flash-lite": 1,
    "gemini-2.5-flash": 2,
    "gemini-2.0-flash-lite": 1,
    "gemini-2.0-flash": 2,
    "gemini-1.5-flash": 2,
    "claude-3-5-haiku-latest": 2,
    "claude-3-5-haiku-20241022": 2,
    "claude-3-haiku-20240307": 2,
    "claude-3-7-sonnet-latest": 4,
    "claude-sonnet-4-20250514": 5,
}


def star_rating(value: int) -> str:
    rating = max(1, min(5, value))
    return (
        "<span class='stars'>"
        f"<span class='star-on'>{'★' * rating}</span>"
        f"<span class='star-off'>{'☆' * (5 - rating)}</span>"
        "</span>"
    )

APP_DISPLAY_NAME = "LinguaFlow AI"
APP_WINDOW_TITLE = "LinguaFlow AI - Popup Translator - © Roman Ostroumov / Oster"
INFO_BUTTON_SIZE = 34
AUTO_TRANSLATE_DELAY_MS = 200
OPENAI_KEYS_URL = "https://platform.openai.com/api-keys"
GEMINI_KEYS_URL = "https://aistudio.google.com/api-keys"
ANTHROPIC_KEYS_URL = "https://console.anthropic.com/settings/keys"

ABOUT_COPY = {
    "ru": {
        "title": "О программе",
        "intro": (
            "LinguaFlow AI - Windows-переводчик для быстрого popup-перевода выделенного текста "
            "через Ctrl+C+C и обычного ручного перевода между выбранными языками."
        ),
        "rights_title": "Права и бренд",
        "rights": [
            "Copyright © 2026 Roman Ostroumov / OSTER. Все права защищены, если отдельная LICENSE не говорит иначе.",
            "Название LinguaFlow AI, OSTER-стиль, логотип, иконки, визуальные материалы, интерфейс, исходный код, сборки и документация защищены правами владельца.",
            "Публичный репозиторий сам по себе не означает разрешение копировать, продавать, распространять, переименовывать или использовать бренд/логотип без письменного разрешения владельца.",
        ],
        "privacy_title": "Приватность и данные",
        "privacy": [
            "API-ключи хранятся локально через Windows Credential Manager/keyring, когда это доступно; иначе приложение может читать ключи из переменных окружения.",
            "Ключи не записываются в историю переводов, базу SQLite, лог-файлы приложения или Git-репозиторий.",
            "История переводов хранится локально на этом компьютере. Текст отправляется только выбранному AI-провайдеру для выполнения текущего перевода.",
            "Не вставляйте конфиденциальные данные, если правила вашей компании или договора запрещают отправку текста внешнему AI-провайдеру.",
        ],
        "disclaimer_title": "Дисклеймеры",
        "disclaimer": [
            "AI-переводы могут быть неточными, неполными или неподходящими по стилю. Важные юридические, медицинские, финансовые, миграционные и технические тексты нужно проверять вручную.",
            "Пользователь сам отвечает за выбранного провайдера, модель, API-ключ, расходы токенов и соблюдение условий OpenAI, Google, Anthropic или другого сервиса.",
            "LinguaFlow AI не является официальным продуктом OpenAI, Google, Anthropic или Microsoft. Названия сторонних сервисов принадлежат их владельцам.",
        ],
    },
    "en": {
        "title": "About",
        "intro": (
            "LinguaFlow AI is a Windows translator for fast selected-text popup translation "
            "with Ctrl+C+C and normal manual translation between chosen languages."
        ),
        "rights_title": "Rights and Brand",
        "rights": [
            "Copyright © 2026 Roman Ostroumov / OSTER. All rights reserved unless a separate LICENSE states otherwise.",
            "The LinguaFlow AI name, OSTER style, logo, icons, visual assets, interface, source code, builds, and documentation are protected by the owner's rights.",
            "A public repository does not by itself grant permission to copy, sell, redistribute, rename, or use the brand/logo without the owner's written permission.",
        ],
        "privacy_title": "Privacy and Data",
        "privacy": [
            "API keys are stored locally through Windows Credential Manager/keyring when available; otherwise the app can read keys from environment variables.",
            "Keys are not written to translation history, the SQLite database, app logs, or the Git repository.",
            "Translation history is stored locally on this computer. Text is sent only to the selected AI provider for the current translation request.",
            "Do not paste confidential data if your company policy or contracts prohibit sending text to an external AI provider.",
        ],
        "disclaimer_title": "Disclaimers",
        "disclaimer": [
            "AI translations can be inaccurate, incomplete, or stylistically unsuitable. Important legal, medical, financial, immigration, and technical texts should be reviewed manually.",
            "The user is responsible for the chosen provider, model, API key, token costs, and compliance with OpenAI, Google, Anthropic, or other service terms.",
            "LinguaFlow AI is not an official product of OpenAI, Google, Anthropic, or Microsoft. Third-party service names belong to their owners.",
        ],
    },
    "de": {
        "title": "Über das Programm",
        "intro": (
            "LinguaFlow AI ist ein Windows-Übersetzer für schnelle Popup-Übersetzung markierter Texte "
            "mit Ctrl+C+C und normale manuelle Übersetzung zwischen ausgewählten Sprachen."
        ),
        "rights_title": "Rechte und Marke",
        "rights": [
            "Copyright © 2026 Roman Ostroumov / OSTER. Alle Rechte vorbehalten, sofern keine separate LICENSE etwas anderes regelt.",
            "Name LinguaFlow AI, OSTER-Stil, Logo, Icons, visuelle Materialien, Oberfläche, Quellcode, Builds und Dokumentation sind durch Rechte des Eigentümers geschützt.",
            "Ein öffentliches Repository erlaubt nicht automatisch das Kopieren, Verkaufen, Weiterverbreiten, Umbenennen oder Nutzen von Marke/Logo ohne schriftliche Erlaubnis des Eigentümers.",
        ],
        "privacy_title": "Datenschutz und Daten",
        "privacy": [
            "API-Schlüssel werden lokal über Windows Credential Manager/keyring gespeichert, wenn verfügbar; andernfalls kann die App Schlüssel aus Umgebungsvariablen lesen.",
            "Schlüssel werden nicht im Übersetzungsverlauf, in der SQLite-Datenbank, in App-Logs oder im Git-Repository gespeichert.",
            "Der Übersetzungsverlauf wird lokal auf diesem Computer gespeichert. Text wird nur für die aktuelle Übersetzung an den ausgewählten AI-Anbieter gesendet.",
            "Fügen Sie keine vertraulichen Daten ein, wenn Richtlinien oder Verträge das Senden an externe AI-Anbieter verbieten.",
        ],
        "disclaimer_title": "Haftungsausschlüsse",
        "disclaimer": [
            "AI-Übersetzungen können ungenau, unvollständig oder stilistisch ungeeignet sein. Wichtige juristische, medizinische, finanzielle, migrationsbezogene und technische Texte sollten manuell geprüft werden.",
            "Der Nutzer ist verantwortlich für Anbieter, Modell, API-Schlüssel, Token-Kosten und die Einhaltung der Bedingungen von OpenAI, Google, Anthropic oder anderen Diensten.",
            "LinguaFlow AI ist kein offizielles Produkt von OpenAI, Google, Anthropic oder Microsoft. Namen von Drittanbieterdiensten gehören ihren Eigentümern.",
        ],
    },
    "es": {
        "title": "Acerca de",
        "intro": (
            "LinguaFlow AI es un traductor para Windows con traducción emergente rápida de texto seleccionado "
            "mediante Ctrl+C+C y traducción manual normal entre idiomas elegidos."
        ),
        "rights_title": "Derechos y marca",
        "rights": [
            "Copyright © 2026 Roman Ostroumov / OSTER. Todos los derechos reservados salvo que una LICENSE separada indique lo contrario.",
            "El nombre LinguaFlow AI, el estilo OSTER, el logotipo, los iconos, materiales visuales, interfaz, código fuente, compilaciones y documentación están protegidos por los derechos del propietario.",
            "Un repositorio público no concede por sí solo permiso para copiar, vender, redistribuir, renombrar o usar la marca/logotipo sin permiso escrito del propietario.",
        ],
        "privacy_title": "Privacidad y datos",
        "privacy": [
            "Las claves API se guardan localmente mediante Windows Credential Manager/keyring cuando está disponible; si no, la app puede leerlas desde variables de entorno.",
            "Las claves no se escriben en el historial de traducciones, la base SQLite, los logs de la app ni el repositorio Git.",
            "El historial de traducciones se guarda localmente en este ordenador. El texto se envía solo al proveedor de AI seleccionado para la traducción actual.",
            "No pegues datos confidenciales si las políticas de tu empresa o contratos prohíben enviar texto a un proveedor externo de AI.",
        ],
        "disclaimer_title": "Avisos",
        "disclaimer": [
            "Las traducciones con AI pueden ser inexactas, incompletas o inadecuadas en estilo. Textos legales, médicos, financieros, migratorios y técnicos importantes deben revisarse manualmente.",
            "El usuario es responsable del proveedor, modelo, clave API, costes de tokens y cumplimiento de los términos de OpenAI, Google, Anthropic u otros servicios.",
            "LinguaFlow AI no es un producto oficial de OpenAI, Google, Anthropic ni Microsoft. Los nombres de servicios de terceros pertenecen a sus propietarios.",
        ],
    },
    "zh": {
        "title": "关于",
        "intro": "LinguaFlow AI 是一款 Windows 翻译器，支持通过 Ctrl+C+C 快速弹窗翻译所选文本，也支持在所选语言之间进行普通手动翻译。",
        "rights_title": "权利和品牌",
        "rights": [
            "Copyright © 2026 Roman Ostroumov / OSTER。除非单独的 LICENSE 另有说明，否则保留所有权利。",
            "LinguaFlow AI 名称、OSTER 风格、标志、图标、视觉素材、界面、源代码、构建文件和文档均受所有者权利保护。",
            "公开仓库本身并不表示允许在未经所有者书面许可的情况下复制、销售、再分发、改名或使用品牌/标志。",
        ],
        "privacy_title": "隐私和数据",
        "privacy": [
            "API 密钥会在可用时通过 Windows Credential Manager/keyring 本地保存；否则应用可以从环境变量读取。",
            "密钥不会写入翻译历史、SQLite 数据库、应用日志或 Git 仓库。",
            "翻译历史保存在本机。文本只会为了当前翻译请求发送给所选 AI 提供商。",
            "如果公司政策或合同禁止向外部 AI 提供商发送文本，请不要粘贴机密数据。",
        ],
        "disclaimer_title": "免责声明",
        "disclaimer": [
            "AI 翻译可能不准确、不完整或风格不合适。重要的法律、医疗、金融、移民和技术文本应人工复核。",
            "用户自行负责所选提供商、模型、API 密钥、token 成本，以及遵守 OpenAI、Google、Anthropic 或其他服务条款。",
            "LinguaFlow AI 不是 OpenAI、Google、Anthropic 或 Microsoft 的官方产品。第三方服务名称属于其各自所有者。",
        ],
    },
}

GUIDE_COPY = {
    "ru": {
        "intro": "Короткая инструкция по настройке и ежедневному использованию LinguaFlow AI.",
        "sections": [
            ("Быстрый popup-перевод", [
                "Выделите текст в браузере, PDF, письме или редакторе.",
                "Нажмите Ctrl+C, не отпуская Ctrl нажмите C ещё раз. Окно LinguaFlow AI откроется поверх остальных окон.",
                "Текст вставится автоматически и начнёт переводиться примерно через 0,2 секунды.",
                "В основном окне Ctrl+Enter запускает перевод, а Esc очищает поле исходного текста.",
            ]),
            ("Обычный перевод", [
                "Откройте приложение через ярлык, трей или окно программы.",
                "Выберите язык исходного текста или оставьте Auto, затем выберите язык в поле “На”.",
                "Вставьте текст и нажмите “Перевести” либо Ctrl+Enter. Enter внутри поля оставляет новую строку, Esc очищает поле.",
            ]),
            ("API-ключи", [
                "Откройте вкладку API, вставьте ключ выбранного провайдера, нажмите “Проверить”, затем “Сохранить” или “Применить”.",
                "Зелёная галочка означает, что ключ прошёл проверку. Крестик означает, что ключ отсутствует или не работает.",
                "Ключи хранятся локально через Windows Credential Manager/keyring, если это доступно.",
            ]),
            ("Безопасность и расходы", [
                "Не публикуйте API-ключи и не отправляйте их в GitHub, чаты или скриншоты.",
                "Для экономии выбирайте mini/nano/flash-lite/haiku модели и смотрите рекомендации во вкладке API.",
                "У провайдера желательно включить лимиты расходов и регулярно проверять usage/billing.",
            ]),
        ],
        "links_title": "Где брать ключи",
        "links": [
            ("OpenAI", OPENAI_KEYS_URL, "создать или посмотреть ключ OpenAI API"),
            ("Google Gemini", GEMINI_KEYS_URL, "создать или посмотреть ключ Gemini в Google AI Studio"),
            ("Anthropic Claude", ANTHROPIC_KEYS_URL, "создать или посмотреть ключ Claude в Anthropic Console"),
        ],
    },
    "en": {
        "intro": "A compact guide for setting up and using LinguaFlow AI every day.",
        "sections": [
            ("Fast popup translation", [
                "Select text in a browser, PDF, email, or editor.",
                "Press Ctrl+C, keep Ctrl held, then press C again. LinguaFlow AI opens above other windows.",
                "The selected text is inserted automatically and starts translating after about 0.2 seconds.",
                "In the main window, Ctrl+Enter starts translation and Esc clears the source field.",
            ]),
            ("Normal translation", [
                "Open the app from the shortcut, tray, or main window.",
                "Choose the source language or keep Auto, then choose the target language in the To field.",
                "Paste text and press Translate or Ctrl+Enter. Enter inside the text field keeps a new line; Esc clears the field.",
            ]),
            ("API keys", [
                "Open the API tab, paste the key for the selected provider, press Check, then Save or Apply.",
                "A green check means the key passed validation. A cross means the key is missing or failed.",
                "Keys are stored locally through Windows Credential Manager/keyring when available.",
            ]),
            ("Safety and costs", [
                "Do not publish API keys or send them to GitHub, chats, or screenshots.",
                "For lower cost, prefer mini/nano/flash-lite/haiku models and review the API tab recommendations.",
                "Set provider-side spending limits and check usage/billing regularly.",
            ]),
        ],
        "links_title": "Where to get keys",
        "links": [
            ("OpenAI", OPENAI_KEYS_URL, "create or manage an OpenAI API key"),
            ("Google Gemini", GEMINI_KEYS_URL, "create or manage a Gemini key in Google AI Studio"),
            ("Anthropic Claude", ANTHROPIC_KEYS_URL, "create or manage a Claude key in Anthropic Console"),
        ],
    },
    "de": {
        "intro": "Eine kurze Anleitung zur Einrichtung und täglichen Nutzung von LinguaFlow AI.",
        "sections": [
            ("Schnelle Popup-Übersetzung", [
                "Markieren Sie Text im Browser, PDF, in E-Mails oder im Editor.",
                "Drücken Sie Ctrl+C, halten Sie Ctrl gedrückt und drücken Sie C erneut. LinguaFlow AI öffnet sich über anderen Fenstern.",
                "Der Text wird automatisch eingefügt und nach etwa 0,2 Sekunden übersetzt.",
                "Im Hauptfenster startet Ctrl+Enter die Übersetzung, Esc leert das Ausgangsfeld.",
            ]),
            ("Normale Übersetzung", [
                "Öffnen Sie die App über Verknüpfung, Tray oder Hauptfenster.",
                "Wählen Sie die Ausgangssprache oder Auto und danach die Zielsprache im Feld Nach.",
                "Text einfügen und Übersetzen oder Ctrl+Enter drücken. Enter bleibt ein Zeilenumbruch, Esc leert das Feld.",
            ]),
            ("API-Schlüssel", [
                "Öffnen Sie die API-Registerkarte, fügen Sie den Schlüssel des Anbieters ein, drücken Sie Prüfen und dann Speichern oder Anwenden.",
                "Ein grüner Haken bedeutet, dass der Schlüssel gültig ist. Ein Kreuz bedeutet, dass er fehlt oder nicht funktioniert.",
                "Schlüssel werden lokal über Windows Credential Manager/keyring gespeichert, wenn verfügbar.",
            ]),
            ("Sicherheit und Kosten", [
                "Veröffentlichen Sie API-Schlüssel nicht in GitHub, Chats oder Screenshots.",
                "Für geringere Kosten nutzen Sie mini/nano/flash-lite/haiku Modelle und prüfen Sie die Empfehlungen im API-Tab.",
                "Setzen Sie Kostenlimits beim Anbieter und prüfen Sie Nutzung/Abrechnung regelmäßig.",
            ]),
        ],
        "links_title": "Wo man Schlüssel bekommt",
        "links": [
            ("OpenAI", OPENAI_KEYS_URL, "OpenAI API-Schlüssel erstellen oder verwalten"),
            ("Google Gemini", GEMINI_KEYS_URL, "Gemini-Schlüssel in Google AI Studio erstellen oder verwalten"),
            ("Anthropic Claude", ANTHROPIC_KEYS_URL, "Claude-Schlüssel in Anthropic Console erstellen oder verwalten"),
        ],
    },
    "es": {
        "intro": "Una guía breve para configurar y usar LinguaFlow AI a diario.",
        "sections": [
            ("Traducción rápida emergente", [
                "Selecciona texto en un navegador, PDF, correo o editor.",
                "Pulsa Ctrl+C, mantén Ctrl y pulsa C otra vez. LinguaFlow AI se abrirá encima de las demás ventanas.",
                "El texto se inserta automáticamente y empieza a traducirse tras unos 0,2 segundos.",
                "En la ventana principal, Ctrl+Enter inicia la traducción y Esc limpia el campo de origen.",
            ]),
            ("Traducción normal", [
                "Abre la app desde el acceso directo, la bandeja o la ventana principal.",
                "Elige el idioma de origen o deja Auto, y después el idioma de destino en el campo A.",
                "Pega el texto y pulsa Traducir o Ctrl+Enter. Enter mantiene una nueva línea; Esc limpia el campo.",
            ]),
            ("Claves API", [
                "Abre la pestaña API, pega la clave del proveedor elegido, pulsa Comprobar y luego Guardar o Aplicar.",
                "Una marca verde significa que la clave pasó la validación. Una cruz significa que falta o no funciona.",
                "Las claves se guardan localmente mediante Windows Credential Manager/keyring cuando está disponible.",
            ]),
            ("Seguridad y costes", [
                "No publiques claves API ni las envíes a GitHub, chats o capturas.",
                "Para reducir costes, usa modelos mini/nano/flash-lite/haiku y revisa las recomendaciones en la pestaña API.",
                "Configura límites de gasto en el proveedor y revisa uso/facturación con regularidad.",
            ]),
        ],
        "links_title": "Dónde obtener claves",
        "links": [
            ("OpenAI", OPENAI_KEYS_URL, "crear o gestionar una clave de OpenAI API"),
            ("Google Gemini", GEMINI_KEYS_URL, "crear o gestionar una clave Gemini en Google AI Studio"),
            ("Anthropic Claude", ANTHROPIC_KEYS_URL, "crear o gestionar una clave Claude en Anthropic Console"),
        ],
    },
    "zh": {
        "intro": "LinguaFlow AI 的设置和日常使用简明指南。",
        "sections": [
            ("快速弹窗翻译", [
                "在浏览器、PDF、邮件或编辑器中选择文本。",
                "按 Ctrl+C，保持 Ctrl 不松开，再按一次 C。LinguaFlow AI 会在其他窗口上方打开。",
                "所选文本会自动插入，并在约 0.2 秒后开始翻译。",
                "在主窗口中，Ctrl+Enter 开始翻译，Esc 清空源文本框。",
            ]),
            ("普通翻译", [
                "通过快捷方式、托盘或主窗口打开应用。",
                "选择源语言或保持 Auto，然后在 To 字段选择目标语言。",
                "粘贴文本并点击翻译，或按 Ctrl+Enter。Enter 保留换行；Esc 清空文本框。",
            ]),
            ("API 密钥", [
                "打开 API 选项卡，粘贴所选提供商的密钥，点击检查，然后保存或应用。",
                "绿色勾表示密钥验证通过。叉号表示密钥缺失或不可用。",
                "可用时，密钥会通过 Windows Credential Manager/keyring 本地保存。",
            ]),
            ("安全和费用", [
                "不要公开 API 密钥，也不要把它们发到 GitHub、聊天或截图中。",
                "为了降低成本，优先选择 mini/nano/flash-lite/haiku 模型，并查看 API 选项卡中的推荐。",
                "建议在提供商端设置消费限制，并定期查看用量/账单。",
            ]),
        ],
        "links_title": "在哪里获取密钥",
        "links": [
            ("OpenAI", OPENAI_KEYS_URL, "创建或管理 OpenAI API 密钥"),
            ("Google Gemini", GEMINI_KEYS_URL, "在 Google AI Studio 创建或管理 Gemini 密钥"),
            ("Anthropic Claude", ANTHROPIC_KEYS_URL, "在 Anthropic Console 创建或管理 Claude 密钥"),
        ],
    },
}


def app_stylesheet(theme: str = "dark") -> str:
    arrow_path = ui_resource_path("assets/dropdown_arrow.svg").as_posix()
    stylesheet = DARK_STYLESHEET.replace("__DROPDOWN_ARROW__", arrow_path)
    if theme == "light":
        return LIGHT_STYLESHEET.replace("__DROPDOWN_ARROW__", arrow_path)
    return stylesheet


DARK_STYLESHEET = """
QWidget {
    background: #0f131a;
    color: #eef3f8;
    font-family: "Calibri";
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
    font-size: 22px;
    font-weight: 700;
}
QLabel#HeroSubtitle {
    color: #9caaba;
    font-size: 13px;
}
QLabel#HotkeyHint {
    color: #f7fbff;
    font-size: 14px;
    font-weight: 800;
}
QLabel#ShortcutHint {
    color: #9caaba;
    font-size: 12px;
    font-weight: 650;
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
QScrollBar:vertical {
    background: #0c1118;
    border: 1px solid #263142;
    border-radius: 6px;
    width: 14px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #8fd8ff;
    border: 1px solid #c7efff;
    border-radius: 6px;
    min-height: 42px;
}
QScrollBar::handle:vertical:hover {
    background: #b6e8ff;
}
QScrollBar::handle:vertical:pressed {
    background: #65cfff;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
    background: transparent;
    border: none;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: #101722;
    border-radius: 6px;
}
QScrollBar:horizontal {
    background: #0c1118;
    border: 1px solid #263142;
    border-radius: 6px;
    height: 14px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #8fd8ff;
    border: 1px solid #c7efff;
    border-radius: 6px;
    min-width: 42px;
}
QScrollBar::handle:horizontal:hover {
    background: #b6e8ff;
}
QScrollBar::handle:horizontal:pressed {
    background: #65cfff;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
    background: transparent;
    border: none;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: #101722;
    border-radius: 6px;
}
QComboBox::drop-down, QDateEdit::drop-down {
    width: 30px;
    border-left: 1px solid #344154;
    background: #1b2634;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}
QComboBox::down-arrow, QDateEdit::down-arrow {
    image: url("__DROPDOWN_ARROW__");
    width: 12px;
    height: 12px;
}
QPushButton#DropdownButton {
    background: #1e78ad;
    border: 1px solid #65cfff;
    color: #ffffff;
    font-size: 15px;
    font-weight: 800;
    padding: 0;
    min-width: 30px;
    max-width: 30px;
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
    font-weight: 800;
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
    border-radius: 17px;
    border: 1px solid #74d2ff;
    background: #1f78ad;
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
    padding: 0px;
    margin: 0px;
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
    text-align: center;
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
    background: transparent;
    border: none;
}
QMenu {
    background: #121821;
    border: 1px solid #303b4d;
    border-radius: 10px;
    color: #eef3f8;
    font-family: "Calibri";
    font-size: 14px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 34px 8px 14px;
    min-width: 210px;
    border-radius: 6px;
}
QMenu::item:selected {
    background: #1b415a;
}
QMenu::item:disabled {
    color: #657386;
}
QMenu::separator {
    height: 1px;
    background: #253142;
    margin: 5px 8px;
}
"""

LIGHT_STYLESHEET = DARK_STYLESHEET.replace("#0f131a", "#f6f8fb").replace("#eef3f8", "#16202c").replace("#d7dee8", "#263241").replace("#f7fbff", "#101720").replace("#9caaba", "#536173").replace("#151b24", "#ffffff").replace("#2b3545", "#cfd8e5").replace("#f2f6fb", "#111827").replace("#60c6ff", "#1686c4").replace("#111722", "#ffffff").replace("#252f3f", "#d8e0eb").replace("#1c2634", "#eaf4fb").replace("#aab7c7", "#46566a").replace("#1d2632", "#edf2f7").replace("#344154", "#c6d0dd").replace("#263244", "#e3edf7").replace("#4f8fb6", "#4a9eca").replace("#18202b", "#dce7f2").replace("#121821", "#ffffff").replace("#303b4d", "#cad5e2").replace("#1b415a", "#d8eefc") + """
QTabBar::tab:selected {
    color: #07111c;
    font-weight: 800;
}
"""
APP_STYLESHEET = DARK_STYLESHEET


class CleanTextEdit(QTextEdit):
    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        is_read_only = self.isReadOnly()
        cursor = self.textCursor()
        has_selection = cursor.hasSelection()
        has_text = bool(self.toPlainText())
        has_clipboard_text = bool(QGuiApplication.clipboard().text())

        self._add_menu_action(menu, "Undo", "Ctrl+Z", self.undo, not is_read_only and self.document().isUndoAvailable())
        self._add_menu_action(menu, "Redo", "Ctrl+Y", self.redo, not is_read_only and self.document().isRedoAvailable())
        menu.addSeparator()
        self._add_menu_action(menu, "Cut", "Ctrl+X", self.cut, not is_read_only and has_selection)
        self._add_menu_action(menu, "Copy", "Ctrl+C", self.copy, has_selection)
        self._add_menu_action(menu, "Paste", "Ctrl+V", self.paste, not is_read_only and has_clipboard_text)
        self._add_menu_action(menu, "Delete", "Del", self._delete_selection, not is_read_only and has_selection)
        menu.addSeparator()
        self._add_menu_action(menu, "Select All", "Ctrl+A", self.selectAll, has_text)
        menu.exec(event.globalPos())

    def _add_menu_action(self, menu: QMenu, label: str, shortcut: str, callback, enabled: bool) -> None:
        action = menu.addAction(label)
        action.setShortcut(QKeySequence(shortcut))
        action.setShortcutVisibleInContextMenu(True)
        action.setEnabled(enabled)
        action.triggered.connect(lambda _checked=False, cb=callback: cb())

    def _delete_selection(self) -> None:
        cursor = self.textCursor()
        cursor.removeSelectedText()
        self.setTextCursor(cursor)


class SubmitTextEdit(CleanTextEdit):
    submitRequested = Signal()
    clearRequested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            submit_modifier = (
                Qt.KeyboardModifier.MetaModifier
                if is_macos()
                else Qt.KeyboardModifier.ControlModifier
            )
            if event.modifiers() & submit_modifier:
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
        self.setWindowIcon(app_icon())
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

        self.text_box = CleanTextEdit()
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


class MainTranslatorWindow(WindowsTitleBarMixin, QWidget):
    translateRequested = Signal(str, str, str)
    copyRequested = Signal()
    historyRequested = Signal()
    settingsRequested = Signal()
    targetLanguageChanged = Signal(str)

    def __init__(self, primary_language_code: str, target_language_code: str | None = None) -> None:
        super().__init__()
        self.ui_language = primary_language_code
        self.setWindowTitle(APP_WINDOW_TITLE)
        self.setWindowIcon(app_icon())
        self.setObjectName("MainTranslatorWindow")
        self.resize(900, 600)

        self.title_label = QLabel(APP_DISPLAY_NAME)
        self.title_label.setObjectName("HeroTitle")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("HotkeyHint")
        self.subtitle_label.setWordWrap(True)

        self.shortcut_hint_label = QLabel()
        self.shortcut_hint_label.setObjectName("ShortcutHint")
        self.shortcut_hint_label.setWordWrap(True)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(54, 54)
        self.logo_label.setScaledContents(True)

        self.source_language_input = QComboBox()
        self.source_language_input.addItem("Auto", "auto")
        for language in LANGUAGES:
            self.source_language_input.addItem(language.english_name, language.code)

        self.target_language_input = QComboBox()
        for language in LANGUAGES:
            self.target_language_input.addItem(language.english_name, language.code)
        target_index = max(0, self.target_language_input.findData(target_language_code or primary_language_code))
        self.target_language_input.setCurrentIndex(target_index)
        self.target_language_input.currentIndexChanged.connect(self.emit_target_language_changed)

        self.source_text = SubmitTextEdit()
        self.source_text.setAcceptRichText(False)
        self.source_text.submitRequested.connect(self.emit_translate_requested)
        self.source_text.clearRequested.connect(self.clear_source_text)
        self.source_text.textChanged.connect(self.schedule_auto_translate)
        self.auto_translate_timer = QTimer(self)
        self.auto_translate_timer.setSingleShot(True)
        self.auto_translate_timer.setInterval(AUTO_TRANSLATE_DELAY_MS)
        self.auto_translate_timer.timeout.connect(self.emit_auto_translate_requested)
        self.last_submitted_text = ""

        self.translation_text = CleanTextEdit()
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
        source_language_group = QWidget()
        source_language_layout = QHBoxLayout(source_language_group)
        source_language_layout.setContentsMargins(0, 0, 0, 0)
        source_language_layout.setSpacing(10)
        source_language_layout.addWidget(self.from_label)
        source_language_layout.addWidget(self.source_language_input, 0)
        source_language_layout.addStretch(1)

        target_language_group = QWidget()
        target_language_layout = QHBoxLayout(target_language_group)
        target_language_layout.setContentsMargins(0, 0, 0, 0)
        target_language_layout.setSpacing(10)
        target_language_layout.addWidget(self.to_label)
        target_language_layout.addWidget(self.target_language_input, 0)
        target_language_layout.addStretch(1)

        language_row = QHBoxLayout()
        language_row.setSpacing(18)
        language_row.addWidget(source_language_group, 1)
        language_row.addWidget(target_language_group, 1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(8)
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

        header_text_layout = QVBoxLayout()
        header_text_layout.setContentsMargins(0, 0, 0, 0)
        header_text_layout.setSpacing(3)
        header_text_layout.addWidget(self.subtitle_label)
        header_text_layout.addWidget(self.shortcut_hint_label)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        header_layout.addLayout(header_text_layout, 1)
        header_layout.addWidget(self.title_label, 0, Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.logo_label)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 12, 18, 14)
        root.setSpacing(8)
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
        self.shortcut_hint_label.setText(t(language_code, "main_shortcuts"))
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
        self.auto_translate_timer.stop()
        self.last_submitted_text = ""
        self.source_text.clear()
        self.translation_text.clear()

    def load_source_text(self, text: str, target_language_code: str) -> None:
        self.auto_translate_timer.stop()
        self.last_submitted_text = ""
        source_index = self.source_language_input.findData("auto")
        if source_index >= 0:
            self.source_language_input.setCurrentIndex(source_index)
        target_index = self.target_language_input.findData(target_language_code)
        if target_index >= 0:
            was_blocked = self.target_language_input.blockSignals(True)
            self.target_language_input.setCurrentIndex(target_index)
            self.target_language_input.blockSignals(was_blocked)
        self.translation_text.clear()
        self.source_text.setPlainText(text)
        self.source_text.moveCursor(QTextCursor.MoveOperation.End)
        self.source_text.setFocus()

    def emit_target_language_changed(self) -> None:
        self.targetLanguageChanged.emit(str(self.target_language_input.currentData()))

    def emit_translate_requested(self) -> None:
        self.auto_translate_timer.stop()
        self.last_submitted_text = self.source_text.toPlainText()
        self.translateRequested.emit(
            str(self.source_language_input.currentData()),
            str(self.target_language_input.currentData()),
            self.source_text.toPlainText(),
        )

    def schedule_auto_translate(self) -> None:
        text = self.source_text.toPlainText().strip()
        if not text or text == self.last_submitted_text.strip():
            self.auto_translate_timer.stop()
            return
        self.auto_translate_timer.start()

    def emit_auto_translate_requested(self) -> None:
        text = self.source_text.toPlainText().strip()
        if not text or text == self.last_submitted_text.strip():
            return
        self.emit_translate_requested()

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
        layout.setSpacing(4)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        header.addWidget(label)
        header.addStretch(1)
        if action_button is not None:
            header.addWidget(action_button)
        layout.addLayout(header)
        layout.addWidget(text_edit, 1)
        return widget


class HistoryDialog(WindowsTitleBarMixin, QDialog):
    filtersChanged = Signal(str, object, object)

    def __init__(self, records: list[HistoryRecord], ui_language: str = "ru", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui_language = ui_language
        self.setWindowIcon(app_icon())
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

        self.source_box = CleanTextEdit()
        self.source_box.setReadOnly(True)
        self.source_box.setAcceptRichText(False)
        self.translation_box = CleanTextEdit()
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
        language_route = f"{_history_language_label(record.source_language)} -> {_history_language_label(record.target_language)}"
        return f"{record.local_date_label}  |  {language_route}  |  {preview}"

    def _labeled_text(self, label: QLabel, text_edit: QTextEdit) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        layout.addWidget(text_edit, 1)
        return widget


def _history_language_label(language_code: str) -> str:
    cleaned = (language_code or "auto").strip().upper()
    return cleaned or "AUTO"


class SettingsDialog(WindowsTitleBarMixin, QDialog):
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
        self.setWindowIcon(app_icon())
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
            model_input.setMinimumWidth(300)
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

        self.about_browser = QTextBrowser()
        self.about_browser.setOpenExternalLinks(False)

        self.guide_button = self._create_info_button()
        self.guide_button.clicked.connect(self.show_usage_guide)
        self.guide_label = QLabel()
        self.guide_label.setObjectName("SectionLabel")
        self.guide_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.info_button = self._create_info_button()
        self.info_button.clicked.connect(self.show_model_info)
        self.recommendations_label = QLabel()
        self.recommendations_label.setObjectName("SectionLabel")
        self.recommendations_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general_tab(), "")
        self.tabs.addTab(self._build_api_tab(), "")
        self.tabs.addTab(self._build_about_tab(), "")

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.apply_button = QPushButton()
        self.apply_button.clicked.connect(self.applyRequested.emit)
        self.buttons.addButton(self.apply_button, QDialogButtonBox.ButtonRole.ApplyRole)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self.tabs)
        layout.addWidget(self.buttons)
        self.theme_input.currentIndexChanged.connect(lambda _index=0: self.about_browser.setHtml(self._about_html()))
        self.apply_locale(config.primary_language)

    def _create_info_button(self) -> QPushButton:
        button = QPushButton("?")
        button.setObjectName("InfoButton")
        button.setFixedSize(QSize(INFO_BUTTON_SIZE, INFO_BUTTON_SIZE))
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return button

    def _build_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()
        self.provider_label = QLabel()
        self.primary_language_label = QLabel()
        self.theme_label = QLabel()
        form.addRow(self.provider_label, self.provider_input)
        form.addRow(self.primary_language_label, self.primary_language_input)
        form.addRow(self.theme_label, self.theme_input)
        form.addRow("", self.autostart_checkbox)
        form.addRow("", self.desktop_shortcut_checkbox)
        layout.addLayout(form)

        guide_box = QVBoxLayout()
        guide_box.setSpacing(5)
        guide_box.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        guide_box.addWidget(self.guide_label, alignment=Qt.AlignmentFlag.AlignCenter)
        guide_box.addWidget(self.guide_button, alignment=Qt.AlignmentFlag.AlignCenter)

        guide_row = QHBoxLayout()
        guide_row.addStretch(1)
        guide_row.addLayout(guide_box)
        guide_row.addStretch(1)
        layout.addStretch(1)
        layout.addLayout(guide_row)
        layout.addStretch(1)
        return widget

    def _build_api_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        header = QHBoxLayout()
        self.api_header_label = QLabel()
        header.addWidget(self.api_header_label)
        header.addStretch(1)
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
            form.addRow(model_label, self._model_row(provider))
        layout.addLayout(form)

        recommendations_box = QVBoxLayout()
        recommendations_box.setSpacing(5)
        recommendations_box.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        recommendations_box.addWidget(self.recommendations_label, alignment=Qt.AlignmentFlag.AlignCenter)
        recommendations_box.addWidget(self.info_button, alignment=Qt.AlignmentFlag.AlignCenter)

        recommendations_row = QHBoxLayout()
        recommendations_row.addStretch(1)
        recommendations_row.addLayout(recommendations_box)
        recommendations_row.addStretch(1)
        layout.addStretch(1)
        layout.addLayout(recommendations_row)
        layout.addStretch(1)
        return widget

    def _model_row(self, provider: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.model_inputs[provider], 1)
        return widget

    def _build_about_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        self.about_browser.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self.about_browser, 1)
        return widget

    def show_usage_guide(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(t(self.ui_language, "usage_guide"))
        dialog.resize(880, 620)
        schedule_windows_title_bar_theme(dialog, self._windows_dark_title_bar)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(self._guide_html())

        close_button = QPushButton(t(self.ui_language, "close"))
        close_button.clicked.connect(dialog.accept)

        layout = QVBoxLayout(dialog)
        layout.addWidget(browser, 1)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def show_model_info(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(t(self.ui_language, "recommended_models"))
        dialog.resize(900, 520)
        schedule_windows_title_bar_theme(dialog, self._windows_dark_title_bar)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(self._model_info_html())

        close_button = QPushButton(t(self.ui_language, "close"))
        close_button.clicked.connect(dialog.accept)

        layout = QVBoxLayout(dialog)
        layout.addWidget(browser, 1)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def _model_info_html(self) -> str:
        language_code = self.ui_language if self.ui_language in MODEL_DESCRIPTIONS else "en"
        descriptions = MODEL_DESCRIPTIONS.get(language_code, MODEL_DESCRIPTIONS["en"])
        theme = self.theme
        dark = theme == "dark" or theme == "system"
        page_background = "#101620" if dark else "#f6f8fb"
        text_color = "#eef3f8" if dark else "#07111c"
        muted_text = "#d7dee8" if dark else "#263241"
        border_color = "#2b3545" if dark else "#c7d3e0"
        header_background = "#1c2634" if dark else "#e7f1fa"
        header_color = "#8fd8ff" if dark else "#0b5f90"
        code_background = "#172231" if dark else "#eaf1f7"
        code_color = "#f7fbff" if dark else "#07111c"
        star_off_color = "#526174" if dark else "#a9b6c5"
        rows: list[str] = []
        provider_names = dict(PROVIDERS)
        for provider, model_names in MODEL_OPTIONS.items():
            for model_name in model_names:
                use, _cost_label = descriptions.get(model_name) or MODEL_DESCRIPTIONS["en"].get(model_name, ("", ""))
                speed = star_rating(MODEL_SPEED_RATINGS.get(model_name, 4))
                cost = star_rating(MODEL_COST_RATINGS.get(model_name, 2))
                rows.append(
                    "<tr>"
                    f"<td>{provider_names.get(provider, provider)}</td>"
                    f"<td><code>{model_name}</code></td>"
                    f"<td>{use}</td>"
                    f"<td>{speed}</td>"
                    f"<td>{cost}</td>"
                    "</tr>"
                )
        return (
            "<style>"
            f"body{{font-family:Calibri,sans-serif;color:{text_color};background:{page_background};font-size:12px;margin:8px;}}"
            "h2,table,th,td,code,.stars{font-family:Calibri,sans-serif;}"
            "h2{font-size:20px;margin:0 0 10px 0;}"
            "table{border-collapse:collapse;width:100%;table-layout:fixed;}"
            f"th,td{{border:1px solid {border_color};padding:5px 7px;vertical-align:top;line-height:1.25;color:{muted_text};}}"
            f"th{{background:{header_background};color:{header_color};text-align:left;font-weight:700;}}"
            f"code{{color:{code_color};background:{code_background};font-weight:700;font-size:12px;padding:1px 3px;border-radius:4px;white-space:normal;}}"
            ".stars{font-size:15px;letter-spacing:1px;white-space:nowrap;}"
            ".star-on{color:#ffc857;font-weight:700;}"
            f".star-off{{color:{star_off_color};font-weight:700;}}"
            "th:nth-child(1),td:nth-child(1){width:16%;}"
            "th:nth-child(2),td:nth-child(2){width:26%;}"
            "th:nth-child(3),td:nth-child(3){width:34%;}"
            "th:nth-child(4),td:nth-child(4){width:12%;}"
            "th:nth-child(5),td:nth-child(5){width:12%;}"
            "</style>"
            f"<h2>{t(self.ui_language, 'recommended_models')}</h2>"
            "<table>"
            "<thead><tr>"
            f"<th>{t(self.ui_language, 'provider_column')}</th>"
            f"<th>{t(self.ui_language, 'model_column')}</th>"
            f"<th>{t(self.ui_language, 'use_column')}</th>"
            f"<th>{t(self.ui_language, 'speed_column')}</th>"
            f"<th>{t(self.ui_language, 'cost_column')}</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        )

    def _guide_html(self) -> str:
        language_code = self.ui_language if self.ui_language in GUIDE_COPY else "en"
        copy = GUIDE_COPY.get(language_code, GUIDE_COPY["en"])
        theme = self.theme
        dark = theme == "dark" or theme == "system"
        page_background = "#101620" if dark else "#f6f8fb"
        text_color = "#eef3f8" if dark else "#07111c"
        muted_text = "#c8d3df" if dark else "#263241"
        accent = "#8fd8ff" if dark else "#0b6fa7"
        panel_background = "#151b24" if dark else "#ffffff"
        border_color = "#2b3545" if dark else "#c7d3e0"
        link_color = "#8fd8ff" if dark else "#075f96"

        sections: list[str] = []
        for section_title, section_items in copy["sections"]:
            item_html = "".join(f"<li>{escape(platform_text(item))}</li>" for item in section_items)
            sections.append(f"<h2>{escape(platform_text(section_title))}</h2><ul>{item_html}</ul>")

        links = "".join(
            "<li>"
            f"<strong>{escape(provider)}</strong>: "
            f"<a href='{escape(url)}'>{escape(url)}</a>"
            f"<div class='note'>{escape(platform_text(description))}</div>"
            "</li>"
            for provider, url, description in copy["links"]
        )

        return (
            "<style>"
            f"body{{font-family:Calibri,sans-serif;color:{text_color};background:{page_background};font-size:14px;margin:8px;}}"
            f".card{{background:{panel_background};border:1px solid {border_color};border-radius:12px;padding:18px 20px;}}"
            "h1{font-size:24px;margin:0 0 6px 0;font-weight:800;}"
            f".intro{{color:{muted_text};font-size:15px;line-height:1.35;margin:0 0 16px 0;}}"
            f"h2{{color:{accent};font-size:17px;margin:17px 0 7px 0;font-weight:800;}}"
            f"ul{{margin:0 0 4px 19px;padding:0;color:{muted_text};line-height:1.36;}}"
            "li{margin:5px 0;}"
            f"a{{color:{link_color};text-decoration:none;font-weight:700;}}"
            f".note{{color:{muted_text};font-size:12px;margin-top:2px;}}"
            "</style>"
            "<div class='card'>"
            f"<h1>{escape(t(self.ui_language, 'usage_guide'))}</h1>"
            f"<p class='intro'>{escape(platform_text(copy['intro']))}</p>"
            f"{''.join(sections)}"
            f"<h2>{escape(copy['links_title'])}</h2><ul>{links}</ul>"
            "</div>"
        )

    def _about_html(self) -> str:
        language_code = self.ui_language if self.ui_language in ABOUT_COPY else "en"
        copy = ABOUT_COPY.get(language_code, ABOUT_COPY["en"])
        theme = self.theme
        dark = theme == "dark" or theme == "system"
        page_background = "#101620" if dark else "#f6f8fb"
        text_color = "#eef3f8" if dark else "#07111c"
        muted_text = "#c8d3df" if dark else "#263241"
        accent = "#8fd8ff" if dark else "#0b6fa7"
        panel_background = "#151b24" if dark else "#ffffff"
        border_color = "#2b3545" if dark else "#c7d3e0"

        def items(name: str) -> str:
            return "".join(f"<li>{escape(platform_text(item))}</li>" for item in copy[name])

        return (
            "<style>"
            f"body{{font-family:Calibri,sans-serif;color:{text_color};background:{page_background};font-size:14px;margin:0;}}"
            f".card{{background:{panel_background};border:1px solid {border_color};border-radius:12px;padding:18px 20px;}}"
            "h1{font-size:26px;margin:0 0 4px 0;font-weight:800;}"
            f".version{{color:{accent};font-weight:700;margin-bottom:14px;}}"
            f".intro{{color:{muted_text};font-size:15px;line-height:1.35;margin:0 0 18px 0;}}"
            f"h2{{color:{accent};font-size:17px;margin:18px 0 8px 0;font-weight:800;}}"
            f"ul{{margin:0 0 4px 19px;padding:0;color:{muted_text};line-height:1.38;}}"
            "li{margin:5px 0;}"
            "</style>"
            "<div class='card'>"
            f"<h1>{escape(APP_DISPLAY_NAME)}</h1>"
            f"<div class='version'>Version {escape(__version__)} · {escape(APP_WINDOW_TITLE)}</div>"
            f"<p class='intro'>{escape(platform_text(copy['intro']))}</p>"
            f"<h2>{escape(copy['rights_title'])}</h2><ul>{items('rights')}</ul>"
            f"<h2>{escape(copy['privacy_title'])}</h2><ul>{items('privacy')}</ul>"
            f"<h2>{escape(copy['disclaimer_title'])}</h2><ul>{items('disclaimer')}</ul>"
            "</div>"
        )

    def apply_locale(self, language_code: str) -> None:
        self.ui_language = language_code
        self.setWindowTitle(t(language_code, "settings_title"))
        self.tabs.setTabText(0, t(language_code, "general"))
        self.tabs.setTabText(1, t(language_code, "api"))
        self.tabs.setTabText(2, t(language_code, "about"))
        self.provider_label.setText(t(language_code, "provider"))
        self.primary_language_label.setText(t(language_code, "primary_language"))
        self.theme_label.setText(t(language_code, "theme"))
        self.theme_input.setItemText(0, t(language_code, "theme_system"))
        self.theme_input.setItemText(1, t(language_code, "theme_dark"))
        self.theme_input.setItemText(2, t(language_code, "theme_light"))
        self.autostart_checkbox.setText(t(language_code, "autostart"))
        self.desktop_shortcut_checkbox.setText(t(language_code, "desktop_shortcut"))
        self.guide_label.setText(t(language_code, "guide"))
        self.guide_button.setToolTip(t(language_code, "guide_tooltip"))
        self.api_header_label.setText(t(language_code, "api_keys_models"))
        self.recommendations_label.setText(t(language_code, "recommendations"))
        self.info_button.setToolTip(t(language_code, "info_tooltip"))
        self.about_browser.setHtml(self._about_html())
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
            label.setText("✕")
            label.setObjectName("KeyStatusBad")
            label.setToolTip(message or t(self.ui_language, "key_not_checked"))
            self.key_valid_status[provider] = False
        label.style().unpolish(label)
        label.style().polish(label)

    def _on_key_text_changed(self, provider: str) -> None:
        if self.key_inputs[provider].text().strip():
            self.update_api_key_status(provider, "saved", t(self.ui_language, "key_not_checked"))
        elif self.saved_key_status.get(provider):
            self.update_api_key_status(provider, "saved", t(self.ui_language, "key_not_checked"))
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
