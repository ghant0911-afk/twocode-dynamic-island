import sys
import os

log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, "debug.log")

with open(log_file, "w", encoding="utf-8") as f:
    f.write(f"Python: {sys.version}\n")
    f.write(f"Executable: {sys.executable}\n")
    try:
        import PyQt6
        f.write("PyQt6 imported successfully\n")
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        screens = app.screens()
        for i, s in enumerate(screens):
            geo = s.geometry()
            f.write(f"Screen {i}: name='{s.name()}', rect=[{geo.x()},{geo.y()},{geo.width()},{geo.height()}], primary={s == app.primaryScreen()}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")

print(f"Environment checked successfully, logged to {log_file}")
