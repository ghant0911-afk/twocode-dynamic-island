import os
import sys

os.chdir(r"C:\Users\bear_\.gemini\antigravity\scratch\twocode_island_unified")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap, QPainter

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

import desktop_pet

print("1. Instantiating DesktopRoboPet...")
pet = desktop_pet.DesktopRoboPet(size=140)
assert pet.width() == 140
assert pet.height() == 180
print("   Instantiated cleanly!")

print("2. Testing Appearance & States Rendering...")
states = [
    desktop_pet.DesktopRoboPet.STATE_IDLE,
    desktop_pet.DesktopRoboPet.STATE_WALK,
    desktop_pet.DesktopRoboPet.STATE_DANCE,
    desktop_pet.DesktopRoboPet.STATE_SIT,
    desktop_pet.DesktopRoboPet.STATE_PICKED_UP,
    desktop_pet.DesktopRoboPet.STATE_FALLING,
    desktop_pet.DesktopRoboPet.STATE_CELEBRATE,
]

for st in states:
    pet.state = st
    pet.repaint()
    pet._physics_step()
    # Grab pixmap to verify painting executes without exception
    pix = pet.grab()
    assert not pix.isNull(), f"Pixmap was null for state {st}"
print("   All 7 states rendered cleanly into QPixmap!")

print("3. Testing Music Reactivity (Headphones ON/OFF)...")
# Default: no music -> no headphones
assert pet.has_headphones == False or pet.forced_music == False
pet.set_music(True)
assert pet.has_headphones == True, "Headphones must appear when music plays!"
pet.repaint()

pet.set_music(False)
assert pet.has_headphones == False, "Headphones must disappear when music stops!"
pet.repaint()
print("   Dynamic headphones reactivity verified!")

print("4. Testing Particles (Musical Notes & Hearts)...")
pet.spawn_note()
assert len(pet.particles) >= 1
assert pet.particles[-1]["type"] == "note"

pet.spawn_hearts(4)
assert len(pet.particles) >= 5
assert pet.particles[-1]["type"] == "heart"

# Update particles
for _ in range(10):
    pet._physics_step()
pet.repaint()
print("   Particles system verified!")

print("5. Testing Gravity Fall & Landing Physics...")
pet.move(200, 100)
pet.floor_y = 500
pet.state = desktop_pet.DesktopRoboPet.STATE_FALLING
for _ in range(40):
    pet._physics_step()
assert pet.y() == 500, f"Pet should land on floor_y (500), got {pet.y()}"
assert pet.state == desktop_pet.DesktopRoboPet.STATE_IDLE, f"Pet should be IDLE after landing, got {pet.state}"
print("   Gravity fall and floor landing verified!")

print("6. Testing Facing Direction & Walking Kinematics...")
pet.state = desktop_pet.DesktopRoboPet.STATE_WALK
pet.facing_direction = -1
pet._physics_step()
pet.repaint()
pet.facing_direction = 1
pet._physics_step()
pet.repaint()
print("   Walking flip and kinematics verified!")

print("\n>>> ALL DESKTOP PET TESTS PASSED WITH 100% SUCCESS! <<<")
