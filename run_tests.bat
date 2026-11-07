@echo off
chcp 65001 >nul
echo ========================================================
echo   TwoCode Dynamic Island - Интерактивный тест на экране
echo ========================================================
echo.
python "%~dp0showcase_demo.py"
echo.
pause
