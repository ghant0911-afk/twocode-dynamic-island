import ctypes
from ctypes import wintypes
import psutil

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def check_all_pythons():
    pids = [p.pid for p in psutil.process_iter(['name']) if 'python' in p.info['name'].lower()]
    print("Active Python PIDs:", pids)

    found = []
    def enum_cb(hwnd, lparam):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            vis = user32.IsWindowVisible(hwnd)
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            cls_name = buf.value
            user32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value
            r = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            w = r.right - r.left
            h = r.bottom - r.top
            found.append((hwnd, pid.value, vis, cls_name, title, (r.left, r.top, r.right, r.bottom), (w, h)))
        return True

    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    for f in found:
        print(f"HWND: {f[0]} PID: {f[1]} Visible: {f[2]} Cls: {f[3]} Title: '{f[4]}' Rect: {f[5]} Size: {f[6]}")

if __name__ == '__main__':
    check_all_pythons()
