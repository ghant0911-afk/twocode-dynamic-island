@echo off
chcp 65001 >nul
title TwoCode Dynamic Island Pro - Установка и Запуск
cd /d "%~dp0"

echo =======================================================
echo   TwoCode Dynamic Island Pro - Настройка на новом ПК
echo =======================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден в системе!
    echo Установите Python 3.10+ с сайта https://www.python.org/ и поставьте галочку "Add to PATH".
    pause
    exit /b 1
)

echo [1/3] Проверка и установка зависимостей (PyQt6, psutil, pywin32)...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Не удалось установить некоторые пакеты через pip без прокси.
)

echo [2/3] Создание ярлыка на Рабочем столе...
python create_shortcut.py

echo [3/3] Запуск TwoCode Dynamic Island...
start "" wscript.exe "launch.vbs"

echo.
echo =======================================================
echo   Готово! Остров запущен вверху экрана!
echo   Ярлык добавлен на ваш Рабочий стол.
echo =======================================================
timeout /t 3 >nul
exit /b 0
