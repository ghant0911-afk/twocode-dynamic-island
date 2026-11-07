Set WshShell = CreateObject("WScript.Shell")
strDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir

pythonPath = ""
On Error Resume Next

Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")

Dim testPaths
testPaths = Array( _
    WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"), _
    WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"), _
    "C:\Program Files\Python312\pythonw.exe", _
    "C:\Program Files\Python313\pythonw.exe" _
)

For Each p In testPaths
    If fso.FileExists(p) Then
        pythonPath = p
        Exit For
    End If
Next

If pythonPath = "" Then
    pythonPath = "pythonw.exe"
End If

WshShell.Run """" & pythonPath & """ """ & strDir & "\main.py""", 0, False
