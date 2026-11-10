# Astra 3D Drum Studio & Motion Animator Pro - PowerShell Launcher
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "Astra 3D Drum Studio Launcher"

Clear-Host
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  🥁 TWOCODE DYNAMIC ISLAND - ASTRA 3D DRUM STUDIO PRO" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python не обнаружен в системе PATH!" -ForegroundColor Red
    Write-Host "Установите Python 3.8+ с сайта https://www.python.org/downloads/"
    Write-Host "Обязательно отметьте галочку 'Add python.exe to PATH' при установке."
    Read-Host "Нажмите Enter для выхода..."
    exit 1
}

$modelsDir = Join-Path $PSScriptRoot "vrm_models"
if (-not (Test-Path (Join-Path $modelsDir "drum_animator.html"))) {
    Write-Host "[ERROR] Не найден каталог $modelsDir\drum_animator.html!" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода..."
    exit 1
}

$port = 8098

# 2. Check if port 8098 is already active
$isListening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue

if ($isListening) {
    Write-Host "[INFO] Локальный сервер уже запущен на порту $port." -ForegroundColor Green
} else {
    Write-Host "[INFO] Запускаем локальный веб-сервер на порту $port..." -ForegroundColor Yellow
    Start-Process python -ArgumentList "-m", "http.server", "$port", "--bind", "127.0.0.1", "--directory", "$modelsDir" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

# 3. Open in Default Browser
$targetUrl = "http://127.0.0.1:$port/drum_animator.html"
Write-Host "[OK] Открываем 3D редактор: $targetUrl" -ForegroundColor Cyan
Start-Process $targetUrl

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  🚀 Студия успешно запущена: $targetUrl" -ForegroundColor Green
Write-Host ""
Write-Host "  Быстрые клавиши в редакторе:" -ForegroundColor White
Write-Host "    [W] - Перемещение манипулятора (Translate Gizmo)"
Write-Host "    [E] - Вращение колец манипулятора (Rotate Gizmo)"
Write-Host "    [S] - Масштабирование установки (Scale Gizmo)"
Write-Host "    [Пробел] - Переключение системы координат Local / World"
Write-Host "    ЛКМ - вращение камеры, ПКМ - панорамирование, Колесико - зум"
Write-Host ""
Write-Host "  Для завершения работы просто закройте это окно." -ForegroundColor DarkGray
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "Нажмите Enter для выхода из лаунчера..."
