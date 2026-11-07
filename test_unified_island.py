import sys
import os
import time

os.chdir(r"C:\Users\bear_\.gemini\antigravity\scratch\twocode_island_unified")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QCursor

# Use offscreen platform for automated test suite
os.environ["QT_QPA_PLATFORM"] = "offscreen"

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

import main

print("1. Testing LiveAnimatedRobo modes...")
robo = main.LiveAnimatedRobo(size=48)
for m in ["idle", "music", "thinking", "coding", "eating", "nom", "hungry", "heart", "shocked", "star", "gaming"]:
    robo.set_mode(m)
    assert robo.mode == m, f"Mode {m} failed to set!"
    # Trigger paintEvent
    robo.repaint()
    robo.advance()
print("   All LiveAnimatedRobo modes rendered without error!")

print("2. Testing TwoCodeIsland instantiation...")
island = main.TwoCodeIsland()
assert island.is_expanded == False, "Island should start collapsed"
assert island.is_pinned == False, "Island should start unpinned"
print("   TwoCodeIsland initialized cleanly!")

print("3. Testing Hover Expand...")
island.expand()
assert island.is_expanded == True, "Island should be expanded"
assert island.is_pinned == False, "Crucial: Island must NOT be pinned when expanded via hover!"
assert island.hover_watchdog.isActive() == True, "Hover watchdog should be active while unpinned and expanded"
print("   Hover expand verified: is_expanded=True, is_pinned=False!")

print("4. Testing Toggle Pin...")
island.toggle_pin()
assert island.is_pinned == True, "Island should be pinned after toggle_pin"
assert island.hover_watchdog.isActive() == False, "Hover watchdog should stop when pinned"
island.toggle_pin()
assert island.is_pinned == False, "Island should be unpinned after second toggle"
print("   Toggle pin verified!")

print("5. Testing Drop Event & Eating Animation...")
dummy_file = os.path.join(r"C:\Users\bear_\.gemini\antigravity\scratch\twocode_island_unified", "test_file.txt")
with open(dummy_file, "w", encoding="utf-8") as f:
    f.write("test content for shelf")

island.on_remote_shelf_add([dummy_file])
assert island.pill_robo.mode == "eating", f"pill_robo should be eating, got {island.pill_robo.mode}"
assert island.file_shelf.drop_robo.mode == "eating", f"drop_robo should be eating, got {island.file_shelf.drop_robo.mode}"
assert island.robo_tab.robo.mode == "eating", f"robo_tab.robo should be eating, got {island.robo_tab.robo.mode}"
print("   Eating animation triggered across all 3 mascots successfully!")

print("6. Testing Auto Collapse...")
# Move cursor far outside
QCursor.setPos(QPoint(5000, 5000))
island.auto_collapse()
assert island.is_expanded == False, "Island should be collapsed"
assert island.is_pinned == False, "Island should be unpinned"
assert island.hover_watchdog.isActive() == False, "Watchdog should be stopped after collapse"
print("   Auto-collapse verified!")

print("7. Testing Desktop Robo Pet Spawning & Toggling...")
island.spawn_desktop_pet()
assert island.desktop_pet is not None, "Desktop pet must be instantiated"
assert island.desktop_pet.isVisible() == True, "Desktop pet must be visible"
assert island.desktop_pet_enabled == True, "Desktop pet state must be enabled"
print("   Desktop pet spawned cleanly!")

island.dismiss_desktop_pet()
assert island.desktop_pet.isVisible() == False, "Desktop pet must be hidden after dismiss"
assert island.desktop_pet_enabled == False, "Desktop pet state must be disabled"
print("   Desktop pet dismissed cleanly!")

island.toggle_desktop_pet()
assert island.desktop_pet.isVisible() == True, "Desktop pet must be toggled on"
print("   Desktop pet toggled cleanly!")

print("8. Testing Desktop Pet Music Reactivity (Dynamic Headphones)...")
class DummyMediaState:
    def __init__(self, is_playing):
        self.is_active = True
        self.is_playing = is_playing
        self.title = "Cyberpunk Phonk"
        self.artist = "TwoCode"
        self.position_sec = 42
        self.duration_sec = 180
        self.thumbnail_bytes = None

music_on = DummyMediaState(is_playing=True)
island.on_media_state_changed(music_on)
assert island.desktop_pet.has_headphones == True, "Desktop pet must wear headphones when music plays!"
print("   Desktop pet headphones equipped dynamically on music play!")

music_off = DummyMediaState(is_playing=False)
island.on_media_state_changed(music_off)
assert island.desktop_pet.has_headphones == False, "Desktop pet must remove headphones when music stops!"
print("   Desktop pet headphones removed dynamically on music pause!")

print("9. Testing HTTP API Signals for Pet...")
main.global_signals.pet_dismiss_requested.emit()
assert island.desktop_pet.isVisible() == False, "HTTP signal dismiss must hide pet"
main.global_signals.pet_spawn_requested.emit()
assert island.desktop_pet.isVisible() == True, "HTTP signal spawn must show pet"
print("   HTTP API pet signals verified!")

# Clean up dummy test file
try:
    os.remove(dummy_file)
except Exception:
    pass

print("\n>>> ALL 9 GOAL ENFORCER TESTS PASSED WITH 100% SUCCESS! <<<")
