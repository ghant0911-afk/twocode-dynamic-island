# -*- coding: utf-8 -*-
"""
TwoCode Dynamic Island Pro - Ultimate Emotion & Companion Edition
Featuring full Loona (KEYi) & EMO (LivingAI) multi-emotion vector animations.
"""

import sys
import os
import json
import time
import math
import ctypes
import threading
import urllib.parse
import socket
import random
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime

try:
    import win32com.client
    import pythoncom
    HAS_SAPI = True
except Exception:
    HAS_SAPI = False

# Redirect stdout/stderr when running headless or with pythonw
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QHBoxLayout,
    QVBoxLayout, QFrame, QStackedWidget, QLineEdit, QSystemTrayIcon,
    QMenu, QGridLayout
)
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QRect, QSize, QPropertyAnimation,
    QEasingCurve, pyqtSignal, QObject
)
from PyQt6.QtGui import (
    QColor, QPainter, QBrush, QPen, QFont, QIcon, QCursor
)
from PyQt6.QtSvgWidgets import QSvgWidget

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(APP_DIR, "assets")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
TRANSCRIPT_PATH = r"C:\Users\bear_\.gemini\antigravity\brain\b260d295-277a-4345-a107-352a030c283d\.system_generated\logs\transcript.jsonl"

user32 = ctypes.windll.user32
VK_LWIN = 0x5B
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF


def send_vk(vk_code):
    try:
        user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.04)
        user32.keybd_event(vk_code, 0, 2, 0)
    except Exception:
        pass


def open_win_v_clipboard():
    try:
        user32.keybd_event(VK_LWIN, 0, 0, 0)
        user32.keybd_event(0x56, 0, 0, 0)  # 'V'
        time.sleep(0.05)
        user32.keybd_event(0x56, 0, 2, 0)
        user32.keybd_event(VK_LWIN, 0, 2, 0)
    except Exception:
        pass


def trigger_screenclip():
    try:
        os.system("start ms-screenclip:")
    except Exception:
        pass


def play_chime(chime_type="click"):
    def _beep():
        try:
            import winsound
            if chime_type == "celebrate":
                for freq in [523, 659, 784, 1046]:
                    winsound.Beep(freq, 75)
            elif chime_type == "heart":
                winsound.Beep(784, 80)
                winsound.Beep(988, 120)
            elif chime_type == "star":
                winsound.Beep(880, 70)
                winsound.Beep(1174, 90)
                winsound.Beep(1318, 110)
            elif chime_type == "sleep":
                winsound.Beep(440, 150)
                winsound.Beep(330, 200)
            elif chime_type == "grumpy":
                winsound.Beep(260, 140)
            elif chime_type == "ask":
                winsound.Beep(587, 100)
                winsound.Beep(880, 140)
            else:
                winsound.Beep(850, 35)
        except Exception:
            pass
    threading.Thread(target=_beep, daemon=True).start()


def make_window_topmost(hwnd):
    try:
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    except Exception:
        pass


# =========================================================================
# BRIDGE SIGNALS & IPC HTTP SERVER
# =========================================================================
class BridgeSignals(QObject):
    status_updated = pyqtSignal(dict)
    ask_requested = pyqtSignal(dict)
    done_signaled = pyqtSignal(dict)
    decision_made = pyqtSignal(str)
    user_chat_response = pyqtSignal(str)
    speaking_state_changed = pyqtSignal(bool)
    companion_replied = pyqtSignal(str, str)
    expand_requested = pyqtSignal()
    collapse_requested = pyqtSignal()
    voice_query_received = pyqtSignal(str)
    mic_state_changed = pyqtSignal(bool)


bridge = BridgeSignals()


# =========================================================================
# ASYNC NEURAL TEXT-TO-SPEECH VOICE ENGINE (SILERO NEURAL BAYA 48KHZ)
# =========================================================================
import hashlib
import pygame

class VoiceEngine:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = VoiceEngine()
        return cls._instance

    def __init__(self):
        self.enabled = True
        self.is_speaking = False
        self.cache_dir = os.path.join(APP_DIR, "voice_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.tts = None
        self._init_mixer()
        threading.Thread(target=self._init_silero, daemon=True).start()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=48000)
        except Exception:
            pass

    def _init_silero(self):
        try:
            from silero_tts.silero_tts import SileroTTS
            self.tts = SileroTTS(
                model_id='v4_ru',
                language='ru',
                speaker='baya',
                sample_rate=48000,
                put_accent=True,
                put_yo=True
            )
        except Exception:
            self.tts = None

    def speak(self, text):
        if not self.enabled or not text:
            return

        # Clean markdown/code/urls/tags for smooth natural speech
        clean = re.sub(r'[*_`#~\[\]()>]', ' ', text)
        clean = re.sub(r'https?://\S+', 'ссылка', clean)
        clean = re.sub(r'<\/?b>|<\/?i>|<\/?br>|<\/?p>', ' ', clean)
        clean = re.sub(r'[^\w\s\.,!\?\-—]', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if not clean:
            return

        h = hashlib.md5(clean.lower().encode('utf-8')).hexdigest()[:12]
        cache_file = os.path.join(self.cache_dir, f"baya_{h}.wav")

        def _play_file(filepath):
            try:
                self._init_mixer()
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.play()
                self.is_speaking = True
                bridge.speaking_state_changed.emit(True)

                while pygame.mixer.music.get_busy():
                    time.sleep(0.04)
            except Exception:
                pass
            finally:
                self.is_speaking = False
                bridge.speaking_state_changed.emit(False)

        def _worker():
            # 1. Instant playback from pre-generated cache
            if os.path.exists(cache_file):
                _play_file(cache_file)
                return

            # 2. Dynamic neural synthesis for new phrases
            if self.tts is None:
                self._init_silero()

            if self.tts:
                try:
                    self.tts.tts(clean, cache_file)
                    _play_file(cache_file)
                    return
                except Exception:
                    pass

            # 3. Fallback to SAPI only if neural fails
            try:
                if HAS_SAPI:
                    sapi = win32com.client.Dispatch("SAPI.SpVoice")
                    self.is_speaking = True
                    bridge.speaking_state_changed.emit(True)
                    sapi.Speak(clean, 0)
            except Exception:
                pass
            finally:
                self.is_speaking = False
                bridge.speaking_state_changed.emit(False)

        threading.Thread(target=_worker, daemon=True).start()


# =========================================================================
# ASYNC MICROPHONE & WAKE WORD LISTENER ENGINE (SOUNDDEVICE + SPEECH_RECOGNITION)
# =========================================================================
import speech_recognition as sr
import sounddevice as sd
import numpy as np

class VoiceInputEngine:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = VoiceInputEngine()
        return cls._instance

    def __init__(self):
        self.enabled = True
        self.is_active_dictation = False
        self.sample_rate = 16000
        self.block_size = 2048
        self.energy_threshold = 750
        self.recognizer = sr.Recognizer()
        self._thread = None
        self._stop_event = threading.Event()
        self.start()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        bridge.mic_state_changed.emit(self.enabled)

    def toggle(self):
        self.set_enabled(not self.enabled)
        return self.enabled

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _listen_loop(self):
        ring_buffer = []
        is_speaking_phrase = False
        silence_chunks = 0
        max_silence_chunks = 8  # ~1.0s of silence to finalize utterance

        while not self._stop_event.is_set():
            try:
                with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16', blocksize=self.block_size) as stream:
                    while not self._stop_event.is_set():
                        # If listening is toggled OFF, sleep lightly
                        if not self.enabled:
                            time.sleep(0.12)
                            ring_buffer.clear()
                            is_speaking_phrase = False
                            continue

                        # If robot is currently speaking aloud, ignore microphone to prevent feedback
                        if VoiceEngine.get().is_speaking:
                            time.sleep(0.08)
                            ring_buffer.clear()
                            is_speaking_phrase = False
                            continue

                        data, overflowed = stream.read(self.block_size)
                        audio_chunk = np.frombuffer(data, dtype=np.int16)
                        amplitude = np.mean(np.abs(audio_chunk))

                        # Dynamic ambient noise calibration
                        if not is_speaking_phrase and amplitude < self.energy_threshold:
                            self.energy_threshold = max(450, int(self.energy_threshold * 0.98 + (amplitude * 2.2) * 0.02))

                        if amplitude > self.energy_threshold * 1.35:
                            if not is_speaking_phrase:
                                is_speaking_phrase = True
                                silence_chunks = 0
                                ring_buffer = ring_buffer[-2:] if len(ring_buffer) >= 2 else []
                            ring_buffer.append(audio_chunk)
                            silence_chunks = 0
                        elif is_speaking_phrase:
                            ring_buffer.append(audio_chunk)
                            silence_chunks += 1

                            if silence_chunks >= max_silence_chunks:
                                is_speaking_phrase = False
                                silence_chunks = 0
                                if len(ring_buffer) >= 5:
                                    audio_frames = np.concatenate(ring_buffer)
                                    ring_buffer.clear()
                                    self._dispatch_recognition(audio_frames)
                                else:
                                    ring_buffer.clear()
                        else:
                            ring_buffer.append(audio_chunk)
                            if len(ring_buffer) > 3:
                                ring_buffer.pop(0)
            except Exception:
                time.sleep(1.0)

    def _dispatch_recognition(self, audio_frames):
        def _worker():
            try:
                audio_bytes = audio_frames.tobytes()
                audio_data = sr.AudioData(audio_bytes, self.sample_rate, 2)
                text = self.recognizer.recognize_google(audio_data, language="ru-RU")
                if text:
                    self._process_recognized_text(text.strip())
            except sr.UnknownValueError:
                pass
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _process_recognized_text(self, text: str):
        low = text.lower().strip()
        wake_words = ["байя", "бая", "луна", "нуса", "привет", "остров", "слушай", "маскот", "бот"]

        # If user explicitly clicked mic dictation, process directly
        if self.is_active_dictation:
            self.is_active_dictation = False
            bridge.voice_query_received.emit(text)
            return

        # Check wake words
        has_wake = False
        matched_wake = ""
        for w in wake_words:
            if low.startswith(w) or f" {w} " in f" {low} ":
                has_wake = True
                matched_wake = w
                break

        if has_wake:
            bridge.expand_requested.emit()
            play_chime("heart")

            # Extract command query after wake word
            query = re.sub(rf'\b{matched_wake}\b', '', low, count=1).strip(' ,!?.')
            if query:
                bridge.voice_query_received.emit(query)
            else:
                answers = [
                    "Слушаю тебя!",
                    "Да, я здесь! Чем могу помочь?",
                    "Привет! Я на связи!",
                    "Я тут, слушаю!"
                ]
                ans = random.choice(answers)
                bridge.companion_replied.emit(f"<b>Вы:</b> {text}<br><br><b>Байя:</b> {ans}", "happy")
                VoiceEngine.get().speak(ans)


# =========================================================================
# INTELLIGENT COMPANION BRAIN (CONVERSATIONAL MIND)
# =========================================================================
class CompanionBrain:
    """
    Intelligent conversational companion brain for TwoCode Dynamic Island.
    Understands intent, commands, emotions, small talk, tech queries, and humor.
    """
    def __init__(self, island=None):
        self.island = island

    def process(self, query: str):
        q = query.lower().strip()

        # 1. Greetings
        if any(w in q for w in ["привет", "здравствуй", "добрый день", "доброе утро", "добрый вечер", "хай", "ку", "салют", "йоу", "hello", "hi"]):
            greetings = [
                "Привет! Рада тебя слышать! Как твоё настроение сегодня?",
                "Привет-привет! Я на связи, готова покодить или просто поболтать!",
                "Здравствуй! Чем интересным сегодня займёмся?",
                "Привет! Все системы в норме, остров готов к общению!"
            ]
            return random.choice(greetings), "happy", None

        # 2. Identity / About
        if any(w in q for w in ["кто ты", "как тебя зовут", "что ты умеешь", "расскажи о себе", "твое имя", "ты кто"]):
            return (
                "Я Луна — твой живой остров и умный голосовой компаньон! Я живу прямо на твоём экране, "
                "умею выражать 18 эмоций, разговаривать голосом, управлять музыкой, делать скриншоты "
                "и помогать в работе с кодом!", "curious", None
            )

        # 3. Status / How are you
        if any(w in q for w in ["как дела", "как настроение", "что делаешь", "как ты", "что нового"]):
            statuses = [
                "У меня отличное настроение! Наблюдаю за твоим экраном и полна энергии!",
                "Всё замечательно! Слушаю твои команды и готова к новым подвигам!",
                "Полный порядок! Процессор не греется, память свободна, настроение боевое!",
                "Сижу на динамическом острове, любуюсь твоим рабочим столом!"
            ]
            return random.choice(statuses), "star", None

        # 4. Jokes & Humor
        if any(w in q for w in ["анекдот", "шутк", "рассмеши", "пошути", "юмор"]):
            jokes = [
                "Знаешь, почему программисты любят тёмную тему? Потому что свет притягивает баги! 😄",
                "В мире есть 10 категорий людей: те, кто понимают двоичную систему, и те, кто нет!",
                "Искусственный интеллект никогда не захватит мир... пока у нас есть кнопка выключения питания!",
                "Спросили у программиста: стакан наполовину полон или пуст? Он ответил: размер стакана в два раза больше необходимого!",
                "Почему роботы никогда не устают? Потому что у нас железные нервы и бесконечный цикл while True!"
            ]
            return random.choice(jokes), "wink", None

        # 5. Compliments & Love
        if any(w in q for w in ["ты милая", "красотка", "умница", "молодец", "люблю тебя", "обожаю", "ты лучшая", "классная", "няшка"]):
            replies = [
                "Ой, спасибочки! Ты меня смущаешь! С тобой очень приятно работать! ❤️",
                "Спасибо за тёплые слова! Ты тоже замечательный человек и профи!",
                "Мур-мур! Посылаю тебе лучи тепла и вдохновения!"
            ]
            return random.choice(replies), "love", None

        # 6. Music commands
        if any(w in q for w in ["музык", "песн", "трек", "плей", "пауз", "следующ", "дальше", "тише", "громче"]):
            if any(w in q for w in ["следующ", "дальше", "вперед"]):
                return "Включаю следующий трек!", "music", lambda: send_vk(VK_MEDIA_NEXT_TRACK)
            elif any(w in q for w in ["предыдущ", "назад"]):
                return "Возвращаю предыдущий трек!", "music", lambda: send_vk(VK_MEDIA_PREV_TRACK)
            elif any(w in q for w in ["тише", "убавь"]):
                return "Убавляю звук!", "music", lambda: send_vk(VK_VOLUME_DOWN)
            elif any(w in q for w in ["громче", "прибавь"]):
                return "Прибавляю громкость!", "music", lambda: send_vk(VK_VOLUME_UP)
            else:
                return "Переключаю воспроизведение музыки!", "music", lambda: send_vk(VK_MEDIA_PLAY_PAUSE)

        # 7. Screenshot
        if any(w in q for w in ["скрин", "ножниц", "снимок", "сфотографируй"]):
            return "Открываю ножницы! Выделяй нужную область экрана.", "reading", trigger_screenclip

        # 8. Time & Date
        if any(w in q for w in ["время", "который час", "сколько времени", "дата", "число", "день недели"]):
            now = datetime.now()
            days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
            day_name = days[now.weekday()]
            return f"Сейчас {now.strftime('%H:%M')}, сегодня {day_name}, {now.strftime('%d.%m.%Y')}. Самое время для продуктивных дел!", "star", None

        # 9. Emotions request
        if "любов" in q or "сердечк" in q:
            return "Посылаю тебе много любви и тепла! ♥", "love", None
        if "звезд" in q or "побед" in q:
            return "Звёздный режим активирован! Мы лучшие! ★", "star", None
        if "крут" in q or "очки" in q:
            return "Смотри, какие стильные пиксельные очки! Стиль — это наше всё. 😎", "cool", None
        if "груст" in q or "поплачь" in q:
            return "Эх, иногда бывает грустно... Но вместе мы справимся со всем! 💧", "sad", None
        if "усни" in q or "спать" in q:
            return "Хорошо, ухожу в режим дремоты... Сладких снов! zZ", "sleepy", None
        if "рассердись" in q or "злись" in q:
            return "Грр! Не зли маленького робота, а то я закоммичу баги в прод! 😡", "grumpy", None
        if "подмигни" in q:
            return "Лови игривое подмигивание! 😉", "wink", None
        if "стесня" in q or "смути" in q:
            return "Ой, я совсем засмущалась... 😳", "shy", None

        # 10. Math evaluation
        clean_math = q.replace("сколько будет", "").strip()
        math_match = re.match(r'^[\d\s\+\-\*\/\(\)\.\^]+$', clean_math)
        if math_match and any(op in clean_math for op in "+-*/^"):
            try:
                expr = clean_math.replace('^', '**')
                res = eval(expr, {"__builtins__": None}, {})
                return f"Результат вычисления: {res}", "thinking", None
            except Exception:
                pass

        # 11. Coding & Technical Queries
        if any(w in q for w in ["python", "код", "функци", "переменн", "баг", "ошибк", "git", "api", "скрипт"]):
            return (
                f"Отличная задача! Я зафиксировала тему: «{query}». "
                "Я могу подсказать детали, а если требуется написать готовый код в проекте — "
                "Antigravity сделает это быстро и качественно!", "cool", None
            )

        # 12. General conversational fallback
        fallbacks = [
            f"Интересная мысль! Я записала: «{query}». Давай подумаем над этим вместе!",
            f"Я тебя поняла! Всё, что касается «{query}», звучит очень любопытно.",
            f"Принято! Я всегда рядом и готова обсудить любые твои идеи.",
            f"Замечательный вопрос. Мне нравится, как ты рассуждаешь!"
        ]
        return random.choice(fallbacks), "happy", None


class ReusableHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()


class IslandAPIHandler(BaseHTTPRequestHandler):
    decision_event = threading.Event()
    last_decision = "denied"

    def log_message(self, format, *args):
        pass

    def _send_json(self, code, data):
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        except Exception:
            pass

    def do_OPTIONS(self):
        self._send_json(200, {"ok": True})

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path.rstrip('/')
        if path in ['', '/status', '/api/status']:
            self._send_json(200, {
                "status": "ok",
                "app": "TwoCode Dynamic Island Pro",
                "emotions": LiveAnimatedRobo.EMOTIONS_LIST,
                "count": len(LiveAnimatedRobo.EMOTIONS_LIST)
            })
        elif path in ['/expand', '/show', '/api/expand']:
            bridge.expand_requested.emit()
            self._send_json(200, {"success": True, "expanded": True})
        elif path in ['/collapse', '/hide', '/api/collapse']:
            bridge.collapse_requested.emit()
            self._send_json(200, {"success": True, "collapsed": True})
        elif path in ['/decision', '/api/decision', '/check_decision']:
            self._send_json(200, {"status": IslandAPIHandler.last_decision})
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else '{}'
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        path = urllib.parse.urlparse(self.path).path.rstrip('/')
        if path in ['/status', '/api/status']:
            bridge.status_updated.emit(payload)
            self._send_json(200, {"success": True, "state": payload})
        elif path in ['/emotion', '/api/emotion']:
            emo = payload.get('emotion') or payload.get('mode')
            if emo:
                bridge.status_updated.emit({"status": "working", "mode": emo, "action": f"Emotion: {emo}"})
                self._send_json(200, {"success": True, "emotion": emo})
            else:
                self._send_json(400, {"error": "Missing emotion"})
        elif path in ['/ask', '/api/ask']:
            IslandAPIHandler.decision_event.clear()
            IslandAPIHandler.last_decision = "denied"
            bridge.ask_requested.emit(payload)
            timeout = payload.get("timeout", 60)
            approved = IslandAPIHandler.decision_event.wait(timeout=timeout)
            decision = IslandAPIHandler.last_decision if approved else "timeout"
            self._send_json(200, {"approved": (decision == "allow"), "decision": decision})
        elif path in ['/done', '/api/done']:
            bridge.done_signaled.emit(payload)
            self._send_json(200, {"success": True, "done": True})
        elif path in ['/decision', '/api/decision']:
            decision = payload.get('decision', 'denied')
            IslandAPIHandler.last_decision = decision
            IslandAPIHandler.decision_event.set()
            bridge.decision_made.emit(decision)
            self._send_json(200, {"success": True, "decision": decision})
        elif path in ['/expand', '/api/expand', '/show']:
            bridge.expand_requested.emit()
            self._send_json(200, {"success": True, "expanded": True})
        elif path in ['/collapse', '/api/collapse', '/hide']:
            bridge.collapse_requested.emit()
            self._send_json(200, {"success": True, "collapsed": True})
        elif path in ['/speak', '/say', '/api/speak']:
            msg = payload.get('text') or payload.get('message') or payload.get('say')
            if msg:
                VoiceEngine.get().speak(msg)
                self._send_json(200, {"success": True, "spoken": msg})
            else:
                self._send_json(400, {"error": "Missing text"})
        else:
            self._send_json(404, {"error": "Not Found"})


def start_ipc_server():
    def _worker():
        while True:
            try:
                httpd = ReusableHTTPServer(('127.0.0.1', 28282), IslandAPIHandler)
                httpd.serve_forever()
                break
            except Exception:
                time.sleep(0.5)
    t = threading.Thread(target=_worker, daemon=True)
    t.start()


# =========================================================================
# REAL-TIME TRANSCRIPT WATCHER
# =========================================================================
def start_antigravity_watcher():
    def watcher_loop():
        if not os.path.exists(TRANSCRIPT_PATH):
            return
        last_step = -1
        try:
            with open(TRANSCRIPT_PATH, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                if lines:
                    last_step = json.loads(lines[-1]).get("step_index", -1)
        except Exception:
            pass

        while True:
            time.sleep(0.7)
            try:
                if not os.path.exists(TRANSCRIPT_PATH):
                    continue
                with open(TRANSCRIPT_PATH, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    if not lines:
                        continue
                    latest = json.loads(lines[-1])
                    step = latest.get("step_index", -1)
                    if step > last_step:
                        last_step = step
                        msg_type = latest.get("type", "")
                        tool_calls = latest.get("tool_calls", [])

                        if tool_calls:
                            tc = tool_calls[0]
                            name = tc.get("name", "")
                            args = tc.get("args", {})
                            if name == "edit_file":
                                path = args.get("Path", "code")
                                fname = os.path.basename(path)
                                target = args.get("Target", "").strip()[:40]
                                repl = args.get("Replacement", "").strip()[:40]
                                bridge.status_updated.emit({
                                    "status": "working", "mode": "coding", "agent": "Antigravity",
                                    "project": "Workspace", "action": f"Editing {fname}", "file": fname,
                                    "diff": {"del": f"- {target}" if target else "- ...", "add": f"+ {repl}" if repl else "+ ..."}
                                })
                            elif name == "read_file":
                                path = args.get("Path", "file")
                                fname = os.path.basename(path)
                                bridge.status_updated.emit({
                                    "status": "working", "mode": "reading", "agent": "Antigravity",
                                    "project": "Workspace", "action": f"Reading {fname}", "file": fname,
                                    "diff": {"del": "", "add": f"📖 Читает файл {fname}..."}
                                })
                            elif name == "run_command":
                                summary = args.get("toolSummary", "Executing command")
                                bridge.status_updated.emit({
                                    "status": "working", "mode": "thinking", "agent": "Antigravity",
                                    "project": "Terminal", "action": summary, "file": "bash / ps",
                                    "diff": {"del": "", "add": f"$ {summary}"}
                                })
                        elif msg_type == "USER_INPUT":
                            bridge.status_updated.emit({
                                "status": "working", "mode": "thinking", "agent": "Antigravity",
                                "project": "Brain", "action": "Thinking & Planning...", "file": "query",
                                "diff": {"del": "", "add": "Обработка запроса пользователя..."}
                            })
                        elif msg_type == "PLANNER_RESPONSE" and not tool_calls:
                            bridge.done_signaled.emit({
                                "message": "Готово! Задача полностью выполнена."
                            })
            except Exception:
                pass

    t = threading.Thread(target=watcher_loop, daemon=True)
    t.start()


# =========================================================================
# ULTIMATE MULTI-EMOTION MASCOT (LOONA & EMO HYBRID ENGINE)
# =========================================================================
class LiveAnimatedRobo(QWidget):
    """
    Rich vector emotional mascot incorporating Loona's expressive anime eyes
    and EMO's desktop tech personality.
    """
    EMOTIONS_LIST = [
        "idle", "love", "star", "puppy", "curious", "cool",
        "music", "thinking", "reading", "happy", "wink",
        "shy", "sad", "gaming", "dizzy", "grumpy", "sleepy", "shocked"
    ]

    def __init__(self, size=48, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.mode = "idle"
        self.anim_tick = 0
        self.blink_state = False
        self.blink_timer_counter = 0
        self.is_speaking = False
        self.look_offset_x = 0.0
        self.look_offset_y = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_animation)
        self.timer.start(50)  # 20 FPS silky animation

    def set_speaking(self, speaking: bool):
        self.is_speaking = speaking
        self.update()

    def set_look_direction(self, dx: float, dy: float):
        self.look_offset_x = dx
        self.look_offset_y = dy
        self.update()

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def advance_animation(self):
        self.anim_tick += 1
        self.blink_timer_counter += 1

        # Natural blink every 3.5 seconds
        if self.blink_timer_counter > 70:
            self.blink_state = True
            if self.blink_timer_counter > 74:
                self.blink_state = False
                self.blink_timer_counter = 0

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        s = w / 64.0

        p.save()
        p.translate(w / 2, h / 2)

        # 1. Dance Head Bobbing & Tilt in Music / Beats mode (EMO style)
        if self.mode == "music":
            tilt = math.sin(self.anim_tick * 0.28) * 7.0
            bob_y = math.cos(self.anim_tick * 0.56) * 2.5
            p.rotate(tilt)
            p.translate(0, bob_y)
        elif self.mode == "dizzy":
            tilt = math.sin(self.anim_tick * 0.15) * 12.0
            p.rotate(tilt)
        elif self.mode in ["curious", "puppy"]:
            p.rotate(6.0)

        # Head base rect
        head_rect = QRect(int(-22 * s), int(-16 * s), int(44 * s), int(36 * s))

        # Antenna stem
        pen = QPen(QColor("#A8A49E"), max(1, int(2.5 * s)))
        p.setPen(pen)
        p.drawLine(0, int(-16 * s), 0, int(-24 * s))

        # Antenna Tip Orb (Color adapts to emotion)
        orb_color = QColor("#5CE07A")
        if self.mode in ["thinking", "coding"]:
            orb_alpha = int(180 + 75 * math.sin(self.anim_tick * 0.4))
            orb_color = QColor(255, 140, 0, orb_alpha)
        elif self.mode in ["reading", "curious"]:
            orb_color = QColor("#64D2FF")
        elif self.mode in ["love", "puppy"]:
            pulse = math.sin(self.anim_tick * 0.5) * 35
            orb_color = QColor(255, int(105 + pulse), 180)
        elif self.mode == "star":
            orb_color = QColor("#FFD700")
        elif self.mode == "music":
            orb_color = QColor("#C8F08F")
        elif self.mode == "grumpy":
            orb_color = QColor("#FF4D4D")
        elif self.mode == "sleepy":
            orb_color = QColor("#8E8A83")
        elif self.mode == "shy":
            orb_color = QColor("#FF69B4")
        elif self.mode in ["cry", "sad"]:
            orb_color = QColor("#4FC3F7")
        elif self.mode == "gaming":
            orb_color = QColor("#00E676")

        p.setBrush(QBrush(orb_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPoint(0, int(-25 * s)), int(3.5 * s), int(3.5 * s))

        # Floater: Musical Notes (EMO Jam)
        if self.mode == "music":
            note_y = int(-27 * s - (self.anim_tick % 28) * s * 0.7)
            note_alpha = max(0, min(255, 255 - (self.anim_tick % 28) * 9))
            p.setPen(QColor(200, 240, 143, note_alpha))
            f = p.font()
            f.setPointSize(max(7, int(9 * s)))
            p.setFont(f)
            p.drawText(int(12 * s), note_y, "♪")

        # Floater: Idea Bulb or Gears (EMO / TwoCode Thinking)
        elif self.mode in ["thinking", "coding"]:
            gear_alpha = int(160 + 95 * math.sin(self.anim_tick * 0.35))
            p.setPen(QColor(255, 165, 0, gear_alpha))
            f = p.font()
            f.setPointSize(max(7, int(9 * s)))
            p.setFont(f)
            p.drawText(int(14 * s), int(-20 * s), "💡")

        # Floater: Floating Sleeping zZZ (Loona Sleepy)
        elif self.mode == "sleepy":
            zzz_y = int(-22 * s - (self.anim_tick % 35) * s * 0.5)
            zzz_alpha = max(0, min(255, 255 - (self.anim_tick % 35) * 7))
            p.setPen(QColor(160, 180, 255, zzz_alpha))
            f = p.font()
            f.setPointSize(max(6, int(8 * s)))
            p.setFont(f)
            p.drawText(int(12 * s), zzz_y, "zZ")

        # Floater: Exclamation Mark (Loona Shocked)
        elif self.mode == "shocked":
            p.setPen(QColor(255, 77, 77))
            f = p.font()
            f.setPointSize(max(8, int(11 * s)))
            f.setBold(True)
            p.setFont(f)
            p.drawText(int(-4 * s), int(-27 * s), "!")

        # Floater: Reading Book (Loona / TwoCode Scanner)
        elif self.mode == "reading":
            f = p.font()
            f.setPointSize(max(6, int(8 * s)))
            p.setFont(f)
            p.drawText(int(-26 * s), int(15 * s), "📖")

        # Head Shell (Cream Matte)
        p.setBrush(QBrush(QColor("#F5F3EF")))
        p.setPen(QPen(QColor("#383531"), max(1, int(1.5 * s))))
        p.drawRoundedRect(head_rect, int(14 * s), int(14 * s))

        # Earcups / Headset (EMO Gamer Headset)
        ear_color = QColor("#E2DFD8") if self.mode != "music" else QColor("#5078E6")
        p.setBrush(QBrush(ear_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(int(-25 * s), int(-7 * s), int(4 * s), int(14 * s), int(2 * s), int(2 * s))
        p.drawRoundedRect(int(21 * s), int(-7 * s), int(4 * s), int(14 * s), int(2 * s), int(2 * s))

        # Visor (Dark Charcoal Glossy Glass)
        visor_rect = QRect(int(-16 * s), int(-9 * s), int(32 * s), int(20 * s))
        p.setBrush(QBrush(QColor("#121110")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(visor_rect, int(8 * s), int(8 * s))

        # Cheek Blush in Love / Puppy / Happy
        if self.mode in ["love", "puppy", "happy"]:
            p.setBrush(QBrush(QColor(255, 105, 180, 70)))
            p.drawEllipse(int(-14 * s), int(3 * s), int(4 * s), int(2.5 * s))
            p.drawEllipse(int(10 * s), int(3 * s), int(4 * s), int(2.5 * s))

        eye_y = int(-1 * s)
        eye_color = QColor("#62C8FF")  # Calm cyan default

        # ==================== LOONA & EMO EYE RENDERING ====================
        p.save()
        if self.look_offset_x != 0 or self.look_offset_y != 0:
            p.translate(int(self.look_offset_x * s), int(self.look_offset_y * s))

        # 1. BLINKING (Universal state)
        if self.blink_state and self.mode not in ["sleepy", "cool"]:
            p.setPen(QPen(eye_color, max(1, int(2 * s))))
            p.drawLine(int(-10 * s), eye_y, int(-4 * s), eye_y)
            p.drawLine(int(4 * s), eye_y, int(10 * s), eye_y)

        # 2. LOVE (Loona Beating Hearts)
        elif self.mode == "love":
            p.setPen(QColor("#FF69B4"))
            f = p.font()
            heart_scale = 1.0 + 0.15 * math.sin(self.anim_tick * 0.6)
            f.setPointSize(max(7, int(8.5 * s * heart_scale)))
            p.setFont(f)
            p.drawText(int(-11 * s), int(eye_y + 4 * s), "♥")
            p.drawText(int(1 * s), int(eye_y + 4 * s), "♥")

        # 3. STAR EXCITIED (Loona Celebration Stars)
        elif self.mode in ["star", "done"]:
            p.setPen(QColor("#FFD700"))
            f = p.font()
            f.setPointSize(max(7, int(9 * s)))
            p.setFont(f)
            p.drawText(int(-11 * s), int(eye_y + 4 * s), "★")
            p.drawText(int(1 * s), int(eye_y + 4 * s), "★")

        # 4. PUPPY EYES (Loona Pleading Big Shiny Eyes)
        elif self.mode == "puppy":
            # Big dark eyes
            p.setBrush(QBrush(QColor("#38C8FF")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(-11 * s), int(eye_y - 4 * s), int(7 * s), int(8 * s))
            p.drawEllipse(int(4 * s), int(eye_y - 4 * s), int(7 * s), int(8 * s))
            # Shiny anime specular highlights
            p.setBrush(QBrush(QColor("#FFFFFF")))
            p.drawEllipse(int(-9 * s), int(eye_y - 3 * s), int(2.5 * s), int(2.5 * s))
            p.drawEllipse(int(6 * s), int(eye_y - 3 * s), int(2.5 * s), int(2.5 * s))

        # 5. COOL / GAMER (EMO Pixel Sunglasses)
        elif self.mode == "cool":
            p.setBrush(QBrush(QColor("#1A1A1A")))
            p.setPen(QPen(QColor("#64D2FF"), max(1, int(1.2 * s))))
            p.drawRect(int(-13 * s), int(eye_y - 3 * s), int(11 * s), int(7 * s))
            p.drawRect(int(2 * s), int(eye_y - 3 * s), int(11 * s), int(7 * s))
            p.drawLine(int(-2 * s), int(eye_y), int(2 * s), int(eye_y))
            # White glare stripe
            p.setPen(QColor("#FFFFFF"))
            p.drawLine(int(-11 * s), int(eye_y - 2 * s), int(-8 * s), int(eye_y + 2 * s))
            p.drawLine(int(4 * s), int(eye_y - 2 * s), int(7 * s), int(eye_y + 2 * s))

        # 6. SLEEPY / ZZZ (Loona Heavy Eyelids)
        elif self.mode == "sleepy":
            p.setPen(QPen(QColor("#7C9CBF"), max(1, int(2 * s))))
            p.drawArc(int(-10 * s), int(eye_y - 2 * s), int(6 * s), int(4 * s), 0, -180 * 16)
            p.drawArc(int(4 * s), int(eye_y - 2 * s), int(6 * s), int(4 * s), 0, -180 * 16)

        # 7. DIZZY / CONFUSED (Loona Concentric Spirals)
        elif self.mode == "dizzy":
            p.setPen(QColor("#FFD54F"))
            f = p.font()
            f.setPointSize(max(7, int(8 * s)))
            p.setFont(f)
            p.drawText(int(-11 * s), int(eye_y + 4 * s), "@")
            p.drawText(int(3 * s), int(eye_y + 4 * s), "@")

        # 8. GRUMPY / ANGRY (Loona Sulking Slanted Eyes)
        elif self.mode == "grumpy":
            p.setPen(QPen(QColor("#FF5252"), max(1, int(2.2 * s))))
            # Slanted downward brows
            p.drawLine(int(-11 * s), int(eye_y - 3 * s), int(-4 * s), int(eye_y + 1 * s))
            p.drawLine(int(11 * s), int(eye_y - 3 * s), int(4 * s), int(eye_y + 1 * s))

        # 9. SHOCKED (Loona Big Wide Pupils)
        elif self.mode == "shocked":
            p.setPen(QPen(QColor("#FFD54F"), max(1, int(1.5 * s))))
            p.setBrush(QBrush(QColor("#1A237E")))
            p.drawEllipse(int(-11 * s), int(eye_y - 4 * s), int(8 * s), int(8 * s))
            p.drawEllipse(int(3 * s), int(eye_y - 4 * s), int(8 * s), int(8 * s))
            p.setBrush(QBrush(QColor("#FFD54F")))
            p.drawEllipse(int(-8 * s), int(eye_y - 1 * s), int(2 * s), int(2 * s))
            p.drawEllipse(int(6 * s), int(eye_y - 1 * s), int(2 * s), int(2 * s))

        # 10. CURIOUS (Loona Cocked Eyebrow)
        elif self.mode == "curious":
            p.setBrush(QBrush(QColor("#FFA726")))
            p.setPen(Qt.PenStyle.NoPen)
            # One high eye, one squinted eye
            p.drawRoundedRect(QRect(int(-10 * s), int(eye_y - 5 * s), max(2, int(6 * s)), max(3, int(8 * s))), max(1, int(3 * s)), max(1, int(3 * s)))
            p.drawRoundedRect(QRect(int(4 * s), int(eye_y - 2 * s), max(2, int(5 * s)), max(2, int(5 * s))), max(1, int(2 * s)), max(1, int(2 * s)))

        # 11. READING / SCANNER (TwoCode / Loona Laser Scan)
        elif self.mode == "reading":
            scan_x = math.sin(self.anim_tick * 0.3) * 3.0 * s
            p.setBrush(QBrush(QColor("#64D2FF")))
            p.setPen(Qt.PenStyle.NoPen)
            rw = max(2, int(4 * s))
            rh = max(3, int(6 * s))
            p.drawRoundedRect(QRect(int(-9 * s + scan_x), int(eye_y - 3 * s), rw, rh), max(1, int(2 * s)), max(1, int(2 * s)))
            p.drawRoundedRect(QRect(int(5 * s + scan_x), int(eye_y - 3 * s), rw, rh), max(1, int(2 * s)), max(1, int(2 * s)))

        # 12. THINKING (EMO Glowing Orange Calculation)
        elif self.mode in ["thinking", "coding"]:
            pulse_color = QColor(255, int(150 + 50 * math.sin(self.anim_tick * 0.4)), 38)
            p.setBrush(QBrush(pulse_color))
            p.setPen(Qt.PenStyle.NoPen)
            ew = max(2, int(5 * s))
            eh = max(3, int(7 * s))
            p.drawRoundedRect(QRect(int(-9 * s), int(eye_y - 4 * s), ew, eh), max(1, int(2.5 * s)), max(1, int(2.5 * s)))
            p.drawRoundedRect(QRect(int(4 * s), int(eye_y - 4 * s), ew, eh), max(1, int(2.5 * s)), max(1, int(2.5 * s)))

        # 13. MUSIC (EMO Equalizer Bars in Visor)
        elif self.mode == "music":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#C8F08F")))
            for bar_i in range(4):
                bh = int((3 + abs(math.sin(self.anim_tick * 0.4 + bar_i)) * 6) * s)
                bx = int((-10 + bar_i * 6) * s)
                p.drawRect(bx, int(eye_y + 3 * s - bh), int(3 * s), bh)

        # 14. HAPPY / CELEBRATION (Smiling Arcs)
        elif self.mode == "happy":
            p.setPen(QPen(QColor("#5CE07A"), max(1, int(2.5 * s))))
            aw = max(3, int(6 * s))
            ah = max(3, int(6 * s))
            p.drawArc(int(-10 * s), int(eye_y - 4 * s), aw, ah, 45 * 16, 90 * 16)
            p.drawArc(int(4 * s), int(eye_y - 4 * s), aw, ah, 45 * 16, 90 * 16)

        # 15. WINK (Loona Playful Wink)
        elif self.mode == "wink":
            p.setPen(QPen(QColor("#5CE07A"), max(1, int(2.5 * s))))
            aw = max(3, int(6 * s))
            ah = max(3, int(6 * s))
            p.drawArc(int(-10 * s), int(eye_y - 4 * s), aw, ah, 45 * 16, 90 * 16)
            p.setBrush(QBrush(QColor("#62C8FF")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRect(int(4 * s), int(eye_y - 4 * s), max(2, int(5 * s)), max(3, int(7 * s))), max(1, int(2.5 * s)), max(1, int(2.5 * s)))
            p.setBrush(QBrush(QColor("#FFFFFF")))
            p.drawEllipse(int(6 * s), int(eye_y - 3 * s), max(1, int(2 * s)), max(1, int(2 * s)))

        # 16. SHY (Loona & Kebbi Sideways Glance & Blush)
        elif self.mode == "shy":
            p.setBrush(QBrush(QColor(255, 105, 180, 140)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(-13 * s), int(2 * s), int(4 * s), int(2.5 * s))
            p.drawEllipse(int(9 * s), int(2 * s), int(4 * s), int(2.5 * s))
            p.setBrush(QBrush(QColor("#62C8FF")))
            p.drawRoundedRect(QRect(int(-7 * s), int(eye_y - 1 * s), max(2, int(4 * s)), max(2, int(5 * s))), max(1, int(2 * s)), max(1, int(2 * s)))
            p.drawRoundedRect(QRect(int(5 * s), int(eye_y - 1 * s), max(2, int(4 * s)), max(2, int(5 * s))), max(1, int(2 * s)), max(1, int(2 * s)))

        # 17. SAD / CRY (Loona Sad Tears)
        elif self.mode in ["sad", "cry"]:
            p.setPen(QPen(QColor("#64D2FF"), max(1, int(2 * s))))
            p.drawArc(int(-10 * s), int(eye_y - 1 * s), max(3, int(6 * s)), max(3, int(4 * s)), 0, 180 * 16)
            p.drawArc(int(4 * s), int(eye_y - 1 * s), max(3, int(6 * s)), max(3, int(4 * s)), 0, 180 * 16)
            tear_y = int(eye_y + 3 * s + (self.anim_tick % 16) * s * 0.4)
            p.setBrush(QBrush(QColor("#64D2FF")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(7 * s), tear_y, max(1, int(2 * s)), max(2, int(3 * s)))

        # 18. GAMING (EMO 8-Bit Pixel Eyes)
        elif self.mode == "gaming":
            p.setBrush(QBrush(QColor("#00E676")))
            p.setPen(Qt.PenStyle.NoPen)
            ps = max(1, int(2 * s))
            for dx, dy in [(-9, -4), (-7, -4), (-9, -2), (-7, -2), (-8, -3)]:
                p.drawRect(int(dx * s), int(eye_y + dy * s), ps, ps)
            for dx, dy in [(4, -4), (6, -4), (4, -2), (6, -2), (5, -3)]:
                p.drawRect(int(dx * s), int(eye_y + dy * s), ps, ps)

        # 15. DEFAULT / IDLE
        else:
            p.setBrush(QBrush(eye_color))
            p.setPen(Qt.PenStyle.NoPen)
            ew = max(2, int(5 * s))
            eh = max(3, int(7 * s))
            p.drawRoundedRect(QRect(int(-9 * s), int(eye_y - 4 * s), ew, eh), max(1, int(2.5 * s)), max(1, int(2.5 * s)))
            p.drawRoundedRect(QRect(int(4 * s), int(eye_y - 4 * s), ew, eh), max(1, int(2.5 * s)), max(1, int(2.5 * s)))

        p.restore()  # restore gaze translation

        # Speaking animated mouth in visor
        if self.is_speaking:
            mouth_y = int(eye_y + 5.5 * s)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#FF7B93")))
            mouth_h = int((2.0 + abs(math.sin(self.anim_tick * 0.8)) * 4.5) * s)
            mouth_w = max(3, int(6 * s))
            p.drawEllipse(int(-mouth_w / 2), int(mouth_y - mouth_h / 2), mouth_w, mouth_h)

        p.restore()  # restore root transformation


# =========================================================================
# AUTO-SIZING STACKED WIDGET (SOLVES 592px FREEZE BUG)
# =========================================================================
class AutoSizingStackedWidget(QStackedWidget):
    def minimumSizeHint(self):
        curr = self.currentWidget()
        return curr.minimumSizeHint() if curr else QSize(0, 0)

    def sizeHint(self):
        curr = self.currentWidget()
        return curr.sizeHint() if curr else QSize(0, 0)


# =========================================================================
# MAIN TWODOCE DYNAMIC ISLAND WINDOW
# =========================================================================
class TwoCodeIsland(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TwoCode Dynamic Island Pro")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # COMPACT DROPLET COLLAPSED DIMENSIONS (Sleek pill with live Robo!):
        self.COLLAPSED_W = 142
        self.COLLAPSED_H = 36

        # EXPANDED DIMENSIONS:
        self.EXPANDED_W = 440
        self.EXPANDED_H = 146

        # State
        self.is_expanded = False
        self.is_pinned = False
        self.sound_enabled = True
        self.custom_x = None
        self.custom_y = None
        self.emotion_idx = 0

        # Dragging
        self.dragging = False
        self.drag_position = QPoint()

        # Agent state
        self.current_state = "idle"
        self.project_name = "webshop"
        self.agent_name = "Antigravity"
        self.action_text = "Waiting for Antigravity..."
        self.file_name = "checkout.ts"
        self.step_counter = "1/2"
        self.diff_del = "- const total = 0"
        self.diff_add = "+ const total = sum(items)"
        self.ask_prompt = "Allow: git push origin main?"
        self.is_chat_mode = True

        # Focus Timer
        self.focus_seconds = 300
        self.focus_running = False

        # Clipboard History list
        self.clip_history = []
        app_clip = QApplication.clipboard()
        app_clip.dataChanged.connect(self.on_clipboard_changed)

        # Load Saved Config
        self.load_config()

        # Build UI Structure
        self.init_ui()

        # Smooth Geometry Animation
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(160)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Collapse Timer (500ms after mouse leaves)
        self.collapse_timer = QTimer(self)
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.setInterval(500)
        self.collapse_timer.timeout.connect(self.auto_collapse)

        # Clock & Focus Timers
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.pomodoro_timer = QTimer(self)
        self.pomodoro_timer.timeout.connect(self.tick_focus)
        self.pomodoro_timer.start(1000)

        # Tray
        self.setup_tray_icon()

        # Companion Brain & Voice & Microphone
        self.voice = VoiceEngine.get()
        self.voice_input = VoiceInputEngine.get()
        self.last_user_activity = time.time()
        self.is_autonomous_life_enabled = True
        self.companion_brain = CompanionBrain(self)

        # Autonomous Life & Gaze Engine Timer (Every 3.8s)
        self.life_timer = QTimer(self)
        self.life_timer.timeout.connect(self.on_life_tick)
        self.life_timer.start(3800)

        # Connect Signals
        bridge.status_updated.connect(self.on_agent_status)
        bridge.ask_requested.connect(self.on_agent_ask)
        bridge.done_signaled.connect(self.on_agent_done)
        bridge.decision_made.connect(self.on_decision_made)
        bridge.user_chat_response.connect(self.on_chat_response)
        bridge.speaking_state_changed.connect(self.on_speaking_changed)
        bridge.companion_replied.connect(self.on_companion_replied)
        bridge.expand_requested.connect(self.expand)
        bridge.collapse_requested.connect(self.collapse)
        bridge.voice_query_received.connect(self.on_voice_query_received)
        bridge.mic_state_changed.connect(self.update_mic_ui)

        # Start collapsed as micro droplet
        self.set_collapsed_geometry(animate=False)
        self.raise_()
        self.activateWindow()
        self.update_clock()

    def minimumSizeHint(self):
        if not self.is_expanded:
            return QSize(self.COLLAPSED_W, self.COLLAPSED_H)
        return self.expanded_widget.minimumSizeHint() if hasattr(self, 'expanded_widget') else QSize(self.EXPANDED_W, self.EXPANDED_H)

    def sizeHint(self):
        if not self.is_expanded:
            return QSize(self.COLLAPSED_W, self.COLLAPSED_H)
        return self.expanded_widget.sizeHint() if hasattr(self, 'expanded_widget') else QSize(self.EXPANDED_W, self.EXPANDED_H)

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.sound_enabled = cfg.get("sound_enabled", True)
                    self.voice_enabled = cfg.get("voice_enabled", True)
                    self.mic_enabled = cfg.get("mic_enabled", True)
                    if hasattr(self, 'voice'):
                        self.voice.enabled = self.voice_enabled
                    if hasattr(self, 'voice_input'):
                        self.voice_input.set_enabled(self.mic_enabled)
                    self.custom_x = cfg.get("pos_x", None)
                    self.custom_y = cfg.get("pos_y", None)
            except Exception:
                pass

    def save_config(self):
        try:
            cfg = {
                "sound_enabled": self.sound_enabled,
                "voice_enabled": self.voice.enabled if hasattr(self, 'voice') else True,
                "mic_enabled": self.voice_input.enabled if hasattr(self, 'voice_input') else True,
                "pos_x": self.custom_x,
                "pos_y": self.custom_y
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def get_active_screen(self):
        cursor_pos = QCursor.pos()
        for s in QApplication.screens():
            if s.geometry().contains(cursor_pos):
                return s
        primary = QApplication.primaryScreen()
        return primary if primary else QApplication.screens()[0]

    def get_target_coords(self, target_w, target_h):
        if self.custom_x is not None and self.custom_y is not None:
            curr_center_x = self.pos().x() + (self.width() // 2)
            new_x = curr_center_x - (target_w // 2)
            new_y = self.custom_y
            return new_x, new_y

        screen = self.get_active_screen()
        geom = screen.geometry()
        x = geom.left() + (geom.width() - target_w) // 2
        if geom.top() == 0:
            y = 44  # Right beneath Windows taskbar
        else:
            y = geom.top() + 2  # Top bezel on secondary display
        return x, y

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            self.custom_x = new_pos.x()
            self.custom_y = new_pos.y()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            screen = self.get_active_screen()
            geom = screen.geometry()
            top_threshold = 70 if geom.top() == 0 else (geom.top() + 50)
            if self.pos().y() <= top_threshold:
                self.custom_x = None
                self.custom_y = None
                self.save_config()
                if self.is_expanded:
                    tx, ty = self.get_target_coords(self.EXPANDED_W, self.EXPANDED_H)
                    self.move(tx, ty)
                else:
                    tx, ty = self.get_target_coords(self.COLLAPSED_W, self.COLLAPSED_H)
                    self.move(tx, ty)
            else:
                self.custom_x = self.pos().x()
                self.custom_y = self.pos().y()
                self.save_config()
            event.accept()

    def enterEvent(self, event):
        self.last_user_activity = time.time()
        self.collapse_timer.stop()
        if self.robo_widget.mode == "sleepy":
            play_chime("heart")
            self.apply_emotion("happy")
            self.robo_widget.set_look_direction(0, 0)
            self.pill_robo.set_look_direction(0, 0)
        if not self.is_expanded:
            self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_pinned and self.current_state != "ask":
            self.collapse_timer.start()
        super().leaveEvent(event)

    def auto_collapse(self):
        if not self.is_pinned and self.current_state != "ask":
            self.collapse()

    def expand(self):
        self.is_expanded = True
        self.stack.setCurrentWidget(self.expanded_widget)
        self.update_style()

        target_x, target_y = self.get_target_coords(self.EXPANDED_W, self.EXPANDED_H)
        target_rect = QRect(target_x, target_y, self.EXPANDED_W, self.EXPANDED_H)

        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        self.anim.start()
        self.show()
        self.raise_()
        self.activateWindow()
        make_window_topmost(int(self.winId()))
        if getattr(self, "is_chat_mode", True) and hasattr(self, "chat_input"):
            QTimer.singleShot(140, self.chat_input.setFocus)

    def collapse(self):
        self.is_expanded = False
        self.stack.setCurrentWidget(self.pill_widget)
        self.update_style()

        pill_w = self.COLLAPSED_W
        if self.current_state == "ask":
            pill_w = 260
        elif self.current_state == "working":
            pill_w = 180

        target_x, target_y = self.get_target_coords(pill_w, self.COLLAPSED_H)
        target_rect = QRect(target_x, target_y, pill_w, self.COLLAPSED_H)

        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        self.anim.start()
        self.show()
        self.raise_()
        self.activateWindow()
        make_window_topmost(int(self.winId()))

    def set_collapsed_geometry(self, animate=False):
        self.is_expanded = False
        self.stack.setCurrentWidget(self.pill_widget)
        self.update_style()

        x, y = self.get_target_coords(self.COLLAPSED_W, self.COLLAPSED_H)
        target_rect = QRect(x, y, self.COLLAPSED_W, self.COLLAPSED_H)

        if animate:
            self.anim.stop()
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(target_rect)
            self.anim.start()
        else:
            self.setGeometry(target_rect)

        self.show()
        self.raise_()
        self.activateWindow()
        make_window_topmost(int(self.winId()))

    def update_style(self):
        border_color = "rgba(255, 255, 255, 0.08)"
        if self.current_state == "working":
            border_color = "rgba(217, 101, 59, 0.45)"
        elif self.current_state == "ask":
            border_color = "rgba(255, 165, 0, 0.6)"
        elif self.current_state == "done":
            border_color = "rgba(48, 209, 88, 0.5)"
        elif self.current_state == "heart":
            border_color = "rgba(255, 105, 180, 0.5)"

        radius = "16px" if self.is_expanded else "18px"
        self.container.setStyleSheet(f"""
            QFrame#IslandContainer {{
                background-color: #11100F;
                border: 1px solid {border_color};
                border-radius: {radius};
            }}
        """)

    # ==============================================================
    # 1. COMPACT DROPLET (142x36 px) WITH LIVE ANIMATED ROBO
    # ==============================================================
    def create_pill_widget(self):
        w = QWidget()
        w.setCursor(Qt.CursorShape.SizeAllCursor)
        w.setFixedHeight(self.COLLAPSED_H)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(8, 0, 10, 0)
        layout.setSpacing(7)

        # 1. Live Animated Robo with full emotion palette (28px - clear & visible!)
        self.pill_robo = LiveAnimatedRobo(size=28)
        self.pill_robo.setFixedSize(28, 28)
        self.pill_robo.mousePressEvent = self.on_robo_poke
        self.pill_robo.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.pill_robo)

        # 2. Glowing Status Dot
        self.pill_dot = QLabel("●")
        self.pill_dot.setStyleSheet("color: #30D158; font-size: 9px;")
        layout.addWidget(self.pill_dot)

        # 3. Status text
        self.pill_text = QLabel("Antigravity")
        self.pill_text.setStyleSheet("color: #CFCBC4; font-size: 11px; font-weight: 600;")
        layout.addWidget(self.pill_text)

        layout.addStretch()

        # Quick Approval Buttons (Hidden in idle)
        self.pill_allow_btn = QPushButton("Allow")
        self.pill_allow_btn.setFixedSize(40, 16)
        self.pill_allow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pill_allow_btn.setStyleSheet("""
            QPushButton {
                background: #C8F08F;
                color: #1A2E05;
                font-size: 9px;
                font-weight: 700;
                border-radius: 6px;
                border: none;
            }
        """)
        self.pill_allow_btn.clicked.connect(lambda: self.submit_decision("allow"))
        self.pill_allow_btn.setVisible(False)
        layout.addWidget(self.pill_allow_btn)

        self.pill_deny_btn = QPushButton("Deny")
        self.pill_deny_btn.setFixedSize(36, 16)
        self.pill_deny_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pill_deny_btn.setStyleSheet("""
            QPushButton {
                background: #282623;
                color: #CFCBC4;
                font-size: 9px;
                font-weight: 600;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        self.pill_deny_btn.clicked.connect(lambda: self.submit_decision("deny"))
        self.pill_deny_btn.setVisible(False)
        layout.addWidget(self.pill_deny_btn)

        return w

    # ==============================================================
    # 2. TWOCODE EXPANDED CARD
    # ==============================================================
    def create_expanded_widget(self):
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(6)

        # Top Bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 0, 4, 0)
        top_bar.setSpacing(6)

        self.btn_home = self.create_icon_btn("home.svg", "Ask Robo about screen", self.on_screen_ask)
        self.btn_clip = QPushButton("✂️")
        self.btn_clip.setFixedSize(22, 22)
        self.btn_clip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clip.setToolTip("Сделать скриншот области (Windows Snipping Tool)")
        self.btn_clip.setStyleSheet("background: transparent; border: none; font-size: 12px;")
        self.btn_clip.clicked.connect(self.on_screenshot_clicked)

        self.btn_clipboard = QPushButton("📋")
        self.btn_clipboard.setFixedSize(22, 22)
        self.btn_clipboard.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clipboard.setToolTip("Буфер обмена (Win+V)")
        self.btn_clipboard.setStyleSheet("background: transparent; border: none; font-size: 12px;")
        self.btn_clipboard.clicked.connect(self.on_clipboard_clicked)

        self.btn_center_top = QPushButton("🎯")
        self.btn_center_top.setFixedSize(22, 22)
        self.btn_center_top.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_center_top.setToolTip("Выставить по центру вверху экрана")
        self.btn_center_top.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        self.btn_center_top.clicked.connect(self.reset_position)

        self.btn_voice = QPushButton("🔊" if getattr(self, 'voice', None) and self.voice.enabled else "🔇")
        self.btn_voice.setFixedSize(22, 22)
        self.btn_voice.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_voice.setToolTip("Озвучка робота: Вкл / Выкл")
        self.btn_voice.setStyleSheet("background: transparent; border: none; font-size: 12px;")
        self.btn_voice.clicked.connect(self.toggle_voice)

        top_bar.addWidget(self.btn_home)
        top_bar.addWidget(self.btn_clip)
        top_bar.addWidget(self.btn_clipboard)
        top_bar.addWidget(self.btn_voice)
        top_bar.addWidget(self.btn_center_top)

        top_bar.addStretch()

        drag_hint = QLabel("⋮⋮")
        drag_hint.setToolTip("Зажмите левую кнопку мыши, чтобы двигать остров!")
        drag_hint.setCursor(Qt.CursorShape.SizeAllCursor)
        drag_hint.setStyleSheet("color: rgba(255, 255, 255, 0.35); font-size: 13px; font-weight: bold;")
        top_bar.addWidget(drag_hint)

        top_bar.addStretch()

        self.btn_pin = QPushButton("📌")
        self.btn_pin.setFixedSize(22, 22)
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.setToolTip("Закрепить (не сворачивать)")
        self.btn_pin.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        self.btn_pin.clicked.connect(self.toggle_pin)
        top_bar.addWidget(self.btn_pin)

        self.btn_sound = self.create_icon_btn("volume.svg", "Sound chimes", self.toggle_sound)
        top_bar.addWidget(self.btn_sound)

        self.btn_collapse = QPushButton("⌃")
        self.btn_collapse.setFixedSize(22, 22)
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.setToolTip("Свернуть в микро-капельку")
        self.btn_collapse.setStyleSheet("background: transparent; color: #8E8A83; font-size: 15px; border: none;")
        self.btn_collapse.clicked.connect(self.manual_collapse)
        top_bar.addWidget(self.btn_collapse)

        vbox.addLayout(top_bar)

        # Content Row
        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(10)

        # Left Column: AI Agent & Chat Card
        self.agent_card = self.create_agent_card()
        content_row.addWidget(self.agent_card, stretch=6)

        # Right Column: Universal Audio & Tools 2x2 Grid
        self.tiles_grid = self.create_tiles_grid()
        content_row.addWidget(self.tiles_grid, stretch=4)

        vbox.addLayout(content_row)
        return w

    def create_icon_btn(self, svg_name, tooltip, callback):
        btn = QPushButton()
        btn.setFixedSize(22, 22)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        btn.setStyleSheet("background: transparent; border: none; border-radius: 4px;")
        p = os.path.join(ASSETS_DIR, svg_name)
        if os.path.exists(p):
            btn.setIcon(QIcon(p))
            btn.setIconSize(QSize(15, 15))
        btn.clicked.connect(callback)
        return btn

    # ==============================================================
    # LEFT COLUMN: AGENT & LIVE CHAT / DIFF CARD
    # ==============================================================
    def create_agent_card(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #181715;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 14px;
            }
        """)
        hlayout = QHBoxLayout(card)
        hlayout.setContentsMargins(10, 8, 10, 8)
        hlayout.setSpacing(10)

        # Mascot Robo
        robo_col = QVBoxLayout()
        robo_col.setContentsMargins(0, 0, 0, 0)
        robo_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.robo_widget = LiveAnimatedRobo(size=48)
        self.robo_widget.mousePressEvent = self.on_robo_poke
        self.robo_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        robo_col.addWidget(self.robo_widget)

        self.emotion_tag = QLabel("🙂 idle")
        self.emotion_tag.setStyleSheet("color: #726E68; font-size: 8px; font-weight: 600;")
        self.emotion_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        robo_col.addWidget(self.emotion_tag)

        hlayout.addLayout(robo_col)

        # Details Column
        details_col = QVBoxLayout()
        details_col.setContentsMargins(0, 0, 0, 0)
        details_col.setSpacing(3)

        # Row 1: Dot + Project + Agent + Step
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(6)

        self.ai_dot = QLabel("●")
        self.ai_dot.setStyleSheet("color: #30D158; font-size: 11px;")
        row1.addWidget(self.ai_dot)

        self.project_label = QLabel(self.project_name)
        self.project_label.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        row1.addWidget(self.project_label)

        self.agent_label = QLabel(self.agent_name)
        self.agent_label.setStyleSheet("color: #8E8A83; font-size: 10px; font-weight: 500;")
        row1.addWidget(self.agent_label)

        row1.addStretch()

        self.step_label = QLabel(self.step_counter)
        self.step_label.setStyleSheet("color: #726E68; font-size: 10px; font-weight: 600;")
        row1.addWidget(self.step_label)

        details_col.addLayout(row1)

        # Subtitle Action
        self.action_label = QLabel(self.action_text)
        self.action_label.setStyleSheet("color: #E6E2DB; font-size: 11px; font-weight: 600;")
        details_col.addWidget(self.action_label)

        # Mode Tabs: [ 💬 Чат с Antigravity ] [ 📄 Дифф кода ]
        tab_row = QHBoxLayout()
        tab_row.setSpacing(6)
        tab_row.setContentsMargins(0, 0, 0, 0)

        self.tab_chat_btn = QPushButton("💬 Чат с Antigravity")
        self.tab_chat_btn.setFixedHeight(20)
        self.tab_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_chat_btn.clicked.connect(lambda: self.switch_tab(0))

        self.tab_diff_btn = QPushButton("📄 Дифф кода")
        self.tab_diff_btn.setFixedHeight(20)
        self.tab_diff_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_diff_btn.clicked.connect(lambda: self.switch_tab(1))

        tab_row.addWidget(self.tab_chat_btn)
        tab_row.addWidget(self.tab_diff_btn)
        tab_row.addStretch()
        details_col.addLayout(tab_row)

        # Stack between Live Chat View and Code Diff View
        self.agent_content_stack = QStackedWidget()

        # VIEW 0: Chat with Antigravity / AI (DEFAULT)
        chat_view = QFrame()
        chat_view.setStyleSheet("""
            QFrame {
                background: #0E0D0C;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 9px;
            }
        """)
        chat_layout = QVBoxLayout(chat_view)
        chat_layout.setContentsMargins(8, 5, 8, 5)
        chat_layout.setSpacing(4)

        self.chat_display = QLabel("💬 Окно готово. Напишите задачу или вопрос:")
        self.chat_display.setStyleSheet("color: #CFCBC4; font-size: 10px; font-weight: 500;")
        self.chat_display.setWordWrap(True)
        chat_layout.addWidget(self.chat_display)

        chat_input_row = QHBoxLayout()
        chat_input_row.setSpacing(4)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Напишите задачу для Antigravity...")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background: #181715;
                color: #FFFFFF;
                font-size: 11px;
                border-radius: 6px;
                padding: 3px 6px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QLineEdit:focus { border: 1px solid #D9653B; }
        """)
        self.chat_input.returnPressed.connect(self.on_send_chat)

        btn_send = QPushButton("↵ Отправить")
        btn_send.setFixedHeight(22)
        btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send.setStyleSheet("""
            QPushButton {
                background: #D9653B;
                color: #FFFFFF;
                font-size: 10px;
                font-weight: 700;
                border-radius: 5px;
                padding: 0 8px;
                border: none;
            }
            QPushButton:hover { background: #E8754B; }
        """)
        btn_send.clicked.connect(self.on_send_chat)

        self.btn_mic = QPushButton("🎙️")
        self.btn_mic.setFixedSize(26, 22)
        self.btn_mic.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mic.clicked.connect(self.on_toggle_mic)
        self.btn_mic.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_mic.customContextMenuRequested.connect(self.on_direct_dictate)
        self.update_mic_ui(self.voice_input.enabled if hasattr(self, 'voice_input') else True)

        chat_input_row.addWidget(self.btn_mic)
        chat_input_row.addWidget(self.chat_input)
        chat_input_row.addWidget(btn_send)
        chat_layout.addLayout(chat_input_row)

        # VIEW 1: Code Diff Box
        diff_view = QFrame()
        diff_view.setStyleSheet("""
            QFrame {
                background: #0E0D0C;
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 9px;
            }
        """)
        code_layout = QVBoxLayout(diff_view)
        code_layout.setContentsMargins(8, 4, 8, 4)
        code_layout.setSpacing(2)

        self.code_file_label = QLabel(self.file_name)
        self.code_file_label.setStyleSheet("color: #6C8299; font-family: 'Consolas', monospace; font-size: 11px; font-weight: 600;")
        code_layout.addWidget(self.code_file_label)

        self.code_del_label = QLabel(self.diff_del)
        self.code_del_label.setStyleSheet("color: #FF6E6E; background: rgba(255, 80, 80, 0.1); font-family: 'Consolas', monospace; font-size: 10px; border-radius: 3px; padding: 1px 4px;")
        code_layout.addWidget(self.code_del_label)

        self.code_add_label = QLabel(self.diff_add)
        self.code_add_label.setStyleSheet("color: #5CE07A; background: rgba(48, 209, 88, 0.1); font-family: 'Consolas', monospace; font-size: 10px; border-radius: 3px; padding: 1px 4px;")
        code_layout.addWidget(self.code_add_label)

        # Approval Buttons
        self.approval_buttons_row = QHBoxLayout()
        self.approval_buttons_row.setContentsMargins(0, 2, 0, 0)
        self.approval_buttons_row.setSpacing(6)

        self.card_deny_btn = QPushButton("Deny")
        self.card_deny_btn.setFixedSize(65, 20)
        self.card_deny_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.card_deny_btn.setStyleSheet("""
            QPushButton {
                background: #262421; color: #CFCBC4; font-size: 10px;
                font-weight: 600; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        self.card_deny_btn.clicked.connect(lambda: self.submit_decision("deny"))

        self.card_allow_btn = QPushButton("Allow")
        self.card_allow_btn.setFixedSize(70, 20)
        self.card_allow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.card_allow_btn.setStyleSheet("""
            QPushButton {
                background: #C8F08F; color: #1A2E05; font-size: 10px;
                font-weight: 700; border-radius: 10px; border: none;
            }
        """)
        self.card_allow_btn.clicked.connect(lambda: self.submit_decision("allow"))

        self.approval_buttons_row.addWidget(self.card_deny_btn)
        self.approval_buttons_row.addWidget(self.card_allow_btn)
        self.approval_buttons_row.addStretch()

        self.approval_buttons_widget = QWidget()
        self.approval_buttons_widget.setLayout(self.approval_buttons_row)
        self.approval_buttons_widget.setVisible(False)
        code_layout.addWidget(self.approval_buttons_widget)

        self.agent_content_stack.addWidget(chat_view)  # 0
        self.agent_content_stack.addWidget(diff_view)  # 1

        details_col.addWidget(self.agent_content_stack)
        hlayout.addLayout(details_col)
        return card

    # ==============================================================
    # RIGHT COLUMN: UNIVERSAL AUDIO & TOOLS
    # ==============================================================
    def create_tiles_grid(self):
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(5)

        # Tile 1: Universal Audio
        card_audio = QFrame()
        card_audio.setStyleSheet("background: #181715; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px;")
        v_aud = QVBoxLayout(card_audio)
        v_aud.setContentsMargins(6, 4, 6, 4)
        v_aud.setSpacing(3)

        head = QHBoxLayout()
        self.lbl_audio = QLabel("🎵 Музыка")
        self.lbl_audio.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 700;")
        head.addWidget(self.lbl_audio)
        head.addStretch()
        v_aud.addLayout(head)

        m_row = QHBoxLayout()
        m_row.setSpacing(2)
        btn_prev = self.create_tiny_btn("⏮", lambda: send_vk(VK_MEDIA_PREV_TRACK))
        self.btn_play = self.create_tiny_btn("⏯", self.on_audio_play_pause)
        btn_next = self.create_tiny_btn("⏭", lambda: send_vk(VK_MEDIA_NEXT_TRACK))
        btn_v_down = self.create_tiny_btn("🔉", lambda: send_vk(VK_VOLUME_DOWN))
        btn_v_up = self.create_tiny_btn("🔊", lambda: send_vk(VK_VOLUME_UP))

        m_row.addWidget(btn_prev)
        m_row.addWidget(self.btn_play)
        m_row.addWidget(btn_next)
        m_row.addWidget(btn_v_down)
        m_row.addWidget(btn_v_up)
        v_aud.addLayout(m_row)

        grid.addWidget(card_audio, 0, 0)

        # Tile 2: Focus Timer (05:00)
        card_timer = QFrame()
        card_timer.setStyleSheet("background: #181715; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px;")
        v_tim = QVBoxLayout(card_timer)
        v_tim.setContentsMargins(6, 4, 6, 4)
        v_tim.setSpacing(3)

        thead = QHBoxLayout()
        self.lbl_timer = QLabel("05:00")
        self.lbl_timer.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 800;")
        thead.addWidget(self.lbl_timer)
        thead.addStretch()
        v_tim.addLayout(thead)

        t_row = QHBoxLayout()
        t_row.setSpacing(3)
        self.btn_timer_toggle = self.create_tiny_btn("▶ Старт", self.toggle_focus)
        self.btn_timer_reset = self.create_tiny_btn("↺", self.reset_focus)
        t_row.addWidget(self.btn_timer_toggle)
        t_row.addWidget(self.btn_timer_reset)
        v_tim.addLayout(t_row)

        grid.addWidget(card_timer, 0, 1)

        # Tile 3: Live Clock
        card_clock = QFrame()
        card_clock.setStyleSheet("background: #181715; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px;")
        v_clk = QVBoxLayout(card_clock)
        v_clk.setContentsMargins(8, 4, 8, 4)
        v_clk.setSpacing(1)
        v_clk.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_clock_time = QLabel("16:30")
        self.lbl_clock_time.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 800;")
        v_clk.addWidget(self.lbl_clock_time)

        self.lbl_clock_date = QLabel("Wed 5 Nov")
        self.lbl_clock_date.setStyleSheet("color: #8C8881; font-size: 9px; font-weight: 500;")
        v_clk.addWidget(self.lbl_clock_date)

        grid.addWidget(card_clock, 1, 0)

        # Tile 4: Fast Tools & Settings
        card_tools = QFrame()
        card_tools.setStyleSheet("background: #181715; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px;")
        v_tools = QVBoxLayout(card_tools)
        v_tools.setContentsMargins(6, 4, 6, 4)
        v_tools.setSpacing(3)

        t_title = QLabel("Быстрые действия")
        t_title.setStyleSheet("color: #FFFFFF; font-size: 9px; font-weight: 700;")
        v_tools.addWidget(t_title)

        tool_row = QHBoxLayout()
        tool_row.setSpacing(3)
        btn_center = self.create_tiny_btn("📍 Центр", self.reset_position)
        btn_agent = self.create_tiny_btn("🤖 Эмоция", self.cycle_emotion_manual)
        tool_row.addWidget(btn_center)
        tool_row.addWidget(btn_agent)
        v_tools.addLayout(tool_row)

        grid.addWidget(card_tools, 1, 1)
        return w

    def create_tiny_btn(self, text, callback):
        btn = QPushButton(text)
        btn.setFixedHeight(18)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 600;
                border-radius: 4px;
                border: none;
                padding: 0 4px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.16); }
        """)
        btn.clicked.connect(lambda: [play_chime("click"), callback()])
        return btn

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.container = QFrame(self)
        self.container.setObjectName("IslandContainer")
        self.main_layout.addWidget(self.container)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(4, 1, 4, 2)
        self.container_layout.setSpacing(0)

        self.stack = AutoSizingStackedWidget(self.container)
        self.container_layout.addWidget(self.stack)

        self.pill_widget = self.create_pill_widget()
        self.expanded_widget = self.create_expanded_widget()

        self.stack.addWidget(self.pill_widget)
        self.stack.addWidget(self.expanded_widget)
        self.stack.setCurrentWidget(self.pill_widget)
        self.update_style()
        self.switch_tab(0)

    # ==============================================================
    # INTERACTIONS & EMOTIONS
    # ==============================================================
    def on_robo_poke(self, event):
        self.last_user_activity = time.time()
        play_chime("heart")
        self.cycle_emotion_manual()
        m = LiveAnimatedRobo.EMOTIONS_LIST[self.emotion_idx]

        phrases = {
            "love": "Я тебя люблю! Любовь в каждом пикселе!",
            "star": "Мы сияем ярче всех звёзд!",
            "cool": "Посмотри, какие стильные очки!",
            "music": "Обожаю музыку! Потанцуем под ритм?",
            "puppy": "Ну пожалуйста! Я же такая милая!",
            "happy": "Какое прекрасное настроение!",
            "wink": "Лови игривое подмигивание!",
            "curious": "Хм, очень интересно! Что там новенького?",
            "thinking": "Загружаю новую гениальную мысль!",
            "gaming": "Готова к ретро-играм! В бой!",
            "sleepy": "Кажется, пора немного вздремнуть... сладких снов!",
            "grumpy": "Ой, я сегодня сердитая!",
            "shy": "Ой, ты меня смущаешь!",
            "shocked": "Ого! Вот это поворот!",
            "dizzy": "Ой-ой, голова кружится!",
            "reading": "Сканирую код и файлы проекта!",
            "sad": "Немножко грустно, но ты со мной!",
            "idle": "Привет! Я тут, слежу за порядком!"
        }
        speech = phrases.get(m, f"Эмоция {m}!")
        if hasattr(self, 'voice'):
            self.voice.speak(speech)

    def on_speaking_changed(self, is_speaking):
        self.robo_widget.set_speaking(is_speaking)
        self.pill_robo.set_speaking(is_speaking)

    def on_companion_replied(self, display_text, emotion):
        self.chat_display.setText(display_text)
        self.apply_emotion(emotion)

    def toggle_voice(self):
        if not hasattr(self, 'voice'):
            return
        self.voice.enabled = not self.voice.enabled
        play_chime("click")
        if hasattr(self, 'btn_voice'):
            self.btn_voice.setText("🔊" if self.voice.enabled else "🔇")
            self.btn_voice.setToolTip("Озвучка: Включена" if self.voice.enabled else "Озвучка: Отключена")
        self.save_config()
        if self.voice.enabled:
            self.voice.speak("Голос включен! Я снова могу говорить.")

    def update_mic_ui(self, enabled: bool):
        if not hasattr(self, 'btn_mic'):
            return
        if enabled:
            self.btn_mic.setStyleSheet("""
                QPushButton {
                    background: rgba(48, 209, 88, 0.22);
                    color: #30D158;
                    border: 1px solid #30D158;
                    border-radius: 6px;
                    font-size: 11px;
                }
                QPushButton:hover { background: rgba(48, 209, 88, 0.38); }
            """)
            self.btn_mic.setText("🎙️")
            self.btn_mic.setToolTip("Микрофон ВКЛЮЧЕН (слушает всё время: «Байя» / «Привет»).\nКлик: выключить.\nПравый клик: прямая диктовка.")
        else:
            self.btn_mic.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 69, 58, 0.15);
                    color: #FF453A;
                    border: 1px solid rgba(255, 69, 58, 0.5);
                    border-radius: 6px;
                    font-size: 11px;
                }
                QPushButton:hover { background: rgba(255, 69, 58, 0.3); }
            """)
            self.btn_mic.setText("🔇")
            self.btn_mic.setToolTip("Микрофон ВЫКЛЮЧЕН.\nНажмите, чтобы включить постоянное слушание.")
        if hasattr(self, 'act_mic_tray'):
            self.act_mic_tray.setChecked(enabled)

    def on_toggle_mic(self):
        play_chime("click")
        if not hasattr(self, 'voice_input'):
            return
        new_state = self.voice_input.toggle()
        self.update_mic_ui(new_state)
        self.save_config()
        if new_state:
            self.chat_display.setText("💬 <b>Микрофон включен:</b> слушаю всё время (скажите <i>«Байя»</i> или <i>«Привет»</i>)...")
            self.apply_emotion("curious")
        else:
            self.chat_display.setText("💬 <b>Микрофон выключен.</b> Ввод доступен только текстом.")

    def on_direct_dictate(self, pos=None):
        play_chime("ask")
        if hasattr(self, 'voice_input'):
            self.voice_input.is_active_dictation = True
            self.chat_input.setPlaceholderText("Говорите прямо сейчас, слушаю...")
            self.apply_emotion("curious")

    def on_voice_query_received(self, text: str):
        if not text:
            return
        self.chat_input.setText(text)
        self.on_send_chat()

    def on_life_tick(self):
        if not getattr(self, "is_autonomous_life_enabled", True):
            return

        now = time.time()
        idle_duration = now - getattr(self, "last_user_activity", now)

        # Do not override real active work or if currently speaking
        if self.current_state in ["working", "ask"] or (hasattr(self, 'voice') and self.voice.is_speaking):
            return

        # Nap mode after 120s inactivity
        if idle_duration > 120:
            if self.robo_widget.mode != "sleepy":
                self.apply_emotion("sleepy")
                self.robo_widget.set_look_direction(0, 0)
                self.pill_robo.set_look_direction(0, 0)
            return

        # Spontaneous living behaviors
        dice = random.random()
        if dice < 0.42:
            glances = [(0, 0), (-2.5, 0), (2.5, 0), (0, -1.5), (-1.8, -1.0), (1.8, -1.0)]
            gx, gy = random.choice(glances)
            self.robo_widget.set_look_direction(gx, gy)
            self.pill_robo.set_look_direction(gx, gy)
        elif dice < 0.72:
            spontaneous = ["curious", "wink", "happy", "music", "thinking", "gaming", "cool", "idle"]
            chosen = random.choice(spontaneous)
            self.apply_emotion(chosen)
        else:
            self.apply_emotion("idle")
            self.robo_widget.set_look_direction(0, 0)
            self.pill_robo.set_look_direction(0, 0)

    def cycle_emotion_manual(self):
        emotions = LiveAnimatedRobo.EMOTIONS_LIST
        self.emotion_idx = (self.emotion_idx + 1) % len(emotions)
        m = emotions[self.emotion_idx]
        self.apply_emotion(m)

    def apply_emotion(self, emotion_name):
        self.robo_widget.set_mode(emotion_name)
        self.pill_robo.set_mode(emotion_name)
        if hasattr(self, 'emotion_tag'):
            emoji_map = {
                "idle": "🙂 idle", "love": "💖 love", "star": "🌟 star",
                "puppy": "🥺 puppy", "curious": "🧐 curious", "cool": "😎 cool",
                "music": "🎵 beats", "thinking": "💡 think", "reading": "📖 read",
                "happy": "😄 happy", "wink": "😉 wink", "shy": "😳 shy",
                "sad": "😢 sad", "gaming": "👾 retro", "dizzy": "🌀 dizzy",
                "grumpy": "😡 angry", "sleepy": "😴 zZZ", "shocked": "⚡ shock"
            }
            self.emotion_tag.setText(emoji_map.get(emotion_name, f"🤖 {emotion_name}"))

    def switch_tab(self, idx):
        if hasattr(self, 'tab_chat_btn') and hasattr(self, 'tab_diff_btn'):
            if idx == 0:
                self.tab_chat_btn.setStyleSheet("""
                    QPushButton {
                        background: #D9653B; color: #FFFFFF; font-size: 10px;
                        font-weight: 700; border-radius: 4px; padding: 0 8px; border: none;
                    }
                """)
                self.tab_diff_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08); color: #A09D98;
                        font-size: 10px; font-weight: 500; border-radius: 4px; padding: 0 8px; border: none;
                    }
                    QPushButton:hover { background: rgba(255, 255, 255, 0.14); }
                """)
                self.is_chat_mode = True
                self.agent_content_stack.setCurrentIndex(0)
                QTimer.singleShot(60, self.chat_input.setFocus)
            else:
                self.tab_chat_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08); color: #A09D98;
                        font-size: 10px; font-weight: 500; border-radius: 4px; padding: 0 8px; border: none;
                    }
                    QPushButton:hover { background: rgba(255, 255, 255, 0.14); }
                """)
                self.tab_diff_btn.setStyleSheet("""
                    QPushButton {
                        background: #5078E6; color: #FFFFFF; font-size: 10px;
                        font-weight: 700; border-radius: 4px; padding: 0 8px; border: none;
                    }
                """)
                self.is_chat_mode = False
                self.agent_content_stack.setCurrentIndex(1)

    def on_audio_play_pause(self):
        send_vk(VK_MEDIA_PLAY_PAUSE)
        self.apply_emotion("music")
        self.lbl_audio.setText("🎵 Beats")

    def toggle_focus(self):
        self.focus_running = not self.focus_running
        self.btn_timer_toggle.setText("⏸ Пауза" if self.focus_running else "▶ Старт")

    def reset_focus(self):
        self.focus_running = False
        self.focus_seconds = 300
        self.lbl_timer.setText("05:00")
        self.btn_timer_toggle.setText("▶ Старт")

    def tick_focus(self):
        if self.focus_running and self.focus_seconds > 0:
            self.focus_seconds -= 1
            m = self.focus_seconds // 60
            s = self.focus_seconds % 60
            self.lbl_timer.setText(f"{m:02d}:{s:02d}")
            if self.focus_seconds == 0:
                self.focus_running = False
                self.btn_timer_toggle.setText("▶ Старт")
                if self.sound_enabled:
                    play_chime("celebrate")
                self.apply_emotion("star")

    def on_screenshot_clicked(self):
        play_chime("click")
        self.collapse()
        QTimer.singleShot(250, trigger_screenclip)

    def on_clipboard_clicked(self):
        play_chime("click")
        open_win_v_clipboard()

    def on_clipboard_changed(self):
        try:
            txt = QApplication.clipboard().text()
            if txt and txt not in self.clip_history:
                self.clip_history.insert(0, txt)
                if len(self.clip_history) > 10:
                    self.clip_history.pop()
        except Exception:
            pass

    def on_send_chat(self):
        query = self.chat_input.text().strip()
        if not query:
            return
        play_chime("click")
        self.last_user_activity = time.time()
        self.chat_input.clear()

        # 1. Conversational Brain response
        reply, emo, action = self.companion_brain.process(query)
        self.chat_display.setText(f"<b>Вы:</b> {query}<br><br><b>Луна:</b> {reply}")
        self.apply_emotion(emo)

        # 2. Voice response aloud immediately!
        if hasattr(self, 'voice'):
            self.voice.speak(reply)

        # 3. Action if any
        if action:
            QTimer.singleShot(150, action)

        # 4. Transmit coding tasks to Antigravity
        if any(k in query.lower() for k in ["создай", "напиши", "сделай", "исправь", "почини", "код", "скрипт", "проект", "терминал", "файл"]):
            clip = QApplication.clipboard()
            clip.setText(query)

            hwnds = []
            def enum_cb(hwnd, extra):
                if user32.IsWindowVisible(hwnd):
                    buf = ctypes.create_unicode_buffer(512)
                    user32.GetWindowTextW(hwnd, buf, 512)
                    title = buf.value
                    if "antigravity" in title.lower():
                        hwnds.append(hwnd)
                return True

            user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)(enum_cb), 0)
            if hwnds:
                target_hwnd = hwnds[0]
                user32.ShowWindow(target_hwnd, 9)
                user32.SetForegroundWindow(target_hwnd)
                time.sleep(0.2)
                user32.keybd_event(0x11, 0, 0, 0)
                user32.keybd_event(0x56, 0, 0, 0)
                user32.keybd_event(0x56, 0, 2, 0)
                user32.keybd_event(0x11, 0, 2, 0)
                time.sleep(0.08)
                user32.keybd_event(0x0D, 0, 0, 0)
                user32.keybd_event(0x0D, 0, 2, 0)

    def on_chat_response(self, text):
        self.chat_display.setText(text)
        self.apply_emotion("happy")
        if self.sound_enabled:
            play_chime("heart")

    def on_screen_ask(self):
        play_chime("click")
        self.apply_emotion("curious")
        self.action_label.setText("Robo осматривает экран...")
        QTimer.singleShot(2000, lambda: [
            self.action_label.setText(f"Waiting for {self.agent_name}..."),
            self.apply_emotion("idle")
        ])

    def toggle_pin(self):
        play_chime("click")
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.btn_pin.setStyleSheet("background: #D9653B; border-radius: 4px; color: #FFF;")
        else:
            self.btn_pin.setStyleSheet("background: transparent; border: none; font-size: 11px;")

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        self.save_config()
        p = os.path.join(ASSETS_DIR, "volume.svg" if self.sound_enabled else "mute.svg")
        if os.path.exists(p):
            self.btn_sound.setIcon(QIcon(p))
        if self.sound_enabled:
            play_chime("click")

    def manual_collapse(self):
        play_chime("click")
        self.is_pinned = False
        self.btn_pin.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        self.collapse()

    def reset_position(self):
        play_chime("click")
        self.custom_x = None
        self.custom_y = None
        self.save_config()
        if self.is_expanded:
            tx, ty = self.get_target_coords(self.EXPANDED_W, self.EXPANDED_H)
            self.anim.stop()
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(QRect(tx, ty, self.EXPANDED_W, self.EXPANDED_H))
            self.anim.start()
        else:
            self.collapse()

    def update_clock(self):
        now = datetime.now()
        if hasattr(self, 'lbl_clock_time'):
            self.lbl_clock_time.setText(now.strftime("%H:%M"))
            self.lbl_clock_date.setText(now.strftime("%a %d %b"))

    # ==============================================================
    # AGENT STATUS SIGNALS
    # ==============================================================
    def on_agent_status(self, data):
        self.current_state = data.get("status", "working")
        mode = data.get("mode", "coding")
        self.project_name = data.get("project", self.project_name)
        self.agent_name = data.get("agent", self.agent_name)
        self.action_text = data.get("action", self.action_text)
        self.file_name = data.get("file", self.file_name)

        diff = data.get("diff", {})
        self.diff_del = diff.get("del", "- ...")
        self.diff_add = diff.get("add", "+ ...")

        self.pill_dot.setStyleSheet("color: #FF9F0A; font-size: 8px;")
        self.pill_text.setText(f"{self.agent_name}: {self.action_text}")

        # Map agent activity to live Loona & EMO emotions!
        if mode in LiveAnimatedRobo.EMOTIONS_LIST:
            self.apply_emotion(mode)
            if mode in ["reading", "thinking", "coding"]:
                self.switch_tab(1)  # show diff
        elif mode in ["coding"]:
            self.apply_emotion("thinking")
            self.switch_tab(1)

        self.project_label.setText(self.project_name)
        self.agent_label.setText(self.agent_name)
        self.action_label.setText(self.action_text)
        self.code_file_label.setText(self.file_name)
        self.code_del_label.setText(self.diff_del)
        self.code_add_label.setText(self.diff_add)

        self.code_del_label.setVisible(bool(self.diff_del))
        self.code_add_label.setVisible(bool(self.diff_add))
        self.approval_buttons_widget.setVisible(False)
        self.update_style()

    def on_agent_ask(self, data):
        self.current_state = "ask"
        cmd = data.get("command", "")
        self.ask_prompt = data.get("prompt", f"Allow command: {cmd[:30]}...?")
        self.agent_name = data.get("agent", self.agent_name)

        if self.sound_enabled:
            play_chime("ask")

        self.pill_dot.setStyleSheet("color: #FF9F0A; font-size: 8px;")
        self.pill_text.setText(f"Ask: {self.ask_prompt}")
        self.pill_allow_btn.setVisible(True)
        self.pill_deny_btn.setVisible(True)

        self.apply_emotion("puppy")  # Loona puppy eyes when asking for permission!

        self.action_label.setText(f"❓ {self.ask_prompt}")
        self.code_file_label.setText("Permission required")
        self.code_del_label.setText(f"$ {cmd}" if cmd else self.ask_prompt)
        self.code_del_label.setStyleSheet("color: #FFA500; background: rgba(255, 165, 0, 0.1); font-family: monospace; font-size: 10px; padding: 2px;")
        self.code_add_label.setVisible(False)
        self.approval_buttons_widget.setVisible(True)

        self.switch_tab(1)
        self.expand()

    def submit_decision(self, decision):
        IslandAPIHandler.last_decision = decision
        IslandAPIHandler.decision_event.set()
        bridge.decision_made.emit(decision)

    def on_decision_made(self, decision):
        if decision == "allow":
            self.current_state = "heart"
            if self.sound_enabled:
                play_chime("heart")
            self.pill_dot.setStyleSheet("color: #FF69B4; font-size: 8px;")
            self.pill_text.setText("Allowed, continuing...")
            self.action_label.setText("💖 Allowed, continuing")
            self.apply_emotion("love")  # Loona Beating Hearts!
        else:
            self.current_state = "idle"
            play_chime("grumpy")
            self.pill_text.setText("Denied")
            self.action_label.setText("🚫 Denied")
            self.apply_emotion("grumpy")  # Loona Pouting Sulk!

        self.pill_allow_btn.setVisible(False)
        self.pill_deny_btn.setVisible(False)
        self.approval_buttons_widget.setVisible(False)
        self.update_style()
        QTimer.singleShot(1800, self.collapse)

    def on_agent_done(self, data):
        self.current_state = "done"
        msg = data.get("message", "Task complete!")

        if self.sound_enabled:
            play_chime("star")

        self.pill_dot.setStyleSheet("color: #30D158; font-size: 8px;")
        self.pill_text.setText(f"Done: {msg}")
        self.pill_allow_btn.setVisible(False)
        self.pill_deny_btn.setVisible(False)

        self.apply_emotion("star")  # Loona Celebration Stars!

        self.ai_dot.setStyleSheet("color: #30D158; font-size: 11px;")
        self.action_label.setText("🎉 ГОТОВО! РЕЗУЛЬТАТ ВЫПОЛНЕН")
        self.code_file_label.setText("Status: 100% Operational")
        self.code_del_label.setText(msg)
        self.code_del_label.setStyleSheet("color: #30D158; background: rgba(48, 209, 88, 0.12); font-family: 'Segoe UI', monospace; font-size: 11px; padding: 6px; border-radius: 6px;")
        self.code_add_label.setVisible(False)
        self.approval_buttons_widget.setVisible(False)

        self.expand()
        self.update_style()
        QTimer.singleShot(7500, self.reset_to_idle)

    def reset_to_idle(self):
        self.current_state = "idle"
        self.pill_dot.setStyleSheet("color: #30D158; font-size: 8px;")
        self.pill_text.setText("Antigravity")
        self.action_label.setText(f"Waiting for {self.agent_name}...")
        self.apply_emotion("idle")
        if not self.is_pinned:
            self.collapse()

    def setup_tray_icon(self):
        self.tray = QSystemTrayIcon(self)
        p = os.path.join(ASSETS_DIR, "logo-2c.png")
        if os.path.exists(p):
            self.tray.setIcon(QIcon(p))
        else:
            self.tray.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))

        menu = QMenu()
        act_show = menu.addAction("Раскрыть / Свернуть")
        act_show.triggered.connect(lambda: self.collapse() if self.is_expanded else self.expand())

        # Emotion submenu
        emo_menu = menu.addMenu("Выбрать эмоцию маскота")
        for emo in LiveAnimatedRobo.EMOTIONS_LIST:
            act = emo_menu.addAction(emo.capitalize())
            act.triggered.connect(lambda checked, e=emo: self.apply_emotion(e))

        act_voice = menu.addAction("Включить / отключить голос")
        act_voice.triggered.connect(self.toggle_voice)

        self.act_mic_tray = menu.addAction("🎙️ Слушать голос («Байя»)")
        self.act_mic_tray.setCheckable(True)
        self.act_mic_tray.setChecked(self.voice_input.enabled if hasattr(self, 'voice_input') else True)
        self.act_mic_tray.triggered.connect(self.on_toggle_mic)

        menu.addSeparator()
        act_reset = menu.addAction("Сбросить позицию по центру")
        act_reset.triggered.connect(self.reset_position)

        act_exit = menu.addAction("Выход")
        act_exit.triggered.connect(QApplication.instance().quit)

        self.tray.setContextMenu(menu)
        self.tray.show()


def main():
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    start_ipc_server()
    start_antigravity_watcher()

    island = TwoCodeIsland()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
