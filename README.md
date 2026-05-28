# Windows Translator

Small Windows tray translator. Hold `Ctrl` and press `C` twice quickly to translate the copied selection in a popup.

Default behavior:

- Non-Russian text translates to Russian.
- Russian text translates to English.
- The popup can retranslate to Russian, English, German, Spanish, or Simplified Chinese.
- Translation history is saved locally after installation under your Windows user profile.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m translator_app
```

On first run, the settings window opens automatically if the selected provider has no saved key. Open tray menu -> `Settings` any time to change provider, models, API keys, or autostart.

Supported providers and default models:

- OpenAI: `gpt-5-mini`
- Google Gemini: `gemini-2.5-flash-lite`
- Anthropic Claude: `claude-3-5-haiku-latest`

Environment variable fallbacks:

- OpenAI: `OPENAI_API_KEY`
- Google: `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`

## Build EXE

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

The executable will be created under `dist\WindowsTranslator\WindowsTranslator.exe`.

## Notes

- Translation history is stored only on this computer in `%APPDATA%\WindowsTranslator\history.sqlite3`.
- Use the `История` button in the popup or tray menu to open local history.
- The app does not replace your clipboard with the translation automatically. Use the popup copy button.
- The global keyboard hook may be blocked by some security tools or elevated apps. If it does not trigger inside an elevated app, run the translator with the same privilege level.
