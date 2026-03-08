# PushAgent Reborn

A minimalist, AI-powered Git wizard for Windows.

## Features
- **Global Hotkey:** `Ctrl+Shift+G` opens the wizard for your active folder.
- **Smart Context:** Automatically detects if you need to create a repo or push changes.
- **AI-Powered:** auto-generates commit messages and READMEs using Google Gemini.
- **Project Isolation:** Zero context leaking between projects.

## Setup
1. Run `install.ps1`.
2. Get a free API Key from [Google AI Studio](https://aistudio.google.com/app/apikey).
3. Press `Ctrl+Shift+G` in any project folder.
4. Enter your API Key on the first run.

## Workflow
1. **New Project?** The wizard asks for a name and creates a private GitHub repo instantly.
2. **Existing Project?** The wizard drafts a commit message for you.
3. **Review & Push:** You check the message, toggle README generation, and click Push.