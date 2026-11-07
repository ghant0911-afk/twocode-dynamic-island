# -*- coding: utf-8 -*-
"""
Live Screen Perception & Streamer Game Commentary Engine for TwoCode Dynamic Island.
Perceives foreground games & window dynamics, generates emotional streamer reactions.
"""

import time
import random
import ctypes
from ctypes import wintypes
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

user32 = ctypes.windll.user32

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class GameCommentaryEngine(QObject):
    commentary_ready = pyqtSignal(str, str)  # text, emotion

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_auto_mode = False
        self.last_comment_time = 0.0
        self.prev_frame_data = None
        self.cooldown = 15.0

        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._auto_tick)
        self.auto_timer.start(8000)

    def set_auto(self, enabled: bool):
        self.is_auto_mode = enabled
        self.last_comment_time = time.time()

    def toggle_auto(self) -> bool:
        self.is_auto_mode = not self.is_auto_mode
        self.last_comment_time = time.time()
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
            if "cs2" in proc_name or "csgo" in proc_name or "counter-strike" in title_low:
                return {"type": "cs2", "name": "Counter-Strike 2", "title": title, "proc": proc_name}
            if "dota2" in proc_name or "dota 2" in title_low:
                return {"type": "dota2", "name": "Dota 2", "title": title, "proc": proc_name}
            if "minecraft" in title_low or proc_name in ["javaw.exe", "minecraft.exe", "bedrock_server.exe"]:
                return {"type": "minecraft", "name": "Minecraft", "title": title, "proc": proc_name}
            if "cyberpunk" in proc_name or "cyberpunk" in title_low:
                return {"type": "cyberpunk", "name": "Cyberpunk 2077", "title": title, "proc": proc_name}
            if "pathofexile" in proc_name or "poe" in proc_name or "path of exile" in title_low:
                return {"type": "poe", "name": "Path of Exile", "title": title, "proc": proc_name}
            if "genshin" in proc_name or "genshin" in title_low:
                return {"type": "genshin", "name": "Genshin Impact", "title": title, "proc": proc_name}
            if "valorant" in proc_name or "valorant" in title_low:
                return {"type": "valorant", "name": "Valorant", "title": title, "proc": proc_name}
            if "r5apex" in proc_name or "apex" in title_low:
                return {"type": "apex", "name": "Apex Legends", "title": title, "proc": proc_name}
            if any(k in proc_name for k in ["eldenring", "darksouls", "sekiro"]):
                return {"type": "souls", "name": "Elden Ring / Souls", "title": title, "proc": proc_name}
            if "tarkov" in proc_name or "tarkov" in title_low:
                return {"type": "tarkov", "name": "Escape from Tarkov", "title": title, "proc": proc_name}

            is_game = any(k in title_low for k in ["game", "play", "simulator", "steam", "unreal", "unity", "remake"])
            return {
                "type": "game" if is_game else "desktop",
                "name": title if title else "Рабочий стол",
                "title": title,
                "proc": proc_name
            }
        except Exception:
            return {"type": "desktop", "name": "Рабочий стол", "title": "", "proc": ""}

    def analyze_screen(self):
        try:
            screen = QApplication.primaryScreen()
            if not screen:
                return {"brightness": 128, "red_ratio": 1.0, "motion": 0}
            pixmap = screen.grabWindow(0)
            if pixmap.isNull():
                return {"brightness": 128, "red_ratio": 1.0, "motion": 0}

            scaled = pixmap.scaled(160, 90)
            qimg = scaled.toImage().convertToFormat(QImage.Format.Format_RGB888)
            w = qimg.width()
            h = qimg.height()
            stride = qimg.bytesPerLine()
            ptr = qimg.bits()
            ptr.setsize(h * stride)
            curr_bytes = bytes(ptr)

            total_r, total_g, total_b = 0, 0, 0
            samples = 0
            for y in range(0, h, 4):
                row_offset = y * stride
                for x in range(0, w, 4):
                    idx = row_offset + x * 3
                    if idx + 2 < len(curr_bytes):
                        total_r += curr_bytes[idx]
                        total_g += curr_bytes[idx + 1]
                        total_b += curr_bytes[idx + 2]
                        samples += 1

            if samples == 0:
                return {"brightness": 128, "red_ratio": 1.0, "motion": 0}

            avg_r = total_r / samples
            avg_g = total_g / samples
            avg_b = total_b / samples
            brightness = (avg_r + avg_g + avg_b) / 3.0
            red_ratio = (avg_r + 1.0) / (max(avg_g, avg_b) + 1.0)

            motion = 0
            if self.prev_frame_data is not None:
                diff_count = 0
                step = 6
                for i in range(0, min(len(curr_bytes), len(self.prev_frame_data)), step):
                    if abs(curr_bytes[i] - self.prev_frame_data[i]) > 35:
                        diff_count += 1
                motion = int((diff_count / (len(curr_bytes) / step)) * 100)

            self.prev_frame_data = curr_bytes
            return {"brightness": brightness, "red_ratio": red_ratio, "motion": motion}
        except Exception:
            return {"brightness": 128, "red_ratio": 1.0, "motion": 0}

    def trigger_commentary(self, forced: bool = False):
        info = self.get_active_game_info()
        metrics = self.analyze_screen()
        now = time.time()

        if not forced and (now - self.last_comment_time < self.cooldown):
            return

        comment, emotion = self._craft_comment(info, metrics)
        self.last_comment_time = now
        self.commentary_ready.emit(comment, emotion)

    def _auto_tick(self):
        if not self.is_auto_mode:
            return
        info = self.get_active_game_info()
        if info["type"] == "desktop" and not info.get("title"):
            return
        self.trigger_commentary(forced=False)

    def _craft_comment(self, info, metrics):
        try:
            from deepseek_brain import DeepSeekBrain
            return DeepSeekBrain.get().generate_streamer_comment(info, metrics)
        except Exception:
            pass

        gtype = info["type"]
        gname = info["name"]
        motion = metrics.get("motion", 0)
        red_ratio = metrics.get("red_ratio", 1.0)
        brightness = metrics.get("brightness", 128)

        # Danger / Low HP
        if red_ratio > 1.45:
            phrases = [
                ("Ой-ой, экран весь в огне! Лечись скорее, здоровье на нуле!", "shocked"),
                ("Опасность! Красный экран, уходи в укрытие!", "dizzy"),
                ("Держи удар! Захилься, не рискуй так!", "shocked")
            ]
            return random.choice(phrases)

        # High Action
        if motion > 45:
            phrases = [
                (f"Какой бешеный экшен в {gname}! Двигайся, не стой на месте!", "gaming"),
                ("Вот это скорость! Руки помнят, тащи этот раунд!", "star"),
                ("Чистый скилл на реакции! Красиво раздаешь!", "cool")
            ]
            return random.choice(phrases)

        # Darkness / Stealth
        if brightness < 35:
            phrases = [
                ("Темнота хоть глаз выколи... Включи фонарик или слушай шаги!", "curious"),
                ("Идеально для стелса. Тихо крадемся и ни звука!", "reading")
            ]
            return random.choice(phrases)

        # Game-specific
        if gtype == "poe":
            return random.choice([
                ("О, Path of Exile! Какой билд качаем? Смотри под ноги на боссе!", "gaming"),
                ("Главное чтобы с мобов упал дивайн! Пылесось весь лут!", "star"),
                ("Плотный маппинг! Следи за резистами и фласками!", "cool")
            ])
        if gtype == "cs2":
            return random.choice([
                ("Слушай шаги, держи прицел на уровне головы!", "gaming"),
                ("Чекай углы, смок на плент и забирай раунд!", "cool"),
                ("Хороший тайминг! Выходи и раздавай хедшоты!", "star")
            ])
        if gtype == "dota2":
            return random.choice([
                ("Смотри на миникарту! Вражеский мидер может быть рядом!", "curious"),
                ("Варды стоят? Копи на БКБ и заходи в файт вторым темпом!", "gaming")
            ])
        if gtype == "minecraft":
            return random.choice([
                ("Главное правило: никогда не копай прямо под себя!", "curious"),
                ("Уютный вечерок в Майнкрафте. Не забудь факелы в шахту!", "happy")
            ])
        if gtype == "cyberpunk":
            return random.choice([
                ("Добро пожаловать в Найт-Сити! Город грехов и аугментаций!", "cool"),
                ("Сандевистан наготове? Разнеси этих корпорантов в щепки!", "gaming")
            ])

        # Generic Desktop / Calm gameplay
        generic = [
            (f"Наблюдаю за {gname}. Спокойный, уверенный темп!", "idle"),
            ("Я рядом и слежу за процессом. Если что — подскажу!", "happy"),
            ("Отличная концентрация! Продолжай в том же духе!", "cool")
        ]
        return random.choice(generic)
