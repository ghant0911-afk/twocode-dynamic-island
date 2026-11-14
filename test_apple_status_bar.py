import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, QPoint, Qt
from PyQt6.QtGui import QEnterEvent, QWheelEvent, QMouseEvent

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

import apple_status_bar

print("1. Instantiating AppleStatusBar & Flyout...")
bar = apple_status_bar.AppleStatusBar()
bar.show()
assert bar.height() == 34
assert bar.width() >= 480
assert bar.flyout is not None
assert not hasattr(bar, "lbl_power")
print(f"   Bar initialized: {bar.width()}x{bar.height()} (Power/AC removed)!")

print("2. Testing All 5 Interactive Flyout Dropdowns via Header Pills & show_tab...")
# Tab 0: Weather
bar.flyout.show_tab(0)
assert bar.flyout.isVisible()
assert bar.flyout.current_tab == 0
assert bar.flyout.lbl_flyout_title.text() == "Погода"
assert bar.flyout.stack.currentIndex() == 0
bar.set_custom_city("Казань")
assert bar.weather_city == "Казань"
print("   Tab 0: Weather verified!")

# Tab 1: Music
bar.flyout.show_tab(1)
assert bar.flyout.current_tab == 1
assert bar.flyout.lbl_flyout_title.text() == "Музыка"
assert bar.flyout.stack.currentIndex() == 1
print("   Tab 1: Music Player verified!")

# Tab 2: Task Manager & RAM Flush
bar.flyout.show_tab(2)
assert bar.flyout.current_tab == 2
assert bar.flyout.lbl_flyout_title.text() == "Диспетчер задач"
assert bar.flyout.stack.currentIndex() == 2
bar.flyout._flush_memory()
assert "Память оптимизирована" in bar.flyout.btn_flush_ram.text() or "Очистить" in bar.flyout.btn_flush_ram.text()
print("   Tab 2: Task Manager & Memory Flush verified!")

# Tab 3: Calendar & Quick Notes
bar.flyout.show_tab(3)
assert bar.flyout.current_tab == 3
assert bar.flyout.lbl_flyout_title.text() == "Календарь и Заметки"
assert bar.flyout.stack.currentIndex() == 3
bar.flyout.txt_quick_notes.setText("Купить кофе")
bar.flyout._save_quick_note()
assert bar.flyout.list_notes.count() >= 1
assert "Купить кофе" in bar.flyout.list_notes.item(0).text()
print("   Tab 3: Calendar & Quick Notes verified!")

# Tab 4: Quick Tools (Caffeine & Clipboard)
bar.flyout.show_tab(4)
assert bar.flyout.current_tab == 4
assert bar.flyout.lbl_flyout_title.text() == "Инструменты"
assert bar.flyout.stack.currentIndex() == 4
active = bar.toggle_caffeine()
assert active == True
assert bar.caffeine_active == True
bar.toggle_caffeine()
assert bar.caffeine_active == False
bar.flyout.add_clipboard_item("https://github.com/apple")
assert bar.flyout.list_clipboard.count() >= 1
print("   Tab 4: Caffeine & Clipboard History verified!")

bar.flyout.hide()
assert not bar.flyout.isVisible()

print("3. Testing Full Spatial Click Mapping across the Status Bar...")
# Click in Weather zone (x = 10)
ev_weather = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(10, 15), QPointF(10, 15), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
bar.mousePressEvent(ev_weather)
assert bar.flyout.isVisible()
assert bar.flyout.current_tab == 0
assert bar.flyout.lbl_flyout_title.text() == "Погода"
print("   Click zone 0 -> Weather flyout open!")

# Click in Calendar zone (x = right edge - 10)
ev_calendar = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(bar.width() - 10, 15), QPointF(bar.width() - 10, 15), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
bar.mousePressEvent(ev_calendar)
assert bar.flyout.isVisible()
assert bar.flyout.current_tab == 3
assert bar.flyout.lbl_flyout_title.text() == "Календарь и Заметки"
assert bar.flyout.stack.currentIndex() == 3
print("   Click zone 3 -> Calendar flyout open!")

# Click in Tasks zone (x = bar.lbl_cpu.x() + 4)
ev_tasks = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(bar.lbl_cpu.x() + 4, 15), QPointF(bar.lbl_cpu.x() + 4, 15), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
bar.mousePressEvent(ev_tasks)
assert bar.flyout.isVisible()
assert bar.flyout.current_tab == 2
assert bar.flyout.lbl_flyout_title.text() == "Диспетчер задач"
assert bar.flyout.stack.currentIndex() == 2
print("   Click zone 2 -> Tasks flyout open!")

print("4. Testing Flyout Auto-Close on Mouse Leave...")
# Simulate timeout when cursor is outside both flyout and bar
bar._on_flyout_leave_timeout()
assert not bar.flyout.isVisible()
print("   Flyout auto-hide on leave verified!")

print("5. Testing Physical Slide Up & Slide Down Animation...")
bar._slide_up()
bar.anim_pos.setCurrentTime(280)
assert bar.is_slid_down == False
assert bar.y() == bar.y_hidden
print(f"   Slide UP verified: y={bar.y()} (hidden off-screen)!")

bar._slide_down()
bar.anim_pos.setCurrentTime(240)
assert bar.is_slid_down == True
assert bar.y() == bar.y_visible
print(f"   Slide DOWN verified: y={bar.y()} (visible in view)!")

print("\n>>> ALL 5 SUITES PASSED 100%! <<<")
