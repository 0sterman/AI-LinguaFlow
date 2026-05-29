# LinguaFlow AI

LinguaFlow AI is a small Windows translator built around a fast `Ctrl+C+C` workflow for translating selected text in a popup. It also opens normally from the desktop shortcut for manual translation between selected languages.

Hotkeys:

`Ctrl+C+C`: fast selected-text translation in the compact popup.

Esc - clear all text
Ctrl+Enter - translate

Default behavior:

- Use `Ctrl+C+C` as the main speed feature for translating selected text without leaving the current app. On Windows this uses a native key-state listener so it works more reliably in browsers and other apps.
- Open the app to translate manually from a selected source language to a selected target language.
- In quick mode, the selected text translates to your primary language by default.
- If the text already appears to be in your primary language, it translates to a fallback language.
- The app supports Russian, English, German, Spanish, and Simplified Chinese.
- The interface follows the selected primary language.
- The popup can retranslate manually to any supported language.
- In the main window, press `Ctrl+Enter` to translate pasted text; `Enter` keeps working as a normal new line.
- Press `Esc` in the main window input field to clear the source text.
- After text is pasted or loaded into the main window, automatic translation starts after about `0.2` seconds.
- Translation history is saved locally after installation under your Windows user profile.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m translator_app
```

On first run, the settings window opens automatically if the selected provider has no saved key. Open tray menu -> `Settings` any time to change provider, primary language, models, API keys, desktop shortcut, or autostart. API keys can be checked with a real provider request and deleted from local secure storage.

The app uses a LinguaFlow AI icon and a clean dark interface based on the repository/avatar style. A desktop shortcut is created automatically on first run and can be toggled in Settings.

Supported providers and default models:

- OpenAI: `gpt-5-mini`
- Google Gemini: `gemini-2.5-flash-lite`
- Anthropic Claude: `claude-3-5-haiku-latest`

The model fields are editable combo boxes. The defaults stay cost-conscious, but users can choose another listed model or type an available model name manually.

Environment variable fallbacks:

- OpenAI: `OPENAI_API_KEY`
- Google: `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`

## Build EXE

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

The executable will be created under `dist\LinguaFlow AI\LinguaFlow AI.exe`.

## Build Installer

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_installer.ps1
```

The one-file installer will be created as `dist\LinguaFlow AI Setup.exe`. It defaults to `Program Files`, requests administrator rights, includes a setup wizard with language selection, a short product description, destination-folder selection, desktop and Start menu shortcut options, Windows uninstall registration, and a final reminder that a personal provider API key is required in `Settings -> API`; the built-in guide is available in `Settings -> General -> Guide`.

## Notes

- Translation history is stored only on this computer in `%APPDATA%\WindowsTranslator\history.sqlite3`.
- Use the `History` button in the popup or tray menu to open local history.
- Use the desktop shortcut or tray icon to open and control the app.
- Language detection before translation is lightweight local detection. Russian and Chinese are detected more reliably than English, German, and Spanish, so the manual language buttons remain useful.
- The app does not replace your clipboard with the translation automatically. Use the popup copy button.
- The global keyboard hook may be blocked by some security tools or elevated apps. If it does not trigger inside an elevated app, run the translator with the same privilege level.
