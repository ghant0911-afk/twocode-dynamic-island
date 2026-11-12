# -*- coding: utf-8 -*-
"""
Lightweight OS & Audio Sensors for TwoCode Desktop Pet:
- SystemAudioBeatDetector: passive Windows CoreAudio peak/BPM estimator (0.08ms/poll, zero audio locks).
- FullscreenAppDetector: Win32 foreground fullscreen game/video detector for auto-pausing WebGL on low-end PCs.
- Win32PetWindowHelper: mouse pass-through (WS_EX_TRANSPARENT) & tight silhouette hit-testing.
"""

import ctypes
from ctypes import wintypes
import time
import math

user32 = getattr(ctypes, "windll", None).user32 if hasattr(ctypes, "windll") else None

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
MONITOR_DEFAULTTONEAREST = 2

SHELL_WINDOW_CLASSES = frozenset({
    "Progman",
    "WorkerW",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "NotifyIconOverflowWindow",
    "Windows.UI.Core.CoreWindow",
})


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", ctypes.c_ulong),
    ]


def is_cursor_in_silhouette(
    local_x: float,
    local_y: float,
    width: int,
    height: int,
    state: str,
    character: str = "shino",
) -> bool:
    """
    Determine whether cursor (local_x, local_y) lies within the solid pet/stage region.
    Clicks outside this box pass cleanly through transparent background to desktop apps.
    """
    if width <= 0 or height <= 0:
        return False
    if local_x < 0 or local_y < 0 or local_x > width or local_y > height:
        return False

    if character == "robo":
        # 2D robot fills compact center portion of pet frame
        x_min, x_max = width * 0.16, width * 0.84
        y_min, y_max = height * 0.24, height * 0.90
    elif state == "dance":
        # Wide drum stage (390x377): cymbals span ~0.12..0.88 W, kit + head ~0.16..0.88 H
        x_min, x_max = width * 0.12, width * 0.88
        y_min, y_max = height * 0.16, height * 0.88
    else:
        # Standing/walking/sitting 3D VRM in 260x377 frame
        x_min, x_max = width * 0.20, width * 0.80
        y_min, y_max = height * 0.14, height * 0.94

    return (x_min <= local_x <= x_max) and (y_min <= local_y <= y_max)


def rect_covers_monitor(win_rect: tuple, mon_rect: tuple, class_name: str = "") -> bool:
    """Pure geometry check whether a foreground window cleanly covers a full monitor."""
    if class_name in SHELL_WINDOW_CLASSES:
        return False
    wl, wt, wr, wb = win_rect
    ml, mt, mr, mb = mon_rect
    if (mr - ml) <= 0 or (mb - mt) <= 0:
        return False
    return wl <= ml + 2 and wt <= mt + 2 and wr >= mr - 2 and wb >= mb - 2


class Win32PetWindowHelper:
    """Manages non-activating & dynamic WS_EX_TRANSPARENT flags without redundant calls."""

    def __init__(self):
        self._last_transparent = None

    def apply_noactivate(self, hwnd: int):
        if not user32 or not hwnd:
            return
        try:
            cur = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if (cur & WS_EX_NOACTIVATE) == 0:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur | WS_EX_NOACTIVATE)
        except Exception:
            pass

    def set_click_through(self, hwnd: int, transparent: bool) -> bool:
        """Toggle WS_EX_TRANSPARENT only when state changes. Returns True if changed."""
        if self._last_transparent is transparent:
            return False
        self._last_transparent = transparent
        if not user32 or not hwnd:
            return True
        try:
            cur = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new_style = (cur | WS_EX_TRANSPARENT) if transparent else (cur & ~WS_EX_TRANSPARENT)
            if new_style != cur:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        except Exception:
            pass
        return True


class FullscreenAppDetector:
    """Detects whether a fullscreen external app (game / video) covers the monitor."""

    @staticmethod
    def is_fullscreen_covered(own_hwnds: set | None = None) -> bool:
        if not user32:
            return False
        try:
            fg = user32.GetForegroundWindow()
            if not fg:
                return False
            if own_hwnds and int(fg) in own_hwnds:
                return False
            if not user32.IsWindowVisible(fg) or user32.IsIconic(fg):
                return False

            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(fg, cls_buf, 256)
            cls_name = cls_buf.value

            w_rect = _RECT()
            if not user32.GetWindowRect(fg, ctypes.byref(w_rect)):
                return False

            hmon = user32.MonitorFromWindow(fg, MONITOR_DEFAULTTONEAREST)
            if not hmon:
                return False
            mi = _MONITORINFO()
            mi.cbSize = ctypes.sizeof(_MONITORINFO)
            if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                return False

            win_tuple = (w_rect.left, w_rect.top, w_rect.right, w_rect.bottom)
            mon_tuple = (mi.rcMonitor.left, mi.rcMonitor.top, mi.rcMonitor.right, mi.rcMonitor.bottom)
            return rect_covers_monitor(win_tuple, mon_tuple, cls_name)
        except Exception:
            return False


class SystemAudioBeatDetector:
    """
    Passive Windows CoreAudio peak & onset/BPM detector.
    Polls IAudioMeterInformation::GetPeakValue (~0.08ms) without opening audio streams.
    """

    def __init__(self):
        self._meter = None
        self._init_attempted = False
        self._avg_energy = 0.05
        self._last_beat_ts = 0.0
        self._beat_intervals = []
        self.bpm = 120.0

    def _ensure_meter(self) -> bool:
        if self._meter is not None:
            return True
        if self._init_attempted:
            return False
        self._init_attempted = True
        try:
            from ctypes import POINTER, c_float
            import comtypes
            from comtypes import GUID, COMMETHOD, HRESULT

            CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
            IID_IAudioMeterInformation = GUID("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")

            class IAudioMeterInformation(comtypes.IUnknown):
                _iid_ = IID_IAudioMeterInformation
                _methods_ = [
                    COMMETHOD([], HRESULT, "GetPeakValue", (["out"], POINTER(c_float), "pfPeak")),
                ]

            class IMMDevice(comtypes.IUnknown):
                _iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
                _methods_ = [
                    COMMETHOD([], HRESULT, "Activate",
                              (["in"], POINTER(GUID), "iid"),
                              (["in"], ctypes.c_uint32, "dwClsCtx"),
                              (["in"], ctypes.c_void_p, "pActivationParams"),
                              (["out"], POINTER(POINTER(comtypes.IUnknown)), "ppInterface")),
                ]

            class IMMDeviceEnumerator(comtypes.IUnknown):
                _iid_ = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
                _methods_ = [
                    COMMETHOD([], HRESULT, "EnumAudioEndpoints", (["in"], ctypes.c_uint32, "dataFlow"), (["in"], ctypes.c_uint32, "dwStateMask"), (["out"], POINTER(ctypes.c_void_p), "ppDevices")),
                    COMMETHOD([], HRESULT, "GetDefaultAudioEndpoint", (["in"], ctypes.c_uint32, "dataFlow"), (["in"], ctypes.c_uint32, "role"), (["out"], POINTER(POINTER(IMMDevice)), "ppEndpoint")),
                ]

            try:
                comtypes.CoInitialize()
            except Exception:
                pass
            enum = comtypes.CoCreateInstance(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
            dev = enum.GetDefaultAudioEndpoint(0, 1)  # eRender, eMultimedia
            unk = dev.Activate(ctypes.byref(IID_IAudioMeterInformation), 23, None)
            self._meter = unk.QueryInterface(IAudioMeterInformation)
            return True
        except Exception:
            self._meter = None
            return False

    def feed_sample(self, peak: float, now: float | None = None) -> tuple:
        """Pure testable beat/BPM tracker given a peak sample in [0.0, 1.0]."""
        if now is None:
            now = time.monotonic()
        peak = max(0.0, min(1.0, float(peak)))

        # Track short-term energy envelope
        self._avg_energy = self._avg_energy * 0.88 + peak * 0.12
        beat_hit = False

        # Dynamic onset threshold with refractory cooldown (280ms -> max ~214 BPM)
        threshold = max(0.08, self._avg_energy * 1.28)
        if peak > threshold and (now - self._last_beat_ts) >= 0.28:
            beat_hit = True
            dt = now - self._last_beat_ts
            if 0.30 <= dt <= 1.25 and self._last_beat_ts > 0:
                inst_bpm = 60.0 / dt
                # Fold double/half-time softly into musical drum range 75..155 BPM
                while inst_bpm < 75.0:
                    inst_bpm *= 2.0
                while inst_bpm > 155.0:
                    inst_bpm *= 0.5
                self._beat_intervals.append(inst_bpm)
                if len(self._beat_intervals) > 8:
                    self._beat_intervals.pop(0)
                self.bpm = sum(self._beat_intervals) / len(self._beat_intervals)
            self._last_beat_ts = now

        # Gentle decay back toward baseline if silent
        if (now - self._last_beat_ts) > 2.5:
            self.bpm = self.bpm * 0.95 + 120.0 * 0.05

        speed_scale = max(0.72, min(1.40, self.bpm / 120.0))
        return peak, beat_hit, round(self.bpm, 1), round(speed_scale, 3)

    def poll(self) -> tuple:
        """Poll CoreAudio master peak & compute beat state. Safe fallback on error."""
        if not self._ensure_meter():
            return 0.0, False, 120.0, 1.0
        try:
            peak = float(self._meter.GetPeakValue())
            return self.feed_sample(peak)
        except Exception:
            return 0.0, False, round(self.bpm, 1), 1.0
