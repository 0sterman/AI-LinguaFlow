from __future__ import annotations

import os


SERVICE_NAME = "WindowsDoubleCtrlTranslator"
ENV_NAMES = {
    "openai": "OPENAI_API_KEY",
    "google": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}
LEGACY_OPENAI_ACCOUNT = "openai_api_key"


def account_name(provider: str) -> str:
    return f"{provider}_api_key"


class ApiKeyStore:
    def __init__(self) -> None:
        try:
            import keyring  # type: ignore
        except ImportError:
            keyring = None
        self._keyring = keyring

    def get_api_key(self, provider: str = "openai") -> str | None:
        if self._keyring is not None:
            try:
                stored = self._keyring.get_password(SERVICE_NAME, account_name(provider))
                if not stored and provider == "openai":
                    stored = self._keyring.get_password(SERVICE_NAME, LEGACY_OPENAI_ACCOUNT)
                if stored:
                    return stored
            except Exception:
                pass

        env_key = os.getenv(ENV_NAMES.get(provider, ""))
        if not env_key and provider == "google":
            env_key = os.getenv("GOOGLE_API_KEY")
        return env_key or None

    def save_api_key(self, provider: str, api_key: str) -> None:
        cleaned = api_key.strip()
        if not cleaned:
            raise ValueError("API key is empty")
        if self._keyring is None:
            raise RuntimeError("keyring is not installed")
        self._keyring.set_password(SERVICE_NAME, account_name(provider), cleaned)

    def delete_api_key(self, provider: str) -> None:
        if self._keyring is None:
            return
        try:
            self._keyring.delete_password(SERVICE_NAME, account_name(provider))
        except Exception:
            pass
        if provider == "openai":
            try:
                self._keyring.delete_password(SERVICE_NAME, LEGACY_OPENAI_ACCOUNT)
            except Exception:
                pass
