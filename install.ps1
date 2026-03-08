Write-Host "Installing PushAgent..." -ForegroundColor Cyan

# Check Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Please install Python 3.10+."
    exit 1
}

# Check Git
if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    Write-Error "Git not found. Please install Git for Windows."
    exit 1
}

# Check GitHub CLI
if (-not (Get-Command "gh" -ErrorAction SilentlyContinue)) {
    Write-Warning "GitHub CLI (gh) not found. Install it from https://cli.github.com/ for repo creation features."
}

# Check AutoHotkey
$ahkPath = Get-Command "AutoHotkey64.exe" -ErrorAction SilentlyContinue
if (-not $ahkPath) {
    $ahkPath = Get-Command "AutoHotkey.exe" -ErrorAction SilentlyContinue
}
if (-not $ahkPath) {
    Write-Warning "AutoHotkey v2 not found. Install it from https://www.autohotkey.com/ for hotkey support."
}

# Install Python dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install Python dependencies."
    exit 1
}

# Create Startup Shortcut for Hotkey
$wsh = New-Object -ComObject WScript.Shell
$startup = $wsh.SpecialFolders.Item("Startup")
$link = Join-Path $startup "PushAgentHotkey.lnk"
$target = Join-Path $PWD "hotkey.ahk"

if (Test-Path $target) {
    $shortcut = $wsh.CreateShortcut($link)
    $shortcut.TargetPath = $target
    $shortcut.WorkingDirectory = $PWD.Path
    $shortcut.Save()
    Write-Host "Startup shortcut created." -ForegroundColor Green

    # Launch hotkey listener
    Start-Process $target
    Write-Host "Hotkey (Ctrl+Shift+G) is now active." -ForegroundColor Green
} else {
    Write-Warning "hotkey.ahk not found at $target. Skipping hotkey setup."
}

Write-Host "Installation complete!" -ForegroundColor Green
