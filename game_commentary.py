# -*- coding: utf-8 -*-
"""
Live Screen Perception & Real-Time Game/App Commentary Engine for TwoCode Dynamic Island.
- Ultra-lightweight downscaled Win32 GDI frame capture (~1.5ms, zero GDI handle leaks).
- Real motion %, brightness, crimson/damage flash & scene-cut detection via NumPy.
- Offline Windows Neural OCR (winsdk.windows.media.ocr, RU+EN ~20ms) for real HUD/error/UI reading.
- Async worker execution so commentary never freezes the Qt UI or games.
"""

import asyncio
import ctypes
from ctypes import wintypes
import random
import re
import threading
import time
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import winsdk.windows.media.ocr as wocr
    import winsdk.windows.graphics.imaging as wimg
    import winsdk.windows.storage.streams as streams
    HAS_WINSDK_OCR = True
except Exception:
    HAS_WINSDK_OCR = False


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", _BITMAPINFOHEADER)]


def grab_scaled_bgra(target_w: int, target_h: int) -> np.ndarray | None:
    """Grab primary desktop directly downscaled to (target_h, target_w, 4) BGRA in kernel GDI."""
    hdc_scr = 0
    hdc_mem = 0
    hbmp = 0
    old = 0
    try:
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        if sw <= 0 or sh <= 0:
            return None
        hdc_scr = user32.GetDC(0)
        if not hdc_scr:
            return None
        hdc_mem = gdi32.CreateCompatibleDC(hdc_scr)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_scr, target_w, target_h)
        if not hdc_mem or not hbmp:
            return None
        old = gdi32.SelectObject(hdc_mem, hbmp)
        gdi32.SetStretchBltMode(hdc_mem, 3)  # COLORONCOLOR
        gdi32.StretchBlt(hdc_mem, 0, 0, target_w, target_h, hdc_scr, 0, 0, sw, sh, 0x00CC0020)

        bmi = _BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = target_w
        bmi.bmiHeader.biHeight = -target_h  # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0

        buf = (ctypes.c_ubyte * (target_w * target_h * 4))()
        gdi32.GetDIBits(hdc_mem, hbmp, 0, target_h, buf, ctypes.byref(bmi), 0)
        arr = np.frombuffer(buf, dtype=np.uint8).reshape((target_h, target_w, 4)).copy()
        arr[:, :, 3] = 255
        return arr
    except Exception:
        return None
    finally:
        if hdc_mem and old:
            gdi32.SelectObject(hdc_mem, old)
        if hbmp:
            gdi32.DeleteObject(hbmp)
        if hdc_mem:
            gdi32.DeleteDC(hdc_mem)
        if hdc_scr:
            user32.ReleaseDC(0, hdc_scr)


def compute_frame_metrics(curr_bgra: np.ndarray, prev_rgb: np.ndarray | None = None) -> tuple[dict, np.ndarray]:
    """
    Compute real visual scene metrics from a tiny BGRA frame (e.g. 96x54).
    Returns (metrics_dict, current_rgb_float_frame).
    """
    bgr = curr_bgra[:, :, :3].astype(np.float32)
    b, g, r = bgr[:, :, 0], bgr[:, :, 1], bgr[:, :, 2]

    brightness = float(np.mean(0.299 * r + 0.587 * g + 0.114 * b))
    is_black = brightness < 3.0

    other_avg = np.maximum(12.0, (g + b) * 0.5)
    red_ratio = float(np.mean(r / other_avg))

    if prev_rgb is not None and prev_rgb.shape == bgr.shape:
        diff = np.mean(np.abs(bgr - prev_rgb), axis=2)
        motion = float(np.mean(diff > 14.0) * 100.0)
        mean_abs_delta = float(np.mean(diff))
        scene_cut = bool(motion > 38.0 or mean_abs_delta > 28.0)
    else:
        motion = 0.0
        scene_cut = False

    return {
        "brightness": round(brightness, 1),
        "red_ratio": round(red_ratio, 2),
        "motion": round(motion, 1),
        "scene_cut": scene_cut,
        "is_black_frame": is_black,
    }, bgr


_CYR_TO_LAT = str.maketrans({
    "а": "a", "в": "b", "е": "e", "к": "k", "м": "m",
    "н": "h", "о": "o", "р": "p", "с": "c", "т": "t",
    "у": "y", "х": "x", "ь": "b", "п": "n", "і": "i", "ї": "i",
})


def extract_hud_signals(ocr_lines: list[str]) -> dict:
    """
    Parse real HUD/UI events and clean snippet from extracted OCR text lines.
    Pure & testable across both English and Russian screens (with homoglyph tolerance).
    """
    cleaned = []
    for raw in ocr_lines or []:
        line = re.sub(r"\s+", " ", str(raw)).strip()
        if len(line) >= 4:
            cleaned.append(line)

    full_text = " | ".join(cleaned)
    low = full_text.lower()
    # Dual matching: original lowercase (for Russian) + homoglyph-normalized Latin (for English HUDs read by RU OCR)
    lat = low.translate(_CYR_TO_LAT)
    both = f"{low} || {lat}"

    events = []
    hp_val = None

    hp_match = re.search(
        r"(?:hp|health|hea[le]th|здоров\w*|жизн\w*)[\s:=]*(\d{1,3})(?:\s*/\s*(\d{1,3}))?",
        both,
    )
    if hp_match:
        val = int(hp_match.group(1))
        mx = int(hp_match.group(2)) if hp_match.group(2) else 100
        if mx > 0 and (val / mx) <= 0.30 and val > 0:
            events.append("low_hp")
            hp_val = val

    if any(k in both for k in ["you died", "game over", "потрачено", "вы погибли", "wasted", "mission failed"]):
        events.append("death")
    elif any(k in both for k in ["victory", "победа", "round won", "match won", "winner"]):
        events.append("victory")
    elif any(k in both for k in ["defeat", "поражение", "round lost", "match lost"]):
        events.append("defeat")

    if any(k in both for k in ["bomb has been planted", "бомба установлена", "spike planted", "bomb planted"]) or re.search(r"bo[mt]b\s+has\s+b[aei]{2}n\s+planted", both):
        events.append("bomb")
    if any(k in both for k in ["boss", "босс", "level up", "новый уровень"]):
        events.append("boss_or_level")
    if any(k in both for k in ["traceback", "syntaxerror", "exception", "failed", "ошибка", "error"]):
        events.append("error")

    informative = [ln for ln in cleaned if 6 <= len(ln) <= 85]
    snippet = " / ".join(informative[:2]) if informative else (cleaned[0][:80] if cleaned else "")

    return {
        "events": events,
        "hp_val": hp_val,
        "snippet": snippet[:160],
        "ocr_text": full_text[:340],
        "line_count": len(cleaned),
    }


async def _recognize_bgra_async(bgra_arr: np.ndarray, lang_hint: str | None = None) -> list[str]:
    if not HAS_WINSDK_OCR or bgra_arr is None:
        return []
    h, w, _ = bgra_arr.shape
    dw = streams.DataWriter()
    dw.write_bytes(bgra_arr.tobytes())
    ibuf = dw.detach_buffer()
    sbmp = wimg.SoftwareBitmap.create_copy_from_buffer(ibuf, wimg.BitmapPixelFormat.BGRA8, w, h)
    engine = None
    if lang_hint:
        for l in wocr.OcrEngine.available_recognizer_languages:
            if l.language_tag.lower().startswith(lang_hint.lower()):
                engine = wocr.OcrEngine.try_create_from_language(l)
                break
    if not engine:
        engine = wocr.OcrEngine.try_create_from_user_profile_languages()
    if not engine:
        langs = list(wocr.OcrEngine.available_recognizer_languages)
        if not langs:
            return []
        engine = wocr.OcrEngine.try_create_from_language(langs[0])
    res = await engine.recognize_async(sbmp)
    return [line.text for line in res.lines]


class GameCommentaryEngine(QObject):
    commentary_ready = pyqtSignal(str, str)  # text, emotion

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_auto_mode = False
        self.last_comment_time = 0.0
        self.prev_frame_rgb = None
        self.cooldown = 15.0
        self._is_generating = False

        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._auto_tick)
        # Only start timer when auto mode is enabled to save CPU

    def set_auto(self, enabled: bool):
        self.is_auto_mode = enabled
        self.last_comment_time = time.time()
        if self.is_auto_mode:
            self.auto_timer.start(12000)
        else:
            self.auto_timer.stop()

    def toggle_auto(self) -> bool:
        self.set_auto(not self.is_auto_mode)
        return self.is_auto_mode

    def get_active_game_info(self):
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return {"type": "desktop", "name": "Рабочий стол", "title": "", "proc": ""}

            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()

            proc_name = ""
            if HAS_PSUTIL:
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                try:
                    proc_name = psutil.Process(pid.value).name().lower()
                except Exception:
                    pass

            title_low = title.lower()
            game_rules = [
                (["cs2", "csgo"], ["counter-strike"], "cs2", "Counter-Strike 2"),
                (["dota2"], ["dota 2"], "dota2", "Dota 2"),
                (["javaw.exe", "minecraft"], ["minecraft"], "minecraft", "Minecraft"),
                (["cyberpunk"], ["cyberpunk"], "cyberpunk", "Cyberpunk 2077"),
                (["pathofexile", "poe"], ["path of exile"], "poe", "Path of Exile"),
                (["genshin"], ["genshin"], "genshin", "Genshin Impact"),
                (["valorant"], ["valorant"], "valorant", "Valorant"),
                (["r5apex"], ["apex legends"], "apex", "Apex Legends"),
                (["eldenring", "darksouls", "sekiro"], ["elden ring", "dark souls", "sekiro"], "souls", "Elden Ring / Souls"),
                (["tarkov"], ["tarkov"], "tarkov", "Escape from Tarkov"),
                (["gta5", "gta_sa"], ["grand theft auto"], "gta", "GTA V"),
                (["witcher3"], ["witcher 3"], "witcher", "Ведьмак 3"),
                (["helldivers2"], ["helldivers"], "helldivers", "Helldivers 2"),
                (["stalker2", "xrengine"], ["s.t.a.l.k.e.r", "stalker"], "stalker", "S.T.A.L.K.E.R."),
                (["robloxplayer"], ["roblox"], "roblox", "Roblox"),
            ]
            for procs, titles, gtype, gname in game_rules:
                if any(p in proc_name for p in procs) or any(t in title_low for t in titles):
                    return {"type": gtype, "name": gname, "title": title, "proc": proc_name}

            if "youtube" in title_low or "twitch" in title_low:
                return {"type": "video", "name": title.split(" - ")[0][:60] or "Видео", "title": title, "proc": proc_name}
            if any(p in proc_name for p in ["code.exe", "pycharm", "idea64", "devenv", "antigravity"]):
                return {"type": "ide", "name": title.split(" - ")[0][:60] or "Код-редактор", "title": title, "proc": proc_name}
            if any(p in proc_name for p in ["chrome", "yandex", "msedge", "firefox", "opera"]):
                return {"type": "browser", "name": title.split(" - ")[0][:60] or "Браузер", "title": title, "proc": proc_name}
            if any(p in proc_name for p in ["telegram", "discord"]):
                return {"type": "chat", "name": proc_name.replace(".exe", "").capitalize(), "title": title, "proc": proc_name}

            is_game = any(k in title_low for k in ["game", "play", "simulator", "steam", "unreal", "unity", "remake"])
            return {
                "type": "game" if is_game else "desktop",
                "name": title if title else "Рабочий стол",
                "title": title,
                "proc": proc_name,
            }
        except Exception:
            return {"type": "desktop", "name": "Рабочий стол", "title": "", "proc": ""}

    def analyze_screen(self, run_ocr: bool = True, lang_hint: str | None = None) -> dict:
        """
        Capture real downscaled screen frames to extract motion %, crimson/damage flash,
        brightness, scene cuts, audio loudness, and optional Windows Neural OCR HUD text.
        """
        metrics = {
            "brightness": 128.0,
            "red_ratio": 1.0,
            "motion": 0.0,
            "scene_cut": False,
            "is_black_frame": True,
            "audio_peak": 0.0,
            "hud_events": [],
            "hp_val": None,
            "ocr_snippet": "",
            "ocr_text": "",
        }

        small = grab_scaled_bgra(96, 54)
        if small is not None:
            vis, new_rgb = compute_frame_metrics(small, self.prev_frame_rgb)
            self.prev_frame_rgb = new_rgb
            metrics.update(vis)

        try:
            from pet_sensors import SystemAudioBeatDetector
            if not hasattr(self, "_audio_meter"):
                self._audio_meter = SystemAudioBeatDetector()
            peak, _, _, _ = self._audio_meter.poll()
            metrics["audio_peak"] = round(float(peak), 2)
        except Exception:
            pass

        if run_ocr and HAS_WINSDK_OCR and not metrics["is_black_frame"]:
            try:
                ocr_arr = grab_scaled_bgra(800, 450)
                if ocr_arr is not None:
                    lines = asyncio.run(_recognize_bgra_async(ocr_arr, lang_hint=lang_hint))
                    hud = extract_hud_signals(lines)
                    metrics["hud_events"] = hud["events"]
                    metrics["hp_val"] = hud["hp_val"]
                    metrics["ocr_snippet"] = hud["snippet"]
                    metrics["ocr_text"] = hud["ocr_text"]
            except Exception:
                pass

        return metrics

    def trigger_commentary(self, forced: bool = False, sync: bool = False):
        now = time.time()
        if not forced and (now - self.last_comment_time < self.cooldown):
            return
        if self._is_generating and not sync:
            return

        def _worker():
            self._is_generating = True
            try:
                info = self.get_active_game_info()
                metrics = self.analyze_screen(run_ocr=True)
                comment, emotion = self._craft_comment(info, metrics)
                self.last_comment_time = time.time()
                self.commentary_ready.emit(comment, emotion)
            finally:
                self._is_generating = False

        if sync:
            _worker()
        else:
            threading.Thread(target=_worker, daemon=True).start()

    def _auto_tick(self):
        if not self.is_auto_mode:
            return
        info = self.get_active_game_info()
        if info["type"] == "desktop" and not info.get("title"):
            return
        self.trigger_commentary(forced=False, sync=False)

    def _craft_comment(self, info, metrics):
        try:
            from deepseek_brain import DeepSeekBrain
            return DeepSeekBrain.get().generate_streamer_comment(info, metrics)
        except Exception:
            pass

        gname = info.get("name", "игре")
        snippet = metrics.get("ocr_snippet", "")
        if snippet:
            return f"Смотрю на экран в {gname}: вижу «{snippet[:45]}»!", "curious"
        return f"Наблюдаю за {gname}!", "happy"
