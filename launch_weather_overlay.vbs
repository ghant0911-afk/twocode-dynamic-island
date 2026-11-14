' Desktop Weather Wallpaper Overlay - Silent Background Launcher
' Runs the wallpaper overlay using pythonw.exe without opening a command prompt window.

Set WshShell = CreateObject("WScript.Shell")
strCurrentDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
WshShell.CurrentDirectory = strCurrentDir

WshShell.Run "pythonw.exe """ & strCurrentDir & "desktop_weather_overlay.py""", 0, False
Set WshShell = Nothing
