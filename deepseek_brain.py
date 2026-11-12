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

# Load config / gitignored secrets for API key if present
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
SECRETS_PATH = os.path.join(APP_DIR, "secrets.json")
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
        self.recent_comments = []
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
        for path in (CONFIG_PATH, SECRETS_PATH):
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        if cfg.get("deepseek_api_key"):
                            self.api_key = cfg["deepseek_api_key"].strip()
                        if cfg.get("deepseek_model"):
                            self.model = cfg["deepseek_model"].strip()
                except Exception:
                    pass

    def save_api_key(self, key: str, model: str = "deepseek-chat"):
        """Save API key exclusively to gitignored secrets.json so config.json stays clean."""
        self.api_key = key.strip()
        self.model = model.strip()
        try:
            sec = {}
            if os.path.exists(SECRETS_PATH):
                with open(SECRETS_PATH, "r", encoding="utf-8") as f:
                    sec = json.load(f)
            sec["deepseek_api_key"] = self.api_key
            sec["deepseek_model"] = self.model
            with open(SECRETS_PATH, "w", encoding="utf-8") as f:
                json.dump(sec, f, ensure_ascii=False, indent=2)
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
            "prompt": f"Система: Ты — Астра (Astra), живой 3D-компаньон рабочего стола. Отвечай живо и кратко (1-2 предложения по-русски).\nЗапрос: {prompt}\nОтвет:",
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
    def _remember_comment(self, text: str) -> str:
        clean = (text or "").replace('"', '').strip()
        if clean:
            self.recent_comments.append(clean)
            if len(self.recent_comments) > 6:
                self.recent_comments.pop(0)
        return clean

    def _pick_fresh(self, candidates: list[str]) -> str:
        fresh = [c for c in candidates if c not in self.recent_comments]
        return random.choice(fresh if fresh else candidates)

    def generate_streamer_comment(self, game_info: Dict[str, str], metrics: Dict[str, Any]) -> Tuple[str, str]:
        """
        Generates live, screen-grounded commentary from real frame metrics,
        active window/app title, audio loudness, and Windows Neural OCR HUD text.
        """
        gname = game_info.get("name", "игре")
        gtype = game_info.get("type", "desktop")
        wtitle = (game_info.get("title") or "").strip()
        motion = float(metrics.get("motion", 0.0))
        red_ratio = float(metrics.get("red_ratio", 1.0))
        brightness = float(metrics.get("brightness", 128.0))
        scene_cut = bool(metrics.get("scene_cut", False))
        audio_peak = float(metrics.get("audio_peak", 0.0))
        hud_events = list(metrics.get("hud_events") or [])
        hp_val = metrics.get("hp_val")
        ocr_snippet = (metrics.get("ocr_snippet") or "").strip()
        ocr_text = (metrics.get("ocr_text") or ocr_snippet).strip()

        # Infer visual emotion honestly from live telemetry & HUD events
        def _infer_emotion() -> str:
            if "death" in hud_events or "defeat" in hud_events or "low_hp" in hud_events or red_ratio > 1.38:
                return "shocked"
            if "victory" in hud_events or "boss_or_level" in hud_events:
                return "star"
            if "error" in hud_events or ocr_snippet:
                return "curious"
            if motion > 38 or scene_cut or audio_peak > 0.65:
                return "gaming"
            if brightness < 42:
                return "curious"
            return "happy"

        # 1. Live LLM commentary (DeepSeek API or local Ollama) grounded in REAL screen data
        if self.api_key or self.has_ollama:
            facts = [f"Окно/игра: '{gname}' (тип: {gtype})"]
            if wtitle and wtitle != gname:
                facts.append(f"Заголовок: '{wtitle[:80]}'")
            facts.append(f"Кадр: движение={motion:.0f}%, красный={red_ratio:.2f}, яркость={brightness:.0f}/255, смена_сцены={scene_cut}, звук={audio_peak:.2f}")
            if hud_events:
                facts.append(f"События на HUD: {', '.join(hud_events)}" + (f" (HP={hp_val})" if hp_val else ""))
            if ocr_text:
                facts.append(f"Текст с экрана (OCR): «{ocr_text[:260]}»")
            avoid = f" Не повторяй прошлые фразы: {self.recent_comments[-3:]}" if self.recent_comments else ""

            context_prompt = (
                "Ты смотришь на реальный экран пользователя прямо сейчас.\n"
                + "\n".join(facts)
                + "\nВыдай одну короткую (1 предложение, 6-14 слов) живую, естественную реакцию по-русски именно на то, что видно на экране или происходит в игре/программе. "
                "Без выдумок того, чего нет в фактах." + avoid
            )
            reply = self._query_deepseek_api(context_prompt) if self.api_key else self._query_ollama(context_prompt)
            if reply:
                return self._remember_comment(reply), _infer_emotion()

        # 2. Honest grounded synthesizer (no LLM key): reacts directly to live HUD OCR & frame telemetry
        if "error" in hud_events:
            snippet_hint = f" («{ocr_snippet[:45]}»)" if ocr_snippet else ""
            cand = [
                f"Ого, на экране в {gname} вылезла ошибка{snippet_hint} — давай разберёмся!",
                f"Вижу ошибку в {gname}{snippet_hint}, проверяй логи или строку выше!",
            ]
            return self._remember_comment(self._pick_fresh(cand)), "curious"

        if "death" in hud_events:
            cand = [
                f"Эх, похоже в {gname} не повезло — не тильтуй, следующая точно за тобой!",
                f"Экран поражения в {gname}... Перезагружаемся и мстим!",
            ]
            return self._remember_comment(self._pick_fresh(cand)), "shocked"

        if "victory" in hud_events:
            cand = [
                f"Есть победа в {gname}! Красиво дожали до конца!",
                f"GG! Вижу победу на экране в {gname}, отличная катка!",
            ]
            return self._remember_comment(self._pick_fresh(cand)), "star"

        if "defeat" in hud_events:
            return self._remember_comment(self._pick_fresh([
                f"Раунд или матч в {gname} не зашёл — ничего, отыграемся!",
                f"Вижу поражение в {gname}, но опыт важнее — го реванш!",
            ])), "sad"

        if "low_hp" in hud_events:
            hp_str = f"{hp_val} HP" if hp_val is not None else "критически мало HP"
            return self._remember_comment(self._pick_fresh([
                f"Осторожнее в {gname}, осталось {hp_str} — срочно хилься!",
                f"Вижу на экране {hp_str}! Уходи в укрытие, не рискуй!",
            ])), "shocked"

        if "bomb" in hud_events:
            return self._remember_comment(self._pick_fresh([
                f"Бомба уже тикает в {gname}! Держим позиции и слушаем шаги!",
                f"Вижу постановку на пленте в {gname} — сейчас будет горячий клатч!",
            ])), "gaming"

        if "boss_or_level" in hud_events:
            return self._remember_comment(self._pick_fresh([
                f"Опа, на экране в {gname} новый уровень или босс — готовься!",
                f"Вижу босса / апгрейд в {gname}, не зевай и следи за таймингами!",
            ])), "star"

        # Real visual / audio spikes observed in frame
        if red_ratio > 1.38:
            return self._remember_comment(self._pick_fresh([
                f"Красный экран в {gname} — похоже прилетел плотный урон!",
                f"Ой-ой, всё замигало красным в {gname}, отступай!",
            ])), "shocked"

        if scene_cut:
            hint = f" («{ocr_snippet[:40]}»)" if ocr_snippet else ""
            return self._remember_comment(self._pick_fresh([
                f"Резкая смена сцены в {gname}{hint} — что там дальше началось?",
                f"Ого, кадр резко переключился{hint}! Погнали смотреть.",
            ])), "surprised"

        if motion > 38.0 or audio_peak > 0.68:
            return self._remember_comment(self._pick_fresh([
                f"В {gname} сейчас мощная динамика ({motion:.0f}% движения в кадре)!",
                f"Ого, в {gname} сейчас шумно и жарко — тащи на реакции!",
            ])), "gaming"

        if brightness < 42.0:
            return self._remember_comment(self._pick_fresh([
                f"В {gname} сейчас очень тёмная сцена (яркость {brightness:.0f}), прям хоррор-вайб!",
                f"Темно как в подземелье в {gname} — будь начеку!",
            ])), "curious"

        # Grounded context remarks citing actual window title / OCR snippet read from screen
        if ocr_snippet and len(ocr_snippet) >= 8:
            short_snip = ocr_snippet[:52].rstrip()
            return self._remember_comment(self._pick_fresh([
                f"Читаю с экрана ({gname}): «{short_snip}» — интересно!",
                f"Смотрю на «{short_snip}» в {gname}, хороший темп!",
            ])), "curious"

        if gtype == "poe":
            return self._remember_comment(self._pick_fresh([
                "Path of Exile на экране! Не забудь забрать орбы и чекнуть резисты.",
                "Чистим карту в PoE — пусть упадёт заветный дивайн!",
            ])), "gaming"
        if gtype == "cs2":
            return self._remember_comment(self._pick_fresh([
                "Counter-Strike 2! Держи прицел на уровне головы и чекай углы.",
                "Хороший темп в CS2 — ждём красивый клатч или эйс!",
            ])), "gaming"
        if gtype == "dota2":
            return self._remember_comment(self._pick_fresh([
                "Dota 2! Поглядывай на миникарту, чтобы мидер не гангнул.",
                "Фармим на слоты в Dota 2 — варды на базе не забывай!",
            ])), "gaming"
        if gtype == "minecraft":
            return self._remember_comment(self._pick_fresh([
                "Уютный Minecraft на экране — только не копай прямо под себя!",
                "Строимся в Minecraft! Не забудь факелы перед спуском в пещеру.",
            ])), "happy"
        if gtype == "cyberpunk":
            return self._remember_comment(self._pick_fresh([
                "Найт-Сити сияет! Сандевистан наготове, разбираемся с корпорантами.",
                "Атмосфера Cyberpunk 2077 на экране — какой же стильный город!",
            ])), "cool"
        if gtype == "video":
            return self._remember_comment(self._pick_fresh([
                f"Смотрим «{gname}»? Я тоже заглянула на экран!",
                f"О, ролик «{gname}» — интересный выбор, можно и под барабаны!",
            ])), "happy"
        if gtype == "ide":
            return self._remember_comment(self._pick_fresh([
                f"Кодим в {gname}? Продуктивный настрой — главное без багов!",
                f"Вижу открытый проект «{gname}» — затащим задачу чисто!",
            ])), "relaxed"

        return self._remember_comment(self._pick_fresh([
            f"Открыто окно «{gname}» (яркость {brightness:.0f}) — всё под контролем!",
            f"Слежу за «{gname}» вместе с тобой — зови, если понадоблюсь!",
        ])), "happy"

    # -------------------------------------------------------------------------
    # Autonomous Situational Fallback Companion
    # -------------------------------------------------------------------------
    def _generate_autonomous_response(self, query: str) -> str:
        q = query.lower().strip()

        if any(k in q for k in ["кто ты", "как тебя зовут", "что ты такое"]):
            return "Я Астра — твой живой 3D-компаньон Dynamic Island! Живу на рабочем столе и помогаю в делах."

        if any(k in q for k in ["привет", "хай", "здравствуй", "салют"]):
            return random.choice([
                "Привет-привет! Рада тебя видеть! Чем займёмся?",
                "Салют! Я рядом на рабочем столе, готова помочь или поболтать!",
                "Привет! Послушаем музыку с барабанами или пообщаемся?"
            ])

        if any(k in q for k in ["как дела", "как ты", "что делаешь"]):
            return random.choice([
                "Отлично! Прогуливаюсь по экрану и готова выполнять твои команды.",
                "Супер! Всё работает плавно, настроение боевое.",
                "Всё отлично! Слежу за порядком на рабочем столе."
            ])

        if any(k in q for k in ["погода"]):
            return "Отличная погода для кодинга и каток! А у нас на рабочем столе всегда тёплый вайб."

        if any(k in q for k in ["шутк", "анекдот", "рассмеши"]):
            return random.choice([
                "Программист ставит на тумбочку два стакана: один с водой на случай жажды, а второй пустой — на случай если пить не захочется!",
                "Искусственный интеллект никогда не победит лень естественного интеллекта!",
                "Есть 10 типов людей: те, кто понимает двоичную систему счисления, и те, кто не понимает."
            ])

        if any(k in q for k in ["музык", "трек", "песн"]):
            return "Врубай свой любимый трек! Как только он заиграет, я сразу надену наушники и сяду за барабаны!"

        return f"Поняла тебя: «{query}». Запомнила! Для полных нейро-диалогов добавь свой API-ключ DeepSeek в настройках."
