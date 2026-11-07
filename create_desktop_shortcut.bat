@echo off
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Dynamic Island.lnk'); $sc.TargetPath = 'wscript.exe'; $sc.Arguments = '\"' + $PSScriptRoot + '\run.vbs\"'; $sc.WorkingDirectory = $PSScriptRoot; $sc.Description = 'Dynamic Island for Windows'; $sc.Save()"
echo Ярлык Dynamic Island успешно создан на Рабочем столе!
pause
