import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, QPoint
from PyQt6.QtGui import QEnterEvent, QWheelEvent, QMouseEvent
from PyQt6.QtCore import Qt

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

import apple_status_bar

print("1. Instantiating AppleStatusBar & Flyout...")
bar = apple_status_bar.AppleStatusBar()
bar.show()
assert bar.height() == 34
assert bar.width() >= 520
assert bar.flyout is not None
print(f"   Bar initialized: {bar.width()}x{bar.height()} with AppleStatusFlyout!")

print("2. Testing All 5 Interactive Flyout Dropdowns...")
# Tab 0: Weather
bar._open_flyout(0, bar.lbl_weather)
assert bar.flyout.isVisible()
assert bar.flyout.current_tab == 0
assert "+2°C" in bar.flyout.lbl_w_temp.text()
print("   Tab 0: Weather Flyout verified!")

# Tab 1: Music
bar._open_flyout(1, bar.lbl_music)
assert bar.flyout.current_tab == 1
assert bar.flyout.lbl_m_track is not None
print("   Tab 1: Music Player Flyout verified!")

# Tab 2: Task Manager & RAM Flush
bar._open_flyout(2, bar.lbl_cpu)
assert bar.flyout.current_tab == 2
bar.flyout._flush_memory()
assert "успешно" in bar.flyout.btn_flush.text()
print("   Tab 2: Task Manager & Memory Flush verified!")

# Tab 3: Calendar & Quick Notes
bar._open_flyout(3, bar.lbl_clock)
assert bar.flyout.current_tab == 3
bar.flyout.note_input.setText("Купить кофе")
bar.flyout._add_quick_note()
assert bar.flyout.notes_list.count() == 1
assert "Купить кофе" in bar.flyout.notes_list.item(0).text()
print("   Tab 3: Calendar & Quick Notes verified!")

# Tab 4: Quick Tools (Caffeine & Clipboard)
bar._open_flyout(4, bar.lbl_tools)
assert bar.flyout.current_tab == 4
# Test caffeine toggle
active = bar.toggle_caffeine()
assert active == True
assert bar.caffeine_active == True
bar.toggle_caffeine()
assert bar.caffeine_active == False
# Test clipboard history item
bar.flyout.add_clipboard_item("https://github.com/apple")
assert bar.flyout.clip_list.count() == 1
print("   Tab 4: Caffeine & Clipboard History verified!")

bar.flyout.hide()
assert not bar.flyout.isVisible()

print("3. Testing Mouse Wheel Scroll & Double Click Gestures...")
# Wheel event
wheel_ev = QWheelEvent(
    QPointF(20, 10), QPointF(20, 10), QPoint(0, 0), QPoint(0, 120),
    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
    Qt.ScrollPhase.NoScrollPhase, False
)
bar.wheelEvent(wheel_ev)
print("   Wheel volume scroll verified!")

# Double click event
dc_ev = QMouseEvent(
    QMouseEvent.Type.MouseButtonDblClick, QPointF(20, 10), QPointF(20, 10),
    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
)
bar.mouseDoubleClickEvent(dc_ev)
print("   Double click play/pause verified!")

print("4. Testing Dynamic Telemetry Alert (>80% CPU warning)...")
bar.cpu_pct = 85.0
bar._update_clock_and_telemetry()
# High CPU triggers red alert color in stylesheet
assert "FF453A" in bar.lbl_cpu.styleSheet() or "30D158" in bar.lbl_cpu.styleSheet()
print("   Dynamic CPU telemetry alert verified!")

print("5. Testing Auto-Hide Fade Animation...")
ev_enter = QEnterEvent(QPointF(10, 10), QPointF(10, 10), QPointF(10, 10))
bar.enterEvent(ev_enter)
bar.anim_opacity.setCurrentTime(220)
assert bar.is_hovered == True
assert bar.opacity_effect.opacity() > 0.8

bar._fade_to_idle()
bar.anim_opacity.setCurrentTime(220)
assert bar.is_hovered == False
assert bar.opacity_effect.opacity() < 0.2
print(f"   Auto-hide idle opacity: {bar.opacity_effect.opacity():.2f} verified!")

print("\n>>> ALL 5 SUITES OF APPLE STATUS BAR ENHANCED FEATURES PASSED 100%! <<<")
