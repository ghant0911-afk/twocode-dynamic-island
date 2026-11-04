import ctypes
import json
import os

user32 = ctypes.windll.user32
results = []

def enum_cb(hwnd, extra):
    if user32.IsWindowVisible(hwnd):
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        title = buf.value
        if title:
            results.append({"hwnd": hwnd, "title": title})
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

with open(r"D:\Dynamic_Island_Work\windows_found.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"Dumped {len(results)} windows")
