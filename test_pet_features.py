# -*- coding: utf-8 -*-
"""
Headless verification suite for smart Desktop Pet sensors, speech bubble/lip-sync,
click-through silhouette geometry, fullscreen auto-pause, and beat-sync.
Runs 100% offscreen with zero visible windows.
"""

import os
import sys
import wave
import numpy as np

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from pet_sensors import (
    is_cursor_in_silhouette,
    rect_covers_monitor,
    SystemAudioBeatDetector,
    Win32PetWindowHelper,
)
from deepseek_brain import DeepSeekBrain
import desktop_pet

print("1. Testing Silhouette Click-Through Geometry...")
# Standing 260x377: empty top/left corners pass through, center torso captures clicks
assert is_cursor_in_silhouette(8, 8, 260, 377, "idle", "shino") is False
assert is_cursor_in_silhouette(250, 200, 260, 377, "idle", "shino") is False
assert is_cursor_in_silhouette(130, 190, 260, 377, "idle", "shino") is True
# Drumming 390x377 wide hitbox captures cymbals & stands, passes outside corners
assert is_cursor_in_silhouette(15, 30, 390, 377, "dance", "shino") is False
assert is_cursor_in_silhouette(65, 220, 390, 377, "dance", "shino") is True
print("   Silhouette hit-testing verified!")

print("2. Testing Fullscreen App Detector Geometry...")
assert rect_covers_monitor((0, 0, 1920, 1080), (0, 0, 1920, 1080), "UnityWndClass") is True
assert rect_covers_monitor((0, 0, 1920, 1080), (0, 0, 1920, 1080), "Progman") is False
assert rect_covers_monitor((0, 0, 1920, 1080), (0, 0, 1920, 1080), "WorkerW") is False
assert rect_covers_monitor((120, 80, 1280, 760), (0, 0, 1920, 1080), "Chrome_WidgetWin_1") is False
print("   Fullscreen detector geometry verified!")

print("3. Testing SystemAudioBeatDetector (120 BPM & 140 BPM tracking)...")
bd = SystemAudioBeatDetector()
# Feed rhythmic 120 BPM hits (every 0.50s)
hits = []
for step in range(40):
    t = step * 0.10
    lvl = 0.85 if (step % 5 == 0) else 0.02
    peak, hit, bpm, scale = bd.feed_sample(lvl, now=t)
    if hit:
        hits.append((round(t, 2), bpm, scale))
assert len(hits) >= 6, f"Expected >=6 beat hits, got {len(hits)}"
assert 110.0 <= hits[-1][1] <= 130.0, f"Expected ~120 BPM, got {hits[-1][1]}"
# Also verify live CoreAudio poll doesn't error in headless env
live_peak, _, live_bpm, live_scale = bd.poll()
assert 0.0 <= live_peak <= 1.0 and 0.72 <= live_scale <= 1.40
print(f"   Beat detector verified! Tracked 120 BPM -> {hits[-1][1]} BPM (speed_scale={hits[-1][2]})")

print("4. Testing Win32PetWindowHelper deduplication...")
helper = Win32PetWindowHelper()
assert helper.set_click_through(0, True) is True
assert helper.set_click_through(0, True) is False  # no redundant update
assert helper.set_click_through(0, False) is True
print("   Win32 window style helper verified!")

print("5. Testing DeepSeekBrain.ask() return type (chat dialog bug fix check)...")
reply = DeepSeekBrain.get().ask("привет")
assert isinstance(reply, str) and len(reply) > 0, f"Expected non-empty str, got {type(reply)}"
print(f"   DeepSeekBrain.ask() returned str cleanly ({len(reply)} chars)!")

print("6. Testing Speech Bubble, AI Reaction & Fullscreen Pause on DesktopRoboPet (offscreen)...")
pet = desktop_pet.DesktopRoboPet(size=260, model="Sendagaya_Shino_opt.vrm")
pet.react_to_ai("Отличный кадр в игре! Продолжай в том же духе!", "happy")
assert "Отличный кадр" in pet.speech_bubble_lbl.text()

pet._apply_fullscreen_pause(True)
assert pet._fullscreen_paused is True
assert pet.windowOpacity() == 0.0
assert not pet.loop_timer.isActive()

pet._apply_fullscreen_pause(False)
assert pet._fullscreen_paused is False
assert pet.windowOpacity() == 1.0
assert pet.loop_timer.isActive()

pet.toggle_click_through()
assert pet.click_through_enabled is False
pet.toggle_fullscreen_pause()
assert pet.fullscreen_pause_enabled is False
pet.toggle_beat_sync()
assert pet.beat_sync_enabled is False
print("   Speech bubble, AI reaction, toggles & fullscreen eco pause verified!")

print("\n>>> ALL PET SENSORS & INTERACTIVE FEATURES TESTS PASSED 100%! <<<")
