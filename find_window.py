import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def check():
    found = []
    def enum_cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            cls_name = buf.value
            user32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value
            r = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            w = r.right - r.left
            h = r.bottom - r.top
            if "qt" in cls_name.lower() or "python" in cls_name.lower() or "island" in title.lower() or w in [640, 190, 330, 400]:
                found.append((hwnd, pid.value, cls_name, title, (r.left, r.top, r.right, r.bottom), (w, h)))
        return True

    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    for f in found:
        print(f"HWND {f[0]} PID {f[1]} Cls: {f[2]} Title: '{f[3]}' Rect: {f[4]} Size: {f[5]}")

if __name__ == '__main__':
    check()
