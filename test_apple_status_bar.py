import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEvent, QPointF
from PyQt6.QtGui import QEnterEvent

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

import apple_status_bar

print("1. Instantiating AppleStatusBar...")
bar = apple_status_bar.AppleStatusBar()
bar.show()
assert bar.height() == 34, f"Expected height 34, got {bar.height()}"
assert bar.width() >= 520, f"Expected width >= 520, got {bar.width()}"
print(f"   Bar instantiated cleanly with size {bar.width()}x{bar.height()}!")

print("2. Testing Top-Right Screen Placement...")
screen = app.primaryScreen()
if screen:
    avail = screen.availableGeometry()
    expected_x = avail.right() - bar.width() - 12
    assert abs(bar.x() - expected_x) <= 2, f"Expected x ~ {expected_x}, got {bar.x()}"
    print(f"   Top-right positioning verified: x={bar.x()}, y={bar.y()}!")

print("3. Testing Telemetry & Clock Updates...")
bar._update_clock_and_telemetry()
assert "CPU" in bar.lbl_cpu.text()
assert "RAM" in bar.lbl_ram.text()
assert "⛅" in bar.lbl_weather.text()
assert len(bar.lbl_clock.text()) > 5
print(f"   Telemetry values verified: {bar.lbl_cpu.text()} | {bar.lbl_ram.text()} | {bar.lbl_clock.text()}!")

print("4. Testing Media Update (Seamless Inline Music)...")
class MockMedia:
    is_active = True
    is_playing = True
    title = "Lil Jon — Get Low"
    artist = "Lil Jon"
bar._on_media_update(MockMedia())
assert "Lil Jon" in bar.lbl_music.text()
print(f"   Seamless music label verified: '{bar.lbl_music.text()}'!")

print("5. Testing Auto-Hide & Hover Animation...")
# Simulate mouse enter
ev_enter = QEnterEvent(QPointF(10, 10), QPointF(10, 10), QPointF(10, 10))
bar.enterEvent(ev_enter)
bar.anim_opacity.setCurrentTime(220)
assert bar.is_hovered == True
assert bar.opacity_effect.opacity() > 0.8
print("   Hover reveal verified (opacity -> 0.98)!")

# Simulate mouse leave
bar._fade_to_idle()
bar.anim_opacity.setCurrentTime(220)
assert bar.is_hovered == False
assert bar.opacity_effect.opacity() < 0.2
print(f"   Idle auto-hide verified (opacity -> {bar.opacity_effect.opacity():.2f})!")

print("\n>>> ALL APPLE STATUS BAR TESTS PASSED 100%! <<<")
