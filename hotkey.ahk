; PushAgent Hotkey (Ctrl+Shift+G)
#Requires AutoHotkey v2.0

^+g::
{
    scriptDir := A_ScriptDir
    path := GetExplorerPath()
    if (path = "")
        Run 'pythonw.exe "' scriptDir '\agent_gui.py"',, "Hide"
    else
        Run 'pythonw.exe "' scriptDir '\agent_gui.py" "' path '"',, "Hide"
}

GetExplorerPath() {
    try {
        explorer := ComObject("Shell.Application")
        hwnd := WinExist("A")
        for window in explorer.Windows {
            if (window.HWND = hwnd)
                return window.Document.Folder.Self.Path
        }
    }
    return ""
}
