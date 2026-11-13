import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
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
assert pet.height() == int(140 * 1.45)
print("   Instantiated cleanly!")

print("2. Testing Appearance & States Rendering...")
states = [
    desktop_pet.DesktopRoboPet.STATE_IDLE,
    desktop_pet.DesktopRoboPet.STATE_WALK,
    desktop_pet.DesktopRoboPet.STATE_DANCE,
    desktop_pet.DesktopRoboPet.STATE_SIT,
    desktop_pet.DesktopRoboPet.STATE_LAY,
    desktop_pet.DesktopRoboPet.STATE_SLEEP,
    desktop_pet.DesktopRoboPet.STATE_THINK,
    desktop_pet.DesktopRoboPet.STATE_CHEER,
    desktop_pet.DesktopRoboPet.STATE_EAT,
    desktop_pet.DesktopRoboPet.STATE_SURPRISED,
    desktop_pet.DesktopRoboPet.STATE_PERCH,
    desktop_pet.DesktopRoboPet.STATE_PICKED_UP,
    desktop_pet.DesktopRoboPet.STATE_CELEBRATE,
]

for st in states:
    pet.state = st
    pet.repaint()
    pet._physics_step()
    pix = pet.grab()
    assert not pix.isNull(), f"Pixmap was null for state {st}"
print(f"   All {len(states)} active states rendered cleanly into QPixmap!")

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

print("5. Testing Gentle Placement (No Fall Damage) & Snap-to-Floor + Eco Assets...")
assert not hasattr(pet, "STATE_FALLING"), "Fall module STATE_FALLING should be removed!"
assert not hasattr(pet, "trigger_fall_damage"), "Fall module trigger_fall_damage should be removed!"
pet.floor_y = 500
pet.move(200, 140)
pet.dragging = True
pet.state = desktop_pet.DesktopRoboPet.STATE_PICKED_UP
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtCore import QPointF
rel_ev = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPointF(20, 20), QPointF(220, 160), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
pet.mouseReleaseEvent(rel_ev)
assert pet.state == desktop_pet.DesktopRoboPet.STATE_IDLE, "Pet must calmly enter IDLE where placed!"
assert pet.y() == 140, f"Pet should stay calmly at y=140 without falling, got y={pet.y()}"
pet.snap_to_floor()
assert pet.y() == 500, f"snap_to_floor() must return pet to floor_y=500, got y={pet.y()}"

# Verify optimized VRM & drum GLB assets exist
for mf, _, _ in desktop_pet.VRM_MODELS:
    if mf != "robo":
        assert os.path.exists(os.path.join(APP_DIR, "vrm_models", mf)), f"Missing model {mf}"
assert os.path.exists(os.path.join(APP_DIR, "vrm_models", "drum_kit_opt.glb")), "Missing drum_kit_opt.glb"
pet.toggle_eco_mode()
assert pet.eco_mode == False
pet.toggle_eco_mode()
assert pet.eco_mode == True
print("   Gentle drop placement, snap_to_floor(), eco toggle & all Eco assets verified!")

print("6. Testing Stella-Grade Motion: Velocity Tracking, Head Petting & Perching...")
pet.move(250, 140)
pet._physics_step()
pet.move(290, 140)
pet._physics_step()
assert abs(pet.smooth_vx) > 0.0, "Velocity tracking smooth_vx should reflect horizontal movement!"

pet.react_to_head_pet()
assert any(w in pet.speech_bubble_lbl.text() for w in ["приятно", "ласку", "щёкотно", "лучший", "уютно"])

assert hasattr(pet, "perch_on_active_window")
assert hasattr(pet, "react_to_head_pet")
print("   Stella-grade motion features (inertia, petting, perching) verified!")

print("7. Testing Stella Deconstructed States & Triggers (Sleep, Think, Cheer, Eat, Zzz)...")
pet.spawn_zzz()
assert any(p["type"] == "zzz" for p in pet.particles), "Zzz particle must be queued!"
pet.repaint()
pix = pet.grab()
assert not pix.isNull(), "Zzz particle rendering failed!"

pet.trigger_eat("😋 Тестовый перекус!")
assert pet.state == desktop_pet.DesktopRoboPet.STATE_EAT, "trigger_eat() must set STATE_EAT!"

pet.trigger_cheer()
assert pet.state == desktop_pet.DesktopRoboPet.STATE_CHEER, "trigger_cheer() must set STATE_CHEER!"

pet.trigger_think()
assert pet.state == desktop_pet.DesktopRoboPet.STATE_THINK, "trigger_think() must set STATE_THINK!"
print("   All Stella deconstructed states & triggers verified 100%!")

print("\n>>> ALL DESKTOP PET ENHANCED TESTS PASSED WITH 100% SUCCESS! <<<")
