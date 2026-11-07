"""
TwoCode Dynamic Island Pro - Production Master Edition
- Compact Droplet with FULL Animated Robot (antenna, orb, eyes, dance bob)
- Real Windows Media Engine via GSMTC (winsdk) - detects Yandex Music, Spotify, YouTube, Chrome
- Staggered File Shelf (Cards drop from top, open, explorer, delete)
- Ambient Robot AI Companion (Antigravity live status & decisions)
- Vayli Tools (CPU/RAM/Uptime, Quick Notes, Clipboard History, Snipping Tool)
- Always on Top toggle, Snug top edge bezel attachment
"""

import sys
import os

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import json
import time
import math
import random
import threading
import socket
import ctypes
from datetime import datetime
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
try:
    from desktop_pet import DesktopRoboPet
    from deepseek_brain import DeepSeekBrain
except Exception:
    DesktopRoboPet = None
import winsound

try:
    import psutil
except ImportError:
    psutil = None

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QRectF, QPoint, QPointF, QSize,
    pyqtSignal, QObject
)
from PyQt6.QtGui import (
    QColor, QFont, QCursor, QPainter, QBrush, QPen, QIcon, QPixmap,
    QPainterPath, QLinearGradient, QRadialGradient
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QStackedWidget, QSystemTrayIcon, QMenu, QSlider,
    QLineEdit, QTextEdit, QScrollArea, QFileDialog
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
SHELF_DATA_PATH = os.path.join(APP_DIR, "shelf_files.json")
NOTES_PATH = os.path.join(APP_DIR, "notes.txt")
SHELF_DIR = os.path.join(APP_DIR, "shelf_files")
os.makedirs(SHELF_DIR, exist_ok=True)

# Windows Virtual Keys
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
        user32.keybd_event(vk_code, 0, 2, 0)
    except Exception:
        pass

def open_win_v_clipboard():
    try:
        user32.keybd_event(VK_LWIN, 0, 0, 0)
        user32.keybd_event(ord('V'), 0, 0, 0)
        user32.keybd_event(ord('V'), 0, 2, 0)
        user32.keybd_event(VK_LWIN, 0, 2, 0)
    except Exception:
        pass

def trigger_screenclip():
    try:
        os.system('start ms-screenclip:')
    except Exception:
        pass

def make_window_topmost(hwnd):
    try:
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    except Exception:
        pass

def play_sound(kind="click"):
    def _run():
        try:
            if kind == "click":
                winsound.Beep(1200, 20)
            elif kind == "heart":
                winsound.Beep(1046, 50)
                winsound.Beep(1318, 70)
            elif kind in ["eat", "nom"]:
                # Playful munching cadence: chomp, chomp, chomp, happy gulp chime!
                winsound.Beep(523, 40)
                time.sleep(0.03)
                winsound.Beep(659, 45)
                time.sleep(0.03)
                winsound.Beep(784, 50)
                time.sleep(0.04)
                winsound.Beep(1046, 85)
            elif kind == "chime":
                winsound.Beep(784, 50)
                winsound.Beep(987, 50)
                winsound.Beep(1318, 90)
            elif kind == "alert":
                winsound.Beep(987, 80)
                winsound.Beep(784, 100)
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()

def format_file_size(bytes_num):
    if bytes_num < 1024:
        return f"{bytes_num} B"
    elif bytes_num < 1024 * 1024:
        return f"{bytes_num / 1024:.1f} KB"
    elif bytes_num < 1024 * 1024 * 1024:
        return f"{bytes_num / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_num / (1024 * 1024 * 1024):.1f} GB"

# ==============================================================================
# REAL WINDOWS MEDIA INTEGRATION (GSMTC & WINSDK)
# ==============================================================================
try:
    from media_engine import WindowsMediaWatcher, RealMediaState
    HAS_MEDIA_ENGINE = True
except Exception:
    HAS_MEDIA_ENGINE = False

try:
    from voice_engine import VoiceEngine, VoiceInputEngine, voice_bridge
    HAS_VOICE_ENGINE = True
except Exception:
    HAS_VOICE_ENGINE = False

try:
    from game_commentary import GameCommentaryEngine
    HAS_GAME_COMMENTARY = True
except Exception:
    HAS_GAME_COMMENTARY = False

# ==============================================================================
# LOCAL HTTP API SIGNALS (ANTIGRAVITY & EXTERNAL TOOLS)
# ==============================================================================
class BridgeSignals(QObject):
    agent_status = pyqtSignal(dict)
    agent_ask = pyqtSignal(dict)
    agent_done = pyqtSignal(dict)
    decision_made = pyqtSignal(str)
    bluetooth_popup = pyqtSignal(dict)
    shelf_add = pyqtSignal(list)
    media_state_changed = pyqtSignal(object)
    set_emotion = pyqtSignal(str)
    trigger_speech = pyqtSignal(str)
    trigger_commentary = pyqtSignal(bool)
    expand_requested = pyqtSignal()
    collapse_requested = pyqtSignal()
    snapshot_requested = pyqtSignal(str)
    select_tab = pyqtSignal(int)
    pet_toggle_requested = pyqtSignal()
    pet_spawn_requested = pyqtSignal()
    pet_dismiss_requested = pyqtSignal()

global_signals = BridgeSignals()

class ReusableHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

class IslandAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, status, payload):
        try:
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/status':
            self._send_json(200, {"status": "ok", "app": "TwoCode Dynamic Island Pro Unified", "version": "4.0.0"})
        elif parsed.path in ['/expand', '/api/expand']:
            global_signals.expand_requested.emit()
            self._send_json(200, {"status": "ok", "action": "expanded"})
        elif parsed.path in ['/collapse', '/api/collapse']:
            global_signals.collapse_requested.emit()
            self._send_json(200, {"status": "ok", "action": "collapsed"})
        elif parsed.path == '/api/chat':
            params = urllib.parse.parse_qs(parsed.query)
            q_list = params.get("q", [])
            query = q_list[0] if q_list else "Привет"
            try:
                from deepseek_brain import DeepSeekBrain
                ans = DeepSeekBrain.get().ask(query)
            except Exception as e:
                ans = str(e)
            self._send_json(200, {"status": "ok", "response": ans})
        elif parsed.path == '/api/pet/spawn':
            global_signals.pet_spawn_requested.emit()
            self._send_json(200, {"status": "ok", "action": "spawned"})
        elif parsed.path == '/api/pet/dismiss':
            global_signals.pet_dismiss_requested.emit()
            self._send_json(200, {"status": "ok", "action": "dismissed"})
        elif parsed.path == '/api/pet/toggle':
            global_signals.pet_toggle_requested.emit()
            self._send_json(200, {"status": "ok", "action": "toggled"})
        elif parsed.path == '/api/bluetooth':
            global_signals.bluetooth_popup.emit({"name": "Baseus Encok WM01", "battery": 79})
            self._send_json(200, {"status": "ok", "triggered": "bluetooth_popup"})
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
            data = json.loads(raw) if raw else {}
        except Exception:
            data = {}

        if parsed.path in ['/expand', '/api/expand']:
            global_signals.expand_requested.emit()
            self._send_json(200, {"status": "ok", "action": "expanded"})
        elif parsed.path in ['/collapse', '/api/collapse']:
            global_signals.collapse_requested.emit()
            self._send_json(200, {"status": "ok", "action": "collapsed"})
        elif parsed.path == '/api/status':
            global_signals.agent_status.emit(data)
            self._send_json(200, {"status": "ok"})
        elif parsed.path == '/api/ask':
            global_signals.agent_ask.emit(data)
            self._send_json(200, {"status": "ok"})
        elif parsed.path == '/api/done':
            global_signals.agent_done.emit(data)
            self._send_json(200, {"status": "ok"})
        elif parsed.path == '/api/bluetooth':
            global_signals.bluetooth_popup.emit(data)
            self._send_json(200, {"status": "ok"})
        elif parsed.path == '/api/shelf':
            files = data.get("files", [])
            if files:
                global_signals.shelf_add.emit(files)
            self._send_json(200, {"status": "ok", "added": len(files)})
        elif parsed.path == '/api/emotion':
            emotion = data.get("emotion", "idle")
            global_signals.set_emotion.emit(emotion)
            self._send_json(200, {"status": "ok", "emotion": emotion})
        elif parsed.path == '/api/speak':
            text = data.get("text", "")
            if text and HAS_VOICE_ENGINE:
                VoiceEngine.get().speak(text)
            self._send_json(200, {"status": "ok", "spoken": text})
        elif parsed.path == '/api/comment':
            global_signals.trigger_commentary.emit(True)
            self._send_json(200, {"status": "ok", "action": "commentary_triggered"})
        elif parsed.path == '/api/snapshot':
            path = data.get("path", "")
            global_signals.snapshot_requested.emit(path)
            self._send_json(200, {"status": "ok", "snapshot": path})
        elif parsed.path == '/api/chat':
            query = data.get("query", "")
            try:
                from deepseek_brain import DeepSeekBrain
                ans = DeepSeekBrain.get().ask(query)
            except Exception as e:
                ans = str(e)
            self._send_json(200, {"status": "ok", "response": ans})
        elif parsed.path == '/api/pet/spawn':
            global_signals.pet_spawn_requested.emit()
            self._send_json(200, {"status": "ok", "action": "spawned"})
        elif parsed.path == '/api/pet/dismiss':
            global_signals.pet_dismiss_requested.emit()
            self._send_json(200, {"status": "ok", "action": "dismissed"})
        elif parsed.path == '/api/pet/toggle':
            global_signals.pet_toggle_requested.emit()
            self._send_json(200, {"status": "ok", "action": "toggled"})
        elif parsed.path == '/api/tab':
            idx = int(data.get("tab", 0))
            global_signals.select_tab.emit(idx)
            self._send_json(200, {"status": "ok", "tab": idx})
        else:
            self._send_json(404, {"error": "Not Found"})

# ==============================================================================
# UI COMPONENTS & ANIMATIONS
# ==============================================================================
class AutoSizingStackedWidget(QStackedWidget):
    """StackedWidget that sizes dynamically to its active child widget."""
    def minimumSizeHint(self):
        curr = self.currentWidget()
        return curr.minimumSizeHint() if curr else QSize(0, 0)

    def sizeHint(self):
        curr = self.currentWidget()
        return curr.sizeHint() if curr else QSize(0, 0)


class EqualizerBars(QWidget):
    """4 animated jumping equalizer bars in cyan/green."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 16)
        self.tick = 0
        self.is_active = True

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(50)

    def advance(self):
        if self.is_active:
            self.tick += 1
            self.update()

    def set_active(self, active=True):
        self.is_active = active
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bar_w = 2.5
        spacing = 2.5
        x_start = 2.0
        max_h = 13.0

        phases = [0.0, 1.8, 3.4, 0.9]
        speeds = [0.25, 0.32, 0.28, 0.36]

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#30D158"))

        for i in range(4):
            if self.is_active:
                sin_val = math.sin(self.tick * speeds[i] + phases[i])
                bar_h = 3.0 + abs(sin_val) * (max_h - 3.0)
            else:
                bar_h = 3.0

            x = x_start + i * (bar_w + spacing)
            y = 14.0 - bar_h
            p.drawRoundedRect(QRectF(x, y, bar_w, bar_h), bar_w / 2.0, bar_w / 2.0)


def draw_vector_heart(p, cx, cy, r, color):
    p.save()
    p.setBrush(QBrush(color))
    p.setPen(Qt.PenStyle.NoPen)
    path = QPainterPath()
    path.moveTo(cx, cy + r * 0.8)
    path.cubicTo(cx - r * 1.3, cy - r * 0.2, cx - r * 0.9, cy - r * 1.3, cx, cy - r * 0.3)
    path.cubicTo(cx + r * 0.9, cy - r * 1.3, cx + r * 1.3, cy - r * 0.2, cx, cy + r * 0.8)
    p.drawPath(path)
    p.restore()


class LiveAnimatedRobo(QWidget):
    """
    Authentic TwoCode Mascot Companion with 60 FPS continuous physics-based animations:
    - Pure white 3D head with metallic shading & side ear pods
    - Curved antenna with glowing sphere orb & halo
    - Glass visor with upper specular reflection pill
    - Real continuous 3-phase eating animation: suction, chomping & squish, blissful heart gulp!
    """
    clicked = pyqtSignal()

    def __init__(self, size=22, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.size_val = size
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.mode = "idle"  # idle, music, thinking, coding, eating, nom, hungry, heart, star, shocked, gaming, cool, dizzy
        self.anim_tick = 0
        self.eat_time = 0.0
        self.blink_state = False
        self.blink_counter = 0

        # Silky smooth 50 FPS timer (20ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(20)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            play_sound("heart")
            self.set_mode("heart", duration_ms=2500)
            self.clicked.emit()
            event.accept()

    def set_mode(self, mode, duration_ms=0):
        self.mode = mode
        if mode in ["eating", "nom"]:
            self.eat_time = 0.0
        self.update()
        if duration_ms > 0 and mode not in ["eating", "nom"]:
            target_mode = mode
            QTimer.singleShot(duration_ms, lambda: self._reset_mode(target_mode))

    def _reset_mode(self, expected_mode):
        if self.mode == expected_mode:
            self.mode = "idle"
            self.eat_time = 0.0
            self.update()

    def advance(self):
        dt = 0.020  # 50 FPS
        self.anim_tick += 1

        if self.mode in ["eating", "nom"]:
            self.eat_time += dt
            if self.eat_time > 3.2:
                self.mode = "idle"
                self.eat_time = 0.0
        else:
            self.eat_time = 0.0
            # Natural periodic blinking
            self.blink_counter += 1
            if self.blink_counter > 140:
                self.blink_state = True
                if self.blink_counter > 147:
                    self.blink_state = False
                    self.blink_counter = 0

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        s = w / 64.0

        p.save()
        p.translate(w / 2.0, h / 2.0)

        # -------------------------------------------------------------
        # Physics calculations for continuous animation
        # -------------------------------------------------------------
        t = self.eat_time
        bob_y = 0.0
        tilt = 0.0
        squash_x = 1.0
        squash_y = 1.0
        mouth_ratio = 0.0
        antenna_flex = 0.0

        if self.mode in ["eating", "nom"]:
            if t < 0.6:
                # Stage 1: Anticipation & Suction Open (0.0s - 0.6s)
                p_prog = t / 0.6
                tilt = math.sin(p_prog * math.pi) * -4.0
                bob_y = -math.sin(p_prog * math.pi) * 2.0 * s
                mouth_ratio = math.sin(p_prog * math.pi * 0.5)
                antenna_flex = -2.0 * p_prog
            elif t < 2.2:
                # Stage 2: Continuous Chomping, Chewing & Squish (0.6s - 2.2s)
                chew_t = (t - 0.6) * 16.0
                bob_y = math.sin(chew_t) * 2.5 * s
                tilt = math.cos(chew_t * 0.5) * 4.0
                squash_x = 1.0 + 0.06 * math.sin(chew_t)
                squash_y = 1.0 - 0.06 * math.sin(chew_t)
                mouth_ratio = (math.sin(chew_t) + 1.0) / 2.0
                antenna_flex = math.sin(chew_t - 0.8) * 3.0
            else:
                # Stage 3: Gulp, Bliss & Happy Hearts (2.2s - 3.2s)
                g_prog = min(1.0, (t - 2.2) / 1.0)
                if g_prog < 0.25:
                    squash_y = 1.15
                    squash_x = 0.90
                    bob_y = 3.0 * s
                else:
                    bounce = math.exp(-(g_prog - 0.25) * 4.0) * math.cos((g_prog - 0.25) * 14.0)
                    bob_y = bounce * 2.0 * s
                mouth_ratio = 0.0
                tilt = math.sin(g_prog * math.pi * 2) * 2.0
        elif self.mode == "music":
            # Dance bobbing tilt in music mode
            m_t = self.anim_tick * 0.14
            tilt = math.sin(m_t) * 7.5
            bob_y = abs(math.cos(m_t)) * 2.2 * s
            antenna_flex = math.sin(m_t * 1.5) * 2.5
        elif self.mode == "dizzy":
            tilt = math.sin(self.anim_tick * 0.2) * 10.0
            bob_y = math.cos(self.anim_tick * 0.2) * 1.5 * s
        elif self.mode == "hungry":
            # Looking up in anticipation
            tilt = -3.0
            bob_y = -1.5 * s
            mouth_ratio = 0.85
            antenna_flex = -1.5
        else:
            # Idle gentle breathing float
            bob_y = math.sin(self.anim_tick * 0.06) * 0.8 * s

        # Apply transformation
        p.translate(0, bob_y)
        p.rotate(tilt)
        p.scale(squash_x, squash_y)

        # -------------------------------------------------------------
        # 1. Soft Ground Shadow
        # -------------------------------------------------------------
        p.setBrush(QColor(0, 0, 0, 40))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(-18 * s, 17 * s, 36 * s, 6 * s))

        # -------------------------------------------------------------
        # 2. Side Ear Pods (TwoCode signature capsule sensors)
        # -------------------------------------------------------------
        p.setBrush(QBrush(QColor("#E2E8F0")))
        p.setPen(QPen(QColor("#CBD5E1"), max(1, int(1.2 * s))))
        p.drawRoundedRect(QRectF(-26.5 * s, -6 * s, 5.5 * s, 13 * s), 2.5 * s, 2.5 * s)
        p.drawRoundedRect(QRectF(21.0 * s, -6 * s, 5.5 * s, 13 * s), 2.5 * s, 2.5 * s)

        # -------------------------------------------------------------
        # 3. Curved Antenna Stalk & Glowing Sphere Orb
        # -------------------------------------------------------------
        ant_path = QPainterPath()
        ant_path.moveTo(0, -17 * s)
        ant_path.cubicTo(antenna_flex * s, -22 * s, (antenna_flex + 1.5) * s, -25 * s, (antenna_flex + 1.0) * s, -28 * s)
        p.setPen(QPen(QColor("#E2E8F0"), max(1, int(2.4 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(ant_path)

        orb_center = QPointF((antenna_flex + 1.0) * s, -29 * s)
        orb_col = QColor("#5CE07A")
        if self.mode in ["eating", "nom"]:
            if t < 0.6:
                orb_col = QColor("#FFA116")
            elif t < 2.2:
                orb_col = QColor("#FFD60A") if (int(t * 15) % 2 == 0) else QColor("#30D158")
            else:
                orb_col = QColor("#FF4081")
        elif self.mode == "hungry":
            orb_col = QColor(255, 161, 22, int(210 + 45 * math.sin(self.anim_tick * 0.3)))
        elif self.mode in ["thinking", "coding"]:
            orb_col = QColor(255, 140, 0, int(180 + 75 * math.sin(self.anim_tick * 0.2)))
        elif self.mode == "music":
            orb_col = QColor("#A3E635")
        elif self.mode in ["heart", "love"]:
            orb_col = QColor("#FF4081")
        elif self.mode == "gaming":
            orb_col = QColor("#BF5AF2")
        elif self.mode == "shocked":
            orb_col = QColor("#FF453A")
        elif self.mode == "star":
            orb_col = QColor("#FFD60A")

        # Halo glow
        glow_grad = QRadialGradient(orb_center, 7 * s)
        glow_grad.setColorAt(0.0, QColor(orb_col.red(), orb_col.green(), orb_col.blue(), 140))
        glow_grad.setColorAt(1.0, QColor(orb_col.red(), orb_col.green(), orb_col.blue(), 0))
        p.setBrush(QBrush(glow_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(orb_center, 7 * s, 7 * s)

        # Crisp sphere
        p.setBrush(QBrush(orb_col))
        p.setPen(QPen(QColor("#FFFFFF"), max(1, int(0.8 * s))))
        p.drawEllipse(orb_center, 3.8 * s, 3.8 * s)

        # -------------------------------------------------------------
        # 4. White Head Body (Authentic TwoCode 3D volume & shading)
        # -------------------------------------------------------------
        head_grad = QLinearGradient(0, -18 * s, 0, 18 * s)
        head_grad.setColorAt(0.0, QColor("#FFFFFF"))
        head_grad.setColorAt(0.65, QColor("#F8FAFC"))
        head_grad.setColorAt(1.0, QColor("#E2E8F0"))

        p.setBrush(QBrush(head_grad))
        p.setPen(QPen(QColor("#CBD5E1"), max(1, int(1.2 * s))))
        p.drawRoundedRect(QRectF(-23 * s, -17 * s, 46 * s, 35 * s), 16 * s, 16 * s)

        # -------------------------------------------------------------
        # 5. Glossy Visor Screen
        # -------------------------------------------------------------
        visor_rect = QRectF(-18 * s, -11 * s, 36 * s, 24 * s)
        v_grad = QLinearGradient(0, -11 * s, 0, 13 * s)
        v_grad.setColorAt(0.0, QColor("#181820"))
        v_grad.setColorAt(1.0, QColor("#0D0D12"))
        p.setBrush(QBrush(v_grad))
        p.setPen(QPen(QColor("#252530"), max(1, int(0.8 * s))))
        p.drawRoundedRect(visor_rect, 10 * s, 10 * s)

        # Visor Upper Glass Reflection Pill
        p.setBrush(QColor(255, 255, 255, 32))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(-12 * s, -9.5 * s, 24 * s, 4 * s), 2 * s, 2 * s)

        # -------------------------------------------------------------
        # 6. Screen Emoticons / Continuous Fluid Eating Animation
        # -------------------------------------------------------------
        if self.mode in ["eating", "nom"]:
            if t < 0.6:
                # Stage 1: Anticipation eyes & opening mouth with file flying in
                p.setBrush(QColor("#5CE07A"))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(-13 * s, -7 * s, 7.5 * s, 8.5 * s))
                p.drawEllipse(QRectF(5.5 * s, -7 * s, 7.5 * s, 8.5 * s))
                p.setBrush(QColor("#FFFFFF"))
                p.drawEllipse(QRectF(-11 * s, -6 * s, 3.0 * s, 3.0 * s))
                p.drawEllipse(QRectF(7.5 * s, -6 * s, 3.0 * s, 3.0 * s))

                m_h = 2.0 * s + mouth_ratio * 6.5 * s
                m_w = 4.0 * s + mouth_ratio * 8.0 * s
                mouth_rect = QRectF(-m_w / 2.0, 2.5 * s - m_h / 2.0, m_w, m_h)
                p.setBrush(QColor("#7A1515"))
                p.setPen(QPen(QColor("#FF453A"), max(1, int(1.0 * s))))
                p.drawRoundedRect(mouth_rect, 3 * s, 3 * s)

                # Suction of file particle
                f_dist = (1.0 - (t / 0.6)) * 20.0 * s
                f_scale = max(0.2, (1.0 - (t / 0.6) * 0.8))
                p.save()
                p.translate(0, -f_dist)
                p.scale(f_scale, f_scale)
                p.setBrush(QColor("#38BDF8"))
                p.setPen(QPen(QColor("#FFFFFF"), 1))
                p.drawRoundedRect(QRectF(-5 * s, -4 * s, 10 * s, 8 * s), 2 * s, 2 * s)
                p.restore()

            elif t < 2.2:
                # Stage 2: Continuous chomping, squinting, blushing & crumbs
                eye_squint = 1.0 - mouth_ratio * 0.5
                p.setPen(QPen(QColor("#5CE07A"), max(1, int(2.4 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(QRectF(-14 * s, -7.5 * s, 8 * s, 6 * s * eye_squint), 20 * 16, 140 * 16)
                p.drawArc(QRectF(6 * s, -7.5 * s, 8 * s, 6 * s * eye_squint), 20 * 16, 140 * 16)

                m_h = max(1.0 * s, mouth_ratio * 8.5 * s)
                m_w = (14.0 - mouth_ratio * 3.0) * s
                mouth_y = 2.5 * s
                mouth_rect = QRectF(-m_w / 2.0, mouth_y - m_h / 2.0, m_w, m_h)

                if mouth_ratio > 0.25:
                    p.setBrush(QColor("#7A1515"))
                    p.setPen(QPen(QColor("#FF453A"), max(1, int(1.0 * s))))
                    p.drawRoundedRect(mouth_rect, 3.5 * s, 3.5 * s)
                    p.setBrush(QColor("#FF7597"))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawEllipse(QRectF(-3.5 * s, mouth_y + 1 * s, 7 * s, 3.5 * s))
                    p.setBrush(QColor("#FFFFFF"))
                    p.drawRoundedRect(QRectF(-2 * s, mouth_y - m_h / 2.0, 4 * s, 2.0 * s), 0.8 * s, 0.8 * s)
                else:
                    p.setPen(QPen(QColor("#5CE07A"), max(1, int(2.0 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    ch_shift = math.sin(t * 20) * 1.5 * s
                    p.drawLine(int(-5.5 * s), int(mouth_y + ch_shift), int(5.5 * s), int(mouth_y - ch_shift))

                cheek_alpha = int(190 * (1.0 - mouth_ratio * 0.7))
                p.setBrush(QColor(255, 80, 150, cheek_alpha))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(-15.5 * s, 1.0 * s, 4.5 * s, 3.5 * s))
                p.drawEllipse(QRectF(11.0 * s, 1.0 * s, 4.5 * s, 3.5 * s))

                spark_phase = (t * 6.0) % 1.0
                p.setBrush(QColor(255, 214, 10, int(255 * (1.0 - spark_phase))))
                p.drawEllipse(QPointF(12 * s + spark_phase * 4 * s, -4 * s - spark_phase * 6 * s), 1.5 * s, 1.5 * s)
                p.drawEllipse(QPointF(-12 * s - spark_phase * 3 * s, -3 * s - spark_phase * 5 * s), 1.2 * s, 1.2 * s)

            else:
                # Stage 3: Heart eyes, blissful tongue lick smile
                draw_vector_heart(p, -10 * s, -3 * s, 4.5 * s, QColor("#FF4081"))
                draw_vector_heart(p, 10 * s, -3 * s, 4.5 * s, QColor("#FF4081"))

                p.setPen(QPen(QColor("#FF4081"), max(1, int(2.0 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawArc(QRectF(-6 * s, 1.5 * s, 12 * s, 6 * s), 190 * 16, 160 * 16)

                p.setBrush(QColor(255, 80, 150, 160))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(-15.5 * s, 1.0 * s, 4.5 * s, 3.5 * s))
                p.drawEllipse(QRectF(11.0 * s, 1.0 * s, 4.5 * s, 3.5 * s))

        elif self.mode == "hungry":
            # Anticipation wide eyes looking up & open mouth
            p.setBrush(QColor("#5CE07A"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-13 * s, -7 * s, 7.5 * s, 8.5 * s))
            p.drawEllipse(QRectF(5.5 * s, -7 * s, 7.5 * s, 8.5 * s))
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QRectF(-11 * s, -6 * s, 3.0 * s, 3.0 * s))
            p.drawEllipse(QRectF(7.5 * s, -6 * s, 3.0 * s, 3.0 * s))

            mouth_rect = QRectF(-6 * s, 0 * s, 12 * s, 7.5 * s)
            p.setBrush(QColor("#7A1515"))
            p.setPen(QPen(QColor("#FF453A"), max(1, int(1.0 * s))))
            p.drawRoundedRect(mouth_rect, 3.5 * s, 3.5 * s)

        elif self.mode in ["heart", "love"]:
            draw_vector_heart(p, -10 * s, -3 * s, 4.5 * s, QColor("#FF4081"))
            draw_vector_heart(p, 10 * s, -3 * s, 4.5 * s, QColor("#FF4081"))

        elif self.mode == "happy":
            p.setPen(QPen(QColor("#5CE07A"), max(1, int(2.4 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(-14 * s, -7.5 * s, 8 * s, 6 * s), 20 * 16, 140 * 16)
            p.drawArc(QRectF(6 * s, -7.5 * s, 8 * s, 6 * s), 20 * 16, 140 * 16)
            p.setBrush(QColor(255, 80, 150, 160))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-15.5 * s, 1.0 * s, 4.5 * s, 3.5 * s))
            p.drawEllipse(QRectF(11.0 * s, 1.0 * s, 4.5 * s, 3.5 * s))

        elif self.mode == "dizzy":
            p.setPen(QPen(QColor("#5CE07A"), max(1, int(1.8 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for center_x in [-10 * s, 10 * s]:
                p.drawArc(QRectF(center_x - 4 * s, -5 * s, 8 * s, 8 * s), int(self.anim_tick * 10 * 16), 260 * 16)
                p.drawArc(QRectF(center_x - 2 * s, -3 * s, 4 * s, 4 * s), int(-self.anim_tick * 10 * 16), 260 * 16)

        elif self.mode == "shocked":
            p.setPen(QPen(QColor("#FF453A"), max(1, int(2.0 * s))))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(-13 * s, -6 * s, 7 * s, 7 * s))
            p.drawEllipse(QRectF(6 * s, -6 * s, 7 * s, 7 * s))

        elif self.mode == "cool":
            p.setBrush(QColor("#0A84FF"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(-15 * s, -6 * s, 13 * s, 8 * s), 2 * s, 2 * s)
            p.drawRoundedRect(QRectF(2 * s, -6 * s, 13 * s, 8 * s), 2 * s, 2 * s)
            p.setPen(QPen(QColor("#0A84FF"), max(1, int(2 * s))))
            p.drawLine(int(-2 * s), int(-2 * s), int(2 * s), int(-2 * s))

        elif self.blink_state:
            # Natural blink line
            p.setPen(QPen(QColor("#5CE07A"), max(1, int(2.2 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(-13 * s), int(-2 * s), int(-5 * s), int(-2 * s))
            p.drawLine(int(5 * s), int(-2 * s), int(13 * s), int(-2 * s))

        else:
            # Iconic TwoCode glowing emerald oval eyes
            p.setBrush(QColor("#5CE07A"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(-13.5 * s, -6 * s, 8 * s, 10 * s), 3.5 * s, 3.5 * s)
            p.drawRoundedRect(QRectF(5.5 * s, -6 * s, 8 * s, 10 * s), 3.5 * s, 3.5 * s)
            # Specular sparkle
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QRectF(-11.5 * s, -4.5 * s, 2.5 * s, 2.5 * s))
            p.drawEllipse(QRectF(7.5 * s, -4.5 * s, 2.5 * s, 2.5 * s))

        p.restore()


class BluetoothDropdownWidget(QFrame):
    """Dynamic Bluetooth Accessory Pop-up (Baseus Encok WM01 · Connected 79%)."""
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.device_name = "Baseus Encok WM01"
        self.battery = 79
        self.setFixedSize(280, 52)
        self.setStyleSheet("""
            BluetoothDropdownWidget {
                background: #111216;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 20px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        self.icon_badge = QLabel("ᛒ")
        self.icon_badge.setFixedSize(34, 34)
        self.icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_badge.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #007AFF, stop:1 #0051C7);
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 700;
                border-radius: 17px;
            }
        """)
        layout.addWidget(self.icon_badge)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.name_label = QLabel(self.device_name)
        self.name_label.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        info_layout.addWidget(self.name_label)

        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(4)
        dot = QLabel("●")
        dot.setStyleSheet("color: #30D158; font-size: 8px;")
        sub_layout.addWidget(dot)

        self.status_label = QLabel("Подключено")
        self.status_label.setStyleSheet("color: #8E8E93; font-size: 10px; font-weight: 500;")
        sub_layout.addWidget(self.status_label)
        sub_layout.addStretch()
        info_layout.addLayout(sub_layout)

        layout.addLayout(info_layout)
        layout.addStretch()

        self.battery_gauge = QLabel()
        self.battery_gauge.setFixedSize(34, 34)
        self.battery_gauge.paintEvent = self.paint_battery
        layout.addWidget(self.battery_gauge)

        self.auto_timer = QTimer(self)
        self.auto_timer.setSingleShot(True)
        self.auto_timer.timeout.connect(self.closed.emit)

    def show_device(self, name="Baseus Encok WM01", battery=79):
        self.device_name = name
        self.battery = battery
        self.name_label.setText(name)
        self.battery_gauge.update()
        play_sound("chime")
        self.auto_timer.stop()
        self.auto_timer.start(3800)

    def paint_battery(self, event):
        p = QPainter(self.battery_gauge)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.battery_gauge.width()
        h = self.battery_gauge.height()
        rect = QRectF(3, 3, w - 6, h - 6)

        pen_bg = QPen(QColor(255, 255, 255, 30), 3.0)
        p.setPen(pen_bg)
        p.drawArc(rect, 0, 360 * 16)

        pen_fg = QPen(QColor("#30D158"), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen_fg)
        span_angle = int((self.battery / 100.0) * 360.0 * 16)
        p.drawArc(rect, 90 * 16, -span_angle)

        p.setPen(QColor("#FFFFFF"))
        font = p.font()
        font.setPointSize(8)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, f"{self.battery}%")


class FileCardWidget(QFrame):
    """File card with staggered fall bounce animation."""
    delete_requested = pyqtSignal(str)

    def __init__(self, file_path, animate=True, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.is_dir = os.path.isdir(file_path)
        self.file_name = os.path.basename(file_path) or file_path
        self.size_bytes = 0
        if not self.is_dir and os.path.exists(file_path):
            try:
                self.size_bytes = os.path.getsize(file_path)
            except Exception:
                self.size_bytes = 0

        self.setFixedHeight(44)
        self.setStyleSheet("""
            FileCardWidget {
                background: #18191E;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            FileCardWidget:hover {
                background: #20222A;
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(10)

        badge_text, badge_color = self.get_badge_info()
        badge = QLabel(badge_text)
        badge.setFixedSize(42, 24)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            QLabel {{
                background: {badge_color};
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 800;
                border-radius: 5px;
            }}
        """)
        layout.addWidget(badge)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        display_name = self.file_name
        if len(display_name) > 30:
            display_name = display_name[:27] + "..."

        name_label = QLabel(display_name)
        name_label.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        name_label.setToolTip(self.file_path)
        info_layout.addWidget(name_label)

        size_text = "Папка" if self.is_dir else format_file_size(self.size_bytes)
        size_label = QLabel(size_text)
        size_label.setStyleSheet("color: #8E8E93; font-size: 9px;")
        info_layout.addWidget(size_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        open_btn = QPushButton("Открыть")
        open_btn.setFixedSize(54, 22)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet("""
            QPushButton {
                background: #2A2C35;
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 600;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #38BDF8;
                color: #000000;
            }
        """)
        open_btn.clicked.connect(self.open_file)
        layout.addWidget(open_btn)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(22, 22)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8E8E93;
                font-size: 11px;
                font-weight: 700;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background: rgba(255, 69, 58, 0.2);
                color: #FF453A;
            }
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.file_path))
        layout.addWidget(del_btn)

    def open_file(self):
        try:
            if os.path.exists(self.file_path):
                os.startfile(self.file_path)
            else:
                play_sound("alert")
        except Exception:
            play_sound("alert")

    def get_badge_info(self):
        if self.is_dir:
            return "DIR", "#30D158"
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".rs", ".cpp", ".c", ".json"]:
            return "CODE", "#00C2FF"
        elif ext in [".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".csv"]:
            return "DOC", "#FF5A5F"
        elif ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"]:
            return "IMG", "#AF52DE"
        elif ext in [".zip", ".rar", ".7z", ".tar", ".gz"]:
            return "ARCH", "#FF9F0A"
        elif ext in [".mp3", ".wav", ".flac", ".ogg", ".mp4", ".mkv", ".mov"]:
            return "MEDIA", "#FF375F"
        else:
            return "FILE", "#6C757D"


class FileShelfWidget(QWidget):
    """File shelf with Drag & Drop target, mini animated Robo mascot, and staggered drop animation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.file_list = []
        self.cards = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        tb_layout = QHBoxLayout()
        tb_layout.setSpacing(8)

        self.title_lbl = QLabel("Полка файлов (0)")
        self.title_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        tb_layout.addWidget(self.title_lbl)

        tb_layout.addStretch()

        add_btn = QPushButton("+ Добавить")
        add_btn.setFixedSize(70, 22)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #252730;
                color: #38BDF8;
                font-size: 9px;
                font-weight: 700;
                border-radius: 6px;
                border: 1px solid rgba(56, 189, 248, 0.3);
            }
            QPushButton:hover {
                background: #38BDF8;
                color: #000000;
            }
        """)
        add_btn.clicked.connect(self.browse_file)
        tb_layout.addWidget(add_btn)

        clear_btn = QPushButton("Очистить")
        clear_btn.setFixedSize(62, 22)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #252730;
                color: #8E8E93;
                font-size: 9px;
                font-weight: 600;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                color: #FF453A;
            }
        """)
        clear_btn.clicked.connect(self.clear_all)
        tb_layout.addWidget(clear_btn)

        main_layout.addLayout(tb_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 2px;
            }
        """)

        self.card_container = QWidget()
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(6)
        self.card_layout.addStretch()

        self.scroll.setWidget(self.card_container)
        main_layout.addWidget(self.scroll)

        # Interactive Drop Zone with Animated Mascot
        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("dropZone")
        self.drop_zone.setStyleSheet("""
            QFrame#dropZone {
                background: rgba(255, 255, 255, 0.04);
                border: 1px dashed rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 4px 8px;
            }
        """)
        dz_layout = QHBoxLayout(self.drop_zone)
        dz_layout.setContentsMargins(8, 4, 8, 4)
        dz_layout.setSpacing(10)

        self.drop_robo = LiveAnimatedRobo(size=34)
        dz_layout.addWidget(self.drop_robo)

        dz_text_layout = QVBoxLayout()
        dz_text_layout.setSpacing(1)
        self.drop_title = QLabel("Положите файл роботу — он его скушает на полку!")
        self.drop_title.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 700;")
        self.drop_sub = QLabel("Перетащите файлы сюда или в капельку острова")
        self.drop_sub.setStyleSheet("color: #8E8E93; font-size: 9.5px;")
        dz_text_layout.addWidget(self.drop_title)
        dz_text_layout.addWidget(self.drop_sub)
        dz_layout.addLayout(dz_text_layout)
        dz_layout.addStretch()

        main_layout.addWidget(self.drop_zone)

        self.load_shelf_data()

    def set_hungry(self, hungry=True):
        if hungry:
            self.drop_robo.set_mode("hungry")
            self.drop_zone.setStyleSheet("""
                QFrame#dropZone {
                    background: rgba(56, 189, 248, 0.12);
                    border: 1.5px dashed #38BDF8;
                    border-radius: 12px;
                    padding: 4px 8px;
                }
            """)
            self.drop_title.setText("Ам! Отпустите файл — Robo готов его съесть!")
            self.drop_title.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 700;")
        else:
            if self.drop_robo.mode == "hungry":
                self.drop_robo.set_mode("idle")
            self._reset_drop_zone()

    def trigger_eat_animation(self, filename):
        self.drop_robo.set_mode("eating", duration_ms=2800)
        self.drop_zone.setStyleSheet("""
            QFrame#dropZone {
                background: rgba(48, 209, 88, 0.12);
                border: 1.5px solid #30D158;
                border-radius: 12px;
                padding: 4px 8px;
            }
        """)
        self.drop_title.setText(f"😋 Ням-ням! Скушал {filename}!")
        self.drop_title.setStyleSheet("color: #30D158; font-size: 11px; font-weight: 700;")
        self.drop_sub.setText("Файл сохранён и добавлен на вашу полочку!")
        QTimer.singleShot(2800, self._reset_drop_zone)

    def _reset_drop_zone(self):
        if self.drop_robo.mode in ["eating", "hungry"]:
            return
        self.drop_title.setText("Положите файл роботу — он его скушает на полку!")
        self.drop_title.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 700;")
        self.drop_sub.setText("Перетащите файлы сюда или в капельку острова")
        self.drop_zone.setStyleSheet("""
            QFrame#dropZone {
                background: rgba(255, 255, 255, 0.04);
                border: 1px dashed rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 4px 8px;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
            self.set_hungry(True)

    def dragLeaveEvent(self, event):
        self.set_hungry(False)

    def dropEvent(self, event):
        paths = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local_p = url.toLocalFile()
                if local_p and os.path.exists(local_p):
                    paths.append(local_p)
        self.dragLeaveEvent(None)
        if paths:
            fname = os.path.basename(paths[0])
            if len(paths) > 1:
                fname += f" (+{len(paths)-1})"
            play_sound("eat")
            self.trigger_eat_animation(fname)
            self.add_files(paths, animate=True)
            island = self.window()
            if hasattr(island, 'pill_robo'):
                island.pill_robo.set_mode("eating", duration_ms=2800)
            if hasattr(island, 'robo_tab') and hasattr(island.robo_tab, 'robo'):
                island.robo_tab.robo.set_mode("eating", duration_ms=2800)
                island.robo_tab.speech_bubble.setText(f"😋 Ням! Скушал {fname}! Файл сохранён на полку!")
            event.acceptProposedAction()

    def browse_file(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Выберите файл для полки")
        if fpath:
            fname = os.path.basename(fpath)
            play_sound("eat")
            self.trigger_eat_animation(fname)
            self.add_files([fpath], animate=True)
            island = self.window()
            if hasattr(island, 'pill_robo'):
                island.pill_robo.set_mode("eating", duration_ms=2800)
            if hasattr(island, 'robo_tab') and hasattr(island.robo_tab, 'robo'):
                island.robo_tab.robo.set_mode("eating", duration_ms=2800)
                island.robo_tab.speech_bubble.setText(f"😋 Ням! Скушал {fname}! Файл сохранён на полку!")

    def add_files(self, paths, animate=True):
        delay = 0
        for p in paths:
            if p not in self.file_list:
                self.file_list.append(p)
                if animate:
                    QTimer.singleShot(delay, lambda path=p: self._create_card(path, animate=True))
                    delay += 60
                else:
                    self._create_card(p, animate=False)
        self.save_shelf_data()
        self.update_header()

    def _create_card(self, path, animate=True):
        if path in self.cards:
            return
        card = FileCardWidget(path, animate=animate)
        card.delete_requested.connect(self.remove_file)
        self.cards[path] = card
        self.card_layout.insertWidget(self.card_layout.count() - 1, card)

    def remove_file(self, path):
        if path in self.file_list:
            self.file_list.remove(path)
        if path in self.cards:
            w = self.cards.pop(path)
            self.card_layout.removeWidget(w)
            w.deleteLater()
        self.save_shelf_data()
        self.update_header()

    def clear_all(self):
        self.file_list.clear()
        for path, w in list(self.cards.items()):
            self.card_layout.removeWidget(w)
            w.deleteLater()
        self.cards.clear()
        self.save_shelf_data()
        self.update_header()

    def update_header(self):
        self.title_lbl.setText(f"Полка файлов ({len(self.file_list)})")

    def load_shelf_data(self):
        if os.path.exists(SHELF_DATA_PATH):
            try:
                with open(SHELF_DATA_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        p = item.get("path")
                        if p and os.path.exists(p) and p not in self.file_list:
                            self.file_list.append(p)
                            self._create_card(p, animate=False)
                self.update_header()
            except Exception:
                pass

    def save_shelf_data(self):
        data = []
        for p in self.file_list:
            data.append({
                "path": p,
                "name": os.path.basename(p),
                "time": time.time()
            })
        try:
            with open(SHELF_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


class RealMusicPlayerWidget(QWidget):
    """Music player streaming REAL Windows playback via GSMTC / WinRT & window titles."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_playing = False
        self.current_sec = 0.0
        self.total_sec = 0.0
        self.disc_angle = 0.0

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(8)

        # 1. Top Track Info & Turntable Disc
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        self.disc = QLabel()
        self.disc.setFixedSize(54, 54)
        self.disc.paintEvent = self.paint_disc
        top_layout.addWidget(self.disc)

        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(2)
        meta_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = QLabel("Загрузка плеера...")
        self.title_lbl.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 800;")
        meta_layout.addWidget(self.title_lbl)

        self.artist_lbl = QLabel("Ожидание медиапотока Windows...")
        self.artist_lbl.setStyleSheet("color: #30D158; font-size: 11px; font-weight: 600;")
        meta_layout.addWidget(self.artist_lbl)

        top_layout.addLayout(meta_layout)
        top_layout.addStretch()

        self.eq = EqualizerBars()
        top_layout.addWidget(self.eq)

        main_layout.addLayout(top_layout)

        # 2. Progress Slider & Real Timestamps
        prog_layout = QHBoxLayout()
        prog_layout.setSpacing(6)

        self.curr_time_lbl = QLabel("00:00")
        self.curr_time_lbl.setStyleSheet("color: #8E8E93; font-size: 10px; font-weight: 600;")
        prog_layout.addWidget(self.curr_time_lbl)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #30D158;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 10px;
                height: 10px;
                margin: -3px 0;
                background: #FFFFFF;
                border-radius: 5px;
            }
        """)
        prog_layout.addWidget(self.slider)

        self.total_time_lbl = QLabel("00:00")
        self.total_time_lbl.setStyleSheet("color: #8E8E93; font-size: 10px; font-weight: 600;")
        prog_layout.addWidget(self.total_time_lbl)

        main_layout.addLayout(prog_layout)

        # 3. Playback Control Buttons
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(16)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        prev_btn = QPushButton("⏮")
        prev_btn.setFixedSize(32, 28)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setStyleSheet("color: #FFFFFF; font-size: 15px; background: transparent; border: none;")
        prev_btn.clicked.connect(self.prev_track)
        ctrl_layout.addWidget(prev_btn)

        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(40, 32)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #000000;
                font-size: 15px;
                font-weight: 800;
                border-radius: 16px;
                border: none;
            }
            QPushButton:hover {
                background: #30D158;
            }
        """)
        self.play_btn.clicked.connect(self.toggle_play)
        ctrl_layout.addWidget(self.play_btn)

        next_btn = QPushButton("⏭")
        next_btn.setFixedSize(32, 28)
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.setStyleSheet("color: #FFFFFF; font-size: 15px; background: transparent; border: none;")
        next_btn.clicked.connect(self.next_track)
        ctrl_layout.addWidget(next_btn)

        main_layout.addLayout(ctrl_layout)

        # Spin timer
        self.spin_timer = QTimer(self)
        self.spin_timer.timeout.connect(self.advance_spin)
        self.spin_timer.start(50)

    def paint_disc(self, event):
        p = QPainter(self.disc)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.disc.width()
        h = self.disc.height()

        p.save()
        p.translate(w / 2.0, h / 2.0)
        p.rotate(self.disc_angle)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(22, 22, 26))
        p.drawEllipse(QRectF(-25, -25, 50, 50))

        p.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(-20, -20, 40, 40))
        p.drawEllipse(QRectF(-14, -14, 28, 28))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#30D158"))
        p.drawEllipse(QRectF(-8, -8, 16, 16))

        p.setBrush(QColor("#000000"))
        p.drawEllipse(QRectF(-2.5, -2.5, 5, 5))

        p.restore()

    def advance_spin(self):
        if self.is_playing:
            self.disc_angle = (self.disc_angle + 3.0) % 360.0
            self.disc.update()

    def update_real_media(self, state):
        self.is_playing = state.is_playing
        self.play_btn.setText("⏸" if state.is_playing else "▶")
        self.eq.set_active(state.is_playing)

        disp_title = state.title if len(state.title) <= 28 else state.title[:25] + "..."
        disp_artist = state.artist if len(state.artist) <= 32 else state.artist[:29] + "..."
        self.title_lbl.setText(disp_title)
        self.artist_lbl.setText(disp_artist)

        self.current_sec = state.position_sec
        self.total_sec = state.duration_sec

        cur_m = int(self.current_sec // 60)
        cur_s = int(self.current_sec % 60)
        self.curr_time_lbl.setText(f"{cur_m:02d}:{cur_s:02d}")

        if self.total_sec > 0:
            tot_m = int(self.total_sec // 60)
            tot_s = int(self.total_sec % 60)
            self.total_time_lbl.setText(f"{tot_m:02d}:{tot_s:02d}")
            pct = int((self.current_sec / float(self.total_sec)) * 100)
            self.slider.setValue(pct)
        else:
            self.total_time_lbl.setText("--:--")
            self.slider.setValue(0)

    def toggle_play(self):
        send_vk(VK_MEDIA_PLAY_PAUSE)

    def next_track(self):
        send_vk(VK_MEDIA_NEXT_TRACK)
        play_sound("click")

    def prev_track(self):
        send_vk(VK_MEDIA_PREV_TRACK)
        play_sound("click")


# ==============================================================================
# AMBIENT ROBOT AI COMPANION (TAB 2)
# ==============================================================================
class AmbientRoboTabWidget(QWidget):
    """Ambient TwoCode Robot Companion with Silero Voice, Wake Word & Live Game Commentary."""
    decision_submitted = pyqtSignal(str)
    pet_toggled = pyqtSignal()

    def __init__(self, parent=None, commentary_engine=None):
        super().__init__(parent)
        self.commentary_engine = commentary_engine

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mascot
        self.robo = LiveAnimatedRobo(size=64)
        layout.addWidget(self.robo, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status & Speech Bubble
        self.status_lbl = QLabel("Робот TwoCode: Готов к работе")
        self.status_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        layout.addWidget(self.status_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        self.speech_bubble = QLabel("«Привет! Я твой живой компаньон на рабочем столе!»")
        self.speech_bubble.setWordWrap(True)
        self.speech_bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speech_bubble.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 6px 12px;
                color: #D1D1D6;
                font-size: 10.5px;
            }
        """)
        layout.addWidget(self.speech_bubble)

        # Action Buttons Row (Mic, Streamer, Voice Test)
        btns_row = QHBoxLayout()
        btns_row.setSpacing(6)

        # Mic Toggle Button
        self.mic_btn = QPushButton("🎙️ Микрофон: Выкл")
        self.mic_btn.setFixedSize(125, 26)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background: #1C1C1E;
                color: #8E8E93;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                font-size: 10px;
                font-weight: 700;
            }
        """)
        self.mic_btn.clicked.connect(self.toggle_microphone)
        btns_row.addWidget(self.mic_btn)

        # Streamer Commentary Button
        self.game_btn = QPushButton("🎮 Стример: Выкл")
        self.game_btn.setFixedSize(125, 26)
        self.game_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.game_btn.setStyleSheet("""
            QPushButton {
                background: #1C1C1E;
                color: #8E8E93;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                font-size: 10px;
                font-weight: 700;
            }
        """)
        self.game_btn.clicked.connect(self.toggle_commentary)
        btns_row.addWidget(self.game_btn)

        # Voice Test Button
        self.speak_btn = QPushButton("🗣️ Озвучка")
        self.speak_btn.setFixedSize(85, 26)
        self.speak_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.speak_btn.setStyleSheet("""
            QPushButton {
                background: #1C1C1E;
                color: #0A84FF;
                border: 1px solid rgba(10, 132, 255, 0.35);
                border-radius: 8px;
                font-size: 10px;
                font-weight: 700;
            }
        """)
        self.speak_btn.clicked.connect(self.test_speech)
        btns_row.addWidget(self.speak_btn)

        layout.addLayout(btns_row)

        # Desktop Mascot Walking & Pet Button
        pet_row = QHBoxLayout()
        self.pet_btn = QPushButton("🐾 Спрыгнуть на рабочий стол")
        self.pet_btn.setFixedHeight(28)
        self.pet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pet_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E293B, stop:1 #0F172A);
                color: #38BDF8;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 8px;
                font-size: 10px;
                font-weight: 700;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: #38BDF8;
                color: #000000;
            }
        """)
        self.pet_btn.clicked.connect(self.pet_toggled.emit)
        pet_row.addWidget(self.pet_btn)
        layout.addLayout(pet_row)

        # DeepSeek AI Chat & Task Execution Row
        chat_box = QHBoxLayout()
        chat_box.setSpacing(6)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("💬 Спроси DeepSeek или дай задачу...")
        self.chat_input.setFixedHeight(28)
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background: #14151B;
                color: #FFFFFF;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 7px;
                padding: 4px 10px;
                font-size: 10px;
            }
            QLineEdit:focus {
                border: 1px solid #38BDF8;
                background: #1A1D24;
            }
        """)
        self.chat_input.returnPressed.connect(self.on_chat_submitted)
        chat_box.addWidget(self.chat_input)

        self.chat_btn = QPushButton("▶")
        self.chat_btn.setFixedSize(28, 28)
        self.chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chat_btn.setStyleSheet("""
            QPushButton {
                background: #38BDF8;
                color: #000000;
                border-radius: 7px;
                font-weight: 800;
                font-size: 11px;
                border: none;
            }
            QPushButton:hover {
                background: #7DD3FC;
            }
        """)
        self.chat_btn.clicked.connect(self.on_chat_submitted)
        chat_box.addWidget(self.chat_btn)

        layout.addLayout(chat_box)

        # Coucou-style Agent Approval Banner
        self.ask_banner = QFrame()
        self.ask_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255, 159, 10, 0.18), stop:1 rgba(255, 69, 58, 0.15));
                border: 1px solid rgba(255, 159, 10, 0.45);
                border-radius: 10px;
            }
        """)
        ask_layout = QVBoxLayout(self.ask_banner)
        ask_layout.setContentsMargins(10, 6, 10, 6)
        ask_layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        self.ask_dot = QLabel("●")
        self.ask_dot.setStyleSheet("color: #FF9F0A; font-size: 11px;")
        header_row.addWidget(self.ask_dot)

        self.ask_agent_lbl = QLabel("coucou: Claude Code / Antigravity запрашивает команду")
        self.ask_agent_lbl.setStyleSheet("color: #FF9F0A; font-size: 10px; font-weight: 700;")
        header_row.addWidget(self.ask_agent_lbl, stretch=1)
        ask_layout.addLayout(header_row)

        self.ask_cmd_box = QLabel("git push origin main")
        self.ask_cmd_box.setStyleSheet("""
            background: rgba(0, 0, 0, 0.55);
            color: #38BDF8;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 10px;
            font-weight: 600;
            padding: 3px 6px;
            border-radius: 5px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        """)
        self.ask_cmd_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        ask_layout.addWidget(self.ask_cmd_box)

        btns_row2 = QHBoxLayout()
        btns_row2.setSpacing(6)
        btns_row2.addStretch()

        deny_btn = QPushButton("Deny [N]")
        deny_btn.setFixedSize(76, 22)
        deny_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        deny_btn.setStyleSheet("""
            QPushButton {
                background: #282623;
                color: #FF453A;
                font-size: 9px;
                font-weight: 700;
                border-radius: 6px;
                border: 1px solid rgba(255, 69, 58, 0.3);
            }
            QPushButton:hover {
                background: rgba(255, 69, 58, 0.2);
            }
        """)
        deny_btn.clicked.connect(lambda: self.decision_submitted.emit("deny"))
        btns_row2.addWidget(deny_btn)

        always_btn = QPushButton("Always allow")
        always_btn.setFixedSize(86, 22)
        always_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        always_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #D1D5DB;
                font-size: 9px;
                font-weight: 600;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
            }
        """)
        always_btn.clicked.connect(lambda: self.decision_submitted.emit("always"))
        btns_row2.addWidget(always_btn)

        allow_btn = QPushButton("Allow [Y]")
        allow_btn.setFixedSize(76, 22)
        allow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        allow_btn.setStyleSheet("""
            QPushButton {
                background: #30D158;
                color: #000000;
                font-size: 9px;
                font-weight: 800;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #28cd41;
            }
        """)
        allow_btn.clicked.connect(lambda: self.decision_submitted.emit("allow"))
        btns_row2.addWidget(allow_btn)

        ask_layout.addLayout(btns_row2)

        self.ask_banner.setVisible(False)
        layout.addWidget(self.ask_banner)

        layout.addStretch()

        # Connect External Signals
        global_signals.set_emotion.connect(self.set_emotion)
        if HAS_VOICE_ENGINE:
            voice_bridge.wake_word_detected.connect(self.on_wake_word)
            voice_bridge.voice_phrase_recognized.connect(self.on_voice_phrase)
            voice_bridge.speaking_state_changed.connect(self.on_speaking_state)

        if self.commentary_engine:
            self.commentary_engine.commentary_ready.connect(self.on_game_commentary)

    def set_ask_data(self, agent, command):
        self.ask_agent_lbl.setText(f"coucou: {agent} запрашивает команду")
        self.ask_cmd_box.setText(command)
        self.speech_bubble.setVisible(False)
        self.ask_banner.setVisible(True)
        self.robo.set_mode("surprised", duration_ms=10000)

    def hide_ask_data(self):
        self.ask_banner.setVisible(False)
        self.speech_bubble.setVisible(True)

    def set_emotion(self, emotion):
        self.robo.set_mode(emotion, duration_ms=4000)

    def update_pet_btn_state(self, is_active: bool):
        if is_active:
            self.pet_btn.setText("🏠 Вернуть маскота в остров")
            self.pet_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #064E3B, stop:1 #022C22);
                    color: #5CE07A;
                    border: 1px solid rgba(92, 224, 122, 0.5);
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 4px 10px;
                }
                QPushButton:hover {
                    background: #5CE07A;
                    color: #000000;
                }
            """)
        else:
            self.pet_btn.setText("🐾 Спрыгнуть на рабочий стол")
            self.pet_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E293B, stop:1 #0F172A);
                    color: #38BDF8;
                    border: 1px solid rgba(56, 189, 248, 0.4);
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 4px 10px;
                }
                QPushButton:hover {
                    background: #38BDF8;
                    color: #000000;
                }
            """)

    def toggle_microphone(self):
        if not HAS_VOICE_ENGINE:
            return
        is_on = VoiceInputEngine.get().toggle()
        if is_on:
            self.mic_btn.setText("🎙️ Микрофон: ВКЛ")
            self.mic_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(48, 209, 88, 0.2);
                    color: #30D158;
                    border: 1px solid #30D158;
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 700;
                }
            """)
            self.speech_bubble.setText("«Слушаю вас! Скажите 'Байя', 'Привет' или 'Остров'»")
        else:
            self.mic_btn.setText("🎙️ Микрофон: Выкл")
            self.mic_btn.setStyleSheet("""
                QPushButton {
                    background: #1C1C1E;
                    color: #8E8E93;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 700;
                }
            """)

    def toggle_commentary(self):
        if not self.commentary_engine:
            return
        is_on = self.commentary_engine.toggle_auto()
        if is_on:
            self.game_btn.setText("🎮 Стример: ВКЛ")
            self.game_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(191, 90, 242, 0.2);
                    color: #BF5AF2;
                    border: 1px solid #BF5AF2;
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 700;
                }
            """)
            self.commentary_engine.trigger_commentary(forced=True)
        else:
            self.game_btn.setText("🎮 Стример: Выкл")
            self.game_btn.setStyleSheet("""
                QPushButton {
                    background: #1C1C1E;
                    color: #8E8E93;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 700;
                }
            """)

    def on_chat_submitted(self):
        query = self.chat_input.text().strip()
        if not query:
            return
        self.chat_input.clear()
        self.process_ai_query(query)

    def process_ai_query(self, query: str):
        self.status_lbl.setText("🧠 DeepSeek думает...")
        self.robo.set_mode("thinking")
        self.speech_bubble.setText(f"«Думаю: {query}...»")

        def _worker():
            try:
                answer = DeepSeekBrain.get().ask(query)
            except Exception as e:
                answer = f"Ошибка DeepSeek: {e}"

            QTimer.singleShot(0, lambda: self._apply_ai_response(answer))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_ai_response(self, answer: str):
        self.status_lbl.setText("Робот TwoCode: Ответил")
        self.robo.set_mode("happy", duration_ms=4500)
        self.speech_bubble.setText(f"«{answer}»")
        if HAS_VOICE_ENGINE:
            VoiceEngine.get().speak(answer)

    def test_speech(self):
        phrase = "Привет! Я Бая, живой голос твоего маскота в красном худи! Работаю на полной мощности с DeepSeek."
        self.speech_bubble.setText(f"«{phrase}»")
        self.robo.set_mode("happy", duration_ms=4000)
        if HAS_VOICE_ENGINE:
            VoiceEngine.get().speak(phrase)

    def on_wake_word(self, text):
        self.speech_bubble.setText(f"«Услышала вас: {text}»")
        self.robo.set_mode("star", duration_ms=3500)
        if HAS_VOICE_ENGINE:
            VoiceEngine.get().speak("Слушаю вас! Чем могу помочь?")

    def on_voice_phrase(self, text):
        self.process_ai_query(text)

    def on_speaking_state(self, is_speaking):
        if is_speaking:
            self.robo.set_mode("happy")
        else:
            if self.robo.mode == "happy":
                self.robo.set_mode("idle")

    def on_game_commentary(self, text, emotion):
        self.speech_bubble.setText(f"«{text}»")
        self.robo.set_mode(emotion, duration_ms=4500)
        if HAS_VOICE_ENGINE:
            VoiceEngine.get().speak(text)

    def set_music_mode(self, is_playing, track_info=""):
        if is_playing:
            self.robo.set_mode("music")
            self.status_lbl.setText("Слушает музыку ♫")
            if track_info:
                self.speech_bubble.setText(f"♪ {track_info}")
        else:
            if self.robo.mode == "music":
                self.robo.set_mode("idle")
                self.status_lbl.setText("Робот TwoCode: В ожидании")
                self.speech_bubble.setText("«Ассистент автоматически реагирует на задачи и музыку»")


# ==============================================================================
# VAYLI TOOLS DASHBOARD (TAB 3)
# ==============================================================================
class ToolsDashboardWidget(QWidget):
    """System stats, Quick Notes, Clipboard History and Snipping tool."""
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(6)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)

        self.cpu_lbl = QLabel("CPU: --%")
        self.cpu_lbl.setStyleSheet("background: #18191E; color: #38BDF8; font-size: 10px; font-weight: 700; border-radius: 6px; padding: 3px 8px;")
        stats_layout.addWidget(self.cpu_lbl)

        self.ram_lbl = QLabel("RAM: --%")
        self.ram_lbl.setStyleSheet("background: #18191E; color: #A78BFA; font-size: 10px; font-weight: 700; border-radius: 6px; padding: 3px 8px;")
        stats_layout.addWidget(self.ram_lbl)

        self.uptime_lbl = QLabel("Uptime: 00:00")
        self.uptime_lbl.setStyleSheet("background: #18191E; color: #34D399; font-size: 10px; font-weight: 700; border-radius: 6px; padding: 3px 8px;")
        stats_layout.addWidget(self.uptime_lbl)

        stats_layout.addStretch()

        snip_btn = QPushButton("✂ Скриншот")
        snip_btn.setFixedSize(80, 24)
        snip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        snip_btn.setStyleSheet("""
            QPushButton {
                background: #2A2C35;
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 700;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #38BDF8;
                color: #000000;
            }
        """)
        snip_btn.clicked.connect(trigger_screenclip)
        stats_layout.addWidget(snip_btn)

        main_layout.addLayout(stats_layout)

        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(8)

        note_box = QVBoxLayout()
        note_box.setSpacing(2)
        note_title = QLabel("Быстрые заметки (автосохранение):")
        note_title.setStyleSheet("color: #8E8E93; font-size: 9px; font-weight: 600;")
        note_box.addWidget(note_title)

        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("Напишите заметку...")
        self.note_edit.setStyleSheet("""
            QTextEdit {
                background: #141519;
                color: #FFFFFF;
                font-size: 10px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 4px;
            }
        """)
        self.note_edit.textChanged.connect(self.save_notes)
        note_box.addWidget(self.note_edit)
        mid_layout.addLayout(note_box, stretch=1)

        clip_box = QVBoxLayout()
        clip_box.setSpacing(4)
        clip_title = QLabel("Буфер обмена:")
        clip_title.setStyleSheet("color: #8E8E93; font-size: 9px; font-weight: 600;")
        clip_box.addWidget(clip_title)

        self.last_clip_btn = QPushButton("История Win+V")
        self.last_clip_btn.setFixedHeight(26)
        self.last_clip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.last_clip_btn.setStyleSheet("""
            QPushButton {
                background: #18191E;
                color: #38BDF8;
                font-size: 10px;
                font-weight: 700;
                border-radius: 6px;
                border: 1px solid rgba(56, 189, 248, 0.2);
            }
            QPushButton:hover {
                background: #38BDF8;
                color: #000000;
            }
        """)
        self.last_clip_btn.clicked.connect(open_win_v_clipboard)
        clip_box.addWidget(self.last_clip_btn)

        self.clip_preview = QLabel("Скопированный текст появится здесь...")
        self.clip_preview.setWordWrap(True)
        self.clip_preview.setFixedHeight(50)
        self.clip_preview.setStyleSheet("""
            QLabel {
                background: #141519;
                color: #94A3B8;
                font-size: 9px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 4px;
            }
        """)
        clip_box.addWidget(self.clip_preview)
        mid_layout.addLayout(clip_box, stretch=1)

        main_layout.addLayout(mid_layout)

        self.load_notes()
        app_clip = QApplication.clipboard()
        app_clip.dataChanged.connect(self.on_clipboard_updated)

        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1500)
        self.start_time = time.time()

    def update_stats(self):
        if psutil:
            try:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                self.cpu_lbl.setText(f"CPU: {cpu:.0f}%")
                self.ram_lbl.setText(f"RAM: {ram:.0f}%")
            except Exception:
                pass

        up_sec = int(time.time() - self.start_time)
        m = up_sec // 60
        s = up_sec % 60
        self.uptime_lbl.setText(f"Uptime: {m:02d}:{s:02d}")

    def on_clipboard_updated(self):
        try:
            text = QApplication.clipboard().text()
            if text:
                preview = text.strip().replace("\n", " ")
                if len(preview) > 60:
                    preview = preview[:57] + "..."
                self.clip_preview.setText(f"Скопировано: {preview}")
        except Exception:
            pass

    def load_notes(self):
        if os.path.exists(NOTES_PATH):
            try:
                with open(NOTES_PATH, "r", encoding="utf-8") as f:
                    self.note_edit.setPlainText(f.read())
            except Exception:
                pass

    def save_notes(self):
        try:
            with open(NOTES_PATH, "w", encoding="utf-8") as f:
                f.write(self.note_edit.toPlainText())
        except Exception:
            pass


# ==============================================================================
# SETTINGS & BOTTOM DOCK (TAB 4)
# ==============================================================================
class SettingsTabWidget(QWidget):
    """Settings: Always on top, sound, reset position and GitHub connect."""
    sound_toggled = pyqtSignal(bool)
    topmost_toggled = pyqtSignal(bool)
    reset_pos_requested = pyqtSignal()
    bluetooth_test_requested = pyqtSignal()
    github_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Always on Top
        top_row = QHBoxLayout()
        top_lbl = QLabel("Поверх всех окон (Always on top):")
        top_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        top_row.addWidget(top_lbl)
        top_row.addStretch()

        self.top_btn = QPushButton("ВКЛ (Поверх)")
        self.top_btn.setFixedSize(110, 24)
        self.top_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.top_btn.setStyleSheet("background: #38BDF8; color: #000000; font-size: 9px; font-weight: 800; border-radius: 6px; border: none;")
        self.top_btn.clicked.connect(self.toggle_topmost)
        top_row.addWidget(self.top_btn)
        layout.addLayout(top_row)

        # Sound
        s_row = QHBoxLayout()
        s_lbl = QLabel("Звуковые эффекты острова:")
        s_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        s_row.addWidget(s_lbl)
        s_row.addStretch()

        self.sound_btn = QPushButton("Включены 🔔")
        self.sound_btn.setFixedSize(110, 24)
        self.sound_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sound_btn.setStyleSheet("background: #30D158; color: #000000; font-size: 9px; font-weight: 800; border-radius: 6px; border: none;")
        self.sound_btn.clicked.connect(self.toggle_sound)
        s_row.addWidget(self.sound_btn)
        layout.addLayout(s_row)

        # DeepSeek API Key
        ds_row = QHBoxLayout()
        ds_lbl = QLabel("DeepSeek API ключ (необязательно):")
        ds_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        ds_row.addWidget(ds_lbl)
        ds_row.addStretch()

        self.ds_key_input = QLineEdit()
        self.ds_key_input.setPlaceholderText("sk-...")
        self.ds_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.ds_key_input.setFixedSize(160, 24)
        self.ds_key_input.setStyleSheet("background: #18191E; color: #FFFFFF; font-size: 9px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.2); padding: 2px 6px;")
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    c = json.load(f)
                    if c.get("deepseek_api_key"):
                        self.ds_key_input.setText(c["deepseek_api_key"])
            except Exception:
                pass
        self.ds_key_input.textChanged.connect(self.on_deepseek_key_changed)
        ds_row.addWidget(self.ds_key_input)
        layout.addLayout(ds_row)

        # GitHub Repo
        gh_row = QHBoxLayout()
        gh_lbl = QLabel("GitHub репозиторий проекта:")
        gh_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        gh_row.addWidget(gh_lbl)
        gh_row.addStretch()

        gh_btn = QPushButton("ghant0911-afk/twocode-dynamic-island")
        gh_btn.setFixedSize(190, 24)
        gh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gh_btn.setStyleSheet("background: #252730; color: #FFFFFF; font-size: 9px; font-weight: 700; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.2);")
        gh_btn.clicked.connect(lambda: os.startfile("https://github.com/ghant0911-afk/twocode-dynamic-island"))
        gh_row.addWidget(gh_btn)
        layout.addLayout(gh_row)

        # Reset Pos
        r_row = QHBoxLayout()
        r_lbl = QLabel("Сбросить положение на верхний центр:")
        r_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        r_row.addWidget(r_lbl)
        r_row.addStretch()

        reset_btn = QPushButton("Сбросить к рамке (y=0)")
        reset_btn.setFixedSize(160, 24)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet("background: #252730; color: #38BDF8; font-size: 9px; font-weight: 700; border-radius: 6px; border: none;")
        reset_btn.clicked.connect(self.reset_pos_requested.emit)
        r_row.addWidget(reset_btn)
        layout.addLayout(r_row)

        layout.addStretch()

    def on_deepseek_key_changed(self, text):
        try:
            DeepSeekBrain.get().save_api_key(text)
        except Exception:
            pass

    def toggle_topmost(self):
        is_on = "ВКЛ" in self.top_btn.text()
        new_state = not is_on
        self.top_btn.setText("ВКЛ (Поверх)" if new_state else "ВЫКЛ (Сзади)")
        self.top_btn.setStyleSheet(f"background: {'#38BDF8' if new_state else '#252730'}; color: {'#000000' if new_state else '#8E8E93'}; font-size: 9px; font-weight: 800; border-radius: 6px; border: none;")
        self.topmost_toggled.emit(new_state)

    def toggle_sound(self):
        is_on = "Включены" in self.sound_btn.text()
        new_state = not is_on
        self.sound_btn.setText("Включены 🔔" if new_state else "Выключены 🔇")
        self.sound_btn.setStyleSheet(f"background: {'#30D158' if new_state else '#252730'}; color: {'#000000' if new_state else '#8E8E93'}; font-size: 9px; font-weight: 800; border-radius: 6px; border: none;")
        self.sound_toggled.emit(new_state)


class BottomDock(QFrame):
    """Sleek iOS frosted glass pill dock for 5 clean tabs."""
    tab_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setStyleSheet("""
            BottomDock {
                background: #15161B;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 17px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        tabs_data = [
            ("🎵 Музыка", 0),
            ("📂 Полка", 1),
            ("🤖 Робот", 2),
            ("⚡ Утилиты", 3),
            ("⚙️ Опции", 4),
        ]

        self.buttons = []
        for text, idx in tabs_data:
            btn = QPushButton(text)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self.select_tab(i))
            layout.addWidget(btn)
            self.buttons.append(btn)

        self.select_tab(0)

    def select_tab(self, index):
        for i, btn in enumerate(self.buttons):
            if i == index:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #FFFFFF;
                        color: #000000;
                        font-size: 10px;
                        font-weight: 800;
                        border-radius: 13px;
                        padding: 0 12px;
                        border: none;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #8E8E93;
                        font-size: 10px;
                        font-weight: 600;
                        border-radius: 13px;
                        padding: 0 10px;
                        border: none;
                    }
                    QPushButton:hover {
                        color: #FFFFFF;
                        background: rgba(255, 255, 255, 0.05);
                    }
                """)
        self.tab_selected.emit(index)

# ==============================================================================
# MAIN WINDOW: TWOCODE DYNAMIC ISLAND PRO (ROBO IN DROPLET & REAL MEDIA)
# ==============================================================================
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
        self.setAcceptDrops(True)

        self.COLLAPSED_W = 176
        self.COLLAPSED_H = 32
        self.EXPANDED_W = 460
        self.EXPANDED_H = 270
        self.BT_W = 280
        self.BT_H = 54

        self.is_expanded = False
        self.is_pinned = False
        self.is_bt_showing = False
        self.always_on_top = True
        self.sound_enabled = True

        self.custom_x = None
        self.custom_y = None
        self.dragging = False
        self.drag_position = QPoint()

        self.load_config()

        # Start Screen Perception & Game Commentary Engine
        if HAS_GAME_COMMENTARY:
            self.commentary_engine = GameCommentaryEngine(self)
        else:
            self.commentary_engine = None

        self.init_ui()

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(160)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.collapse_timer = QTimer(self)
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.setInterval(700)
        self.collapse_timer.timeout.connect(self.auto_collapse)

        # Watchdog for reliable hover exit detection
        self.hover_watchdog = QTimer(self)
        self.hover_watchdog.setInterval(250)
        self.hover_watchdog.timeout.connect(self._check_hover_watchdog)

        self.setup_tray_icon()

        # Connect signals
        global_signals.agent_status.connect(self.on_agent_status)
        global_signals.agent_ask.connect(self.on_agent_ask)
        global_signals.agent_done.connect(self.on_agent_done)
        global_signals.bluetooth_popup.connect(self.show_bluetooth_popup)
        global_signals.shelf_add.connect(self.on_remote_shelf_add)
        global_signals.media_state_changed.connect(self.on_media_state_changed)
        global_signals.expand_requested.connect(self.expand)
        global_signals.collapse_requested.connect(self.collapse)
        global_signals.snapshot_requested.connect(self.on_snapshot_requested)
        global_signals.select_tab.connect(self.on_select_tab)
        global_signals.pet_toggle_requested.connect(self.toggle_desktop_pet)
        global_signals.pet_spawn_requested.connect(self.spawn_desktop_pet)
        global_signals.pet_dismiss_requested.connect(self.dismiss_desktop_pet)

        # Start Real Windows Media Watcher
        if HAS_MEDIA_ENGINE:
            self.media_watcher = WindowsMediaWatcher(self.on_media_update_threadsafe)
        else:
            self.media_watcher = None

        self.set_collapsed_geometry(animate=False)
        if getattr(self, "desktop_pet_enabled", True):
            QTimer.singleShot(600, self.spawn_desktop_pet)

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setObjectName("IslandContainer")
        self.update_style()

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(6, 4, 6, 4)
        container_layout.setSpacing(4)

        self.main_stack = AutoSizingStackedWidget()

        # ----------------------------------------------------------------------
        # PAGE 0: COLLAPSED COMPACT DROPLET (FULL ANIMATED ROBOT!)
        # ----------------------------------------------------------------------
        self.pill_widget = QWidget()
        self.pill_widget.setFixedHeight(self.COLLAPSED_H - 8)
        self.pill_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pill_widget.mousePressEvent = lambda e: self.expand()
        pill_layout = QHBoxLayout(self.pill_widget)
        pill_layout.setContentsMargins(6, 0, 8, 0)
        pill_layout.setSpacing(6)

        # 1. Full Animated TwoCode Robot in the droplet (antenna, orb, eyes, dance)
        self.pill_robo = LiveAnimatedRobo(size=22)
        self.pill_robo.clicked.connect(self.expand)
        pill_layout.addWidget(self.pill_robo)

        # 2. Status / Real Song Label
        self.pill_title = QLabel("TwoCode")
        self.pill_title.setStyleSheet("color: #FFFFFF; font-size: 10px; font-weight: 700;")
        pill_layout.addWidget(self.pill_title)

        pill_layout.addStretch()

        # 3. Compact Equalizer
        self.pill_eq = EqualizerBars()
        pill_layout.addWidget(self.pill_eq)

        self.main_stack.addWidget(self.pill_widget)

        # ----------------------------------------------------------------------
        # PAGE 1: EXPANDED ISLAND
        # ----------------------------------------------------------------------
        self.expanded_widget = QWidget()
        exp_layout = QVBoxLayout(self.expanded_widget)
        exp_layout.setContentsMargins(4, 4, 4, 4)
        exp_layout.setSpacing(6)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 0, 4, 0)
        top_bar.setSpacing(6)

        self.brand_lbl = QLabel("TwoCode Dynamic Island Pro")
        self.brand_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 800;")
        top_bar.addWidget(self.brand_lbl)

        top_bar.addStretch()

        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(22, 22)
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.setStyleSheet("color: #8E8E93; background: transparent; border: none; font-size: 11px;")
        self.pin_btn.clicked.connect(self.toggle_pin)
        top_bar.addWidget(self.pin_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("color: #8E8E93; background: transparent; border: none; font-size: 11px; font-weight: 700;")
        close_btn.clicked.connect(self.collapse)
        top_bar.addWidget(close_btn)

        exp_layout.addLayout(top_bar)

        self.tab_stack = QStackedWidget()

        # Tab 0: Real Windows Music Player
        self.music_player = RealMusicPlayerWidget()
        self.tab_stack.addWidget(self.music_player)

        # Tab 1: File Shelf
        self.file_shelf = FileShelfWidget()
        self.tab_stack.addWidget(self.file_shelf)

        # Tab 2: Ambient Robot Companion with Voice & Streamer Commentary
        self.robo_tab = AmbientRoboTabWidget(commentary_engine=self.commentary_engine)
        self.robo_tab.decision_submitted.connect(self.on_decision_submitted)
        self.robo_tab.pet_toggled.connect(self.toggle_desktop_pet)
        self.tab_stack.addWidget(self.robo_tab)

        # Tab 3: Tools Dashboard
        self.tools_widget = ToolsDashboardWidget()
        self.tab_stack.addWidget(self.tools_widget)

        # Tab 4: Settings
        self.settings_widget = SettingsTabWidget()
        self.settings_widget.topmost_toggled.connect(self.set_always_on_top)
        self.settings_widget.sound_toggled.connect(self.on_sound_toggled)
        self.settings_widget.reset_pos_requested.connect(self.reset_to_center)
        self.tab_stack.addWidget(self.settings_widget)

        exp_layout.addWidget(self.tab_stack, stretch=1)

        # Bottom Dock (5 tabs)
        self.dock = BottomDock()
        self.dock.tab_selected.connect(self.tab_stack.setCurrentIndex)
        exp_layout.addWidget(self.dock)

        self.main_stack.addWidget(self.expanded_widget)

        # ----------------------------------------------------------------------
        # PAGE 2: BLUETOOTH DROPDOWN
        # ----------------------------------------------------------------------
        self.bt_popup = BluetoothDropdownWidget()
        self.bt_popup.closed.connect(self.collapse)
        self.main_stack.addWidget(self.bt_popup)

        container_layout.addWidget(self.main_stack)
        outer_layout.addWidget(self.container)

    def on_media_update_threadsafe(self, state):
        global_signals.media_state_changed.emit(state)

    def on_media_state_changed(self, state):
        # Update expanded music player
        self.music_player.update_real_media(state)

        # Update pill and robot animations
        if state.is_active and state.is_playing:
            clean_t = state.title if len(state.title) <= 16 else state.title[:14] + ".."
            self.pill_title.setText(clean_t)
            self.pill_robo.set_mode("music")
            self.pill_eq.set_active(True)
            self.robo_tab.set_music_mode(True, f"{state.title} · {state.artist}")
            self.current_media_playing = True
            if getattr(self, "desktop_pet", None):
                self.desktop_pet.set_music(True)
        else:
            if self.pill_robo.mode == "music":
                self.pill_robo.set_mode("idle")
            self.pill_eq.set_active(False)
            self.robo_tab.set_music_mode(False)
            self.current_media_playing = False
            if getattr(self, "desktop_pet", None):
                self.desktop_pet.set_music(False)

    def minimumSizeHint(self):
        if not self.is_expanded:
            return QSize(self.COLLAPSED_W, self.COLLAPSED_H)
        return QSize(self.EXPANDED_W, self.EXPANDED_H)

    def sizeHint(self):
        if not self.is_expanded:
            return QSize(self.COLLAPSED_W, self.COLLAPSED_H)
        return QSize(self.EXPANDED_W, self.EXPANDED_H)

    def update_style(self):
        radius = "22px" if self.is_expanded else "16px"
        self.container.setStyleSheet(f"""
            QFrame#IslandContainer {{
                background-color: #0B0B0E;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: {radius};
            }}
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
            self.pill_robo.set_mode("hungry")
            if not self.is_expanded:
                self.expand()
                self.dock.select_tab(1)
            if hasattr(self, 'file_shelf'):
                self.file_shelf.set_hungry(True)

    def dragLeaveEvent(self, event):
        if self.pill_robo.mode == "hungry":
            self.pill_robo.set_mode("idle")
        if hasattr(self, 'file_shelf'):
            self.file_shelf.set_hungry(False)

    def dropEvent(self, event):
        paths = []
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                lp = u.toLocalFile()
                if lp and os.path.exists(lp):
                    paths.append(lp)
        if paths:
            fname = os.path.basename(paths[0])
            if len(paths) > 1:
                fname += f" (+{len(paths)-1})"
            play_sound("eat")
            self.pill_robo.set_mode("eating", duration_ms=2800)
            if hasattr(self, 'file_shelf'):
                self.file_shelf.trigger_eat_animation(fname)
                self.file_shelf.add_files(paths, animate=True)
            if hasattr(self, 'robo_tab') and hasattr(self.robo_tab, 'robo'):
                self.robo_tab.robo.set_mode("eating", duration_ms=2800)
                self.robo_tab.speech_bubble.setText(f"😋 Ням! Скушал {fname}! Файл сохранён на полку!")
            event.acceptProposedAction()

    def get_active_screen(self):
        cursor_pos = QCursor.pos()
        for s in QApplication.screens():
            if s.geometry().contains(cursor_pos):
                return s
        primary = QApplication.primaryScreen()
        return primary if primary else QApplication.screens()[0]

    def get_target_coords(self, target_w, target_h):
        if self.custom_x is not None and self.custom_y is not None:
            new_x = self.custom_x
            new_y = self.custom_y
            return new_x, new_y

        screen = self.get_active_screen()
        geom = screen.geometry()
        x = geom.left() + (geom.width() - target_w) // 2
        y = geom.top()
        return x, y

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.is_expanded:
                self.expand()
                event.accept()
                return
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
            top_threshold = 60 if geom.top() == 0 else (geom.top() + 40)
            if self.pos().y() <= top_threshold:
                self.custom_x = None
                self.custom_y = None
                self.save_config()
                tw = self.EXPANDED_W if self.is_expanded else self.COLLAPSED_W
                th = self.EXPANDED_H if self.is_expanded else self.COLLAPSED_H
                tx, ty = self.get_target_coords(tw, th)
                self.move(tx, ty)
            else:
                self.custom_x = self.pos().x()
                self.custom_y = self.pos().y()
                self.save_config()
            event.accept()

    def enterEvent(self, event):
        self.collapse_timer.stop()
        if not self.is_expanded and not self.is_bt_showing:
            self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_pinned and not self.is_bt_showing and not self.dragging:
            cursor_pos = QCursor.pos()
            if not self.geometry().contains(cursor_pos):
                self.collapse_timer.start(700)
            else:
                self.collapse_timer.stop()
        super().leaveEvent(event)

    def _check_hover_watchdog(self):
        if self.is_expanded and not self.is_pinned and not self.is_bt_showing and not self.dragging:
            cursor_pos = QCursor.pos()
            if not self.geometry().contains(cursor_pos):
                if not self.collapse_timer.isActive():
                    self.collapse_timer.start(650)
            else:
                if self.collapse_timer.isActive():
                    self.collapse_timer.stop()

    def auto_collapse(self):
        if not self.is_pinned and not self.is_bt_showing and not self.dragging:
            cursor_pos = QCursor.pos()
            if not self.geometry().contains(cursor_pos):
                self.collapse()
            else:
                self.collapse_timer.stop()

    def expand(self):
        self.is_expanded = True
        # Fluid hover: do NOT force is_pinned = True
        self.is_bt_showing = False
        self.collapse_timer.stop()
        if not self.is_pinned:
            self.hover_watchdog.start(250)
        self.setMinimumSize(self.EXPANDED_W, self.EXPANDED_H)
        self.setMaximumSize(self.EXPANDED_W, self.EXPANDED_H)
        self.main_stack.setCurrentWidget(self.expanded_widget)
        self.update_style()

        tx, ty = self.get_target_coords(self.EXPANDED_W, self.EXPANDED_H)
        target_rect = QRect(tx, ty, self.EXPANDED_W, self.EXPANDED_H)

        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        self.anim.start()
        self.show()
        self.update_topmost()

    def collapse(self):
        self.is_expanded = False
        self.is_pinned = False
        self.is_bt_showing = False
        self.collapse_timer.stop()
        self.hover_watchdog.stop()
        if hasattr(self, 'pin_btn'):
            self.pin_btn.setStyleSheet("color: #8E8E93; background: transparent; border: none; font-size: 11px;")
        self.main_stack.setCurrentWidget(self.pill_widget)
        self.setMinimumSize(self.COLLAPSED_W, self.COLLAPSED_H)
        self.setMaximumSize(self.COLLAPSED_W, self.COLLAPSED_H)
        self.update_style()

        tx, ty = self.get_target_coords(self.COLLAPSED_W, self.COLLAPSED_H)
        target_rect = QRect(tx, ty, self.COLLAPSED_W, self.COLLAPSED_H)

        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        self.anim.start()
        self.show()
        self.update_topmost()

    def set_collapsed_geometry(self, animate=False):
        self.is_expanded = False
        self.is_bt_showing = False
        self.main_stack.setCurrentWidget(self.pill_widget)
        self.setMinimumSize(self.COLLAPSED_W, self.COLLAPSED_H)
        self.setMaximumSize(self.COLLAPSED_W, self.COLLAPSED_H)
        self.update_style()

        tx, ty = self.get_target_coords(self.COLLAPSED_W, self.COLLAPSED_H)
        target_rect = QRect(tx, ty, self.COLLAPSED_W, self.COLLAPSED_H)

        if animate:
            self.anim.stop()
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(target_rect)
            self.anim.start()
        else:
            self.setGeometry(target_rect)

        self.show()
        self.update_topmost()

    def update_topmost(self):
        if getattr(self, "always_on_top", True):
            make_window_topmost(int(self.winId()))
        else:
            user32.SetWindowPos(int(self.winId()), -2, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0040)

    def set_always_on_top(self, enabled):
        self.always_on_top = enabled
        self.save_config()
        self.update_topmost()

    def show_bluetooth_popup(self, data):
        self.is_expanded = False
        self.is_bt_showing = True
        name = data.get("name", "Baseus Encok WM01")
        battery = data.get("battery", 79)
        self.bt_popup.show_device(name, battery)
        self.main_stack.setCurrentWidget(self.bt_popup)
        self.setMinimumSize(self.BT_W, self.BT_H)
        self.setMaximumSize(self.BT_W, self.BT_H)
        self.update_style()

        tx, ty = self.get_target_coords(self.BT_W, self.BT_H)
        target_rect = QRect(tx, ty, self.BT_W, self.BT_H)

        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        self.anim.start()
        self.show()
        self.update_topmost()

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.pin_btn.setStyleSheet(f"""
            QPushButton {{
                color: {"#38BDF8" if self.is_pinned else "#8E8E93"};
                background: transparent;
                border: none;
                font-size: 11px;
            }}
        """)
        if self.is_pinned:
            self.collapse_timer.stop()
            self.hover_watchdog.stop()
        else:
            cursor_pos = QCursor.pos()
            if not self.geometry().contains(cursor_pos):
                self.collapse_timer.start(650)
            else:
                self.hover_watchdog.start(250)

    def reset_to_center(self):
        self.custom_x = None
        self.custom_y = None
        self.save_config()
        tw = self.EXPANDED_W if self.is_expanded else self.COLLAPSED_W
        th = self.EXPANDED_H if self.is_expanded else self.COLLAPSED_H
        tx, ty = self.get_target_coords(tw, th)
        self.move(tx, ty)

    def on_sound_toggled(self, enabled):
        self.sound_enabled = enabled
        self.save_config()

    def on_remote_shelf_add(self, files):
        fname = os.path.basename(files[0]) if files else "файл"
        if len(files) > 1:
            fname += f" (+{len(files)-1})"
        play_sound("eat")
        self.pill_robo.set_mode("eating", duration_ms=2800)
        self.file_shelf.trigger_eat_animation(fname)
        self.file_shelf.add_files(files, animate=True)
        if hasattr(self, 'robo_tab') and hasattr(self.robo_tab, 'robo'):
            self.robo_tab.robo.set_mode("eating", duration_ms=2800)
            self.robo_tab.speech_bubble.setText(f"😋 Ням! Скушал {fname}! Файл сохранён на полку!")
        self.expand()
        self.dock.select_tab(1)

    def on_agent_status(self, data):
        action = data.get("action", "TwoCode")
        self.pill_title.setText(action[:14])

    def on_agent_ask(self, data):
        agent = data.get("agent", "Antigravity")
        cmd = data.get("command") or data.get("prompt") or data.get("question") or "npm run build"
        self.robo_tab.set_ask_data(agent, cmd)
        self.expand()
        self.dock.select_tab(2)
        self.pill_robo.set_mode("surprised", duration_ms=10000)
        play_sound("alert")

    def keyPressEvent(self, event):
        if self.robo_tab.ask_banner.isVisible():
            if event.key() == Qt.Key.Key_Y:
                self.on_decision_submitted("allow")
                event.accept()
                return
            elif event.key() == Qt.Key.Key_N:
                self.on_decision_submitted("deny")
                event.accept()
                return
        if event.key() == Qt.Key.Key_Escape:
            if self.is_expanded:
                self.is_pinned = False
                self.collapse()
                event.accept()
                return
        super().keyPressEvent(event)

    def on_agent_done(self, data):
        self.robo_tab.hide_ask_data()
        self.pill_robo.set_mode("heart", 3000)
        play_sound("chime")

    def on_decision_submitted(self, decision):
        self.robo_tab.hide_ask_data()
        global_signals.decision_made.emit(decision)
        play_sound("click")

    def on_snapshot_requested(self, path):
        if not path:
            path = os.path.join(os.path.dirname(__file__), "island_snapshot.png")
        pix = self.grab()
        pix.save(path, "PNG")
        print(f"Island snapshot saved to: {path}")

    def on_select_tab(self, idx):
        self.expand()
        self.dock.select_tab(idx)

    def spawn_desktop_pet(self):
        if not getattr(self, "desktop_pet", None):
            try:
                from desktop_pet import DesktopRoboPet
                self.desktop_pet = DesktopRoboPet()
                self.desktop_pet.dismiss_requested.connect(self.dismiss_desktop_pet)
                self.desktop_pet.jump_to_island_requested.connect(self.dismiss_desktop_pet)
            except Exception as e:
                print(f"[Island] Error creating DesktopRoboPet: {e}")
                return
        if self.desktop_pet:
            if getattr(self, "current_media_playing", False):
                self.desktop_pet.set_music(True)
            self.desktop_pet.show()
            self.desktop_pet_enabled = True
            self.save_config()
            if hasattr(self, "robo_tab"):
                self.robo_tab.update_pet_btn_state(True)

    def dismiss_desktop_pet(self):
        if getattr(self, "desktop_pet", None):
            self.desktop_pet.hide()
        self.desktop_pet_enabled = False
        self.save_config()
        if hasattr(self, "robo_tab"):
            self.robo_tab.update_pet_btn_state(False)

    def toggle_desktop_pet(self):
        if getattr(self, "desktop_pet_enabled", False) and getattr(self, "desktop_pet", None) and self.desktop_pet.isVisible():
            self.dismiss_desktop_pet()
        else:
            self.spawn_desktop_pet()

    def setup_tray_icon(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.create_tray_icon())
        self.tray.setToolTip("TwoCode Dynamic Island Pro")

        menu = QMenu()
        act_toggle = menu.addAction("Развернуть / Свернуть")
        act_toggle.triggered.connect(lambda: self.collapse() if self.is_expanded else self.expand())

        act_top = menu.addAction("📌 Поверх всех окон")
        act_top.setCheckable(True)
        act_top.setChecked(self.always_on_top)
        act_top.triggered.connect(self.set_always_on_top)

        act_pet = menu.addAction("🐾 Маскот на рабочем столе")
        act_pet.triggered.connect(self.toggle_desktop_pet)

        act_shelf = menu.addAction("📂 Полка файлов")
        act_shelf.triggered.connect(lambda: (self.expand(), self.dock.select_tab(1)))

        act_bt = menu.addAction("ᛒ Тест Bluetooth Pop-up")
        act_bt.triggered.connect(lambda: self.show_bluetooth_popup({"name": "Baseus Encok WM01", "battery": 79}))

        act_snip = menu.addAction("✂ Сделать скриншот")
        act_snip.triggered.connect(trigger_screenclip)

        menu.addSeparator()
        act_quit = menu.addAction("Выход")
        act_quit.triggered.connect(QApplication.instance().quit)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def create_tray_icon(self):
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#0B0B0E"))
        p.setPen(QPen(QColor("#38BDF8"), 2.0))
        p.drawRoundedRect(QRectF(2, 6, 28, 20), 10, 10)
        p.setBrush(QColor("#5CE07A"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(8, 12, 4, 4))
        p.drawEllipse(QRectF(20, 12, 4, 4))
        p.end()
        return QIcon(pix)

    def load_config(self):
        self.always_on_top = True
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.sound_enabled = cfg.get("sound_enabled", True)
                    self.always_on_top = cfg.get("always_on_top", True)
                    self.desktop_pet_enabled = cfg.get("desktop_pet_enabled", True)
                    self.custom_x = cfg.get("pos_x", None)
                    self.custom_y = cfg.get("pos_y", None)
            except Exception:
                pass

    def save_config(self):
        try:
            cfg = {
                "sound_enabled": self.sound_enabled,
                "always_on_top": self.always_on_top,
                "desktop_pet_enabled": getattr(self, 'desktop_pet_enabled', True),
                "pos_x": self.custom_x,
                "pos_y": self.custom_y
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass


def start_http_server():
    port = 28283
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                port = cfg.get("http_port", 28283)
    except Exception:
        pass

    for candidate in [port, 28283, 28284, 28285]:
        try:
            server = ReusableHTTPServer(("127.0.0.1", candidate), IslandAPIHandler)
            print(f"Unified Sandbox Island HTTP Daemon listening on port {candidate}")
            server.serve_forever()
            break
        except Exception:
            continue

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    island = TwoCodeIsland()
    island.show()
    # Pop open on start so the user can immediately interact with buttons & tabs
    QTimer.singleShot(400, island.expand)

    sys.exit(app.exec())
