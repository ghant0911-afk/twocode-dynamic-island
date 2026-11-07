@echo off
chcp 65001 >nul
echo ====================================================
echo  Установка зависимостей для Dynamic Island Windows
echo ====================================================
echo.
python -m pip install --upgrade pip
python -m pip install PyQt6 psutil
echo.
echo Все библиотеки успешно установлены!
echo Нажмите любую клавишу для запуска...
pause >nul
start pythonw "%~dp0main.py"
exit
