@echo off
cd /d "%~dp0"

:: 1. Check local pythonw paths
if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" "%~dp0main.py"
    exit
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" "%~dp0main.py"
    exit
)
if exist "%ProgramFiles%\Python312\pythonw.exe" (
    start "" "%ProgramFiles%\Python312\pythonw.exe" "%~dp0main.py"
    exit
)
if exist "%ProgramFiles%\Python313\pythonw.exe" (
    start "" "%ProgramFiles%\Python313\pythonw.exe" "%~dp0main.py"
    exit
)

:: 2. Try pythonw from PATH
where pythonw >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" pythonw "%~dp0main.py"
    exit
)

:: 3. Try py launcher
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" py -3 "%~dp0main.py"
    exit
)

:: 4. Fallback to python
start "" python "%~dp0main.py"
exit
