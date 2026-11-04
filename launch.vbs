Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\Dynamic_Island_Work"
WshShell.Run """C:\Program Files\Python313\pythonw.exe"" ""D:\Dynamic_Island_Work\main.py""", 0, False
