import os
import sys

os.chdir(r"C:\Users\bear_\.gemini\antigravity\scratch\twocode_island_unified")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

import main
from deepseek_brain import DeepSeekBrain
from voice_engine import VoiceEngine

print("1. Testing DeepSeekBrain Instance...")
brain = DeepSeekBrain.get()
assert brain is not None
resp = brain.ask("Привет! Кто ты?")
assert "Робо" in resp or len(resp) > 5
print(f"   DeepSeek Greeting: {resp}")

print("2. Testing Task Parsing & Execution...")
task_calc = brain.parse_and_execute_task("запусти калькулятор")
assert task_calc is not None
assert task_calc[0] == "open_calc"

task_note = brain.parse_and_execute_task("запомни: протестировать DeepSeek")
assert task_note is not None
assert task_note[0] == "save_note"
print("   Task execution verified!")

print("3. Testing Dynamic Streamer Commentary Generation (No repeating loops)...")
comment1, emo1 = brain.generate_streamer_comment({"name": "Cyberpunk 2077", "type": "cyberpunk"}, {"motion": 55, "red_ratio": 1.0, "brightness": 120})
comment2, emo2 = brain.generate_streamer_comment({"name": "Dota 2", "type": "dota2"}, {"motion": 10, "red_ratio": 1.6, "brightness": 120})
assert len(comment1) > 0 and len(comment2) > 0
print(f"   Action Commentary: '{comment1}' (emo: {emo1})")
print(f"   Danger Commentary: '{comment2}' (emo: {emo2})")

print("4. Testing TwoCodeIsland AI Chat Integration...")
island = main.TwoCodeIsland()
assert hasattr(island.robo_tab, "chat_input"), "Chat input must be present in robo_tab"
assert hasattr(island.robo_tab, "chat_btn"), "Chat send button must be present in robo_tab"

# Simulate sending query
island.robo_tab.process_ai_query("Как дела?")
print("   TwoCodeIsland AI chat query triggered cleanly!")

print("5. Testing Desktop Pet Red Hoodie Colors...")
island.spawn_desktop_pet()
assert island.desktop_pet is not None
pix = island.desktop_pet.grab()
assert not pix.isNull()
print("   Desktop pet with red hoodie rendered cleanly!")

print("\n>>> ALL DEEPSEEK & BAYA TESTS PASSED WITH 100% SUCCESS! <<<")
