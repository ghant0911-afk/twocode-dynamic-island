@echo off
chcp 65001 >nul
title Astra 3D Drum Studio Launcher
cls

echo =====================================================================
echo   🥁 TWOCODE DYNAMIC ISLAND - ASTRA 3D DRUM STUDIO PRO
echo =====================================================================
echo.

:: 1. Check Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python не обнаружен в системе PATH!
    echo Установите Python 3.8+ с сайта https://www.python.org/downloads/
    echo Обязательно отметьте галочку "Add python.exe to PATH" при установке.
    echo.
    pause
    exit /b 1
)

:: 2. Set Directory
cd /d "%~dp0vrm_models"
if not exist "drum_animator.html" (
    echo [ERROR] Не найден файл vrm_models\drum_animator.html!
    pause
    exit /b 1
)

set PORT=8098

:: 3. Check if server is already running on port 8098
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [INFO] Локальный сервер уже запущен на порту %PORT%.
) else (
    echo [INFO] Запускаем локальный веб-сервер на порту %PORT%...
    start /b "" python -m http.server %PORT% --bind 127.0.0.1 >nul 2>&1
    :: Wait 1.5 seconds for socket binding
    timeout /t 2 /nobreak >nul
)

:: 4. Open in default browser
echo [OK] 3D Студия готова! Открываем браузер...
start http://127.0.0.1:%PORT%/drum_animator.html

echo.
echo =====================================================================
echo   🚀 Студия открыта: http://127.0.0.1:%PORT%/drum_animator.html
echo.
echo   Горячие клавиши в редакторе:
echo     [W] - Перемещение (Translate Gizmo)
echo     [E] - Вращение суставов/палочек (Rotate Gizmo)
echo     [S] - Масштабирование установки (Scale Gizmo)
echo     [Пробел] - Переключение Local / World координат
echo     ЛКМ - вращение камеры, ПКМ - панорамирование, Колесико - зум
echo.
echo   Файлы калибровки и проектов:
echo     - astra_drum_animation.json (координаты барабанов и дорожки ударов)
echo     - drumstick_calibrator.html (калибровщик хвата палочек в ладонях)
echo.
echo   Для остановки сервера закройте это окно или нажмите Ctrl+C.
echo =====================================================================
echo.

pause
