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
pet.show()
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
    desktop_pet.DesktopRoboPet.STATE_HURT,
]

for st in states:
    pet.state = st
    pet.repaint()
    pet._physics_step()
    pix = pet.grab()
    assert not pix.isNull(), f"Pixmap was null for state {st}"
print("   All 8 states (including STATE_HURT) rendered cleanly into QPixmap!")

print("3. Testing 4 Expressive Dance Styles...")
pet.state = desktop_pet.DesktopRoboPet.STATE_DANCE
pet.has_headphones = True
for style_idx in range(4):
    pet.dance_style = style_idx
    pet.repaint()
    pet._physics_step()
    pix = pet.grab()
    assert not pix.isNull(), f"Dance style {style_idx} failed to render!"
print("   All 4 Dance Styles (Breakbeat, DJ Sky Pump, Shuffle kicks, Rave wave) verified!")

print("4. Testing Honest Music Reactivity (Stop Dancing on Pause)...")
pet.set_music(True)
assert pet.has_headphones == True, "Headphones must appear when music plays!"
assert pet.state == desktop_pet.DesktopRoboPet.STATE_DANCE, "Pet should start dancing when music plays!"

pet.set_music(False)
assert pet.has_headphones == False, "Headphones must disappear when music pauses!"
assert pet.state == desktop_pet.DesktopRoboPet.STATE_IDLE, "Pet MUST STOP dancing when music pauses!"
print("   Honest music reactivity verified: dance stops immediately on pause!")

print("5. Testing Fall Damage, Comic Squash & Orbiting Dizzy Stars...")
pet.move(200, 100)
pet.floor_y = 500
pet.fall_start_y = 100
pet.state = desktop_pet.DesktopRoboPet.STATE_FALLING
pet.vy = 8.0 # High velocity drop
pet.trigger_fall_damage(fall_dist=400, impact_speed=8.0)
assert pet.state == desktop_pet.DesktopRoboPet.STATE_HURT, "Pet must enter STATE_HURT on hard fall!"
assert pet.squash_factor > 1.2, "Pet must squash horizontally on impact!"
assert any(p["type"] == "dizzy_star" for p in pet.particles), "Pet must spawn orbiting dizzy stars!"
pet.repaint()
pix_hurt = pet.grab()
assert not pix_hurt.isNull()
# Simulate recovery after hurt_timer
pet.hurt_timer = 1
pet._physics_step()
assert pet.state == desktop_pet.DesktopRoboPet.STATE_IDLE, "Pet must recover back to IDLE after hurt daze!"
print("   Fall damage, comic impact squash, dizzy stars, and recovery verified!")

print("\n>>> ALL DESKTOP PET ENHANCED TESTS PASSED WITH 100% SUCCESS! <<<")
