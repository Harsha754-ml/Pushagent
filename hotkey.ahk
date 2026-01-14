#Requires AutoHotkey v2.0

^+g::
{
    path := ""
    
    ; Try to get path from Explorer
    if WinActive("ahk_class CabinetWClass")
    {
        path := GetActiveExplorerPath()
    }
    ; Try to get path from VS Code (Best Effort: Title Parsing)
    else if WinActive("ahk_exe Code.exe")
    {
        title := WinGetTitle("A")
        ; VS Code titles are usually "FileName - FolderName - Visual Studio Code" or "FolderName - Visual Studio Code"
        ; We can't easily get the full path, but we can try to guess or just let the GUI ask if ambiguous.
        ; However, if the user opens VS Code via "code .", the working directory of the process MIGHT be the project root.
        ; Let's try to get the command line of the active process.
        
        pid := WinGetPID("A")
        path := GetProcessPath(pid)
    }

    ; Run the python script
    ; Using pythonw.exe to avoid console window
    ; Assuming pythonw is in PATH. If not, the install script should help or user needs to set it.
    
    scriptPath := A_ScriptDir . "\agent_gui.py"
    
    if (path != "")
    {
        Run "pythonw.exe `"" . scriptPath . "`" `"" . path . "`""
    }
    else
    {
        Run "pythonw.exe `"" . scriptPath . "`""
    }
}

GetActiveExplorerPath() {
    explorerHwnd := WinActive("ahk_class CabinetWClass")
    if (explorerHwnd)
    {
        for window in ComObject("Shell.Application").Windows
        {
            if (window.hwnd == explorerHwnd)
            {
                return window.Document.Folder.Self.Path
            }
        }
    }
    return ""
}

GetProcessPath(pid) {
    ; Attempt to get the CurrentDirectory of the process or extract from command line?
    ; Command line is easier via WMI but might be just "code .".
    ; If "code ." is used, the CWD of that process is usually the project path.
    ; But getting CWD of a remote process is hard.
    ; Let's stick to returning "" for VS Code to enforce the Folder Picker if we can't be sure.
    ; Getting the "FolderName" from title is risky as it's not a full path.
    
    return "" 
}