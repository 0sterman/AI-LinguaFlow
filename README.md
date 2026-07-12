# LinguaPopUp AI

Fast popup translation for selected text on Windows and macOS.

**Current Windows release: 2.1.1.** The macOS Intel build remains at **1.0.9**.

LinguaPopUp AI helps you translate text without breaking your workflow: select text anywhere, press the shortcut, and get a quick translation popup. It automatically translates selected text into your chosen target language, including mixed-language text, while preserving the meaning as clearly as possible. You can also open the main translator window for normal manual translation, choose your preferred target language, and keep local translation history on your computer.

Official landing page: [LinguaPopUp AI](https://0sterman.github.io/AI-LinguaFlow/)

<p align="center">
  <a href="https://0sterman.github.io/AI-LinguaFlow/assets/linguapopup-ai-main-window.png?v=2.1.1-screenshot">
    <img src="https://0sterman.github.io/AI-LinguaFlow/assets/linguapopup-ai-main-window.png?v=2.1.1-screenshot" alt="LinguaPopUp AI main translator window — click to open full size" width="900">
  </a>
</p>

## Download

Choose the installer for your system:

- **Windows:** [LinguaPopUp AI v2.1.1](https://github.com/0sterman/AI-LinguaFlow/releases/tag/v2.1.1)
- **macOS Intel:** [LinguaPopUp AI / legacy macOS build v1.0.9](https://github.com/0sterman/AI-LinguaFlow/releases/tag/v1.0.9)

Windows 2.1.1 removes the trailing punctuation from the quick-translation instruction in every supported UI language. Windows 2.1.0 introduced synchronized selection and scrolling between the original and translation panes, plus language-direction switching.

## Shortcuts

- **Windows popup translation:** `Ctrl+C+C`
- **macOS popup translation:** `Cmd (Ctrl)+C+C`
- **Clear text:** `Esc`
- **Translate in the main window:** `Ctrl+Enter` on Windows, `Cmd (Ctrl)+Enter` on macOS

## What It Supports

- Popup translation for selected text
- Automatic translation into the selected target language
- Mixed-language text translation with meaning preservation
- Manual translation in the main app window
- Synchronized selection between the original and translation panes on Windows 2.1.0
- Synchronized scrolling between the original and translation panes on Windows 2.1.0
- Language-direction switching in the main window on Windows 2.1.0
- Local translation history
- Configurable primary language
- OpenAI, Google Gemini, and Anthropic Claude providers

## API Key Required

LinguaPopUp AI does not include a shared translation API key.

After installation, enter your own API key for the selected provider in:

`Settings -> API`

## API Key Storage

Your API key is stored locally on your computer. LinguaPopUp AI uses the system key storage through `keyring`:

- **Windows:** Windows Credential Manager
- **macOS:** the system keychain/keyring available to the app

The key is saved under the local service entry used by the app and is not included in the installer, not published in this repository, and not shared with other users.

If no saved key is found, LinguaPopUp AI can also read provider keys from environment variables:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `ANTHROPIC_API_KEY`

Usage help is available inside the app in:

`Settings -> General -> Guide`

## Privacy

Your settings and translation history are stored locally on your computer. Text is sent only to the AI provider you choose for the current translation request.

## Source Code

This public repository is only for downloads and product information. The LinguaPopUp AI source code is private and proprietary.

Copyright (c) Roman Ostroumov / Oster. Copying, redistribution, reverse engineering, or modification is not permitted without written permission from Roman Ostroumov / Oster.
