import ctypes
from ctypes import wintypes
import psutil

user32 = ctypes.windll.user32

pids = [p.info['pid'] for p in psutil.process_iter(['pid', 'name']) if 'python' in p.info['name'].lower()]
print('Python PIDs:', pids)

def enum_cb(hwnd, lparam):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value in pids:
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        vis = user32.IsWindowVisible(hwnd)
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, 512)
        cls = ctypes.create_unicode_buffer(512)
        user32.GetClassNameW(hwnd, cls, 512)
        print(f"HWND {hwnd} (PID {pid.value}): vis={vis}, rect=({rect.left}, {rect.top}, {rect.right}, {rect.bottom}), cls='{cls.value}', title='{title.value}'")
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
