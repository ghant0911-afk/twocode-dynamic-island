"""
TwoCode Dynamic Island - Ultimate Production Edition
Features:
- Micro Droplet Collapsed State: 68x14 px (Ultra compact!)
- Live Animated Robot (Blinking, Reading book with scanning eyes, Thinking with gears/bulb, Dancing to music with floating notes, Heart eyes, Star smile)
- Free Dragging with Left Mouse Button (Saves position, works on dual monitors)
- Universal Audio Controller (Yandex.Music, Spotify, Browser, VK, YouTube) with Play/Pause, Next, Prev, Volume +/- and Mute
- Screenshot Snipping Tool (1-click rectangular area selection via ms-screenclip:)
- Clipboard History Manager (Recent snippets + 1-click Win+V native clipboard history)
- Live Chat & Communication with Antigravity / AI right inside the Island
- Real-time Antigravity Transcript Event Stream Watcher
- Creative Animated Completion Banner from Robo
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
import threading
import socket
import ctypes
from datetime import datetime
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import winsound

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint, QSize,
    pyqtSignal, QObject
)
from PyQt6.QtGui import (
    QColor, QFont, QCursor, QPainter, QBrush, QPen, QIcon, QPixmap,
    QPainterPath, QLinearGradient
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QStackedWidget, QSystemTrayIcon, QMenu, QSlider,
    QLineEdit, QTextEdit, QScrollArea
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


def play_chime(kind="success"):
    try:
        if kind == "success":
            winsound.Beep(920, 60)
            winsound.Beep(1380, 100)
        elif kind == "celebrate":
            winsound.Beep(784, 60)
            winsound.Beep(987, 60)
            winsound.Beep(1318, 120)
        elif kind == "alert":
            winsound.Beep(987, 80)
            winsound.Beep(784, 100)
        elif kind == "heart":
            winsound.Beep(1046, 60)
            winsound.Beep(1318, 90)
        elif kind == "click":
            winsound.Beep(1200, 20)
    except Exception:
        pass


# =========================================================================
# IPC HTTP API & SIGNALS
# =========================================================================
class BridgeSignals(QObject):
    status_updated = pyqtSignal(dict)
    ask_requested = pyqtSignal(dict)
    done_signaled = pyqtSignal(dict)
    decision_made = pyqtSignal(str)
    user_chat_response = pyqtSignal(str)


bridge = BridgeSignals()


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
            self._send_json(200, {"status": "ok", "app": "TwoCode Dynamic Island Pro"})
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
        else:
            self._send_json(404, {"error": "Not Found"})


def _server_worker():
    server_address = ('127.0.0.1', 28282)
    while True:
        try:
            httpd = ReusableHTTPServer(server_address, IslandAPIHandler)
            httpd.serve_forever()
            break
        except Exception:
            time.sleep(0.5)


def start_ipc_server():
    t = threading.Thread(target=_server_worker, daemon=True)
    t.start()


# =========================================================================
# ANTIGRAVITY REAL-TIME TRANSCRIPT WATCHER
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
                                    "status": "working",
                                    "mode": "coding",
                                    "agent": "Antigravity",
                                    "project": "Workspace",
                                    "action": f"Editing {fname}",
                                    "file": fname,
                                    "diff": {
                                        "del": f"- {target}" if target else "- ...",
                                        "add": f"+ {repl}" if repl else "+ ..."
                                    }
                                })
                            elif name == "read_file":
                                path = args.get("Path", "file")
                                fname = os.path.basename(path)
                                bridge.status_updated.emit({
                                    "status": "working",
                                    "mode": "reading",
                                    "agent": "Antigravity",
                                    "project": "Workspace",
                                    "action": f"Reading {fname}",
                                    "file": fname,
                                    "diff": {"del": "", "add": f"📖 Читает файл {fname}..."}
                                })
                            elif name == "run_command":
                                summary = args.get("toolSummary", "Executing command")
                                bridge.status_updated.emit({
                                    "status": "working",
                                    "mode": "thinking",
                                    "agent": "Antigravity",
                                    "project": "Terminal",
                                    "action": summary,
                                    "file": "bash / ps",
                                    "diff": {"del": "", "add": f"$ {summary}"}
                                })
                        elif msg_type == "USER_INPUT":
                            bridge.status_updated.emit({
                                "status": "working",
                                "mode": "thinking",
                                "agent": "Antigravity",
                                "project": "Brain",
                                "action": "Thinking & Planning...",
                                "file": "query",
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
# LIVE ANIMATED ROBO MASCOT (Custom QPainter with Emotive Frames)
# =========================================================================
class LiveAnimatedRobo(QWidget):
    def __init__(self, size=64):
        super().__init__()
        self.setFixedSize(size, size)
        self.size_val = size
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.mode = "idle"  # idle, reading, thinking, coding, music, heart, done, curious, dizzy
        self.anim_tick = 0
        self.blink_state = False
        self.blink_timer_counter = 0

        # Animation timer (20 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_animation)
        self.timer.start(50)

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def advance_animation(self):
        self.anim_tick += 1

        # Natural eye blink every 3.5 seconds
        self.blink_timer_counter += 1
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
        s = w / 64.0  # Scale relative to 64px base

        p.save()
        p.translate(w / 2, h / 2)

        # 1. Dance Head Bobbing if music mode
        if self.mode == "music":
            tilt = math.sin(self.anim_tick * 0.25) * 6.0
            bob_y = math.cos(self.anim_tick * 0.5) * 2.0
            p.rotate(tilt)
            p.translate(0, bob_y)

        # Head base
        head_rect = QRect(int(-22 * s), int(-16 * s), int(44 * s), int(36 * s))

        # Antenna
        pen = QPen(QColor("#A8A49E"), max(1, int(2.5 * s)))
        p.setPen(pen)
        p.drawLine(0, int(-16 * s), 0, int(-24 * s))

        # Antenna Tip Orb (Glows based on mode)
        orb_color = QColor("#5CE07A")  # Green idle
        if self.mode in ["thinking", "coding"]:
            orb_alpha = int(180 + 75 * math.sin(self.anim_tick * 0.4))
            orb_color = QColor(255, 140, 0, orb_alpha)  # Pulsing amber
        elif self.mode == "reading":
            orb_color = QColor("#64D2FF")  # Blue reading
        elif self.mode == "heart":
            orb_color = QColor("#FF69B4")
        elif self.mode == "music":
            orb_color = QColor("#C8F08F")

        p.setBrush(QBrush(orb_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPoint(0, int(-25 * s)), int(3.5 * s), int(3.5 * s))

        # Floating Musical Notes if music mode
        if self.mode == "music":
            note_y = int(-28 * s - (self.anim_tick % 30) * s * 0.6)
            note_alpha = max(0, min(255, 255 - (self.anim_tick % 30) * 8))
            p.setPen(QColor(200, 240, 143, note_alpha))
            font = p.font()
            font.setPointSize(int(10 * s))
            p.setFont(font)
            p.drawText(int(10 * s), note_y, "♪")

        # Floating Bulb or Gears if thinking
        if self.mode in ["thinking", "coding"]:
            gear_alpha = int(160 + 95 * math.sin(self.anim_tick * 0.3))
            p.setPen(QColor(255, 165, 0, gear_alpha))
            font = p.font()
            font.setPointSize(int(9 * s))
            p.setFont(font)
            p.drawText(int(14 * s), int(-20 * s), "💡")

        # Little Book if reading
        if self.mode == "reading":
            p.setPen(QColor(100, 210, 255, 220))
            font = p.font()
            font.setPointSize(int(9 * s))
            p.setFont(font)
            p.drawText(int(-28 * s), int(16 * s), "📖")

        # Head Shell (TwoCode Matte White/Cream)
        p.setBrush(QBrush(QColor("#F5F3EF")))
        p.setPen(QPen(QColor("#383531"), max(1, int(1.5 * s))))
        p.drawRoundedRect(head_rect, int(14 * s), int(14 * s))

        # Earcups
        p.setBrush(QBrush(QColor("#E2DFD8")))
        p.drawRoundedRect(int(-25 * s), int(-6 * s), int(4 * s), int(14 * s), int(2 * s), int(2 * s))
        p.drawRoundedRect(int(21 * s), int(-6 * s), int(4 * s), int(14 * s), int(2 * s), int(2 * s))

        # Visor (Dark Charcoal Glass)
        visor_rect = QRect(int(-16 * s), int(-9 * s), int(32 * s), int(20 * s))
        p.setBrush(QBrush(QColor("#121110")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(visor_rect, int(8 * s), int(8 * s))

        # Eyes Rendering
        eye_y = int(-1 * s)
        eye_color = QColor("#62C8FF")  # Calm cyan

        if self.mode in ["thinking", "coding"]:
            eye_color = QColor("#FFA726")
        elif self.mode == "done":
            eye_color = QColor("#5CE07A")
        elif self.mode == "heart":
            eye_color = QColor("#FF69B4")

        # Eyes: Blinking
        if self.blink_state:
            p.setPen(QPen(eye_color, max(1, int(2 * s))))
            p.drawLine(int(-10 * s), eye_y, int(-4 * s), eye_y)
            p.drawLine(int(4 * s), eye_y, int(10 * s), eye_y)

        # Eyes: Reading (Scanning left-right)
        elif self.mode == "reading":
            scan_x = math.sin(self.anim_tick * 0.3) * 2.5 * s
            p.setBrush(QBrush(QColor("#64D2FF")))
            p.drawRoundedRect(QRect(int(-9 * s + scan_x), int(eye_y - 3 * s), int(4 * s), int(6 * s)), int(2 * s), int(2 * s))
            p.drawRoundedRect(QRect(int(5 * s + scan_x), int(eye_y - 3 * s), int(4 * s), int(6 * s)), int(2 * s), int(2 * s))

        # Eyes: Heart (Allowed)
        elif self.mode == "heart":
            p.setPen(QColor("#FF69B4"))
            font = p.font()
            font.setPointSize(max(7, int(8 * s)))
            p.setFont(font)
            p.drawText(int(-11 * s), int(eye_y + 4 * s), "♥")
            p.drawText(int(1 * s), int(eye_y + 4 * s), "♥")

        # Eyes: Done (Happy Smiling Arcs)
        elif self.mode == "done":
            p.setPen(QPen(QColor("#5CE07A"), max(1, int(2.5 * s))))
            aw = max(3, int(6 * s))
            ah = max(3, int(6 * s))
            p.drawArc(int(-10 * s), int(eye_y - 4 * s), aw, ah, 45 * 16, 90 * 16)
            p.drawArc(int(4 * s), int(eye_y - 4 * s), aw, ah, 45 * 16, 90 * 16)

        # Eyes: Dizzy
        elif self.mode == "dizzy":
            p.setPen(QColor("#FFD54F"))
            font = p.font()
            font.setPointSize(max(7, int(8 * s)))
            p.setFont(font)
            p.drawText(int(-11 * s), int(eye_y + 4 * s), "@")
            p.drawText(int(3 * s), int(eye_y + 4 * s), "@")

        # Eyes: Curious (One eye big, one small)
        elif self.mode == "curious":
            p.setBrush(QBrush(QColor("#FFA726")))
            p.drawRoundedRect(QRect(int(-10 * s), int(eye_y - 4 * s), max(2, int(6 * s)), max(3, int(8 * s))), max(1, int(3 * s)), max(1, int(3 * s)))
            p.drawRoundedRect(QRect(int(4 * s), int(eye_y - 2 * s), max(2, int(4 * s)), max(2, int(5 * s))), max(1, int(2 * s)), max(1, int(2 * s)))

        # Default Eyes
        else:
            p.setBrush(QBrush(eye_color))
            ew = max(2, int(5 * s))
            eh = max(3, int(7 * s))
            p.drawRoundedRect(QRect(int(-9 * s), int(eye_y - 4 * s), ew, eh), max(1, int(2.5 * s)), max(1, int(2.5 * s)))
            p.drawRoundedRect(QRect(int(4 * s), int(eye_y - 4 * s), ew, eh), max(1, int(2.5 * s)), max(1, int(2.5 * s)))

        p.restore()


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
        self.setWindowTitle("TwoCode Dynamic Island")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # COMPACT DROPLET COLLAPSED DIMENSIONS (Sleek pill with live Robo!):
        self.COLLAPSED_W = 118
        self.COLLAPSED_H = 26

        # EXPANDED DIMENSIONS (Compact TwoCode proportion, sleek and crisp):
        self.EXPANDED_W = 440
        self.EXPANDED_H = 136

        # State
        self.is_expanded = False
        self.is_pinned = False
        self.sound_enabled = True
        self.custom_x = None
        self.custom_y = None

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
        self.is_chat_mode = False

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

        # Connect Signals
        bridge.status_updated.connect(self.on_agent_status)
        bridge.ask_requested.connect(self.on_agent_ask)
        bridge.done_signaled.connect(self.on_agent_done)
        bridge.decision_made.connect(self.on_decision_made)
        bridge.user_chat_response.connect(self.on_chat_response)

        # Start collapsed as micro droplet
        self.set_collapsed_geometry(animate=False)
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
                    self.custom_x = cfg.get("pos_x", None)
                    self.custom_y = cfg.get("pos_y", None)
            except Exception:
                pass

    def save_config(self):
        try:
            cfg = {
                "sound_enabled": self.sound_enabled,
                "pos_x": self.custom_x,
                "pos_y": self.custom_y
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def get_active_screen(self):
        # Pick screen where mouse cursor is located, or primary
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
        # Attached right at top edge:
        # If taskbar is on top (primary screen y=0..44), hang right under it at y=44.
        # Otherwise attach right to the upper monitor bezel (geom.top() + 2)
        if geom.top() == 0:
            y = 44
        else:
            y = geom.top() + 2
        return x, y

    # ==============================================================
    # MOUSE DRAGGING (Click and move anywhere!)
    # ==============================================================
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
            # Magnetic snap to top if dropped near screen top (within 50px)
            screen = self.get_active_screen()
            geom = screen.geometry()
            top_threshold = 70 if geom.top() == 0 else (geom.top() + 50)
            if self.pos().y() <= top_threshold:
                # Snap to centered top
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

    # ==============================================================
    # HOVER ANIMATIONS
    # ==============================================================
    def enterEvent(self, event):
        self.collapse_timer.stop()
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
        make_window_topmost(int(self.winId()))
        if getattr(self, "is_chat_mode", True) and hasattr(self, "chat_input"):
            QTimer.singleShot(140, self.chat_input.setFocus)

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
        make_window_topmost(int(self.winId()))
        if getattr(self, "is_chat_mode", True) and hasattr(self, "chat_input"):
            QTimer.singleShot(140, self.chat_input.setFocus)

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

        radius = "16px" if self.is_expanded else "13px"

        self.container.setStyleSheet(f"""
            QFrame#IslandContainer {{
                background-color: #11100F;
                border: 1px solid {border_color};
                border-radius: {radius};
            }}
        """)

    # ==============================================================
    # 1. COMPACT DROPLET (118x26 px) WITH LIVE ANIMATED ROBO
    # ==============================================================
    def create_pill_widget(self):
        w = QWidget()
        w.setCursor(Qt.CursorShape.SizeAllCursor)
        w.setFixedHeight(self.COLLAPSED_H)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(6, 0, 8, 0)
        layout.setSpacing(6)

        # 1. Live Animated Robo with Emotions (20px)
        self.pill_robo = LiveAnimatedRobo(size=20)
        self.pill_robo.setFixedSize(20, 20)
        self.pill_robo.mousePressEvent = self.on_robo_poke
        self.pill_robo.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.pill_robo)

        # 2. Glowing Status Dot
        self.pill_dot = QLabel("●")
        self.pill_dot.setStyleSheet("color: #30D158; font-size: 8px;")
        layout.addWidget(self.pill_dot)

        # 3. Status text
        self.pill_text = QLabel("Antigravity")
        self.pill_text.setStyleSheet("color: #B5B1AA; font-size: 10px; font-weight: 600;")
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

        # Top Bar: Home, ScreenClip, Win+V Clipboard, Drag Grip, Volume, Pin, Collapse
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 0, 4, 0)
        top_bar.setSpacing(8)

        # Tools: Screen Ask, Screenshot, Clipboard, Switch Project
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

        self.btn_chat_toggle = QPushButton("💬 Чат")
        self.btn_chat_toggle.setFixedHeight(22)
        self.btn_chat_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_chat_toggle.setToolTip("Общаться с Antigravity прямо через остров!")
        self.btn_chat_toggle.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                font-size: 10px;
                font-weight: 600;
                border-radius: 4px;
                padding: 0 6px;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.18); }
        """)
        self.btn_chat_toggle.clicked.connect(self.toggle_chat_mode)

        top_bar.addWidget(self.btn_home)
        top_bar.addWidget(self.btn_clip)
        top_bar.addWidget(self.btn_clipboard)
        top_bar.addWidget(self.btn_chat_toggle)

        self.btn_center_top = QPushButton("🎯")
        self.btn_center_top.setFixedSize(22, 22)
        self.btn_center_top.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_center_top.setToolTip("Выставить по центру вверху активного экрана")
        self.btn_center_top.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        self.btn_center_top.clicked.connect(self.reset_position)
        top_bar.addWidget(self.btn_center_top)

        top_bar.addStretch()

        # Center Drag grip
        drag_hint = QLabel("⋮⋮")
        drag_hint.setToolTip("Зажмите левую кнопку мыши, чтобы двигать остров!")
        drag_hint.setCursor(Qt.CursorShape.SizeAllCursor)
        drag_hint.setStyleSheet("color: rgba(255, 255, 255, 0.35); font-size: 13px; font-weight: bold;")
        top_bar.addWidget(drag_hint)

        top_bar.addStretch()

        # Pin button 📌
        self.btn_pin = QPushButton("📌")
        self.btn_pin.setFixedSize(22, 22)
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.setToolTip("Закрепить (не сворачивать)")
        self.btn_pin.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        self.btn_pin.clicked.connect(self.toggle_pin)
        top_bar.addWidget(self.btn_pin)

        # Volume toggle 🔊
        self.btn_sound = self.create_icon_btn("volume.svg", "Sound chimes", self.toggle_sound)
        top_bar.addWidget(self.btn_sound)

        # Collapse chevron ⌃
        self.btn_collapse = QPushButton("⌃")
        self.btn_collapse.setFixedSize(22, 22)
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.setToolTip("Свернуть в микро-капельку")
        self.btn_collapse.setStyleSheet("background: transparent; color: #8E8A83; font-size: 15px; border: none;")
        self.btn_collapse.clicked.connect(self.manual_collapse)
        top_bar.addWidget(self.btn_collapse)

        vbox.addLayout(top_bar)

        # Two Columns
        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(10)

        # Left Column: AI Agent & Chat Card (60%)
        self.agent_card = self.create_agent_card()
        content_row.addWidget(self.agent_card, stretch=6)

        # Right Column: Universal Audio & Tools 2x2 Grid (40%)
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
    # LEFT COLUMN: AGENT & CHAT CARD
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
        hlayout.setContentsMargins(10, 10, 10, 10)
        hlayout.setSpacing(10)

        # Mascot Robo (Live Animated!)
        robo_col = QVBoxLayout()
        robo_col.setContentsMargins(0, 0, 0, 0)
        robo_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.robo_widget = LiveAnimatedRobo(size=64)
        self.robo_widget.mousePressEvent = self.on_robo_poke
        robo_col.addWidget(self.robo_widget)
        hlayout.addLayout(robo_col)

        # Details Column
        details_col = QVBoxLayout()
        details_col.setContentsMargins(0, 0, 0, 0)
        details_col.setSpacing(4)

        # Row 1: Dot + Project + Agent + Step
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(6)

        self.ai_dot = QLabel("●")
        self.ai_dot.setStyleSheet("color: #30D158; font-size: 11px;")
        row1.addWidget(self.ai_dot)

        self.project_label = QLabel(self.project_name)
        self.project_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700;")
        row1.addWidget(self.project_label)

        self.agent_label = QLabel(self.agent_name)
        self.agent_label.setStyleSheet("color: #8E8A83; font-size: 11px; font-weight: 500;")
        row1.addWidget(self.agent_label)

        row1.addStretch()

        self.step_label = QLabel(self.step_counter)
        self.step_label.setStyleSheet("color: #726E68; font-size: 11px; font-weight: 600;")
        row1.addWidget(self.step_label)

        details_col.addLayout(row1)

        # Subtitle Action
        self.action_label = QLabel(self.action_text)
        self.action_label.setStyleSheet("color: #E6E2DB; font-size: 12px; font-weight: 600;")
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

        # VIEW 0: Chat with Antigravity / AI (PRIMARY & DEFAULT!)
        chat_view = QFrame()
        chat_view.setStyleSheet("""
            QFrame {
                background: #0E0D0C;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 9px;
            }
        """)
        chat_layout = QVBoxLayout(chat_view)
        chat_layout.setContentsMargins(8, 6, 8, 6)
        chat_layout.setSpacing(4)

        self.chat_display = QLabel("💬 Окно Antigravity готово. Напишите задачу или вопрос:")
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
                padding: 4px 8px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QLineEdit:focus {
                border: 1px solid #D9653B;
            }
        """)
        self.chat_input.returnPressed.connect(self.on_send_chat)

        btn_send = QPushButton("↵ Отправить")
        btn_send.setFixedHeight(24)
        btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send.setStyleSheet("""
            QPushButton {
                background: #D9653B;
                color: #FFFFFF;
                font-size: 10px;
                font-weight: 700;
                border-radius: 6px;
                padding: 0 10px;
                border: none;
            }
            QPushButton:hover { background: #E8754B; }
        """)
        btn_send.clicked.connect(self.on_send_chat)

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
        code_layout.setContentsMargins(8, 6, 8, 6)
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

        # Approval Buttons (Allow / Deny)
        self.approval_buttons_row = QHBoxLayout()
        self.approval_buttons_row.setContentsMargins(0, 4, 0, 0)
        self.approval_buttons_row.setSpacing(8)

        self.card_deny_btn = QPushButton("Deny")
        self.card_deny_btn.setFixedSize(70, 22)
        self.card_deny_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.card_deny_btn.setStyleSheet("""
            QPushButton {
                background: #262421;
                color: #CFCBC4;
                font-size: 11px;
                font-weight: 600;
                border-radius: 11px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover { background: #35332F; }
        """)
        self.card_deny_btn.clicked.connect(lambda: self.submit_decision("deny"))

        self.card_allow_btn = QPushButton("Allow")
        self.card_allow_btn.setFixedSize(74, 22)
        self.card_allow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.card_allow_btn.setStyleSheet("""
            QPushButton {
                background: #C8F08F;
                color: #1A2E05;
                font-size: 11px;
                font-weight: 700;
                border-radius: 11px;
                border: none;
            }
            QPushButton:hover { background: #DCF5B0; }
        """)
        self.card_allow_btn.clicked.connect(lambda: self.submit_decision("allow"))

        self.approval_buttons_row.addWidget(self.card_deny_btn)
        self.approval_buttons_row.addWidget(self.card_allow_btn)
        self.approval_buttons_row.addStretch()

        self.approval_buttons_widget = QWidget()
        self.approval_buttons_widget.setLayout(self.approval_buttons_row)
        self.approval_buttons_widget.setVisible(False)
        code_layout.addWidget(self.approval_buttons_widget)

        # Add to stack: Chat is 0, Diff is 1
        self.agent_content_stack.addWidget(chat_view)
        self.agent_content_stack.addWidget(diff_view)

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
        grid.setSpacing(6)

        # Tile 1: Universal Audio (Yandex.Music, Spotify, Browser, VK)
        card_audio = QFrame()
        card_audio.setStyleSheet("background: #181715; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px;")
        v_aud = QVBoxLayout(card_audio)
        v_aud.setContentsMargins(8, 6, 8, 6)
        v_aud.setSpacing(4)

        head = QHBoxLayout()
        icon = QSvgWidget(os.path.join(ASSETS_DIR, "spotify.svg"))
        icon.setFixedSize(18, 18)
        head.addWidget(icon)
        self.lbl_audio = QLabel("Аудио / Музыка")
        self.lbl_audio.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 700;")
        head.addWidget(self.lbl_audio)
        head.addStretch()
        v_aud.addLayout(head)

        # Media Control Buttons
        m_row = QHBoxLayout()
        m_row.setSpacing(4)
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
        v_tim.setContentsMargins(8, 6, 8, 6)
        v_tim.setSpacing(4)

        thead = QHBoxLayout()
        f_svg = QSvgWidget(os.path.join(ASSETS_DIR, "focus.svg"))
        f_svg.setFixedSize(16, 16)
        thead.addWidget(f_svg)
        self.lbl_timer = QLabel("05:00")
        self.lbl_timer.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 800;")
        thead.addWidget(self.lbl_timer)
        thead.addStretch()
        v_tim.addLayout(thead)

        t_row = QHBoxLayout()
        t_row.setSpacing(4)
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
        v_clk.setContentsMargins(10, 6, 10, 6)
        v_clk.setSpacing(1)
        v_clk.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_clock_time = QLabel("16:30")
        self.lbl_clock_time.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 800;")
        v_clk.addWidget(self.lbl_clock_time)

        self.lbl_clock_date = QLabel("Wed 4 Nov")
        self.lbl_clock_date.setStyleSheet("color: #8C8881; font-size: 9px; font-weight: 500;")
        v_clk.addWidget(self.lbl_clock_date)

        line = QFrame()
        line.setFixedHeight(2)
        line.setFixedWidth(20)
        line.setStyleSheet("background: #5078E6; border-radius: 1px;")
        v_clk.addWidget(line)

        grid.addWidget(card_clock, 1, 0)

        # Tile 4: Fast Tools & Settings
        card_tools = QFrame()
        card_tools.setStyleSheet("background: #181715; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px;")
        v_tools = QVBoxLayout(card_tools)
        v_tools.setContentsMargins(8, 6, 8, 6)
        v_tools.setSpacing(4)

        t_title = QLabel("Быстрые действия")
        t_title.setStyleSheet("color: #FFFFFF; font-size: 10px; font-weight: 700;")
        v_tools.addWidget(t_title)

        tool_row = QHBoxLayout()
        tool_row.setSpacing(4)
        btn_center = self.create_tiny_btn("📍 Центр", self.reset_position)
        btn_agent = self.create_tiny_btn("🤖 Агент", self.cycle_agent)
        tool_row.addWidget(btn_center)
        tool_row.addWidget(btn_agent)
        v_tools.addLayout(tool_row)

        grid.addWidget(card_tools, 1, 1)

        return w

    def create_tiny_btn(self, text, callback):
        btn = QPushButton(text)
        btn.setFixedHeight(20)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                font-size: 10px;
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

    def switch_tab(self, idx):
        if hasattr(self, 'tab_chat_btn') and hasattr(self, 'tab_diff_btn'):
            if idx == 0:
                self.tab_chat_btn.setStyleSheet("""
                    QPushButton {
                        background: #D9653B;
                        color: #FFFFFF;
                        font-size: 10px;
                        font-weight: 700;
                        border-radius: 4px;
                        padding: 0 8px;
                        border: none;
                    }
                """)
                self.tab_diff_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08);
                        color: #A09D98;
                        font-size: 10px;
                        font-weight: 500;
                        border-radius: 4px;
                        padding: 0 8px;
                        border: none;
                    }
                    QPushButton:hover { background: rgba(255, 255, 255, 0.14); }
                """)
                self.is_chat_mode = True
                self.agent_content_stack.setCurrentIndex(0)
                QTimer.singleShot(60, self.chat_input.setFocus)
            else:
                self.tab_chat_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08);
                        color: #A09D98;
                        font-size: 10px;
                        font-weight: 500;
                        border-radius: 4px;
                        padding: 0 8px;
                        border: none;
                    }
                    QPushButton:hover { background: rgba(255, 255, 255, 0.14); }
                """)
                self.tab_diff_btn.setStyleSheet("""
                    QPushButton {
                        background: #5078E6;
                        color: #FFFFFF;
                        font-size: 10px;
                        font-weight: 700;
                        border-radius: 4px;
                        padding: 0 8px;
                        border: none;
                    }
                """)
                self.is_chat_mode = False
                self.agent_content_stack.setCurrentIndex(1)

    # ==============================================================
    # INTERACTIONS
    # ==============================================================
    def on_robo_poke(self, event):
        play_chime("click")
        emotions = ["wink", "dizzy", "heart", "curious", "reading", "thinking", "music"]
        self.emotion_idx = (self.emotion_idx + 1) % len(emotions)
        m = emotions[self.emotion_idx]
        self.robo_widget.set_mode(m)
        self.pill_robo.set_mode(m)

    def on_audio_play_pause(self):
        send_vk(VK_MEDIA_PLAY_PAUSE)
        self.robo_widget.set_mode("music")
        self.pill_robo.set_mode("music")
        self.lbl_audio.setText("Playing / Paused")

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

    def on_screenshot_clicked(self):
        play_chime("click")
        # Briefly collapse to not block screen, then trigger snipping tool
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

    def toggle_chat_mode(self):
        play_chime("click")
        self.is_chat_mode = not self.is_chat_mode
        self.agent_content_stack.setCurrentIndex(1 if self.is_chat_mode else 0)
        self.btn_chat_toggle.setText("Дифф" if self.is_chat_mode else "💬 Чат")

    def on_send_chat(self):
        query = self.chat_input.text().strip()
        if not query:
            return
        play_chime("click")
        self.chat_input.clear()
        self.chat_display.setText(f"Вы: {query}\n\nAntigravity: Передаю задачу агенту...")
        self.robo_widget.set_mode("thinking")
        self.pill_robo.set_mode("thinking")

        def transmit_thread():
            try:
                # 1. Copy query to clipboard
                clip = QApplication.clipboard()
                clip.setText(query)

                # 2. Find Antigravity window HWND
                hwnds = []
                def enum_cb(hwnd, extra):
                    if user32.IsWindowVisible(hwnd):
                        buf = ctypes.create_unicode_buffer(512)
                        user32.GetWindowTextW(hwnd, buf, 512)
                        title = buf.value
                        if "antigravity" in title.lower():
                            hwnds.append(hwnd)
                        else:
                            pid = ctypes.c_ulong()
                            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                            try:
                                p = psutil.Process(pid.value)
                                if "antigravity" in p.name().lower():
                                    hwnds.append(hwnd)
                            except:
                                pass
                    return True

                user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)(enum_cb), 0)

                if hwnds:
                    target_hwnd = hwnds[0]
                    user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
                    user32.SetForegroundWindow(target_hwnd)
                    time.sleep(0.25)
                    # Paste Ctrl+V
                    user32.keybd_event(0x11, 0, 0, 0)
                    user32.keybd_event(0x56, 0, 0, 0)
                    user32.keybd_event(0x56, 0, 2, 0)
                    user32.keybd_event(0x11, 0, 2, 0)
                    time.sleep(0.08)
                    # Enter
                    user32.keybd_event(0x0D, 0, 0, 0)
                    user32.keybd_event(0x0D, 0, 2, 0)

                    ans = f"Вы: {query}\n\n✅ Успешно передано в Antigravity! Задача запущена."
                else:
                    ans = f"Вы: {query}\n\n⚠️ Скопировано в буфер. Вставьте в окно Antigravity (Ctrl+V)."
                bridge.user_chat_response.emit(ans)
            except Exception as e:
                bridge.user_chat_response.emit(f"Вы: {query}\n\n⚠️ Ошибка: {e}")

        threading.Thread(target=transmit_thread, daemon=True).start()

    def on_chat_response(self, text):
        self.chat_display.setText(text)
        self.robo_widget.set_mode("done")
        self.pill_robo.set_mode("done")
        if self.sound_enabled:
            play_chime("success")

    def on_screen_ask(self):
        play_chime("click")
        self.robo_widget.set_mode("reading")
        self.action_label.setText("Robo сканирует экран...")
        QTimer.singleShot(1800, lambda: [
            self.action_label.setText("Robo наблюдает за Antigravity"),
            self.robo_widget.set_mode("idle")
        ])

    def cycle_agent(self):
        play_chime("click")
        agents = ["Antigravity", "Claude Code", "OpenAI Codex"]
        try:
            curr = agents.index(self.agent_name)
            self.agent_name = agents[(curr + 1) % len(agents)]
        except Exception:
            self.agent_name = "Antigravity"
        self.agent_label.setText(self.agent_name)
        self.action_label.setText(f"Connected to {self.agent_name}")

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
        self.step_counter = data.get("step", self.step_counter)

        diff = data.get("diff", {})
        if isinstance(diff, dict):
            self.diff_del = diff.get("del", self.diff_del)
            self.diff_add = diff.get("add", self.diff_add)

        # Update pill
        self.pill_dot.setStyleSheet("color: #FF8C00; font-size: 8px;")
        self.pill_text.setText(f"{self.project_name}: {self.action_text}")
        self.pill_allow_btn.setVisible(False)
        self.pill_deny_btn.setVisible(False)

        # Emotive robot mode
        self.robo_widget.set_mode(mode)
        self.pill_robo.set_mode(mode)

        # Update card
        self.ai_dot.setStyleSheet("color: #FF8C00; font-size: 11px;")
        self.project_label.setText(self.project_name)
        self.agent_label.setText(self.agent_name)
        self.step_label.setText(self.step_counter)
        self.action_label.setText(f"🔄 {self.action_text}")
        self.code_file_label.setText(self.file_name)
        self.code_del_label.setText(self.diff_del)
        self.code_add_label.setText(self.diff_add)
        self.code_del_label.setVisible(True)
        self.code_add_label.setVisible(True)
        self.approval_buttons_widget.setVisible(False)

        if data.get("expand", False):
            self.expand()
        elif not self.is_expanded:
            self.collapse()

    def on_agent_ask(self, data):
        self.current_state = "ask"
        self.agent_name = data.get("agent", self.agent_name)
        self.ask_prompt = data.get("question", data.get("prompt", "Allow action?"))
        cmd = data.get("command", "")

        if self.sound_enabled:
            play_chime("alert")

        self.pill_dot.setStyleSheet("color: #FFA500; font-size: 8px;")
        self.pill_text.setText(f"Allow: {self.ask_prompt}?")
        self.pill_allow_btn.setVisible(True)
        self.pill_deny_btn.setVisible(True)

        self.robo_widget.set_mode("curious")
        self.pill_robo.set_mode("curious")

        self.ai_dot.setStyleSheet("color: #FFA500; font-size: 11px;")
        self.action_label.setText(f"❓ {self.ask_prompt}")
        self.code_file_label.setText("Permission required")
        self.code_del_label.setText(f"$ {cmd}" if cmd else self.ask_prompt)
        self.code_del_label.setStyleSheet("color: #FFA500; background: rgba(255, 165, 0, 0.1); font-family: monospace; font-size: 10px; padding: 2px;")
        self.code_add_label.setVisible(False)
        self.approval_buttons_widget.setVisible(True)

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
            self.robo_widget.set_mode("heart")
            self.pill_robo.set_mode("heart")
        else:
            self.current_state = "idle"
            play_chime("click")
            self.pill_text.setText("Denied")
            self.action_label.setText("🚫 Denied")
            self.robo_widget.set_mode("idle")
            self.pill_robo.set_mode("idle")

        self.pill_allow_btn.setVisible(False)
        self.pill_deny_btn.setVisible(False)
        self.approval_buttons_widget.setVisible(False)
        self.update_style()
        QTimer.singleShot(1800, self.collapse)

    def on_agent_done(self, data):
        self.current_state = "done"
        msg = data.get("message", "Task complete!")

        if self.sound_enabled:
            play_chime("celebrate")

        self.pill_dot.setStyleSheet("color: #30D158; font-size: 8px;")
        self.pill_text.setText(f"Done: {msg}")
        self.pill_allow_btn.setVisible(False)
        self.pill_deny_btn.setVisible(False)

        self.robo_widget.set_mode("done")
        self.pill_robo.set_mode("done")

        self.ai_dot.setStyleSheet("color: #30D158; font-size: 11px;")
        self.action_label.setText("🎉 ГОТОВО! РЕЗУЛЬТАТ ВЫПОЛНЕН")
        self.code_file_label.setText("Status: 100% Operational")
        self.code_del_label.setText(msg)
        self.code_del_label.setStyleSheet("color: #30D158; background: rgba(48, 209, 88, 0.12); font-family: 'Segoe UI', monospace; font-size: 11px; padding: 6px; border-radius: 6px;")
        self.code_add_label.setVisible(False)
        self.approval_buttons_widget.setVisible(False)

        # Smoothly expand so user instantly sees the live result banner
        self.expand()
        self.update_style()
        QTimer.singleShot(7500, self.reset_to_idle)

    def reset_to_idle(self):
        self.current_state = "idle"
        self.pill_dot.setStyleSheet("color: #30D158; font-size: 8px;")
        self.pill_text.setText("")
        self.action_label.setText(f"Waiting for {self.agent_name}...")
        self.robo_widget.set_mode("idle")
        self.pill_robo.set_mode("idle")
        if not self.is_pinned:
            self.collapse()
        self.pill_dot.setStyleSheet("color: #30D158; font-size: 8px;")
        self.pill_text.setText("")
        self.action_label.setText(f"Waiting for {self.agent_name}...")
        self.robo_widget.set_mode("idle")
        self.pill_robo.set_mode("idle")
        self.update_style()
        if not self.is_expanded:
            self.collapse()

    # ==============================================================
    # SYSTEM TRAY
    # ==============================================================
    def setup_tray_icon(self):
        self.tray = QSystemTrayIcon(self)
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#D9653B"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(4, 10, 24, 12, 6, 6)
        p.end()

        self.tray.setIcon(QIcon(pix))
        self.tray.setToolTip("TwoCode Dynamic Island")

        menu = QMenu()
        act_toggle = menu.addAction("Показать / Скрыть остров")
        act_toggle.triggered.connect(lambda: self.collapse() if self.is_expanded else self.expand())

        menu.addSeparator()
        act_clip = menu.addAction("✂️ Скриншот области")
        act_clip.triggered.connect(self.on_screenshot_clicked)

        act_clip_v = menu.addAction("📋 Буфер обмена (Win+V)")
        act_clip_v.triggered.connect(self.on_clipboard_clicked)

        menu.addSeparator()
        act_reset = menu.addAction("Сбросить позицию по центру")
        act_reset.triggered.connect(self.reset_position)

        act_exit = menu.addAction("Выход")
        act_exit.triggered.connect(QApplication.instance().quit)

        self.tray.setContextMenu(menu)
        self.tray.show()


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    island = TwoCodeIsland()
    bridge.user_chat_response.connect(island.on_chat_response)

    # Start IPC HTTP Server
    start_ipc_server()

    # Start Real Antigravity Transcript Watcher
    start_antigravity_watcher()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
