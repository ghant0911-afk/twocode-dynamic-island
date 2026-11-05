Set WshShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir
WshShell.Run """C:\Program Files\Python313\pythonw.exe"" """ & scriptDir & "\main.py""", 0, False
