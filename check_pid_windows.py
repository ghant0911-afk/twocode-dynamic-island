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

def check_pid(target_pid):
    found = []
    def enum_cb(hwnd, lparam):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == target_pid:
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
            found.append((hwnd, vis, cls_name, title, (r.left, r.top, r.right, r.bottom), (w, h)))
        return True

    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    print(f"Windows for PID {target_pid}:")
    for f in found:
        print(f"  HWND: {f[0]} Visible: {f[1]} Cls: {f[2]} Title: '{f[3]}' Rect: {f[4]} Size: {f[5]}")

if __name__ == '__main__':
    check_pid(16688)
