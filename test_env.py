import sys
import os

with open(r"D:\Dynamic_Island_Work\debug.log", "w", encoding="utf-8") as f:
    f.write(f"Python: {sys.version}\n")
    f.write(f"Executable: {sys.executable}\n")
    try:
        import PyQt6
        f.write("PyQt6 imported successfully\n")
        from PyQt6.QtWidgets import QApplication
        app = QApplication([])
        screens = app.screens()
        for i, s in enumerate(screens):
            geo = s.geometry()
            f.write(f"Screen {i}: name='{s.name()}', rect=[{geo.x()},{geo.y()},{geo.width()},{geo.height()}], primary={s == app.primaryScreen()}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
