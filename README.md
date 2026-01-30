# GitHub Push Agent 🚀

**A modern, AI-powered Windows utility to automate your GitHub workflow.**

PushAgent integrates seamlessly with Windows Explorer and uses Google's Gemini AI to write professional commit messages and READMEs for you. Stop worrying about "git commit -m" and focus on coding.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![Gemini](https://img.shields.io/badge/AI-Gemini-8E75B2?logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- **🤖 AI Auto-Commit**: Analyzes your `git diff` and generates concise, context-aware commit messages using Gemini 1.5 Flash.
- **📝 AI README Generator**: Scans your project structure to generate a full, formatted `README.md` instantly.
- **📂 Explorer Integration**: Press `Ctrl+Shift+G` inside any folder to launch the agent with that context.
- **🔐 Secure**: API keys are stored safely in the Windows Credential Manager (keyring).
- **☁️ Remote Automation**: Creates new private/public repositories on GitHub or links to existing ones automatically.
- **🎨 Modern UI**: Clean, intuitive interface built with CustomTkinter for Windows 10+ aesthetic.
- **⚡ Single Instance**: Only one instance can run at a time—perfect for hotkey integration.

## 🛠️ Requirements

- **Windows 10/11** (64-bit)
- **Python 3.10+**
- **Git** (installed and in PATH)
- **GitHub CLI** (`gh` CLI, authenticated with GitHub account)
- **Google Gemini API Key** (free tier available)

## 📦 Installation

### Quick Setup

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/Harsha754-ml/Pushagent.git
   cd Pushagent
   ```

2. **Run the installer**:
   ```powershell
   .\install.ps1
   ```

### Manual Setup

1. **Install prerequisites**:
   ```powershell
   # Install GitHub CLI
   winget install GitHub.cli
   
   # Authenticate with GitHub
   gh auth login
   ```

2. **Install Python dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Get your Gemini API Key**:
   - Visit [Google AI Studio](https://aistudio.google.com/)
   - Click "Get API Key"
   - Copy your free API key

4. **(Optional) Setup Hotkey**:
   - Install [AutoHotkey v2](https://www.autohotkey.com/)
   - Run `hotkey.ahk`
   - Press `Ctrl+Shift+G` in any Windows Explorer window to launch!

## 🚀 Usage

### Launch Options

**From Command Line:**
```powershell
python agent_gui.py [optional_folder_path]
```

**Via Hotkey:**
- Press `Ctrl+Shift+G` in any Windows Explorer folder (requires AutoHotkey setup)

**Via Python:**
```bash
python agent_gui.py
```

### Workflow

1. **Settings Tab**:
   - Paste your Gemini API Key
   - Click "Save & Fetch Models"
   - (Optional) Test connection with "Test Selected Model"

2. **Main Tab**:
   - **Project Folder**: Select a folder with `Browse` or sync active Explorer with `🔄 Sync`
   - **Repository Options**:
     - *Existing Remote*: Link to an existing GitHub repository
     - *Create New Remote*: Generate a new GitHub repo
   - **Commit Message**: Type manually or check ✨ Generate with Gemini
   - **README.md**: Do nothing / Create Minimal / Generate with Gemini
   - Click **🚀 Push to GitHub**

3. **Sit Back**: The agent handles:
   - Git initialization (if needed)
   - Creating `.gitignore`
   - Adding files
   - Committing changes
   - Creating/linking remote repository
   - Pushing to origin

## 📂 Project Structure

```
pushagent/
├── agent_gui.py           # Main application (CustomTkinter UI)
├── hotkey.ahk             # AutoHotkey Explorer integration script
├── install.ps1            # PowerShell installation script
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── api_key.txt            # API key storage (git-ignored)
└── 2.0/                   # Experimental v2 (local LLM support)
    ├── app.py
    ├── analyzer.py
    ├── generator.py
    └── auditor.py
```

## 🔧 Configuration

### Environment Variables
- `GEMINI_API_KEY`: Set this to skip entering API key each time
- `PUSHAGENT_HOME`: Custom configuration directory (defaults to `%APPDATA%\PushAgent`)

### Secure Storage
API keys are encrypted and stored in **Windows Credential Manager** via Python's `keyring` library.

## ⚙️ Advanced

### Single Instance Behavior
- Uses IPC (Inter-Process Communication) on port `65432`
- When launched again, brings existing window to focus
- Supports path passing between instances

### Model Selection
The app auto-detects available Gemini models:
- Prioritizes `gemini-1.5-flash` (best quota limits)
- Falls back to `gemini-1.5-pro` if available
- Supports manual model selection in Settings

### Git Workflow
- Auto-creates `.gitignore` if missing
- Stages all files automatically
- Only commits if changes exist
- Supports creating/linking remote repositories

## 🤝 Contributing

Contributions welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m '✨ Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the **MIT License** - see the LICENSE file for details.

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "GitHub CLI not found" | Install from [cli.github.com](https://cli.github.com) and run `gh auth login` |
| "API Key is missing" | Get a free key from [Google AI Studio](https://aistudio.google.com/) |
| Hotkey not working | Ensure AutoHotkey v2 is installed and `hotkey.ahk` is running |
| "Quota exceeded" for a model | Switch to `gemini-1.5-flash` in Settings (better quota limits) |
| Permission denied on push | Ensure `gh auth login` completed successfully |

## 📞 Support

- **Issues & Bugs**: [GitHub Issues](https://github.com/Harsha754-ml/Pushagent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Harsha754-ml/Pushagent/discussions)

## 🔮 Roadmap

- [ ] Linux/macOS support
- [ ] Support for multiple AI providers (Claude, LLaMA, etc.)
- [ ] Commit message templates
- [ ] Auto-generate CHANGELOG
- [ ] Web-based UI
- [ ] VS Code extension

---

**Made with ❤️ by HarsH for developers who just want to code**

