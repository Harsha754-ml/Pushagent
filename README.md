# GitHub Push Agent (AI Powered)

A modern Windows desktop utility that uses Gemini AI to automate your GitHub workflow.

## Features
- **Secure Key Storage**: Uses Windows Credential Manager (via `keyring`) for API keys.
- **AI Commit Messages**: Analyzes your `git diff` to write professional commit messages.
- **AI README Generation**: Scans your project structure to generate a full `README.md`.
- **Remote Automation**: Creates new private/public repos via `gh` CLI or links to existing ones.
- **Explorer Integration**: Use `Ctrl+Shift+G` to launch the agent for your current folder.

## Setup
1. **Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
2. **GitHub CLI**: Ensure `gh` is installed and you are logged in:
   ```powershell
   gh auth login
   ```
3. **Gemini API**:
   - Get a key from [Google AI Studio](https://aistudio.google.com/).
   - Open the app, go to **Settings**, and save your key.

## Usage
- Run `python agent_gui.py [path]` to start manually.
- Run `hotkey.ahk` (requires AutoHotkey) to enable the `Ctrl+Shift+G` shortcut.
