; GitHub Push Agent - Hotkey Script (AHK v2)
; Press Ctrl+Shift+G while in File Explorer to launch the agent for that folder

#Requires AutoHotkey v2.0

^+g::
{
    ; Get the path of the current Explorer window
    folderPath := GetExplorerPath()
    
    if (folderPath = "") {
        ; Fallback if not in Explorer
        Run "pythonw.exe agent_gui.py"
    } else {
        ; Run with path argument. We wrap the path in quotes to handle spaces.
        Run 'pythonw.exe agent_gui.py "' folderPath '"'
    }
}

GetExplorerPath() {
    try {
        explorer := ComObject("Shell.Application")
        for window in explorer.Windows {
            try {
                if (window.HWND = WinExist("A")) {
                    return window.Document.Folder.Self.Path
                }
            }
        }
    }
    return ""
}
