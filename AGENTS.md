# AGENTS.md

## Project

AI-LinguaFlow is a Windows tray translator. It listens for `Ctrl+C+C`, reads the copied selection, translates it through the selected AI provider, shows a compact popup, and keeps local translation history.

Repository: `0sterman/AI-LinguaFlow`

## Tone and Collaboration

- Use a friendly but critical mentor style.
- Do not blindly agree with requested changes. Point out privacy, security, cost, UX, or reliability risks directly.
- Separate verified facts from assumptions when discussing model behavior, pricing, APIs, or Windows limitations.
- Prefer practical implementation over broad redesign unless the current architecture is clearly wrong.

## Runtime and Commands

Use Python 3.12 on Windows.

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run locally:

```powershell
python -m translator_app
```

Run tests:

```powershell
python -m pytest
```

Build the Windows executable:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

The built app is created at:

```text
dist\WindowsTranslator\WindowsTranslator.exe
```

## Architecture

- `translator_app/app.py`: tray app, hotkey flow, translation orchestration, settings/history dialogs.
- `translator_app/ui.py`: PySide6 popup, settings UI, history UI.
- `translator_app/openai_client.py`: provider API clients for OpenAI, Google Gemini, and Anthropic.
- `translator_app/languages.py`: supported languages, lightweight local detection, primary-language routing.
- `translator_app/history.py`: local SQLite translation history.
- `translator_app/secure_store.py`: API key storage through Windows Credential Manager/keyring with environment fallback.
- `translator_app/config.py`: user config under `%APPDATA%\WindowsTranslator`.
- `translator_app/hotkey.py`: isolated `Ctrl+C+C` detection logic.
- `translator_app/startup.py`: Windows startup and desktop shortcut integration.
- `assets/app_icon.ico`: executable, tray, and shortcut icon based on the repository/avatar style.

Keep business logic testable outside the GUI. Put reusable logic in small modules and test it directly.

## Supported Languages

Supported translation targets:

- Russian
- English
- German
- Spanish
- Simplified Chinese

The primary language is user-configurable in Settings. Default routing should translate into the primary language unless the text appears to already be in that language, in which case it should use the configured fallback behavior in `languages.py`.

Language detection is intentionally lightweight. Russian and Chinese detection are more reliable than English/German/Spanish. Do not overpromise detection quality in UI text or documentation.

## AI Providers

Supported providers:

- OpenAI
- Google Gemini
- Anthropic Claude

Default model values are defined in `translator_app/config.py`.

Do not hardcode API keys. Never log copied text, translation text, or API keys. API keys must be read from Windows Credential Manager/keyring first, then environment variables:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `ANTHROPIC_API_KEY`

If provider API details or model recommendations may have changed, verify against official provider documentation before updating defaults or README text.

## Privacy and Local Data

Translation history is stored locally in:

```text
%APPDATA%\WindowsTranslator\history.sqlite3
```

Treat history as sensitive user data. Do not move it into the project folder, do not include it in Git, and do not send it anywhere except the selected translation provider for the current translation request.

History should remain compact and searchable. Keep deletion/clear-history behavior available.

## UX Rules

- The popup should stay compact, fast, and unobtrusive.
- Do not replace the clipboard with translations automatically; keep explicit copy buttons.
- Keep the `История` button visible and simple.
- Settings should expose provider, primary language, API keys, model names, desktop shortcut, and autostart.
- The executable, tray icon, and desktop shortcut should use `assets/app_icon.ico`.
- Avoid adding large dashboards or heavy flows. This is a quick translator, not a knowledge-management app.
- Any feature that stores more user data needs a clear local-only behavior and an easy way to delete data.

## Testing Expectations

Before finishing code changes, run:

```powershell
python -m pytest
python -m compileall translator_app tests
```

For UI or packaging changes, also rebuild:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

After rebuilding, briefly launch the executable and confirm it starts without immediately exiting.

## Git and Generated Files

Commit source changes to Git. Push to `origin/main` when the user asks for GitHub updates or the change is complete and already expected to be published.

Do not commit generated folders:

- `build/`
- `dist/`
- `.pytest_cache/`
- `__pycache__/`
- local databases or `.env` files

If `dist\WindowsTranslator` is locked during build, stop the running `WindowsTranslator` process and rebuild.

## Current Known Limits

- Global hotkeys may not work inside elevated apps unless AI-LinguaFlow runs with matching privileges.
- Language detection is heuristic.
- Very long text is rejected by the first-version length limit in `openai_client.py`.
- The executable is a PyInstaller folder build and is larger than a native Windows app.
