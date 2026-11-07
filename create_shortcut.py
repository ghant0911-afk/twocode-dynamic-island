import os
import win32com.client

wsh = win32com.client.Dispatch("WScript.Shell")
desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
shortcut_path = os.path.join(desktop, "TwoCode Dynamic Island.lnk")

sc = wsh.CreateShortcut(shortcut_path)
sc.TargetPath = "wscript.exe"
sc.Arguments = '"D:\\Dynamic_Island_Work\\launch.vbs"'
sc.WorkingDirectory = "D:\\Dynamic_Island_Work"
sc.Description = "TwoCode Dynamic Island Pro"
sc.Save()
print("Shortcut created at:", shortcut_path)
