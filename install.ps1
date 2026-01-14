# Check requirements
Write-Host "Checking for Python..." -ForegroundColor Cyan
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}

Write-Host "Checking for GitHub CLI (gh)..." -ForegroundColor Cyan
if (-not (Get-Command "gh" -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI ('gh') is not installed."
    Write-Host "Please install it: https://cli.github.com/"
    exit 1
}

Write-Host "Checking for Git..." -ForegroundColor Cyan
if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    Write-Error "Git is not installed."
    exit 1
}

# Install Python deps
Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

# Create Startup Shortcut
$wsh = New-Object -ComObject WScript.Shell
$startupPath = $wsh.SpecialFolders.Item("Startup")
$shortcutPath = Join-Path $startupPath "PushAgent.lnk"
$ahkScriptPath = Join-Path $PWD "hotkey.ahk"

Write-Host "Creating startup shortcut at: $shortcutPath" -ForegroundColor Cyan

$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $ahkScriptPath
$shortcut.WorkingDirectory = $PWD
$shortcut.Description = "GitHub Push Agent Hotkey"
$shortcut.Save()

Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "1. Ensure AutoHotkey v2 is installed."
Write-Host "2. Double-click 'hotkey.ahk' to start the agent now."
Write-Host "3. Press Ctrl+Shift+G to test."
Write-Host "NOTE: To use AI features, get a free API key from https://aistudio.google.com/app/apikey"