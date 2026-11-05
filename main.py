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
    try:
        if kind == "click":
            winsound.Beep(1200, 20)
        elif kind == "heart":
            winsound.Beep(1046, 50)
            winsound.Beep(1318, 70)
        elif kind == "chime":
            winsound.Beep(784, 50)
            winsound.Beep(987, 50)
            winsound.Beep(1318, 90)
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
# REAL WINDOWS MEDIA INTEGRATION (GSMTC & WINSDK)
# ==============================================================================
try:
    from media_engine import WindowsMediaWatcher, RealMediaState
    HAS_MEDIA_ENGINE = True
except Exception:
    HAS_MEDIA_ENGINE = False

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
            self._send_json(200, {"status": "ok", "app": "TwoCode Dynamic Island Pro", "version": "3.5.0"})
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


class LiveAnimatedRobo(QWidget):
    """The TwoCode High-Tech Robot Companion with blinking, antenna orb and music dance."""
    clicked = pyqtSignal()

    def __init__(self, size=22, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.size_val = size
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.mode = "idle"  # idle, music, thinking, coding, heart, done
        self.anim_tick = 0
        self.blink_state = False
        self.blink_counter = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(45)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            play_sound("heart")
            self.set_mode("heart", duration_ms=2500)
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

        # Dance bobbing tilt when music is playing
        if self.mode == "music":
            tilt = math.sin(self.anim_tick * 0.28) * 7.0
            bob_y = math.cos(self.anim_tick * 0.56) * 1.5 * s
            p.rotate(tilt)
            p.translate(0, bob_y)

        # Antenna stem
        p.setPen(QPen(QColor("#A8A49E"), max(1, int(2.5 * s))))
        p.drawLine(0, int(-16 * s), 0, int(-24 * s))

        # Antenna Glowing Orb Tip
        orb_color = QColor("#5CE07A")
        if self.mode in ["thinking", "coding"]:
            orb_color = QColor(255, 140, 0, int(180 + 75 * math.sin(self.anim_tick * 0.4)))
        elif self.mode == "music":
            orb_color = QColor("#C8F08F")
        elif self.mode == "heart":
            orb_color = QColor("#FF69B4")

        p.setBrush(QBrush(orb_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(0, -25.0 * s), 3.8 * s, 3.8 * s)

        # Robo Head Body
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
            font.setPointSize(max(6, int(10 * s)))
            font.setBold(True)
            p.setFont(font)
            p.drawText(QRectF(-18 * s, -12 * s, 36 * s, 26 * s), Qt.AlignmentFlag.AlignCenter, "♥  ♥")
        elif self.blink_state:
            p.setPen(QPen(QColor("#5CE07A"), max(1, int(2 * s))))
            p.drawLine(int(-12 * s), 0, int(-4 * s), 0)
            p.drawLine(int(4 * s), 0, int(12 * s), 0)
        else:
            p.setBrush(QColor("#5CE07A"))
            p.drawRoundedRect(QRectF(-13 * s, -5 * s, 8 * s, 10 * s), 3 * s, 3 * s)
            p.drawRoundedRect(QRectF(5 * s, -5 * s, 8 * s, 10 * s), 3 * s, 3 * s)

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
    """File shelf with Drag & Drop target and staggered drop animation."""
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
            play_sound("heart")
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
# REAL WINDOWS MUSIC PLAYER (YANDEX.MUSIC, SPOTIFY, CHROME, YOUTUBE)
# ==============================================================================
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
    """Ambient TwoCode Robot Companion reacting to coding, music and system tasks."""
    decision_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.robo = LiveAnimatedRobo(size=64)
        layout.addWidget(self.robo, alignment=Qt.AlignmentFlag.AlignCenter)

        self.status_lbl = QLabel("Робот TwoCode: Готов к работе")
        self.status_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        layout.addWidget(self.status_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        self.sub_lbl = QLabel("Ассистент автоматически реагирует на задачи и музыку")
        self.sub_lbl.setStyleSheet("color: #8E8E93; font-size: 10px;")
        layout.addWidget(self.sub_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        # Antigravity Approval Banner
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

        self.ask_text = QLabel("Запрос действия от Antigravity")
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
        layout.addWidget(self.ask_banner)

        layout.addStretch()

    def set_music_mode(self, is_playing, track_info=""):
        if is_playing:
            self.robo.set_mode("music")
            self.status_lbl.setText(f"Слушает музыку ♫")
            if track_info:
                self.sub_lbl.setText(track_info)
        else:
            if self.robo.mode == "music":
                self.robo.set_mode("idle")
                self.status_lbl.setText("Робот TwoCode: В ожидании")
                self.sub_lbl.setText("Ассистент автоматически реагирует на задачи и музыку")


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

        # GitHub Repo
        gh_row = QHBoxLayout()
        gh_lbl = QLabel("GitHub репозиторий проекта:")
        gh_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        gh_row.addWidget(gh_lbl)
        gh_row.addStretch()

        gh_btn = QPushButton("sticiandrei9/dinamic-island")
        gh_btn.setFixedSize(160, 24)
        gh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gh_btn.setStyleSheet("background: #252730; color: #FFFFFF; font-size: 9px; font-weight: 700; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.2);")
        gh_btn.clicked.connect(lambda: os.startfile("https://github.com/sticiandrei9/dinamic-island-windows"))
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
        self.EXPANDED_H = 250
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
        self.init_ui()

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(160)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.collapse_timer = QTimer(self)
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.setInterval(450)
        self.collapse_timer.timeout.connect(self.auto_collapse)

        self.setup_tray_icon()

        # Connect signals
        global_signals.agent_status.connect(self.on_agent_status)
        global_signals.agent_ask.connect(self.on_agent_ask)
        global_signals.agent_done.connect(self.on_agent_done)
        global_signals.bluetooth_popup.connect(self.show_bluetooth_popup)
        global_signals.shelf_add.connect(self.on_remote_shelf_add)
        global_signals.media_state_changed.connect(self.on_media_state_changed)

        # Start Real Windows Media Watcher
        if HAS_MEDIA_ENGINE:
            self.media_watcher = WindowsMediaWatcher(self.on_media_update_threadsafe)
        else:
            self.media_watcher = None

        self.set_collapsed_geometry(animate=False)

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
        pill_layout = QHBoxLayout(self.pill_widget)
        pill_layout.setContentsMargins(6, 0, 8, 0)
        pill_layout.setSpacing(6)

        # 1. Full Animated TwoCode Robot in the droplet (antenna, orb, eyes, dance)
        self.pill_robo = LiveAnimatedRobo(size=22)
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

        # Tab 2: Ambient Robot Companion
        self.robo_tab = AmbientRoboTabWidget()
        self.robo_tab.decision_submitted.connect(self.on_decision_submitted)
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
        else:
            if self.pill_robo.mode == "music":
                self.pill_robo.set_mode("idle")
            self.pill_eq.set_active(False)
            self.robo_tab.set_music_mode(False)

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
            if not self.is_expanded:
                self.expand()
                self.dock.select_tab(1)

    def dropEvent(self, event):
        paths = []
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                lp = u.toLocalFile()
                if lp and os.path.exists(lp):
                    paths.append(lp)
        if paths:
            self.file_shelf.add_files(paths, animate=True)
            self.pill_robo.set_mode("heart", 2500)
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
        if not self.is_pinned and not self.is_bt_showing:
            self.collapse_timer.start()
        super().leaveEvent(event)

    def auto_collapse(self):
        if not self.is_pinned and not self.is_bt_showing:
            self.collapse()

    def expand(self):
        self.is_expanded = True
        self.is_bt_showing = False
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
        self.is_bt_showing = False
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
        self.file_shelf.add_files(files, animate=True)
        self.expand()
        self.dock.select_tab(1)

    def on_agent_status(self, data):
        action = data.get("action", "TwoCode")
        self.pill_title.setText(action[:14])

    def on_agent_ask(self, data):
        prompt = data.get("prompt", "Разрешить действие?")
        self.robo_tab.ask_text.setText(f"Запрос: {prompt}")
        self.robo_tab.ask_banner.setVisible(True)
        self.expand()
        self.dock.select_tab(2)
        play_sound("alert")

    def on_agent_done(self, data):
        self.robo_tab.ask_banner.setVisible(False)
        self.pill_robo.set_mode("heart", 3000)
        play_sound("chime")

    def on_decision_submitted(self, decision):
        self.robo_tab.ask_banner.setVisible(False)
        global_signals.decision_made.emit(decision)
        play_sound("click")

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
                    self.custom_x = cfg.get("pos_x", None)
                    self.custom_y = cfg.get("pos_y", None)
            except Exception:
                pass

    def save_config(self):
        try:
            cfg = {
                "sound_enabled": self.sound_enabled,
                "always_on_top": self.always_on_top,
                "pos_x": self.custom_x,
                "pos_y": self.custom_y
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass


def start_http_server():
    try:
        server = ReusableHTTPServer(("127.0.0.1", 28282), IslandAPIHandler)
        server.serve_forever()
    except Exception as e:
        print(f"HTTP Server error: {e}")

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    island = TwoCodeIsland()
    island.show()

    sys.exit(app.exec())
