Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir
pythonwPath = "C:\Users\bear_\AppData\Local\Programs\Python\Python312\pythonw.exe"
If Not fso.FileExists(pythonwPath) Then
    pythonwPath = "pythonw.exe"
End If
WshShell.Run """" & pythonwPath & """ """ & strDir & "\main.py""", 0, False
