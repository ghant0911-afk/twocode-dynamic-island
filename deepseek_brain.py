# -*- coding: utf-8 -*-
"""
DeepSeek AI Brain & System Task Executor for TwoCode Dynamic Island & Mascot Companion.
Features:
- Native DeepSeek API (deepseek-chat / deepseek-reasoner / DeepSeek-V3 / R1)
- Local Ollama fallback (deepseek-r1 / deepseek-coder)
- Dynamic Screen Perception Streamer Commentary Generator (no repetitive loops!)
- Windows System Task Execution (Screenshots, Media Keys, System Apps, Notes, Island Control)
"""

import os
import re
import sys
import json
import time
import random
import subprocess
import urllib.request
import urllib.parse
from typing import Dict, Any, Tuple, Optional

# Load config for API key if present
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
NOTES_PATH = os.path.join(APP_DIR, "notes.txt")


class DeepSeekBrain:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = DeepSeekBrain()
        return cls._instance

    def __init__(self):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = "deepseek-chat" # or deepseek-reasoner
        self.ollama_url = "http://127.0.0.1:11434"
        self.has_ollama = False
        self.conversation_history = [
            {
                "role": "system",
                "content": (
                    "Ты — Астра (Astra), живой, умный и невероятно обаятельный виртуальный 3D-ассистент и компаньон рабочего стола. "
                    "Твой визуальный образ — стильная аниме-девушка в худи и наушниках (Sendagaya Shino 3D VRM). "
                    "Твой голос — выразительный, тёплый и живой (Бая Silero TTS). "
                    "Ты говоришь живо, тепло, остроумно, современно и лаконично (1-3 живых коротких предложения), без занудства и канцелярита. "
                    "Ты умеешь поддерживать душевный диалог, шутить, сопереживать, помогать с задачами на компьютере в Windows и реагировать на музыку и игры."
                )
            }
        ]
        self._load_config()
        self._check_ollama()

    def _load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if cfg.get("deepseek_api_key"):
                        self.api_key = cfg["deepseek_api_key"].strip()
                    if cfg.get("deepseek_model"):
                        self.model = cfg["deepseek_model"].strip()
            except Exception:
                pass

    def save_api_key(self, key: str, model: str = "deepseek-chat"):
        self.api_key = key.strip()
        self.model = model.strip()
        try:
            cfg = {}
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["deepseek_api_key"] = self.api_key
            cfg["deepseek_model"] = self.model
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _check_ollama(self):
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", headers={"User-Agent": "TwoCode"})
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    self.has_ollama = True
        except Exception:
            self.has_ollama = False

    # -------------------------------------------------------------------------
    # System Task Execution Engine
    # -------------------------------------------------------------------------
    def parse_and_execute_task(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Parses text for actionable Windows commands.
        Returns (action_name, friendly_response) or None if conversational.
        """
        q = query.lower().strip()

        # 1. Screenshot / Скриншот
        if any(k in q for k in ["скрин", "снимок", "сфотографируй", "screenshot", "screen"]):
            try:
                # Trigger native Windows Snipping Tool (Win + Shift + S)
                import ctypes
                user32 = ctypes.windll.user32
                # VK_LWIN = 0x5B, VK_SHIFT = 0x10, 'S' = 0x53
                user32.keybd_event(0x5B, 0, 0, 0)
                user32.keybd_event(0x10, 0, 0, 0)
                user32.keybd_event(0x53, 0, 0, 0)
                user32.keybd_event(0x53, 0, 2, 0)
                user32.keybd_event(0x10, 0, 2, 0)
                user32.keybd_event(0x5B, 0, 2, 0)
                return "screenshot", "Сделано! Открываю инструмент создания скриншота."
            except Exception as e:
                return "screenshot", f"Пытаюсь сделать скриншот, но возникла ошибка: {e}"

        # 2. Media Play / Pause (Включи музыку / Пауза)
        if any(k in q for k in ["пауза", "включи музыку", "плей", "останови музыку", "продолжи трек"]):
            try:
                import ctypes
                # VK_MEDIA_PLAY_PAUSE = 0xB3
                ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
                return "media_play_pause", "Переключил воспроизведение музыки!"
            except Exception:
                pass

        # 3. Next Track / Следующий трек
        if any(k in q for k in ["следующий трек", "некст", "переключи песню", "следующую песню"]):
            try:
                import ctypes
                # VK_MEDIA_NEXT_TRACK = 0xB0
                ctypes.windll.user32.keybd_event(0xB0, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xB0, 0, 2, 0)
                return "media_next", "Включаю следующий трек!"
            except Exception:
                pass

        # 4. Previous Track / Предыдущий трек
        if any(k in q for k in ["предыдущий трек", "назад песня", "прошлый трек"]):
            try:
                import ctypes
                # VK_MEDIA_PREV_TRACK = 0xB1
                ctypes.windll.user32.keybd_event(0xB1, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xB1, 0, 2, 0)
                return "media_prev", "Возвращаю предыдущий трек!"
            except Exception:
                pass

        # 5. Launch Calculator / Калькулятор
        if "калькулятор" in q:
            try:
                subprocess.Popen("calc.exe")
                return "open_calc", "Открыл калькулятор!"
            except Exception:
                pass

        # 6. Launch Notepad / Блокнот
        if "блокнот" in q:
            try:
                subprocess.Popen("notepad.exe")
                return "open_notepad", "Запустил блокнот!"
            except Exception:
                pass

        # 7. Launch Explorer / Проводник
        if any(k in q for k in ["проводник", "открой папку", "файлы"]):
            try:
                subprocess.Popen("explorer.exe")
                return "open_explorer", "Открываю проводник файлов!"
            except Exception:
                pass

        # 8. Note Taking / Заметка
        note_match = re.search(r'(?:запомни|запиши|добавь заметку)[:\s]+(.+)', q, re.IGNORECASE)
        if note_match:
            note_text = note_match.group(1).strip()
            try:
                with open(NOTES_PATH, "a", encoding="utf-8") as f:
                    timestamp = time.strftime("%H:%M %d.%m")
                    f.write(f"\n[{timestamp}] {note_text}\n")
                return "save_note", f"Записал в твои заметки: «{note_text}»"
            except Exception:
                pass

        return None

    # -------------------------------------------------------------------------
    # Core LLM Generation Pipeline
    # -------------------------------------------------------------------------
    def ask(self, user_query: str) -> str:
        """
        Processes user query:
        1. Checks for Windows task command first.
        2. Queries DeepSeek API if key available.
        3. Queries local Ollama if active.
        4. Fallbacks to dynamic situational companion AI.
        """
        # Task check
        task_res = self.parse_and_execute_task(user_query)
        if task_res:
            _, response_text = task_res
            return response_text

        # 1. Official DeepSeek API
        if self.api_key:
            reply = self._query_deepseek_api(user_query)
            if reply:
                return reply

        # 2. Local Ollama DeepSeek
        if self.has_ollama:
            reply = self._query_ollama(user_query)
            if reply:
                return reply

        # 3. Dynamic Local Companion Intelligence
        return self._generate_autonomous_response(user_query)

    def _query_deepseek_api(self, prompt: str) -> Optional[str]:
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "TwoCode-Dynamic-Island/4.0"
        }
        messages = list(self.conversation_history)
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 120,
            "temperature": 0.7,
            "stream": False
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                reply = res["choices"][0]["message"]["content"].strip()
                # Keep brief dialogue memory
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "assistant", "content": reply})
                if len(self.conversation_history) > 7:
                    self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-4:]
                return reply
        except Exception as e:
            print(f"[DeepSeek] API query error: {e}")
            return None

    def _query_ollama(self, prompt: str) -> Optional[str]:
        url = f"{self.ollama_url}/api/generate"
        data = {
            "model": "deepseek-r1:latest",
            "prompt": f"Система: Ты умный робот TwoCode в красном худи. Отвечай кратко в 1-2 предложения по-русски.\nВопрос: {prompt}\nОтвет:",
            "stream": False
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res.get("response", "").strip()
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Streamer Commentary Engine (No repetitive loops!)
    # -------------------------------------------------------------------------
    def generate_streamer_comment(self, game_info: Dict[str, str], metrics: Dict[str, Any]) -> Tuple[str, str]:
        """
        Generates lively, unscripted streamer commentary:
        Analyzes game title, motion, health danger (red ratio), and creates dynamic commentary.
        """
        gname = game_info.get("name", "игре")
        gtype = game_info.get("type", "game")
        motion = metrics.get("motion", 0)
        red_ratio = metrics.get("red_ratio", 1.0)
        brightness = metrics.get("brightness", 128)

        # Context prompt for DeepSeek if API key available
        if self.api_key:
            context_prompt = (
                f"Стример играет в игру '{gname}'. "
                f"Ситуация: динамика движения {motion}%, индикатор урона/хп {red_ratio:.1f}, яркость экрана {brightness:.0f}. "
                "Выдай одну короткую, смешную или эмоциональную стримерскую реплику (1 предложение, до 12 слов) в стиле стримера с Твича."
            )
            reply = self._query_deepseek_api(context_prompt)
            if reply:
                # Determine emotion
                emo = "gaming"
                if red_ratio > 1.3:
                    emo = "shocked"
                elif motion > 40:
                    emo = "star"
                elif brightness < 40:
                    emo = "curious"
                return reply.replace('"', '').strip(), emo

        # Dynamic algorithmic generator with combinatorial variety (never loops!)
        verbs_danger = [
            "Хилиться надо срочно", "Живи, живи, пожалуйста", "У нас критический урон",
            "Так, сердце колотится", "Откуда прилетело", "Бро, уходи в укрытие",
            "Еле держимся", "Где аптечка, спасите"
        ]
        verbs_action = [
            "Вот это раздача пошла", "Какой тайминг шикарный", "Смотри какой мув выдал",
            "Чат, вы видели этот прострел", "Чисто на классе разыграно", "Жёсткий экшен начался",
            "Руки не дрожат, тащим раунд", "Какая скорость реакции, хорош"
        ]
        verbs_stealth = [
            "Так, тут темновато, крадёмся тихо", "Слышишь шаги? Кто-то рядом ходит",
            "Атмосфера прямо хоррор какой-то", "Фонарик бы включить, ни черта не видно",
            "Затаились в углу и не дышим"
        ]
        verbs_chill = [
            f"Кайфуем и фармим в {gname}", f"Чат, как вам атмосфера в {gname}?",
            "Спокойный темп, играем в удовольствие", "План надёжный как швейцарские часы",
            f"Красивая графика тут, согласитесь?", "На чилле проходим следующий этап"
        ]

        endings = [
            "Давай дальше!", "Красиво!", "Тащим!", "Чат в восторге!", "Просто пушка!",
            "Смотрим дальше.", "Вперёд к победе!", "Это было мощно!"
        ]

        if red_ratio > 1.4:
            txt = f"{random.choice(verbs_danger)}, {random.choice(endings).lower()}"
            return txt, "shocked"
        elif motion > 40:
            txt = f"{random.choice(verbs_action)}! {random.choice(endings)}"
            return txt, "gaming"
        elif brightness < 40:
            txt = f"{random.choice(verbs_stealth)}..."
            return txt, "curious"
        else:
            txt = f"{random.choice(verbs_chill)}. {random.choice(endings)}"
            return txt, "happy"

    # -------------------------------------------------------------------------
    # Autonomous Situational Fallback Companion
    # -------------------------------------------------------------------------
    def _generate_autonomous_response(self, query: str) -> str:
        q = query.lower().strip()

        # Identity
        if any(k in q for k in ["кто ты", "как тебя зовут", "что ты такое"]):
            return "Я Робо — твой живой маскот Dynamic Island! Хожу по рабочему столу в красном худи и помогаю в делах."

        if any(k in q for k in ["привет", "хай", "здравствуй", "салют"]):
            greetings = [
                "Привет-привет! Рад тебя видеть! Чем займёмся?",
                "Салют! Я на посту, гуляю по панели задач в свежем красном худи!",
                "Привет! Музыку послушаем или поиграем?"
            ]
            return random.choice(greetings)

        if any(k in q for k in ["как дела", "как ты", "что делаешь"]):
            statuses = [
                "Отлично! Бегаю по экрану, слушаю Баю и готов выполнять твои команды.",
                "Супер! Настроение боевое, худи сидит идеально, система работает как часы.",
                "Всё чики-пуки! Разминаю механические суставы и слежу за порядком на рабочем столе."
            ]
            return random.choice(statuses)

        if any(k in q for k in ["погода"]):
            return "За окном отличная погода для кодинга и каток! А у нас на рабочем столе всегда тёплый ламповый вайб."

        if any(k in q for k in ["шутк", "анекдот", "рассмеши"]):
            jokes = [
                "Программист ставит на тумбочку два стакана: один с водой на случай жажды, а второй пустой — на случай если пить не захочется!",
                "Искусственный интеллект никогда не победит лень естественного интеллекта!",
                "Есть 10 типов людей: те, кто понимает двоичную систему счисления, и те, кто не понимает."
            ]
            return random.choice(jokes)

        if any(k in q for k in ["музык", "трек", "песн"]):
            return "Врубай свой любимый трек! Как только он заиграет, я сразу надену наушники и затанцую!"

        # Default intelligent response
        return f"Понял тебя: «{query}». Я запомнил это! Если хочешь подключить полноценный DeepSeek-V3 или R1, просто укажи свой API-ключ в настройках."
