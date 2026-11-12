# -*- coding: utf-8 -*-
"""
Headless verification suite for smart Desktop Pet sensors, speech bubble/lip-sync,
click-through silhouette geometry, fullscreen auto-pause, beat-sync, and REAL screen-aware commentary.
Runs 100% offscreen with zero visible windows.
"""

import asyncio
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

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
from game_commentary import (
    GameCommentaryEngine,
    compute_frame_metrics,
    extract_hud_signals,
    _recognize_bgra_async,
    HAS_WINSDK_OCR,
)
from deepseek_brain import DeepSeekBrain
import desktop_pet

print("1. Testing Silhouette Click-Through Geometry...")
assert is_cursor_in_silhouette(8, 8, 260, 377, "idle", "shino") is False
assert is_cursor_in_silhouette(250, 200, 260, 377, "idle", "shino") is False
assert is_cursor_in_silhouette(130, 190, 260, 377, "idle", "shino") is True
assert is_cursor_in_silhouette(15, 30, 390, 377, "dance", "shino") is False
assert is_cursor_in_silhouette(65, 220, 390, 377, "dance", "shino") is True
print("   Silhouette hit-testing verified!")

print("2. Testing Fullscreen App Detector Geometry...")
assert rect_covers_monitor((0, 0, 1920, 1080), (0, 0, 1920, 1080), "UnityWndClass") is True
assert rect_covers_monitor((0, 0, 1920, 1080), (0, 0, 1920, 1080), "Progman") is False
assert rect_covers_monitor((0, 0, 1920, 1080), (0, 0, 1920, 1080), "WorkerW") is False
assert rect_covers_monitor((120, 80, 1280, 760), (0, 0, 1920, 1080), "Chrome_WidgetWin_1") is False
print("   Fullscreen detector geometry verified!")

print("3. Testing SystemAudioBeatDetector (120 BPM tracking)...")
bd = SystemAudioBeatDetector()
hits = []
for step in range(40):
    t = step * 0.10
    lvl = 0.85 if (step % 5 == 0) else 0.02
    peak, hit, bpm, scale = bd.feed_sample(lvl, now=t)
    if hit:
        hits.append((round(t, 2), bpm, scale))
assert len(hits) >= 6
assert 110.0 <= hits[-1][1] <= 130.0
live_peak, _, live_bpm, live_scale = bd.poll()
assert 0.0 <= live_peak <= 1.0 and 0.72 <= live_scale <= 1.40
print(f"   Beat detector verified! Tracked 120 BPM -> {hits[-1][1]} BPM (speed_scale={hits[-1][2]})")

print("4. Testing Win32PetWindowHelper deduplication...")
helper = Win32PetWindowHelper()
assert helper.set_click_through(0, True) is True
assert helper.set_click_through(0, True) is False
assert helper.set_click_through(0, False) is True
print("   Win32 window style helper verified!")

print("5. Testing DeepSeekBrain.ask() return type (chat dialog bug fix check)...")
reply = DeepSeekBrain.get().ask("привет")
assert isinstance(reply, str) and len(reply) > 0
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

print("7. Testing REAL Screen Telemetry, Windows Neural OCR & Grounded Commentary...")
# A) Visual frame metrics (dark frame -> crimson danger flash + scene cut)
dark_bgra = np.full((54, 96, 4), [18, 18, 18, 255], dtype=np.uint8)
m_dark, prev_rgb = compute_frame_metrics(dark_bgra, None)
assert m_dark["brightness"] < 25.0 and m_dark["is_black_frame"] is False

crimson_bgra = np.full((54, 96, 4), [25, 25, 220, 255], dtype=np.uint8)
m_red, _ = compute_frame_metrics(crimson_bgra, prev_rgb)
assert m_red["red_ratio"] > 5.0
assert m_red["motion"] > 90.0 and m_red["scene_cut"] is True

# B) Windows Neural OCR + HUD parsing on synthetic CS2 & IDE error HUD frames
if HAS_WINSDK_OCR:
    im = Image.new("RGBA", (800, 450), (20, 24, 34, 255))
    dr = ImageDraw.Draw(im)
    fnt = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
    dr.text((50, 50), "HEALTH: 14 / 100   SCORE 11:12", fill=(245, 245, 245, 255), font=fnt)
    dr.text((50, 120), "Bomb has been planted", fill=(255, 210, 90, 255), font=fnt)
    arr_bgra = np.array(im, dtype=np.uint8)[:, :, [2, 1, 0, 3]]
    ocr_lines = asyncio.run(_recognize_bgra_async(arr_bgra))
    hud = extract_hud_signals(ocr_lines)
    assert "low_hp" in hud["events"] and hud["hp_val"] == 14, f"Missed low_hp in HUD: {hud}"
    assert "bomb" in hud["events"], f"Missed bomb in HUD: {hud}"

    brain = DeepSeekBrain.get()
    c_hud, e_hud = brain.generate_streamer_comment(
        {"name": "Counter-Strike 2", "type": "cs2", "title": "Counter-Strike 2"},
        {"motion": 25.0, "red_ratio": 1.1, "brightness": 110.0, "hud_events": hud["events"], "hp_val": hud["hp_val"], "ocr_snippet": hud["snippet"]},
    )
    assert "14 HP" in c_hud or "хилься" in c_hud.lower() or "укрыт" in c_hud.lower(), f"Expected real low-HP reaction, got: {c_hud}"
    print(f"   OCR + Low-HP HUD grounded reaction: '{c_hud}' (emo={e_hud})")

# C) Error screen HUD detection
hud_err = extract_hud_signals(["SyntaxError: invalid syntax line 42"])
assert "error" in hud_err["events"]
c_err, e_err = DeepSeekBrain.get().generate_streamer_comment(
    {"name": "VS Code", "type": "ide", "title": "desktop_pet.py"},
    {"motion": 5.0, "red_ratio": 1.0, "brightness": 95.0, "hud_events": hud_err["events"], "ocr_snippet": hud_err["snippet"]},
)
assert "ошибк" in c_err.lower() and e_err == "curious"
print(f"   IDE Error grounded reaction: '{c_err}' (emo={e_err})")

# D) GameCommentaryEngine sync emission check
gce = GameCommentaryEngine()
emitted = []
gce.commentary_ready.connect(lambda txt, emo: emitted.append((txt, emo)))
gce.trigger_commentary(forced=True, sync=True)
assert len(emitted) == 1 and len(emitted[0][0]) > 5
print(f"   GameCommentaryEngine live emission verified: '{emitted[0][0]}' (emo={emitted[0][1]})")

print("\n>>> ALL PET SENSORS & REAL SCREEN COMMENTARY TESTS PASSED 100%! <<<")
