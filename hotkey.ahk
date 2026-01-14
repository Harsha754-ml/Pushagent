#Requires AutoHotkey v2.0

^+g::
{
    path := ""
    
    ; 1. Try Explorer
    if WinActive("ahk_class CabinetWClass")
    {
        path := GetActiveExplorerPath()
    }
    ; 2. Try VS Code
    else if WinActive("ahk_exe Code.exe")
    {
        ; We cannot reliably get the full path from VS Code external API easily without IPC.
        ; However, the GUI can handle an empty path by showing the folder picker.
        ; OR we can try to copy the path if the user has focus on the sidebar? No, that's flaky.
        ; Let's pass blank, but we know we are coming from VS Code.
        ; The Python script will check if path is empty -> Open FileDialog.
        path := "" 
    }
    
    ; Run the python script
    scriptPath := A_ScriptDir . "\agent_gui.py"
    
    ; Wrap path in quotes if it exists
    args := ""
    if (path != "")
        args := " `"" . path . "`""

    ; Run with pythonw to avoid console
    Run "pythonw.exe `"" . scriptPath . "`"" . args
}

GetActiveExplorerPath() {
    explorerHwnd := WinActive("ahk_class CabinetWClass")
    if (explorerHwnd)
    {
        for window in ComObject("Shell.Application").Windows
        {
            if (window.hwnd == explorerHwnd)
            {
                try {
                    return window.Document.Folder.Self.Path
                }
            }
        }
    }
    return ""
}
