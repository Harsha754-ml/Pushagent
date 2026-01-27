# GitHub Push Agent 🚀

**A modern, AI-powered Windows utility to automate your GitHub workflow.**

PushAgent integrates seamlessly with Windows Explorer and uses Google's Gemini AI to write professional commit messages and READMEs for you. Stop worrying about "git commit -m" and focus on coding.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![Gemini](https://img.shields.io/badge/AI-Gemini-8E75B2?logo=google&logoColor=white)

## ✨ Features

- **🤖 AI Auto-Commit**: Analyzes your `git diff` and generates concise, context-aware commit messages using Gemini 1.5 Flash.
- **📝 AI README Generator**: Scans your project structure to generate a full, formatted `README.md` instantly.
- **📂 Explorer Integration**: Press `Ctrl+Shift+G` inside any folder to launch the agent with that context.
- **🔐 Secure**: API keys are stored safely in the Windows Credential Manager.
- **☁️ Remote Automation**: Creates new private/public repositories on GitHub or links to existing ones automatically.

## 🛠️ Installation

1. **Prerequisites**:
   - Python 3.10+
   - GitHub CLI (`gh`) installed and authenticated:
     ```powershell
     winget install GitHub.cli
     gh auth login
     ```

2. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Get a Gemini API Key**:
   - Obtain a free API key from [Google AI Studio](https://aistudio.google.com/).

4. **(Optional) Setup Hotkey**:
   - Install [AutoHotkey v2](https://www.autohotkey.com/).
   - Run `hotkey.ahk`.
   - Now you can press `Ctrl+Shift+G` in any folder!

## 🚀 Usage

1. **Launch**: Run `python agent_gui.py` or use the hotkey.
2. **Settings**: Go to the **Settings** tab and paste your Gemini API Key.
3. **Select Folder**:
   - If opened via Hotkey, the folder is already selected.
   - Otherwise, click "Browse" or "🔄 Sync" to grab the active Explorer window.
4. **Push**:
   - **Commit Message**: Check "Generate with Gemini" to let AI write it.
   - **README**: Select "Generate with Gemini" if you need one.
   - Click **Push to GitHub**.

The agent will initialize git, add files, commit, create the remote repo (if needed), and push—all in one click.

## 📂 Project Structure

- `agent_gui.py`: Main application logic and UI (CustomTkinter).
- `hotkey.ahk`: AutoHotkey script for Explorer integration.
- `2.0/`: Experimental prototype exploring local LLM (Ollama) support.

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

