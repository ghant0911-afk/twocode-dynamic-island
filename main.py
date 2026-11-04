"""
TwoCode Dynamic Island Pro - Nusa, Vayli and Tamagotchi Edition
Replicates all animations, living mascot, file shelf, karaoke lyrics, and health widgets 100%.
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
import winsound

try:
    import psutil
except ImportError:
    psutil = None

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QRectF, QPoint, QPointF, QSize,
    pyqtSignal, QObject, QTime
)
from PyQt6.QtGui import (
    QColor, QFont, QCursor, QPainter, QBrush, QPen, QIcon, QPixmap,
    QPainterPath, QLinearGradient, QRadialGradient, QFontMetrics
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QStackedWidget, QSystemTrayIcon, QMenu, QSlider,
    QLineEdit, QTextEdit, QScrollArea, QFileDialog
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(APP_DIR, "assets")
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
    try:
        if kind == "click":
            winsound.Beep(1200, 25)
        elif kind == "purr":
            winsound.Beep(980, 40)
            winsound.Beep(1320, 60)
        elif kind == "eat":
            winsound.Beep(650, 45)
            winsound.Beep(850, 50)
            winsound.Beep(1150, 70)
        elif kind == "water":
            winsound.Beep(1100, 40)
            winsound.Beep(1450, 60)
        elif kind == "bluetooth":
            winsound.Beep(880, 50)
            winsound.Beep(1320, 90)
        elif kind == "chime":
            winsound.Beep(784, 60)
            winsound.Beep(987, 60)
            winsound.Beep(1318, 110)
        elif kind == "alert":
            winsound.Beep(987, 80)
            winsound.Beep(784, 100)
    except Exception:
        pass

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
# LOCAL HTTP API ON PORT 28282 (ANTIGRAVITY & SYSTEM INTEGRATION)
# ==============================================================================
class BridgeSignals(QObject):
    agent_status = pyqtSignal(dict)
    agent_ask = pyqtSignal(dict)
    agent_done = pyqtSignal(dict)
    decision_made = pyqtSignal(str)
    bluetooth_popup = pyqtSignal(dict)
    shelf_add = pyqtSignal(list)
    pet_emote = pyqtSignal(str)
    water_drink = pyqtSignal(int)

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
            self._send_json(200, {"status": "ok", "app": "TwoCode Dynamic Island Pro", "version": "3.0.0"})
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

        if parsed.path == '/api/status':
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
        elif parsed.path == '/api/pet':
            emote = data.get("emote", "happy")
            global_signals.pet_emote.emit(emote)
            self._send_json(200, {"status": "ok", "emote": emote})
        elif parsed.path == '/api/water':
            amount = data.get("amount", 250)
            global_signals.water_drink.emit(amount)
            self._send_json(200, {"status": "ok", "drank": amount})
        else:
            self._send_json(404, {"error": "Not Found"})

# ==============================================================================
# COMPACT NOTCH LIVING WIDGETS (EYES, EQUALIZER, ACCESSORY DROPDOWN)
# ==============================================================================
class NotchEyes(QWidget):
    """Living compact eyes (• •) for the collapsed notch with pupil tracking and blinking."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 20)
        self.blink_tick = 0
        self.blink_interval = random.randint(60, 110)
        self.is_blinking = False
        self.blink_progress = 0.0  # 0.0 to 1.0
        self.happy = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(40)  # 25 FPS

    def set_happy(self, happy=True):
        self.happy = happy
        self.update()

    def update_animation(self):
        self.blink_tick += 1
        if not self.is_blinking:
            if self.blink_tick >= self.blink_interval:
                self.is_blinking = True
                self.blink_tick = 0
                self.blink_progress = 0.0
                self.blink_interval = random.randint(60, 120)
        else:
            self.blink_progress += 0.25
            if self.blink_progress >= 2.0:
                self.is_blinking = False
                self.blink_progress = 0.0

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Mouse tracking for pupils
        cursor = QCursor.pos()
        global_pos = self.mapToGlobal(QPoint(19, 10))
        dx = (cursor.x() - global_pos.x()) / 400.0
        dy = (cursor.y() - global_pos.y()) / 300.0
        dx = max(-2.0, min(2.0, dx * 2.0))
        dy = max(-1.5, min(1.5, dy * 1.5))

        # Blinking calculation
        open_ratio = 1.0
        if self.is_blinking:
            if self.blink_progress <= 1.0:
                open_ratio = 1.0 - self.blink_progress * 0.85
            else:
                open_ratio = 0.15 + (self.blink_progress - 1.0) * 0.85

        # Blushing cheeks
        p.setPen(Qt.PenStyle.NoPen)
        blush_color = QColor(255, 122, 144, 140 if self.happy else 80)
        p.setBrush(blush_color)
        p.drawEllipse(QRectF(1, 9, 5, 3))
        p.drawEllipse(QRectF(32, 9, 5, 3))

        # Eyes: left at x=11, right at x=23
        eye_w = 6.0
        eye_h = max(1.8, 11.0 * open_ratio)

        for eye_x in (11.0, 23.0):
            eye_y = 10.0 - (eye_h / 2.0)
            rect = QRectF(eye_x, eye_y, eye_w, eye_h)

            # Eye Sclera / Base
            p.setBrush(QColor(250, 250, 252))
            p.drawRoundedRect(rect, eye_w / 2.0, eye_h / 2.0)

            # Pupil (Black)
            pupil_w = 4.0
            pupil_h = max(1.5, 7.0 * open_ratio)
            px = eye_x + (eye_w - pupil_w) / 2.0 + dx
            py = 10.0 - (pupil_h / 2.0) + dy
            p.setBrush(QColor(18, 18, 22))
            p.drawEllipse(QRectF(px, py, pupil_w, pupil_h))

            # Glossy specular shine
            if open_ratio > 0.4:
                p.setBrush(QColor(255, 255, 255, 220))
                p.drawEllipse(QRectF(px + 0.8, py + 0.8, 1.6, 1.6))


class EqualizerBars(QWidget):
    """4 animated jumping equalizer bars next to track cover."""
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


class BluetoothDropdownWidget(QFrame):
    """Dynamic Bluetooth Accessory Pop-up (Reel 3: Baseus Encok WM01 · Connected 79%)."""
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

        # 1. Bluetooth Rune Icon Badge
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

        # 2. Device info
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

        # 3. Circular Battery Gauge
        self.battery_gauge = QLabel()
        self.battery_gauge.setFixedSize(34, 34)
        self.battery_gauge.paintEvent = self.paint_battery
        layout.addWidget(self.battery_gauge)

        # Auto-retract timer (3.8 seconds)
        self.auto_timer = QTimer(self)
        self.auto_timer.setSingleShot(True)
        self.auto_timer.timeout.connect(self.closed.emit)

    def show_device(self, name="Baseus Encok WM01", battery=79):
        self.device_name = name
        self.battery = battery
        self.name_label.setText(name)
        self.battery_gauge.update()
        play_sound("bluetooth")
        self.auto_timer.stop()
        self.auto_timer.start(3800)

    def paint_battery(self, event):
        p = QPainter(self.battery_gauge)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.battery_gauge.width()
        h = self.battery_gauge.height()
        rect = QRectF(3, 3, w - 6, h - 6)

        # Track background
        pen_bg = QPen(QColor(255, 255, 255, 30), 3.0)
        p.setPen(pen_bg)
        p.drawArc(rect, 0, 360 * 16)

        # Active progress arc
        pen_fg = QPen(QColor("#30D158"), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen_fg)
        span_angle = int((self.battery / 100.0) * 360.0 * 16)
        p.drawArc(rect, 90 * 16, -span_angle)

        # Percentage text
        p.setPen(QColor("#FFFFFF"))
        font = p.font()
        font.setPointSize(8)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, f"{self.battery}%")

# ==============================================================================
# LIVING MASCOT: NUSA & VAYLI TAMAGOTCHI & TWOCODE ROBO
# ==============================================================================
class NusaPet(QWidget):
    """The Living White Marshmallow Mascot & Tamagotchi from Reels 1, 2, 3."""
    clicked = pyqtSignal()

    def __init__(self, size=72, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.size_val = size
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.state = "idle"  # idle, happy, eating, music, sleeping, thinking
        self.tick = 0
        self.blink_tick = 0
        self.blink_interval = random.randint(70, 130)
        self.is_blinking = False
        self.blink_progress = 0.0

        # Eating animation state
        self.eating_progress = 0.0
        self.is_eating = False

        # Interactive bouncing & floating particles
        self.bounce_offset = 0.0
        self.particles = []  # dict of {x, y, vy, text, alpha, size}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_animation)
        self.timer.start(35)  # ~28 FPS

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.poke()
            self.clicked.emit()
            event.accept()

    def poke(self):
        play_sound("purr")
        self.bounce_offset = 6.0
        self.set_state("happy", duration_ms=2500)
        self.spawn_particle("❤️")

    def feed_file(self):
        play_sound("eat")
        self.is_eating = True
        self.eating_progress = 1.0
        self.set_state("eating", duration_ms=3000)
        for _ in range(3):
            self.spawn_particle("✨")
        self.spawn_particle("❤️")

    def set_state(self, state, duration_ms=0):
        self.state = state
        self.update()
        if duration_ms > 0:
            QTimer.singleShot(duration_ms, self.reset_to_idle)

    def reset_to_idle(self):
        if self.state in ["happy", "eating"]:
            self.state = "idle"
            self.update()

    def spawn_particle(self, text="❤️"):
        px = random.uniform(-10, 10)
        self.particles.append({
            "x": px,
            "y": -16.0,
            "vy": random.uniform(1.2, 2.0),
            "text": text,
            "alpha": 255.0,
            "size": random.uniform(9.0, 13.0)
        })

    def advance_animation(self):
        self.tick += 1

        # Bounce spring decay
        if self.bounce_offset > 0.1:
            self.bounce_offset *= 0.85
        else:
            self.bounce_offset = 0.0

        # Natural blink
        if not self.is_blinking:
            self.blink_tick += 1
            if self.blink_tick >= self.blink_interval:
                self.is_blinking = True
                self.blink_tick = 0
                self.blink_progress = 0.0
                self.blink_interval = random.randint(70, 140)
        else:
            self.blink_progress += 0.28
            if self.blink_progress >= 2.0:
                self.is_blinking = False
                self.blink_progress = 0.0

        # Eating decay
        if self.is_eating:
            self.eating_progress -= 0.03
            if self.eating_progress <= 0:
                self.is_eating = False

        # Random music note spawn
        if self.state == "music" and (self.tick % 32 == 0):
            self.spawn_particle("♪" if random.random() > 0.5 else "♫")

        # Sleep Zzz
        if self.state == "sleeping" and (self.tick % 45 == 0):
            self.spawn_particle("Zzz")

        # Update floating particles
        alive_particles = []
        for p in self.particles:
            p["y"] -= p["vy"]
            p["alpha"] -= 4.5
            if p["alpha"] > 0:
                alive_particles.append(p)
        self.particles = alive_particles

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        s = w / 72.0

        p.save()
        p.translate(w / 2.0, h / 2.0)

        # 1. Squash-and-stretch breathing & bounce physics
        breath_y = math.sin(self.tick * 0.12) * 0.04
        breath_x = -breath_y * 0.5
        scale_x = 1.0 + breath_x
        scale_y = 1.0 + breath_y

        if self.state == "eating":
            chew = math.sin(self.tick * 0.5) * 0.08
            scale_y += chew
            scale_x -= chew * 0.5

        p.scale(scale_x, scale_y)
        p.translate(0, -self.bounce_offset * s)

        # Music dance sway
        if self.state == "music":
            tilt = math.sin(self.tick * 0.22) * 8.0
            p.rotate(tilt)

        # 2. Draw Soft Rounded Ears
        ear_pen = Qt.PenStyle.NoPen
        p.setPen(ear_pen)

        # Left Ear
        p.setBrush(QColor(250, 250, 255))
        p.drawRoundedRect(QRectF(-20 * s, -30 * s, 13 * s, 15 * s), 6 * s, 6 * s)
        p.setBrush(QColor(255, 182, 193, 180))  # Inner ear blush
        p.drawRoundedRect(QRectF(-18 * s, -27 * s, 8 * s, 10 * s), 4 * s, 4 * s)

        # Right Ear
        p.setBrush(QColor(250, 250, 255))
        p.drawRoundedRect(QRectF(7 * s, -30 * s, 13 * s, 15 * s), 6 * s, 6 * s)
        p.setBrush(QColor(255, 182, 193, 180))
        p.drawRoundedRect(QRectF(10 * s, -27 * s, 8 * s, 10 * s), 4 * s, 4 * s)

        # 3. Marshmallow Head & Body Base
        body_gradient = QLinearGradient(0, -22 * s, 0, 24 * s)
        body_gradient.setColorAt(0.0, QColor(255, 255, 255))
        body_gradient.setColorAt(1.0, QColor(238, 240, 246))
        p.setBrush(body_gradient)
        p.setPen(QPen(QColor(0, 0, 0, 15), 1.0))
        p.drawRoundedRect(QRectF(-24 * s, -20 * s, 48 * s, 42 * s), 20 * s, 20 * s)

        # 4. Cheeks (Pink Blush Glow)
        blush_alpha = 180 if self.state in ["happy", "eating"] else 110
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 122, 144, blush_alpha))
        p.drawEllipse(QRectF(-21 * s, -2 * s, 8 * s, 5 * s))
        p.drawEllipse(QRectF(13 * s, -2 * s, 8 * s, 5 * s))

        # 5. Eyes & Blinking
        cursor = QCursor.pos()
        global_pos = self.mapToGlobal(QPoint(int(w / 2), int(h / 2)))
        dx = (cursor.x() - global_pos.x()) / 450.0
        dy = (cursor.y() - global_pos.y()) / 350.0
        dx = max(-2.5, min(2.5, dx * 2.5)) * s
        dy = max(-2.0, min(2.0, dy * 2.0)) * s

        open_ratio = 1.0
        if self.state == "sleeping":
            open_ratio = 0.05
        elif self.is_blinking:
            if self.blink_progress <= 1.0:
                open_ratio = 1.0 - self.blink_progress * 0.9
            else:
                open_ratio = 0.1 + (self.blink_progress - 1.0) * 0.9

        eye_w = 6.5 * s
        eye_h = max(1.8 * s, 9.5 * s * open_ratio)

        for eye_base_x in (-13.0 * s, 6.5 * s):
            eye_base_y = -8.0 * s - (eye_h / 2.0)
            rect = QRectF(eye_base_x, eye_base_y, eye_w, eye_h)

            p.setBrush(QColor(22, 22, 26))
            p.drawRoundedRect(rect, eye_w / 2.0, eye_h / 2.0)

            # Specular glossy shine
            if open_ratio > 0.4:
                p.setBrush(QColor(255, 255, 255, 230))
                p.drawEllipse(QRectF(eye_base_x + 1.2 * s + dx * 0.4, eye_base_y + 1.2 * s + dy * 0.4, 2.2 * s, 2.2 * s))

        # 6. Mouth & Eating Slot (Reel 1 & 2)
        if self.is_eating or self.state == "eating":
            # Wide open eating slot!
            mouth_rect = QRectF(-7 * s, 2 * s, 14 * s, 11 * s)
            p.setBrush(QColor(20, 20, 24))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(mouth_rect, 6 * s, 6 * s)

            # Little pink tongue
            p.setBrush(QColor(255, 130, 160))
            p.drawRoundedRect(QRectF(-4 * s, 8 * s, 8 * s, 4 * s), 2 * s, 2 * s)
        elif self.state in ["happy", "music"]:
            # Joyful open smile
            p.setPen(QPen(QColor(30, 30, 34), 2.0 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(QColor(255, 140, 170))
            path = QPainterPath()
            path.moveTo(-4 * s, 4 * s)
            path.arcTo(QRectF(-5 * s, 2 * s, 10 * s, 6 * s), 0, -180)
            p.drawPath(path)
        else:
            # Subtle cute smile ◡
            p.setPen(QPen(QColor(30, 30, 34), 1.8 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath()
            path.moveTo(-3.5 * s, 4 * s)
            path.quadTo(0, 6.5 * s, 3.5 * s, 4 * s)
            p.drawPath(path)

        # 7. Waving Arms / Paws \ (• •) /
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255))

        if self.state in ["happy", "eating", "music"]:
            # Waving paws raised up!
            paw_wave = math.sin(self.tick * 0.35) * 4.0 * s
            p.drawRoundedRect(QRectF(-26 * s, -12 * s + paw_wave, 7 * s, 12 * s), 3.5 * s, 3.5 * s)
            p.drawRoundedRect(QRectF(19 * s, -12 * s - paw_wave, 7 * s, 12 * s), 3.5 * s, 3.5 * s)
        else:
            # Paws resting gently
            p.drawRoundedRect(QRectF(-15 * s, 12 * s, 8 * s, 7 * s), 4 * s, 4 * s)
            p.drawRoundedRect(QRectF(7 * s, 12 * s, 8 * s, 7 * s), 4 * s, 4 * s)

        p.restore()

        # 8. Draw Floating Particles (Hearts, Notes, Zzz)
        for part in self.particles:
            p.save()
            p.translate(w / 2.0 + part["x"] * s, h / 2.0 + part["y"] * s)
            font = p.font()
            font.setPointSize(int(part["size"] * s))
            font.setBold(True)
            p.setFont(font)

            if "❤️" in part["text"]:
                p.setPen(QColor(255, 80, 110, int(part["alpha"])))
            elif "♪" in part["text"] or "♫" in part["text"]:
                p.setPen(QColor(48, 209, 88, int(part["alpha"])))
            else:
                p.setPen(QColor(160, 160, 175, int(part["alpha"])))

            p.drawText(QRectF(-14 * s, -14 * s, 28 * s, 28 * s), Qt.AlignmentFlag.AlignCenter, part["text"])
            p.restore()


class LiveAnimatedRobo(QWidget):
    """The TwoCode High-Tech Robot Companion with interactive scanning, gears, and dance."""
    clicked = pyqtSignal()

    def __init__(self, size=64, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.size_val = size
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.mode = "idle"  # idle, reading, thinking, coding, music, heart, done
        self.anim_tick = 0
        self.blink_state = False
        self.blink_counter = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(50)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            play_sound("click")
            self.set_mode("heart", duration_ms=2000)
            self.clicked.emit()
            event.accept()

    def set_mode(self, mode, duration_ms=0):
        self.mode = mode
        self.update()
        if duration_ms > 0:
            QTimer.singleShot(duration_ms, lambda: self.set_mode("idle"))

    def advance(self):
        self.anim_tick += 1
        self.blink_counter += 1
        if self.blink_counter > 75:
            self.blink_state = True
            if self.blink_counter > 79:
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

        # Dance tilt
        if self.mode == "music":
            tilt = math.sin(self.anim_tick * 0.25) * 6.0
            p.rotate(tilt)

        # Antenna
        p.setPen(QPen(QColor("#A8A49E"), max(1, int(2.5 * s))))
        p.drawLine(0, int(-16 * s), 0, int(-24 * s))

        # Antenna glowing tip
        orb_color = QColor("#5CE07A")
        if self.mode in ["thinking", "coding"]:
            orb_color = QColor(255, 140, 0, int(180 + 75 * math.sin(self.anim_tick * 0.4)))
        elif self.mode == "music":
            orb_color = QColor("#C8F08F")
        elif self.mode == "heart":
            orb_color = QColor("#FF69B4")

        p.setBrush(QBrush(orb_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(0, -25.0 * s), 3.5 * s, 3.5 * s)

        # Robo Head
        p.setPen(QPen(QColor("#45423E"), max(1, int(1.5 * s))))
        p.setBrush(QColor("#242220"))
        p.drawRoundedRect(QRectF(-22 * s, -16 * s, 44 * s, 34 * s), 10 * s, 10 * s)

        # Visor Screen
        p.setBrush(QColor("#11100F"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(-18 * s, -12 * s, 36 * s, 26 * s), 7 * s, 7 * s)

        # Visor Eyes / Emoticons
        if self.mode == "heart":
            p.setPen(QColor("#FF4081"))
            font = p.font()
            font.setPointSize(int(10 * s))
            font.setBold(True)
            p.setFont(font)
            p.drawText(QRectF(-18 * s, -12 * s, 36 * s, 26 * s), Qt.AlignmentFlag.AlignCenter, "♥  ♥")
        elif self.blink_state:
            p.setPen(QPen(QColor("#5CE07A"), int(2 * s)))
            p.drawLine(int(-12 * s), 0, int(-4 * s), 0)
            p.drawLine(int(4 * s), 0, int(12 * s), 0)
        else:
            p.setBrush(QColor("#5CE07A"))
            p.drawRoundedRect(QRectF(-13 * s, -5 * s, 8 * s, 10 * s), 3 * s, 3 * s)
            p.drawRoundedRect(QRectF(5 * s, -5 * s, 8 * s, 10 * s), 3 * s, 3 * s)

        p.restore()

# ==============================================================================
# FILE SHELF & STAGGERED CARD DROP PHYSICS (REEL 1 & REEL 3)
# ==============================================================================
class FileCardWidget(QFrame):
    """File card with staggered fall bounce animation (Reel 3: Kartu jatuh dari atas satu per satu)."""
    delete_requested = pyqtSignal(str)
    feed_requested = pyqtSignal(str)

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

        self.setFixedHeight(48)
        self.setStyleSheet("""
            FileCardWidget {
                background: #18191E;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
            FileCardWidget:hover {
                background: #20222A;
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        # 1. Badge by file extension
        badge_text, badge_color = self.get_badge_info()
        badge = QLabel(badge_text)
        badge.setFixedSize(44, 26)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            QLabel {{
                background: {badge_color};
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 800;
                border-radius: 6px;
            }}
        """)
        layout.addWidget(badge)

        # 2. File Name & Size
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        display_name = self.file_name
        if len(display_name) > 28:
            display_name = display_name[:25] + "..."

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

        # 3. Action Buttons
        # Open Button
        open_btn = QPushButton("Открыть")
        open_btn.setFixedSize(54, 24)
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

        # Feed to Pet Button (Reel 1: File-eating tamagotchi!)
        feed_btn = QPushButton("🍽️")
        feed_btn.setFixedSize(26, 24)
        feed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        feed_btn.setToolTip("Скормить файл питомцу!")
        feed_btn.setStyleSheet("""
            QPushButton {
                background: #2A2C35;
                color: #FFFFFF;
                font-size: 11px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #FF5A5F;
            }
        """)
        feed_btn.clicked.connect(lambda: self.feed_requested.emit(self.file_path))
        layout.addWidget(feed_btn)

        # Delete Button
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8E8E93;
                font-size: 11px;
                font-weight: 700;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: rgba(255, 69, 58, 0.2);
                color: #FF453A;
            }
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.file_path))
        layout.addWidget(del_btn)

        # Staggered fall animation
        if animate:
            self.anim = QPropertyAnimation(self, b"pos")
            self.anim.setDuration(320)
            self.anim.setEasingCurve(QEasingCurve.Type.OutBounce)

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
    """File shelf with Drag & Drop target and staggered drop animation."""
    feed_to_pet = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.file_list = []
        self.cards = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # 1. Header Toolbar
        tb_layout = QHBoxLayout()
        tb_layout.setSpacing(8)

        self.title_lbl = QLabel("Полка файлов (0)")
        self.title_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        tb_layout.addWidget(self.title_lbl)

        tb_layout.addStretch()

        # Add File Button
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

        # Clear All Button
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

        # 2. Scroll Area for Staggered Cards
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

        # 3. Drop Zone Visual Hint
        self.drop_hint = QLabel("Перетащите файлы сюда или на остров")
        self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_hint.setStyleSheet("""
            QLabel {
                color: #555866;
                font-size: 10px;
                border: 1px dashed rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px;
            }
        """)
        main_layout.addWidget(self.drop_hint)

        self.load_shelf_data()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
            self.drop_hint.setStyleSheet("""
                QLabel {
                    color: #38BDF8;
                    font-size: 10px;
                    border: 1px dashed #38BDF8;
                    border-radius: 8px;
                    padding: 4px;
                    background: rgba(56, 189, 248, 0.1);
                }
            """)

    def dragLeaveEvent(self, event):
        self.drop_hint.setStyleSheet("""
            QLabel {
                color: #555866;
                font-size: 10px;
                border: 1px dashed rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px;
            }
        """)

    def dropEvent(self, event):
        paths = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local_p = url.toLocalFile()
                if local_p and os.path.exists(local_p):
                    paths.append(local_p)
        self.dragLeaveEvent(None)
        if paths:
            self.add_files(paths, animate=True)
            play_sound("purr")
            event.acceptProposedAction()

    def browse_file(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Выберите файл для полки")
        if fpath:
            self.add_files([fpath], animate=True)

    def add_files(self, paths, animate=True):
        delay = 0
        for p in paths:
            if p not in self.file_list:
                self.file_list.append(p)
                if animate:
                    QTimer.singleShot(delay, lambda path=p: self._create_card(path, animate=True))
                    delay += 60  # Staggered card fall delay!
                else:
                    self._create_card(p, animate=False)
        self.save_shelf_data()
        self.update_header()

    def _create_card(self, path, animate=True):
        if path in self.cards:
            return
        card = FileCardWidget(path, animate=animate)
        card.delete_requested.connect(self.remove_file)
        card.feed_requested.connect(self.on_feed_card)
        self.cards[path] = card
        # Insert before stretch
        self.card_layout.insertWidget(self.card_layout.count() - 1, card)

    def on_feed_card(self, path):
        self.feed_to_pet.emit(path)

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
                    self.add_files(data, animate=False)
            except Exception:
                pass

    def save_shelf_data(self):
        try:
            with open(SHELF_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(self.file_list, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

# ==============================================================================
# NUSA MUSIC PLAYER & LIVE SYNCHRONIZED KARAOKE LYRICS (REEL 3)
# ==============================================================================
class KaraokeLyricsWidget(QWidget):
    """Live Synchronized Karaoke Lyrics with active line glow and auto-scrolling."""
    time_seek_requested = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(94)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)

        self.container = QWidget()
        self.lyrics_layout = QVBoxLayout(self.container)
        self.lyrics_layout.setContentsMargins(8, 20, 8, 20)
        self.lyrics_layout.setSpacing(8)
        self.lyrics_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # Built-in synced lyrics: (time_sec, lyric_text)
        self.lyrics_data = [
            (0.0, "♪ (Intro - Chill Island Vibe) ♪"),
            (4.0, "Floating above the desktop screen"),
            (8.5, "Soft marshmallow pet in between"),
            (13.0, "Eyes are tracking where you go"),
            (17.5, "Dancing to the rhythm slow"),
            (22.0, "TwoCode Island glowing bright"),
            (26.5, "Karaoke lyrics in the night"),
            (31.0, "Drop your files into the tray"),
            (35.5, "Sip some water, seize the day"),
            (40.0, "♪ (Gentle Melodic Outro) ♪"),
        ]

        self.labels = []
        self.current_index = -1
        self.build_labels()

    def build_labels(self):
        # Clear existing
        for lbl in self.labels:
            self.lyrics_layout.removeWidget(lbl)
            lbl.deleteLater()
        self.labels.clear()

        for idx, (t, text) in enumerate(self.lyrics_data):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.32); font-size: 11px; font-weight: 500;")
            lbl.mousePressEvent = lambda e, seek_t=t: self.time_seek_requested.emit(seek_t)
            self.lyrics_layout.addWidget(lbl)
            self.labels.append(lbl)

    def sync_time(self, current_sec):
        new_idx = -1
        for i, (t, text) in enumerate(self.lyrics_data):
            if current_sec >= t:
                new_idx = i
            else:
                break

        if new_idx != self.current_index:
            self.current_index = new_idx
            self.update_styles()

    def update_styles(self):
        for i, lbl in enumerate(self.labels):
            if i == self.current_index:
                # Active singing line: Glowing white, bold, larger font
                lbl.setStyleSheet("""
                    QLabel {
                        color: #FFFFFF;
                        font-size: 13px;
                        font-weight: 800;
                        background: rgba(255, 255, 255, 0.08);
                        border-radius: 6px;
                        padding: 2px 8px;
                    }
                """)
                # Auto-scroll to center active line
                self.scroll_to_label(lbl)
            elif i < self.current_index:
                # Past line
                lbl.setStyleSheet("color: rgba(255, 255, 255, 0.25); font-size: 11px; font-weight: 400;")
            else:
                # Upcoming line
                lbl.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 11px; font-weight: 500;")

    def scroll_to_label(self, lbl):
        sb = self.scroll.verticalScrollBar()
        lbl_y = lbl.y()
        target_val = max(0, lbl_y - (self.height() // 2) + 12)
        sb.setValue(target_val)


class NusaMusicPlayer(QWidget):
    """Music player with ambient glow, disc spin, time bar and live karaoke lyrics."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_playing = True
        self.current_sec = 0.0
        self.total_sec = 45.0
        self.disc_angle = 0.0

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(6)

        # 1. Top Track Info & Turntable Disc
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # Animated Turntable Disc
        self.disc = QLabel()
        self.disc.setFixedSize(48, 48)
        self.disc.paintEvent = self.paint_disc
        top_layout.addWidget(self.disc)

        # Track Meta
        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(1)
        meta_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = QLabel("Nusa Aesthetic Island")
        self.title_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        meta_layout.addWidget(self.title_lbl)

        self.artist_lbl = QLabel("TwoCode Lo-Fi • Spotify Activity")
        self.artist_lbl.setStyleSheet("color: #30D158; font-size: 10px; font-weight: 600;")
        meta_layout.addWidget(self.artist_lbl)

        top_layout.addLayout(meta_layout)
        top_layout.addStretch()

        # Equalizer in player
        self.eq = EqualizerBars()
        top_layout.addWidget(self.eq)

        main_layout.addLayout(top_layout)

        # 2. Live Synchronized Karaoke Lyrics
        self.karaoke = KaraokeLyricsWidget()
        self.karaoke.time_seek_requested.connect(self.seek_to)
        main_layout.addWidget(self.karaoke)

        # 3. Progress Slider & Timestamps
        prog_layout = QHBoxLayout()
        prog_layout.setSpacing(6)

        self.curr_time_lbl = QLabel("00:00")
        self.curr_time_lbl.setStyleSheet("color: #8E8E93; font-size: 9px; font-weight: 600;")
        prog_layout.addWidget(self.curr_time_lbl)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, int(self.total_sec))
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
        self.slider.sliderMoved.connect(self.on_slider_moved)
        prog_layout.addWidget(self.slider)

        self.rem_time_lbl = QLabel("-00:45")
        self.rem_time_lbl.setStyleSheet("color: #8E8E93; font-size: 9px; font-weight: 600;")
        prog_layout.addWidget(self.rem_time_lbl)

        main_layout.addLayout(prog_layout)

        # 4. Playback Control Buttons
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(14)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Prev Track
        prev_btn = QPushButton("⏮")
        prev_btn.setFixedSize(30, 24)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setStyleSheet("color: #FFFFFF; font-size: 14px; background: transparent; border: none;")
        prev_btn.clicked.connect(self.prev_track)
        ctrl_layout.addWidget(prev_btn)

        # Play / Pause
        self.play_btn = QPushButton("⏸")
        self.play_btn.setFixedSize(36, 28)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #000000;
                font-size: 14px;
                font-weight: 700;
                border-radius: 14px;
                border: none;
            }
            QPushButton:hover {
                background: #30D158;
            }
        """)
        self.play_btn.clicked.connect(self.toggle_play)
        ctrl_layout.addWidget(self.play_btn)

        # Next Track
        next_btn = QPushButton("⏭")
        next_btn.setFixedSize(30, 24)
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.setStyleSheet("color: #FFFFFF; font-size: 14px; background: transparent; border: none;")
        next_btn.clicked.connect(self.next_track)
        ctrl_layout.addWidget(next_btn)

        main_layout.addLayout(ctrl_layout)

        # Playback timer (100ms)
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self.advance_playback)
        self.play_timer.start(100)

    def paint_disc(self, event):
        p = QPainter(self.disc)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.disc.width()
        h = self.disc.height()

        p.save()
        p.translate(w / 2.0, h / 2.0)
        p.rotate(self.disc_angle)

        # Black vinyl body with grooves
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(22, 22, 26))
        p.drawEllipse(QRectF(-22, -22, 44, 44))

        # Grooves
        p.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(-17, -17, 34, 34))
        p.drawEllipse(QRectF(-12, -12, 24, 24))

        # Center Green Label
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#30D158"))
        p.drawEllipse(QRectF(-7, -7, 14, 14))

        # Spindle Hole
        p.setBrush(QColor("#000000"))
        p.drawEllipse(QRectF(-2, -2, 4, 4))

        p.restore()

    def advance_playback(self):
        if self.is_playing:
            self.current_sec += 0.1
            if self.current_sec >= self.total_sec:
                self.current_sec = 0.0

            self.disc_angle = (self.disc_angle + 2.5) % 360.0
            self.disc.update()

            self.slider.blockSignals(True)
            self.slider.setValue(int(self.current_sec))
            self.slider.blockSignals(False)

            # Timestamps
            m = int(self.current_sec // 60)
            s = int(self.current_sec % 60)
            self.curr_time_lbl.setText(f"{m:02d}:{s:02d}")

            rem = max(0, int(self.total_sec - self.current_sec))
            rm = rem // 60
            rs = rem % 60
            self.rem_time_lbl.setText(f"-{rm:02d}:{rs:02d}")

            # Sync Karaoke
            self.karaoke.sync_time(self.current_sec)

    def toggle_play(self):
        self.is_playing = not self.is_playing
        send_vk(VK_MEDIA_PLAY_PAUSE)
        self.play_btn.setText("▶" if not self.is_playing else "⏸")
        self.eq.set_active(self.is_playing)

    def next_track(self):
        send_vk(VK_MEDIA_NEXT_TRACK)
        self.current_sec = 0.0
        play_sound("click")

    def prev_track(self):
        send_vk(VK_MEDIA_PREV_TRACK)
        self.current_sec = 0.0
        play_sound("click")

    def on_slider_moved(self, val):
        self.current_sec = float(val)
        self.karaoke.sync_time(self.current_sec)

    def seek_to(self, sec):
        self.current_sec = float(sec)
        self.slider.setValue(int(sec))
        self.karaoke.sync_time(self.current_sec)
        play_sound("click")

# ==============================================================================
# WATER INTAKE TRACKER & FOCUS POMODORO (REEL 3: WATER INTAKE 1.0 / 1.5 L)
# ==============================================================================
class WaterReminderWidget(QWidget):
    """Water intake tracker with circular fluid gauge, hourly chart, and focus timer."""
    water_drank = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.goal_ml = 1500
        self.current_ml = 1000  # Default 1.0 L as seen in Reel 3
        self.wave_tick = 0

        # Hourly intake stats (7 intervals)
        self.hourly_labels = ["08", "10", "12", "14", "16", "18", "20"]
        self.hourly_data = [250, 250, 0, 250, 250, 0, 0]

        # Focus Pomodoro
        self.focus_total_sec = 25 * 60
        self.focus_sec_left = self.focus_total_sec
        self.focus_running = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(6)

        # 1. Header (Water intake: 1.0 / 1.5 L)
        h_layout = QHBoxLayout()
        h_layout.setSpacing(6)

        title_lbl = QLabel("Водный баланс")
        title_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        h_layout.addWidget(title_lbl)

        h_layout.addStretch()

        self.amount_lbl = QLabel("1.0 / 1.5 L")
        self.amount_lbl.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 800;")
        h_layout.addWidget(self.amount_lbl)

        main_layout.addLayout(h_layout)

        # 2. Middle Row: Circular Fluid Gauge + Hourly Bar Chart
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(12)

        # Circular Fluid Gauge (64x64)
        self.gauge = QLabel()
        self.gauge.setFixedSize(64, 64)
        self.gauge.paintEvent = self.paint_water_gauge
        mid_layout.addWidget(self.gauge)

        # Hourly Bar Chart
        self.chart = QLabel()
        self.chart.setFixedHeight(64)
        self.chart.paintEvent = self.paint_hourly_chart
        mid_layout.addWidget(self.chart, stretch=1)

        main_layout.addLayout(mid_layout)

        # 3. Actions Row (+250 ml button & Reset)
        act_layout = QHBoxLayout()
        act_layout.setSpacing(8)

        self.drink_btn = QPushButton("💧 +250 мл")
        self.drink_btn.setFixedSize(110, 26)
        self.drink_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drink_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #007AFF, stop:1 #38BDF8);
                color: #FFFFFF;
                font-size: 10px;
                font-weight: 800;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: #38BDF8;
                color: #000000;
            }
        """)
        self.drink_btn.clicked.connect(lambda: self.add_water(250))
        act_layout.addWidget(self.drink_btn)

        reset_btn = QPushButton("↺ Сброс")
        reset_btn.setFixedSize(64, 26)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton {
                background: #202228;
                color: #8E8E93;
                font-size: 9px;
                font-weight: 600;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                color: #FFFFFF;
            }
        """)
        reset_btn.clicked.connect(self.reset_water)
        act_layout.addWidget(reset_btn)

        act_layout.addStretch()

        # Pomodoro Mini Bar
        pomo_layout = QHBoxLayout()
        pomo_layout.setSpacing(6)

        self.pomo_lbl = QLabel("⏱️ 25:00")
        self.pomo_lbl.setStyleSheet("color: #FFFFFF; font-size: 10px; font-weight: 700;")
        pomo_layout.addWidget(self.pomo_lbl)

        self.pomo_btn = QPushButton("Старт")
        self.pomo_btn.setFixedSize(50, 22)
        self.pomo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pomo_btn.setStyleSheet("""
            QPushButton {
                background: #30D158;
                color: #000000;
                font-size: 9px;
                font-weight: 700;
                border-radius: 6px;
                border: none;
            }
        """)
        self.pomo_btn.clicked.connect(self.toggle_pomodoro)
        pomo_layout.addWidget(self.pomo_btn)

        act_layout.addLayout(pomo_layout)
        main_layout.addLayout(act_layout)

        # Timers
        self.wave_timer = QTimer(self)
        self.wave_timer.timeout.connect(self.advance_wave)
        self.wave_timer.start(50)

        self.pomo_timer = QTimer(self)
        self.pomo_timer.timeout.connect(self.tick_pomodoro)
        self.pomo_timer.start(1000)

    def add_water(self, ml=250):
        play_sound("water")
        self.current_ml = min(3000, self.current_ml + ml)
        # Update current hour bar
        self.hourly_data[3] = min(500, self.hourly_data[3] + ml)
        self.update_display()
        self.water_drank.emit(ml)

    def reset_water(self):
        self.current_ml = 0
        self.update_display()

    def update_display(self):
        liters = self.current_ml / 1000.0
        goal_l = self.goal_ml / 1000.0
        self.amount_lbl.setText(f"{liters:.1f} / {goal_l:.1f} L")
        self.gauge.update()
        self.chart.update()

    def advance_wave(self):
        self.wave_tick += 1
        self.gauge.update()

    def paint_water_gauge(self, event):
        p = QPainter(self.gauge)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.gauge.width()
        h = self.gauge.height()
        rect = QRectF(3, 3, w - 6, h - 6)

        # Outer Track
        pen_bg = QPen(QColor(255, 255, 255, 25), 4.0)
        p.setPen(pen_bg)
        p.drawArc(rect, 0, 360 * 16)

        # Fluid Arc
        ratio = min(1.0, self.current_ml / float(self.goal_ml))
        pen_fg = QPen(QColor("#38BDF8"), 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen_fg)
        span_angle = int(ratio * 360.0 * 16)
        p.drawArc(rect, 90 * 16, -span_angle)

        # Center Water Percentage & Droplet Icon
        p.setPen(QColor("#38BDF8"))
        font = p.font()
        font.setPointSize(10)
        font.setBold(True)
        p.setFont(font)
        pct = int(ratio * 100)
        p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, f"{pct}%")

    def paint_hourly_chart(self, event):
        p = QPainter(self.chart)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.chart.width()
        h = self.chart.height()

        bar_count = len(self.hourly_data)
        spacing = (w - (bar_count * 12)) / float(bar_count + 1)
        max_bar_h = h - 22.0

        for i, (val, lbl) in enumerate(zip(self.hourly_data, self.hourly_labels)):
            x = spacing + i * (12 + spacing)
            bar_ratio = min(1.0, val / 400.0)
            bar_h = max(3.0, bar_ratio * max_bar_h)
            y = max_bar_h - bar_h + 4.0

            # Bar Fill
            p.setPen(Qt.PenStyle.NoPen)
            if val > 0:
                p.setBrush(QColor("#007AFF"))
            else:
                p.setBrush(QColor(255, 255, 255, 20))
            p.drawRoundedRect(QRectF(x, y, 12, bar_h), 4, 4)

            # Hour label
            p.setPen(QColor("#8E8E93"))
            font = p.font()
            font.setPointSize(7)
            font.setBold(False)
            p.setFont(font)
            p.drawText(QRectF(x - 4, h - 14, 20, 12), Qt.AlignmentFlag.AlignCenter, lbl)

    def toggle_pomodoro(self):
        self.focus_running = not self.focus_running
        self.pomo_btn.setText("Пауза" if self.focus_running else "Старт")
        self.pomo_btn.setStyleSheet(f"""
            QPushButton {{
                background: {"#FF9F0A" if self.focus_running else "#30D158"};
                color: #000000;
                font-size: 9px;
                font-weight: 700;
                border-radius: 6px;
                border: none;
            }}
        """)

    def tick_pomodoro(self):
        if self.focus_running and self.focus_sec_left > 0:
            self.focus_sec_left -= 1
            m = self.focus_sec_left // 60
            s = self.focus_sec_left % 60
            self.pomo_lbl.setText(f"⏱️ {m:02d}:{s:02d}")
            if self.focus_sec_left == 0:
                self.focus_running = False
                play_sound("chime")
                self.pomo_btn.setText("Старт")
                self.focus_sec_left = self.focus_total_sec

# ==============================================================================
# VAYLI TOOLS DASHBOARD & ANTIGRAVITY AI BRIDGE (REEL 2)
# ==============================================================================
class ToolsDashboardWidget(QWidget):
    """System stats, Quick Notes, Clipboard History and Antigravity Live Bridge."""
    decision_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(6)

        # 1. System Stats Row (CPU, RAM, Uptime)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)

        # CPU
        self.cpu_lbl = QLabel("CPU: --%")
        self.cpu_lbl.setStyleSheet("""
            QLabel {
                background: #18191E;
                color: #38BDF8;
                font-size: 10px;
                font-weight: 700;
                border-radius: 6px;
                padding: 3px 8px;
            }
        """)
        stats_layout.addWidget(self.cpu_lbl)

        # RAM
        self.ram_lbl = QLabel("RAM: --%")
        self.ram_lbl.setStyleSheet("""
            QLabel {
                background: #18191E;
                color: #A78BFA;
                font-size: 10px;
                font-weight: 700;
                border-radius: 6px;
                padding: 3px 8px;
            }
        """)
        stats_layout.addWidget(self.ram_lbl)

        # Uptime
        self.uptime_lbl = QLabel("Uptime: 00:00")
        self.uptime_lbl.setStyleSheet("""
            QLabel {
                background: #18191E;
                color: #34D399;
                font-size: 10px;
                font-weight: 700;
                border-radius: 6px;
                padding: 3px 8px;
            }
        """)
        stats_layout.addWidget(self.uptime_lbl)

        stats_layout.addStretch()

        # Snipping tool button
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

        # 2. Mid Row: Quick Notes & Clipboard Quick History
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(8)

        # Quick Notes
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

        # Clipboard Tool
        clip_box = QVBoxLayout()
        clip_box.setSpacing(4)
        clip_title = QLabel("Буфер обмена:")
        clip_title.setStyleSheet("color: #8E8E93; font-size: 9px; font-weight: 600;")
        clip_box.addWidget(clip_title)

        self.last_clip_btn = QPushButton("История Win+V")
        self.last_clip_btn.setFixedHeight(28)
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
        self.clip_preview.setFixedHeight(48)
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

        # 3. Antigravity Approval Banner
        self.ask_banner = QFrame()
        self.ask_banner.setStyleSheet("""
            QFrame {
                background: rgba(255, 165, 0, 0.12);
                border: 1px solid rgba(255, 165, 0, 0.35);
                border-radius: 8px;
            }
        """)
        ask_layout = QHBoxLayout(self.ask_banner)
        ask_layout.setContentsMargins(8, 4, 8, 4)
        ask_layout.setSpacing(8)

        self.ask_text = QLabel("Запрос: Разрешить выполнение действия?")
        self.ask_text.setStyleSheet("color: #FFA500; font-size: 10px; font-weight: 700;")
        ask_layout.addWidget(self.ask_text, stretch=1)

        allow_btn = QPushButton("Разрешить")
        allow_btn.setFixedSize(70, 22)
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
        """)
        allow_btn.clicked.connect(lambda: self.decision_submitted.emit("allow"))
        ask_layout.addWidget(allow_btn)

        deny_btn = QPushButton("Отклонить")
        deny_btn.setFixedSize(70, 22)
        deny_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        deny_btn.setStyleSheet("""
            QPushButton {
                background: #282623;
                color: #FF453A;
                font-size: 9px;
                font-weight: 700;
                border-radius: 6px;
                border: none;
            }
        """)
        deny_btn.clicked.connect(lambda: self.decision_submitted.emit("deny"))
        ask_layout.addWidget(deny_btn)

        self.ask_banner.setVisible(False)
        main_layout.addWidget(self.ask_banner)

        # Load notes & listen to clipboard
        self.load_notes()
        app_clip = QApplication.clipboard()
        app_clip.dataChanged.connect(self.on_clipboard_updated)

        # Stats updater timer
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
# MASCOT PLAYROOM, SETTINGS & BOTTOM NAVIGATION DOCK
# ==============================================================================
class MascotRoomWidget(QWidget):
    """Interactive room for Nusa & Vayli Tamagotchi."""
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(6)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mascot Stack (Nusa or Robo)
        self.mascot_stack = QStackedWidget()

        self.nusa = NusaPet(size=76)
        self.mascot_stack.addWidget(self.nusa)

        self.robo = LiveAnimatedRobo(size=64)
        self.mascot_stack.addWidget(self.robo)

        main_layout.addWidget(self.mascot_stack, alignment=Qt.AlignmentFlag.AlignCenter)

        # Mascot status label
        self.status_lbl = QLabel("Нуса: Мурчит и следит за курсором")
        self.status_lbl.setStyleSheet("color: #8E8E93; font-size: 10px; font-weight: 500;")
        main_layout.addWidget(self.status_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        # Quick interaction pill buttons
        act_layout = QHBoxLayout()
        act_layout.setSpacing(8)
        act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        feed_btn = QPushButton("🍪 Покормить")
        feed_btn.setFixedSize(90, 24)
        feed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        feed_btn.setStyleSheet("""
            QPushButton {
                background: #202228;
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 700;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover {
                background: #FF5A5F;
            }
        """)
        feed_btn.clicked.connect(self.feed_pet)
        act_layout.addWidget(feed_btn)

        pet_btn = QPushButton("❤️ Погладить")
        pet_btn.setFixedSize(90, 24)
        pet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pet_btn.setStyleSheet("""
            QPushButton {
                background: #202228;
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 700;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover {
                background: #FF7A90;
            }
        """)
        pet_btn.clicked.connect(self.pet_mascot)
        act_layout.addWidget(pet_btn)

        dance_btn = QPushButton("🎵 Танцевать")
        dance_btn.setFixedSize(90, 24)
        dance_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dance_btn.setStyleSheet("""
            QPushButton {
                background: #202228;
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 700;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover {
                background: #30D158;
                color: #000000;
            }
        """)
        dance_btn.clicked.connect(self.dance_pet)
        act_layout.addWidget(dance_btn)

        main_layout.addLayout(act_layout)

    def feed_pet(self):
        self.nusa.feed_file()
        self.robo.set_mode("heart", 2000)
        self.status_lbl.setText("Нуса: Вкусно кушает печеньку!")
        QTimer.singleShot(3000, lambda: self.status_lbl.setText("Нуса: Сытый и довольный"))

    def pet_mascot(self):
        self.nusa.poke()
        self.robo.set_mode("heart", 2000)
        self.status_lbl.setText("Нуса: Мурчит от счастья ❤️")
        QTimer.singleShot(2500, lambda: self.status_lbl.setText("Нуса: Отдохнул"))

    def dance_pet(self):
        self.nusa.set_state("music", 4000)
        self.robo.set_mode("music", 4000)
        self.status_lbl.setText("Нуса: Танцует под ритм ♫")
        QTimer.singleShot(4000, lambda: self.status_lbl.setText("Нуса: Перевел дыхание"))

    def set_mascot_mode(self, mode="nusa"):
        if mode == "robo":
            self.mascot_stack.setCurrentWidget(self.robo)
            self.status_lbl.setText("Робот: Онлайн и готов к работе")
        else:
            self.mascot_stack.setCurrentWidget(self.nusa)
            self.status_lbl.setText("Нуса: Мурчит и следит за курсором")


class SettingsTabWidget(QWidget):
    """Settings: Mascot selection, sound, reset position."""
    mascot_changed = pyqtSignal(str)
    sound_toggled = pyqtSignal(bool)
    reset_pos_requested = pyqtSignal()
    bluetooth_test_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Mascot selector
        m_row = QHBoxLayout()
        m_lbl = QLabel("Выбор питомца острова:")
        m_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        m_row.addWidget(m_lbl)
        m_row.addStretch()

        self.btn_nusa = QPushButton("🐾 Нуса (Котик)")
        self.btn_nusa.setFixedSize(110, 24)
        self.btn_nusa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nusa.setStyleSheet("""
            QPushButton {
                background: #38BDF8;
                color: #000000;
                font-size: 9px;
                font-weight: 800;
                border-radius: 6px;
                border: none;
            }
        """)
        self.btn_nusa.clicked.connect(lambda: self.select_mascot("nusa"))
        m_row.addWidget(self.btn_nusa)

        self.btn_robo = QPushButton("🤖 Робот")
        self.btn_robo.setFixedSize(80, 24)
        self.btn_robo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_robo.setStyleSheet("""
            QPushButton {
                background: #252730;
                color: #8E8E93;
                font-size: 9px;
                font-weight: 700;
                border-radius: 6px;
                border: none;
            }
        """)
        self.btn_robo.clicked.connect(lambda: self.select_mascot("robo"))
        m_row.addWidget(self.btn_robo)
        layout.addLayout(m_row)

        # Sound Toggle
        s_row = QHBoxLayout()
        s_lbl = QLabel("Звуковые эффекты острова:")
        s_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        s_row.addWidget(s_lbl)
        s_row.addStretch()

        self.sound_btn = QPushButton("Включены 🔔")
        self.sound_btn.setFixedSize(100, 24)
        self.sound_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sound_btn.setStyleSheet("""
            QPushButton {
                background: #30D158;
                color: #000000;
                font-size: 9px;
                font-weight: 800;
                border-radius: 6px;
                border: none;
            }
        """)
        self.sound_btn.clicked.connect(self.toggle_sound)
        s_row.addWidget(self.sound_btn)
        layout.addLayout(s_row)

        # Bluetooth Pop-up Test
        bt_row = QHBoxLayout()
        bt_lbl = QLabel("Тест аксессуара (Reel 3 Pop-up):")
        bt_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        bt_row.addWidget(bt_lbl)
        bt_row.addStretch()

        bt_test_btn = QPushButton("Baseus Encok WM01")
        bt_test_btn.setFixedSize(140, 24)
        bt_test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        bt_test_btn.setStyleSheet("""
            QPushButton {
                background: #007AFF;
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 800;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #38BDF8;
                color: #000000;
            }
        """)
        bt_test_btn.clicked.connect(self.bluetooth_test_requested.emit)
        bt_row.addWidget(bt_test_btn)
        layout.addLayout(bt_row)

        # Reset position
        r_row = QHBoxLayout()
        r_lbl = QLabel("Положение окна острова:")
        r_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        r_row.addWidget(r_lbl)
        r_row.addStretch()

        reset_btn = QPushButton("Сбросить по центру экрана")
        reset_btn.setFixedSize(170, 24)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton {
                background: #252730;
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 700;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #FF453A;
            }
        """)
        reset_btn.clicked.connect(self.reset_pos_requested.emit)
        r_row.addWidget(reset_btn)
        layout.addLayout(r_row)

        layout.addStretch()

    def select_mascot(self, mode):
        self.mascot_changed.emit(mode)
        if mode == "nusa":
            self.btn_nusa.setStyleSheet("background: #38BDF8; color: #000000; font-size: 9px; font-weight: 800; border-radius: 6px; border: none;")
            self.btn_robo.setStyleSheet("background: #252730; color: #8E8E93; font-size: 9px; font-weight: 700; border-radius: 6px; border: none;")
        else:
            self.btn_robo.setStyleSheet("background: #38BDF8; color: #000000; font-size: 9px; font-weight: 800; border-radius: 6px; border: none;")
            self.btn_nusa.setStyleSheet("background: #252730; color: #8E8E93; font-size: 9px; font-weight: 700; border-radius: 6px; border: none;")

    def toggle_sound(self):
        # Emits toggle
        current = "Включены" in self.sound_btn.text()
        new_state = not current
        self.sound_btn.setText("Включены 🔔" if new_state else "Выключены 🔇")
        self.sound_btn.setStyleSheet(f"""
            QPushButton {{
                background: {"#30D158" if new_state else "#252730"};
                color: {"#000000" if new_state else "#8E8E93"};
                font-size: 9px;
                font-weight: 800;
                border-radius: 6px;
                border: none;
            }}
        """)
        self.sound_toggled.emit(new_state)


class BottomDock(QFrame):
    """Sleek iOS frosted glass pill dock for tab navigation."""
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
        layout.setSpacing(4)

        tabs_data = [
            ("🐾 Питомец", 0),
            ("🎵 Музыка", 1),
            ("📂 Полка", 2),
            ("💧 Баланс", 3),
            ("⚡ Утилиты", 4),
            ("⚙️ Опции", 5),
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
                        font-size: 9px;
                        font-weight: 800;
                        border-radius: 13px;
                        padding: 0 10px;
                        border: none;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #8E8E93;
                        font-size: 9px;
                        font-weight: 600;
                        border-radius: 13px;
                        padding: 0 8px;
                        border: none;
                    }
                    QPushButton:hover {
                        color: #FFFFFF;
                        background: rgba(255, 255, 255, 0.05);
                    }
                """)
        self.tab_selected.emit(index)

# ==============================================================================
# MAIN WINDOW: TWOCODE DYNAMIC ISLAND PRO (NUSA & VAYLI & TAMAGOTCHI)
# ==============================================================================
class TwoCodeIsland(QWidget):
    """The Ultimate Dynamic Island with Living Mascot, Karaoke, File Shelf & Health."""
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

        # Dimension specifications
        self.COLLAPSED_W = 168
        self.COLLAPSED_H = 32
        self.EXPANDED_W = 460
        self.EXPANDED_H = 254
        self.BT_W = 280
        self.BT_H = 54

        # States
        self.is_expanded = False
        self.is_pinned = False
        self.is_bt_showing = False
        self.sound_enabled = True
        self.mascot_type = "nusa"  # nusa or robo

        # Custom coordinates
        self.custom_x = None
        self.custom_y = None
        self.dragging = False
        self.drag_position = QPoint()

        # Load Saved Config
        self.load_config()

        # Build UI layout
        self.init_ui()

        # Smooth Geometry Animation
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(180)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Auto-collapse timer (450ms delay)
        self.collapse_timer = QTimer(self)
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.setInterval(450)
        self.collapse_timer.timeout.connect(self.auto_collapse)

        # Setup Tray
        self.setup_tray_icon()

        # Connect Global HTTP & App Signals
        global_signals.agent_status.connect(self.on_agent_status)
        global_signals.agent_ask.connect(self.on_agent_ask)
        global_signals.agent_done.connect(self.on_agent_done)
        global_signals.bluetooth_popup.connect(self.show_bluetooth_popup)
        global_signals.shelf_add.connect(self.on_remote_shelf_add)
        global_signals.pet_emote.connect(self.on_remote_pet_emote)
        global_signals.water_drink.connect(self.water_widget.add_water)

        # Start collapsed
        self.set_collapsed_geometry(animate=False)

    def init_ui(self):
        # Outer main layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Container Frame with G2 continuous rounded corners and deep OLED black
        self.container = QFrame()
        self.container.setObjectName("IslandContainer")
        self.update_style()

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(6, 4, 6, 4)
        container_layout.setSpacing(4)

        # Main Stack: Collapsed Pill (0), Expanded Island (1), Bluetooth Dropdown (2)
        self.main_stack = QStackedWidget()

        # ----------------------------------------------------------------------
        # PAGE 0: COLLAPSED COMPACT NOTCH
        # ----------------------------------------------------------------------
        self.pill_widget = QWidget()
        self.pill_widget.setFixedHeight(self.COLLAPSED_H - 8)
        pill_layout = QHBoxLayout(self.pill_widget)
        pill_layout.setContentsMargins(6, 0, 8, 0)
        pill_layout.setSpacing(6)

        # 1. Notch Living Eyes (• •)
        self.notch_eyes = NotchEyes()
        pill_layout.addWidget(self.notch_eyes)

        # 2. Status Label / Brand
        self.notch_title = QLabel("TwoCode")
        self.notch_title.setStyleSheet("color: #FFFFFF; font-size: 10px; font-weight: 700;")
        pill_layout.addWidget(self.notch_title)

        pill_layout.addStretch()

        # 3. Compact Equalizer
        self.notch_eq = EqualizerBars()
        pill_layout.addWidget(self.notch_eq)

        self.main_stack.addWidget(self.pill_widget)

        # ----------------------------------------------------------------------
        # PAGE 1: EXPANDED FULL ISLAND
        # ----------------------------------------------------------------------
        self.expanded_widget = QWidget()
        exp_layout = QVBoxLayout(self.expanded_widget)
        exp_layout.setContentsMargins(4, 4, 4, 4)
        exp_layout.setSpacing(6)

        # Top Bar: Title & Window Pin Button
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

        # Sub Stack with Tabs
        self.tab_stack = QStackedWidget()

        # Tab 0: Mascot Interactive Room
        self.mascot_room = MascotRoomWidget()
        self.tab_stack.addWidget(self.mascot_room)

        # Tab 1: Music Player & Live Karaoke Lyrics
        self.music_player = NusaMusicPlayer()
        self.tab_stack.addWidget(self.music_player)

        # Tab 2: File Shelf with Staggered Fall Animation
        self.file_shelf = FileShelfWidget()
        self.file_shelf.feed_to_pet.connect(self.on_feed_file_to_pet)
        self.tab_stack.addWidget(self.file_shelf)

        # Tab 3: Water Intake Tracker & Pomodoro
        self.water_widget = WaterReminderWidget()
        self.tab_stack.addWidget(self.water_widget)

        # Tab 4: Tools Dashboard (CPU/RAM/Notes/Clipboard)
        self.tools_widget = ToolsDashboardWidget()
        self.tools_widget.decision_submitted.connect(self.on_decision_submitted)
        self.tab_stack.addWidget(self.tools_widget)

        # Tab 5: Settings
        self.settings_widget = SettingsTabWidget()
        self.settings_widget.mascot_changed.connect(self.on_mascot_changed)
        self.settings_widget.sound_toggled.connect(self.on_sound_toggled)
        self.settings_widget.reset_pos_requested.connect(self.reset_to_center)
        self.settings_widget.bluetooth_test_requested.connect(lambda: self.show_bluetooth_popup({"name": "Baseus Encok WM01", "battery": 79}))
        self.tab_stack.addWidget(self.settings_widget)

        exp_layout.addWidget(self.tab_stack, stretch=1)

        # Bottom iOS Frosted Glass Pill Dock
        self.dock = BottomDock()
        self.dock.tab_selected.connect(self.tab_stack.setCurrentIndex)
        exp_layout.addWidget(self.dock)

        self.main_stack.addWidget(self.expanded_widget)

        # ----------------------------------------------------------------------
        # PAGE 2: BLUETOOTH DROPDOWN ACCESSORY POP-UP (REEL 3)
        # ----------------------------------------------------------------------
        self.bt_popup = BluetoothDropdownWidget()
        self.bt_popup.closed.connect(self.collapse)
        self.main_stack.addWidget(self.bt_popup)

        container_layout.addWidget(self.main_stack)
        outer_layout.addWidget(self.container)

    def update_style(self):
        radius = "22px" if self.is_expanded else "16px"
        self.container.setStyleSheet(f"""
            QFrame#IslandContainer {{
                background-color: #0B0B0E;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: {radius};
            }}
        """)

    # Drag & Drop files directly onto the notch
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
            if not self.is_expanded:
                self.expand()
                self.dock.select_tab(2)  # Switch to Shelf tab

    def dropEvent(self, event):
        paths = []
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                lp = u.toLocalFile()
                if lp and os.path.exists(lp):
                    paths.append(lp)
        if paths:
            self.file_shelf.add_files(paths, animate=True)
            self.mascot_room.feed_pet()
            event.acceptProposedAction()

    # Geometry & Multi-monitor
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
        y = 44 if geom.top() == 0 else (geom.top() + 4)
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
                tw = self.EXPANDED_W if self.is_expanded else self.COLLAPSED_W
                th = self.EXPANDED_H if self.is_expanded else self.COLLAPSED_H
                tx, ty = self.get_target_coords(tw, th)
                self.move(tx, ty)
            else:
                self.custom_x = self.pos().x()
                self.custom_y = self.pos().y()
                self.save_config()
            event.accept()

    # Hover Expand & Collapse
    def enterEvent(self, event):
        self.collapse_timer.stop()
        if not self.is_expanded and not self.is_bt_showing:
            self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_pinned and not self.is_bt_showing:
            self.collapse_timer.start()
        super().leaveEvent(event)

    def auto_collapse(self):
        if not self.is_pinned and not self.is_bt_showing:
            self.collapse()

    def expand(self):
        self.is_expanded = True
        self.is_bt_showing = False
        self.main_stack.setCurrentWidget(self.expanded_widget)
        self.update_style()

        tx, ty = self.get_target_coords(self.EXPANDED_W, self.EXPANDED_H)
        target_rect = QRect(tx, ty, self.EXPANDED_W, self.EXPANDED_H)

        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        self.anim.start()
        self.show()
        make_window_topmost(int(self.winId()))

    def collapse(self):
        self.is_expanded = False
        self.is_bt_showing = False
        self.main_stack.setCurrentWidget(self.pill_widget)
        self.update_style()

        tx, ty = self.get_target_coords(self.COLLAPSED_W, self.COLLAPSED_H)
        target_rect = QRect(tx, ty, self.COLLAPSED_W, self.COLLAPSED_H)

        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        self.anim.start()
        self.show()
        make_window_topmost(int(self.winId()))

    def set_collapsed_geometry(self, animate=False):
        self.is_expanded = False
        self.is_bt_showing = False
        self.main_stack.setCurrentWidget(self.pill_widget)
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
        make_window_topmost(int(self.winId()))

    def show_bluetooth_popup(self, data):
        self.is_expanded = False
        self.is_bt_showing = True
        name = data.get("name", "Baseus Encok WM01")
        battery = data.get("battery", 79)
        self.bt_popup.show_device(name, battery)
        self.main_stack.setCurrentWidget(self.bt_popup)
        self.update_style()

        tx, ty = self.get_target_coords(self.BT_W, self.BT_H)
        target_rect = QRect(tx, ty, self.BT_W, self.BT_H)

        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        self.anim.start()
        self.show()
        make_window_topmost(int(self.winId()))

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

    def reset_to_center(self):
        self.custom_x = None
        self.custom_y = None
        self.save_config()
        tw = self.EXPANDED_W if self.is_expanded else self.COLLAPSED_W
        th = self.EXPANDED_H if self.is_expanded else self.COLLAPSED_H
        tx, ty = self.get_target_coords(tw, th)
        self.move(tx, ty)

    # Pet & Mascot handlers
    def on_feed_file_to_pet(self, path):
        self.mascot_room.feed_pet()
        self.notch_eyes.set_happy(True)
        QTimer.singleShot(2500, lambda: self.notch_eyes.set_happy(False))

    def on_mascot_changed(self, mode):
        self.mascot_type = mode
        self.mascot_room.set_mascot_mode(mode)
        self.save_config()

    def on_sound_toggled(self, enabled):
        self.sound_enabled = enabled
        self.save_config()

    # Remote HTTP Signals
    def on_remote_shelf_add(self, files):
        self.file_shelf.add_files(files, animate=True)
        self.expand()
        self.dock.select_tab(2)

    def on_remote_pet_emote(self, emote):
        if emote == "eat":
            self.mascot_room.feed_pet()
        elif emote == "music":
            self.mascot_room.dance_pet()
        else:
            self.mascot_room.pet_mascot()

    def on_agent_status(self, data):
        state = data.get("state", "idle")
        action = data.get("action", "Antigravity")
        self.notch_title.setText(action[:16])

    def on_agent_ask(self, data):
        prompt = data.get("prompt", "Разрешить действие?")
        self.tools_widget.ask_text.setText(f"Запрос: {prompt}")
        self.tools_widget.ask_banner.setVisible(True)
        self.expand()
        self.dock.select_tab(4)
        play_sound("alert")

    def on_agent_done(self, data):
        self.tools_widget.ask_banner.setVisible(False)
        self.mascot_room.dance_pet()
        play_sound("chime")

    def on_decision_submitted(self, decision):
        self.tools_widget.ask_banner.setVisible(False)
        global_signals.decision_made.emit(decision)
        play_sound("click")

    # Tray Setup
    def setup_tray_icon(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.create_tray_icon())
        self.tray.setToolTip("TwoCode Dynamic Island Pro")

        menu = QMenu()
        act_toggle = menu.addAction("Развернуть / Свернуть")
        act_toggle.triggered.connect(lambda: self.collapse() if self.is_expanded else self.expand())

        act_shelf = menu.addAction("📂 Полка файлов (Shelf)")
        act_shelf.triggered.connect(lambda: (self.expand(), self.dock.select_tab(2)))

        act_bt = menu.addAction("ᛒ Тест Bluetooth Pop-up")
        act_bt.triggered.connect(lambda: self.show_bluetooth_popup({"name": "Baseus Encok WM01", "battery": 79}))

        act_feed = menu.addAction("🍪 Покормить Нусу")
        act_feed.triggered.connect(self.mascot_room.feed_pet)

        act_snip = menu.addAction("✂ Сделать скриншот")
        act_snip.triggered.connect(trigger_screenclip)

        menu.addSeparator()
        act_quit = menu.addAction("Выход")
        act_quit.triggered.connect(QApplication.instance().quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.is_expanded:
                self.collapse()
            else:
                self.expand()

    def create_tray_icon(self):
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#0B0B0E"))
        p.setPen(QPen(QColor("#38BDF8"), 2.0))
        p.drawRoundedRect(QRectF(2, 6, 28, 20), 10, 10)
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(8, 12, 4, 4))
        p.drawEllipse(QRectF(20, 12, 4, 4))
        p.end()
        return QIcon(pix)

    # Configuration persistence
    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.sound_enabled = cfg.get("sound_enabled", True)
                    self.mascot_type = cfg.get("mascot_type", "nusa")
                    self.custom_x = cfg.get("pos_x", None)
                    self.custom_y = cfg.get("pos_y", None)
            except Exception:
                pass

    def save_config(self):
        try:
            cfg = {
                "sound_enabled": self.sound_enabled,
                "mascot_type": self.mascot_type,
                "pos_x": self.custom_x,
                "pos_y": self.custom_y
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
def start_http_server():
    try:
        server = ReusableHTTPServer(("127.0.0.1", 28282), IslandAPIHandler)
        server.serve_forever()
    except Exception as e:
        print(f"HTTP Server error: {e}")

if __name__ == "__main__":
    # Start HTTP Server in background daemon thread
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    island = TwoCodeIsland()
    island.show()

    sys.exit(app.exec())
