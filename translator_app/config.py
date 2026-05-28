from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


APP_NAME = "WindowsTranslator"
CONFIG_DIR = Path.home() / "AppData" / "Roaming" / APP_NAME
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_MODELS = {
    "openai": "gpt-5-mini",
    "google": "gemini-2.5-flash-lite",
    "anthropic": "claude-3-5-haiku-latest",
}

MODEL_OPTIONS = {
    "openai": [
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "gpt-4o-mini",
    ],
    "google": [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ],
    "anthropic": [
        "claude-3-5-haiku-latest",
        "claude-3-5-haiku-20241022",
        "claude-3-haiku-20240307",
        "claude-3-7-sonnet-latest",
        "claude-sonnet-4-20250514",
    ],
}

THEME_OPTIONS = {"system", "dark", "light"}


@dataclass
class AppConfig:
    provider: str = "openai"
    primary_language: str = "ru"
    openai_model: str = DEFAULT_MODELS["openai"]
    google_model: str = DEFAULT_MODELS["google"]
    anthropic_model: str = DEFAULT_MODELS["anthropic"]
    enabled: bool = True
    autostart: bool = False
    desktop_shortcut: bool = True
    theme: str = "system"
    openai_key_valid: bool | None = None
    google_key_valid: bool | None = None
    anthropic_key_valid: bool | None = None
    popup_width: int = 520
    popup_height: int = 360

    def model_for_provider(self, provider: str | None = None) -> str:
        selected = provider or self.provider
        if selected == "google":
            return self.google_model
        if selected == "anthropic":
            return self.anthropic_model
        return self.openai_model

    def key_status_for_provider(self, provider: str) -> bool | None:
        if provider == "google":
            return self.google_key_valid
        if provider == "anthropic":
            return self.anthropic_key_valid
        return self.openai_key_valid

    def set_key_status_for_provider(self, provider: str, is_valid: bool | None) -> None:
        if provider == "google":
            self.google_key_valid = is_valid
        elif provider == "anthropic":
            self.anthropic_key_valid = is_valid
        else:
            self.openai_key_valid = is_valid


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        return AppConfig()

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppConfig()

    defaults = asdict(AppConfig())
    if "model" in data and "openai_model" not in data:
        data["openai_model"] = data["model"]
    defaults.update({key: value for key, value in data.items() if key in defaults})
    if defaults["provider"] not in DEFAULT_MODELS:
        defaults["provider"] = "openai"
    if defaults["primary_language"] not in {"ru", "en", "de", "es", "zh"}:
        defaults["primary_language"] = "ru"
    if defaults["theme"] not in THEME_OPTIONS:
        defaults["theme"] = "system"
    return AppConfig(**defaults)


def save_config(config: AppConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
