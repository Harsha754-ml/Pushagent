# GitHub Push Agent (AI Powered)

A powerful Windows automation tool that streamlines your git workflow. It detects your current project, handles git initialization/commits/pushing, and leverages AI to generate commit messages and README files.

## Features
- **Global Hotkey:** `Ctrl + Shift + G`
- **Smart Detection:** Automatically grabs the folder path from File Explorer or asks via Picker.
- **AI Integration (Gemini):**
  - **Auto-Commit Messages:** Generates concise, professional commit messages based on `git diff`.
  - **Auto-README:** Analyzes your file structure to write a complete `README.md`.
- **Git Automation:**
  - Handles `git init`, `.gitignore` creation, `git add`, `commit`, and `push`.
  - Creates new private/public repos on GitHub automatically via CLI.
- **Secure:** API Keys are stored securely in Windows Credential Manager.

## Requirements
1. **Windows 10/11**
2. **AutoHotkey v2** ([Download](https://www.autohotkey.com/))
3. **Python 3.10+** (Ensure `pythonw` is in PATH)
4. **Git** and **GitHub CLI (`gh`)**
   - Run `gh auth login` before using.

## Installation

1. Open PowerShell in this directory:
   ```powershell
   .\install.ps1
   ```
2. The script will install Python libraries (`customtkinter`, `requests`, `keyring`) and set up the startup shortcut.

## Usage

1. **Start the Agent:**
   - Double-click `hotkey.ahk` (it also starts automatically on reboot).
2. **Trigger:**
   - Navigate to a project folder.
   - Press **`Ctrl` + `Shift` + `G`**.
3. **First Run Setup:**
   - Enter your **Gemini API Key** (get one [here](https://aistudio.google.com/app/apikey)) and click "Save Key".
4. **Workflow:**
   - **New Repo:** It suggests a name. Select Private/Public.
   - **Commit:** Type manually or check "Generate with Gemini" for AI magic.
   - **README:** Select "Generate with Gemini" to create documentation instantly.
   - **Execute:** Click the rocket button.

## Troubleshooting
- **Script doesn't start?** Ensure AutoHotkey v2 is installed.
- **AI errors?** Check your internet connection and API Key validity.
- **Git errors?** Ensure you are logged in via `gh auth login` and `git config user.name` is set.