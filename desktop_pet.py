try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    WEBENGINE_AVAILABLE = True
except Exception:
    WEBENGINE_AVAILABLE = False
from PyQt6.QtCore import QUrl, QEvent

import os
import sys
import math
import random

from PyQt6.QtWidgets import (
    QApplication, QWidget, QMenu
)
from PyQt6.QtCore import (
    Qt, QPoint, QPointF, QRectF, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient, QRadialGradient,
    QCursor, QAction
)

# -------------------------------------------------------------------------
# Pure Vector Shapes (Heart, Single Note, Double Note)
# -------------------------------------------------------------------------
def draw_vector_heart(p: QPainter, cx: float, cy: float, r: float, color: QColor):
    p.save()
    p.setBrush(QBrush(color))
    p.setPen(Qt.PenStyle.NoPen)
    path = QPainterPath()
    path.moveTo(cx, cy + r * 0.8)
    path.cubicTo(cx - r * 1.3, cy - r * 0.2, cx - r * 0.9, cy - r * 1.3, cx, cy - r * 0.3)
    path.cubicTo(cx + r * 0.9, cy - r * 1.3, cx + r * 1.3, cy - r * 0.2, cx, cy + r * 0.8)
    p.drawPath(path)
    p.restore()

def draw_vector_note(p: QPainter, x: float, y: float, size: float, color: QColor):
    p.save()
    p.translate(x, y)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Note head (tilted oval)
    p.save()
    p.rotate(-25)
    p.setBrush(QBrush(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(-size * 0.6, -size * 0.45, size * 1.2, size * 0.9))
    p.restore()
    # Stem
    p.setPen(QPen(color, max(1.5, size * 0.32), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(size * 0.45, 0), QPointF(size * 0.45, -size * 2.2))
    # Flag
    flag_path = QPainterPath()
    flag_path.moveTo(size * 0.45, -size * 2.2)
    flag_path.cubicTo(size * 1.2, -size * 1.9, size * 1.3, -size * 1.1, size * 0.7, -size * 0.7)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(color, max(1.5, size * 0.32), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawPath(flag_path)
    p.restore()


def draw_vector_star(p: QPainter, cx: float, cy: float, r: float, color: QColor):
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(color))
    p.setPen(Qt.PenStyle.NoPen)
    path = QPainterPath()
    points = 4
    for i in range(points * 2):
        rad = r if (i % 2 == 0) else (r * 0.42)
        angle = i * math.pi / points - math.pi / 2
        px = cx + math.cos(angle) * rad
        py = cy + math.sin(angle) * rad
        if i == 0:
            path.moveTo(px, py)
        else:
            path.lineTo(px, py)
    path.closeSubpath()
    p.drawPath(path)
    p.restore()

def draw_vector_double_note(p: QPainter, x: float, y: float, size: float, color: QColor):
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Head 1
    p.save()
    p.translate(x, y)
    p.rotate(-25)
    p.setBrush(QBrush(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(-size * 0.55, -size * 0.4, size * 1.1, size * 0.8))
    p.restore()
    # Head 2
    p.save()
    p.translate(x + size * 1.3, y - size * 0.25)
    p.rotate(-25)
    p.setBrush(QBrush(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(-size * 0.55, -size * 0.4, size * 1.1, size * 0.8))
    p.restore()
    # Stems
    p.setPen(QPen(color, max(1.5, size * 0.28), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(x + size * 0.4, y), QPointF(x + size * 0.4, y - size * 1.9))
    p.drawLine(QPointF(x + size * 1.7, y - size * 0.25), QPointF(x + size * 1.7, y - size * 2.15))
    # Connecting Beam
    p.setPen(QPen(color, max(2.2, size * 0.55), Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
    p.drawLine(QPointF(x + size * 0.4, y - size * 1.8), QPointF(x + size * 1.7, y - size * 2.05))
    p.restore()

# -------------------------------------------------------------------------
# Desktop Robo Pet Widget
# -------------------------------------------------------------------------
VRM_MODELS = [
    ("Sendagaya_Shino.vrm", "Sendagaya Shino (Астра 3D)", "shino"),
    ("Victoria_Rubin.vrm", "Victoria Rubin (Виктория 3D)", "victoria"),
    ("AvatarSample_A.vrm", "Avatar Sample A (3D)", "sample_a"),
    ("AvatarSample_B.vrm", "Avatar Sample B (3D)", "sample_b"),
    ("AvatarSample_C.vrm", "Avatar Sample C (3D)", "sample_c"),
    ("robo", "TwoCode Robo (Робот 2D)", "robo")
]

class DesktopRoboPet(QWidget):
    dismiss_requested = pyqtSignal()
    jump_to_island_requested = pyqtSignal()

    # States
    STATE_IDLE = "idle"
    STATE_WALK = "walk"
    STATE_DANCE = "dance"
    STATE_SIT = "sit"
    STATE_PICKED_UP = "picked_up"
    STATE_FALLING = "falling"
    STATE_CELEBRATE = "celebrate"
    STATE_HURT = "hurt"

    def __init__(self, parent=None, size=260, model="Sendagaya_Shino.vrm"):
        super().__init__(parent)
        self.setWindowTitle("TwoCode Desktop Robo")

        # Window Flags for desktop pet: completely non-activating & never steals focus
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)

        self.pet_size = size
        self.current_vrm_model = model or "Sendagaya_Shino.vrm"
        self.character = "robo" if self.current_vrm_model == "robo" else "shino"
        self.setFixedSize(self.pet_size, int(self.pet_size * 1.45))

        # Mascot Appearance & Wardrobe
        self.has_headphones = False
        self.forced_music = False
        self.state = self.STATE_IDLE
        self.facing_direction = 1  # 1 = Right, -1 = Left
        self.is_speaking = False
        self.speech_tick = 0.0
        # Real 3D VRM Engine View (for Sendagaya Shino / Astra 3D)
        self.vrm_view = None
        if WEBENGINE_AVAILABLE:
            try:
                self.vrm_view = QWebEngineView(self)
                self.vrm_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                if self.vrm_view.focusProxy():
                    self.vrm_view.focusProxy().setFocusPolicy(Qt.FocusPolicy.NoFocus)
                self.vrm_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                self.vrm_view.setStyleSheet("background: transparent;")
                self.vrm_view.page().setBackgroundColor(QColor(0, 0, 0, 0))
                self.vrm_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                self.vrm_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                self.vrm_view.settings().setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
                self.vrm_view.setUrl(QUrl(f"http://127.0.0.1:8098/vrm_pet.html?model={self.current_vrm_model}"))
                self.vrm_view.resize(self.width(), self.height())
                self.vrm_view.installEventFilter(self)
                if self.vrm_view.focusProxy():
                    self.vrm_view.focusProxy().installEventFilter(self)
                if self.character == "robo":
                    self.vrm_view.hide()
                else:
                    self.vrm_view.show()
            except Exception as e:
                print(f"[DesktopPet] VRM WebEngine init note: {e}")
                self.vrm_view = None


        # Animation Ticks & Kinematics
        self.anim_tick = 0
        self.walk_phase = 0.0
        self.walk_speed = 0.75  # Gentle calm natural walking pace (not frantic run)
        self.blink_tick = 0
        self.is_blinking = False
        self.dangle_phase = 0.0

        # Physics
        self.vy = 0.0
        self.gravity = 1.2
        self.floor_y = 600

        # Floating Particles (Notes & Hearts)
        self.particles = []

        # Dragging
        self.dragging = False
        self.drag_offset = QPoint()

        # Behavior AI Timer (State switching)
        self.dance_style = 0
        self.dance_switch_timer = 0
        self.fall_start_y = 0
        self.hurt_timer = 0
        self.squash_factor = 1.0
        self.ai_timer = QTimer(self)
        self.ai_timer.setInterval(4000)
        self.ai_timer.timeout.connect(self._ai_decide_next_action)

        # Silky smooth 60 FPS Physics & Render Loop (16ms)
        self.loop_timer = QTimer(self)
        self.loop_timer.setInterval(16)
        self.loop_timer.timeout.connect(self._physics_step)

        # Spawn at bottom center on primary screen
        self.init_position()

        self.loop_timer.start()
        self.ai_timer.start()

    def init_position(self):
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            self.floor_y = avail.bottom() - self.height() + 8
            start_x = avail.left() + (avail.width() - self.width()) // 2 + 100
            self.move(start_x, self.floor_y)
        else:
            self.floor_y = 700
            self.move(300, self.floor_y)

    def set_music(self, is_playing: bool):
        if self.forced_music:
            return
        self.has_headphones = is_playing
        if is_playing:
            if self.state in [self.STATE_IDLE, self.STATE_SIT, self.STATE_WALK]:
                self.state = self.STATE_DANCE
                self._sync_vrm_state()
        else:
            # Stop drumming immediately when music paused!
            if self.state == self.STATE_DANCE:
                self.state = self.STATE_IDLE
                self._sync_vrm_state()

    def set_forced_headphones(self, enabled: bool):
        self.forced_music = enabled
        self.has_headphones = enabled
        if enabled:
            self.state = self.STATE_DANCE
        else:
            if self.state == self.STATE_DANCE:
                self.state = self.STATE_IDLE
        self._sync_vrm_state()

    def _ai_decide_next_action(self):
        if self.state in [self.STATE_PICKED_UP, self.STATE_FALLING, self.STATE_CELEBRATE, self.STATE_HURT]:
            return

        # If music is playing, rotate between dancing with new styles and walking with headphones
        if self.has_headphones:
            choices = [self.STATE_DANCE, self.STATE_WALK, self.STATE_DANCE]
            self.state = random.choice(choices)
            if self.state == self.STATE_DANCE:
                self.dance_style = random.randint(0, 3)
            elif self.state == self.STATE_WALK:
                self.facing_direction = random.choice([-1, 1])
            self.ai_timer.setInterval(random.randint(3500, 6000))
            return

        # Regular state choices (no floating sit on air)
        r = random.random()
        if r < 0.35:
            self.state = self.STATE_WALK
            self.facing_direction = random.choice([-1, 1])
            self.ai_timer.setInterval(random.randint(4000, 7000))
        else:
            self.state = self.STATE_IDLE
            self.ai_timer.setInterval(random.randint(4500, 8500))

    def showEvent(self, event):
        super().showEvent(event)
        try:
            import ctypes
            hwnd = int(self.winId())
            if hwnd:
                GWL_EXSTYLE = -20
                WS_EX_NOACTIVATE = 0x08000000
                cur = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur | WS_EX_NOACTIVATE)
        except Exception:
            pass

    def setVisible(self, visible: bool):
        super().setVisible(visible)
        if visible:
            if not self.loop_timer.isActive():
                self.loop_timer.start(16)
            if not self.ai_timer.isActive():
                self.ai_timer.start(4000)
        else:
            self.loop_timer.stop()
            self.ai_timer.stop()

    def _physics_step(self):
        if not self.isVisible():
            return

        self.anim_tick += 1

        # Auto-sync state and facing changes to 3D VRM runtime
        if not hasattr(self, '_last_synced_vrm_state'):
            self._last_synced_vrm_state = None
            self._last_synced_facing = None

        curr_facing = getattr(self, 'facing_direction', 1)
        if self._last_synced_vrm_state != self.state or self._last_synced_facing != curr_facing:
            self._last_synced_vrm_state = self.state
            self._last_synced_facing = curr_facing
            self._sync_vrm_state()

        # Periodic Blinking
        if self.anim_tick % 120 == 0:
            self.is_blinking = True
            self.blink_tick = 5
        elif self.is_blinking:
            self.blink_tick -= 1
            if self.blink_tick <= 0:
                self.is_blinking = False

        # Particle management
        self._update_particles()

        # Elastic squash restoration after landing impact
        if hasattr(self, "squash_factor") and self.squash_factor != 1.0:
            self.squash_factor += (1.0 - self.squash_factor) * 0.14
            if abs(self.squash_factor - 1.0) < 0.02:
                self.squash_factor = 1.0

        # Handle States
        if self.state == self.STATE_PICKED_UP:
            self.dangle_phase += 0.25
            self.update()
            return

        elif self.state == self.STATE_HURT:
            self.hurt_timer -= 1
            if self.anim_tick % 18 == 0:
                self.spawn_dizzy_stars(2)
            if self.hurt_timer <= 0:
                self.state = self.STATE_IDLE
                self.squash_factor = 1.0
                self.spawn_hearts(2)

        elif self.state == self.STATE_FALLING:
            self.vy += self.gravity
            new_y = int(self.y() + self.vy)
            if new_y >= self.floor_y:
                new_y = self.floor_y
                fall_dist = self.floor_y - getattr(self, "fall_start_y", self.floor_y)
                impact_speed = self.vy
                self.vy = 0
                if impact_speed > 5.5 or fall_dist > 50:
                    self.trigger_fall_damage(fall_dist, impact_speed)
                else:
                    self.state = self.STATE_IDLE
                    self.spawn_hearts(2)
            if new_y != self.y():
                self.move(self.x(), new_y)
            self.update()
            return

        elif self.state == self.STATE_WALK:
            self.walk_phase += 0.22
            step = int(self.walk_speed * self.facing_direction)
            new_x = self.x() + step

            # Boundary check against screen edges
            screen = QApplication.primaryScreen()
            if screen:
                avail = screen.availableGeometry()
                left_bound = avail.left() + 10
                right_bound = avail.right() - self.width() - 10
                if new_x <= left_bound:
                    new_x = left_bound
                    self.facing_direction = 1
                elif new_x >= right_bound:
                    new_x = right_bound
                    self.facing_direction = -1

            if new_x != self.x():
                self.move(new_x, self.y())

            # Chance of spawning musical note if walking with music
            if self.has_headphones and (self.anim_tick % 25 == 0):
                self.spawn_note()

        elif self.state == self.STATE_DANCE:
            self.walk_phase += 0.25
            self.dance_switch_timer += 1
            if self.dance_switch_timer > 220:  # Switch dance styles smoothly every ~3.5s
                self.dance_switch_timer = 0
                self.dance_style = (self.dance_style + 1) % 4
            if self.anim_tick % 18 == 0:
                self.spawn_note()

        elif self.state == self.STATE_CELEBRATE:
            # Jumping celebration
            if self.anim_tick % 15 == 0:
                self.spawn_hearts(2)
            if self.anim_tick > 80:
                self.state = self.STATE_IDLE

        need_paint = (
            self.state in [self.STATE_WALK, self.STATE_DANCE, self.STATE_PICKED_UP, self.STATE_FALLING, self.STATE_CELEBRATE, self.STATE_HURT]
            or self.is_blinking
            or len(self.particles) > 0
            or getattr(self, "squash_factor", 1.0) != 1.0
        )
        if need_paint:
            self.update()

    def trigger_fall_damage(self, fall_dist, impact_speed):
        self.state = self.STATE_HURT
        self.has_headphones = False
        self.hurt_timer = 180  # ~3 seconds at 60 FPS
        self.squash_factor = 1.45  # Comic cartoon squash on impact
        self.spawn_dizzy_stars(5)

        # Comic impact thud
        try:
            import winsound
            winsound.Beep(180, 70)
            winsound.Beep(130, 80)
        except Exception:
            pass

        # Expressive voice reaction via Baya
        hurt_lines = [
            "Ой-ёй! За что уронили?!",
            "Ай! Осторожнее, я же хрупкая!",
            "Уф... земля оказалась слишком твёрдой!",
            "Осторожнее! Я же твоя Астра, а не мячик!",
            "Ох... звёздочки перед глазами кружатся..."
        ]
        try:
            from voice_engine import VoiceEngine
            VoiceEngine.get().speak(random.choice(hurt_lines))
        except Exception:
            pass

    def spawn_dizzy_stars(self, count=4):
        cx = self.width() / 2.0
        cy = self.height() / 2.0 - 28
        for i in range(count):
            angle = random.uniform(0, math.pi * 2)
            rad = random.uniform(16.0, 25.0)
            self.particles.append({
                "type": "dizzy_star",
                "center_x": cx,
                "center_y": cy,
                "orbit_angle": angle,
                "orbit_radius": rad,
                "speed": random.uniform(0.14, 0.22),
                "alpha": 255,
                "size": random.uniform(5.5, 8.0),
                "color": QColor('#FFD700'),
                "x": cx + math.cos(angle) * rad,
                "y": cy + math.sin(angle) * (rad * 0.38)
            })

    def spawn_note(self):
        cx = self.width() / 2.0 + (22 if self.facing_direction == 1 else -22)
        cy = self.height() / 2.0 - 28
        is_double = (random.random() < 0.45)
        self.particles.append({
            "type": "note",
            "is_double": is_double,
            "x": cx + random.uniform(-6, 6),
            "y": cy,
            "vx": random.uniform(-0.5, 0.5),
            "vy": random.uniform(-1.2, -0.6),
            "alpha": 255,
            "size": random.uniform(4.5, 6.5),
            "color": QColor('#1DB954')
        })

    def spawn_hearts(self, count=3):
        cx = self.width() / 2.0
        cy = self.height() / 2.0 - 20
        for _ in range(count):
            self.particles.append({
                "type": "heart",
                "x": cx + random.uniform(-15, 15),
                "y": cy + random.uniform(-5, 5),
                "vx": random.uniform(-0.8, 0.8),
                "vy": random.uniform(-1.5, -0.8),
                "alpha": 255,
                "r": random.uniform(4.0, 7.0),
                "color": QColor(255, 60, 130)
            })

    def _update_particles(self):
        for p in self.particles:
            if p.get("type") == "dizzy_star":
                p["orbit_angle"] += p["speed"]
                p["x"] = p["center_x"] + math.cos(p["orbit_angle"]) * p["orbit_radius"]
                p["y"] = p["center_y"] + math.sin(p["orbit_angle"]) * (p["orbit_radius"] * 0.38)
                p["alpha"] = max(0, p["alpha"] - 4)
            else:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["alpha"] = max(0, p["alpha"] - 6)
        self.particles = [p for p in self.particles if p["alpha"] > 0]

    # -------------------------------------------------------------------------
    # Mouse Interactivity
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.state = self.STATE_PICKED_UP
            self.hurt_timer = 0
            self.squash_factor = 1.0
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            new_pos = event.globalPosition().toPoint() - self.drag_offset
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            # Check if dropped in mid-air
            if self.y() < self.floor_y - 20:
                self.state = self.STATE_FALLING
                self.fall_start_y = self.y()
                self.vy = 0
            else:
                self.move(self.x(), self.floor_y)
                self.state = self.STATE_IDLE
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.state = self.STATE_CELEBRATE
            self.anim_tick = 0
            self.spawn_hearts(5)
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #16181F;
                color: #FFFFFF;
                border: 1px solid #2B2F3E;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
            }
            QMenu::item {
                padding: 6px 18px 6px 10px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #262A38;
                color: #5CE07A;
            }
            QMenu::separator {
                height: 1px;
                background: #252834;
                margin: 4px 6px;
            }
        """)

        # 3D Model Selection Submenu
        model_menu = menu.addMenu("🎭 Выбрать модель маскота")
        for m_file, m_label, m_id in VRM_MODELS:
            is_active = (getattr(self, "current_vrm_model", "") == m_file if m_file != "robo" else self.character == "robo")
            prefix = "✓ " if is_active else "   "
            act_m = model_menu.addAction(f"{prefix}{m_label}")
            act_m.triggered.connect(lambda chk, mf=m_file: self.set_vrm_model(mf))

        # 3D VRM Viewer in browser
        act_vrm = QAction("🌐 Открыть 3D VRM в браузере", self)
        act_vrm.triggered.connect(lambda: self.open_vrm_viewer())
        menu.addAction(act_vrm)

        menu.addSeparator()

        # Music Headphones Toggle
        act_music = QAction("🎧 Наушники: Вкл" if not self.has_headphones else "🎧 Снять наушники", self)
        act_music.triggered.connect(lambda: self.set_forced_headphones(not self.has_headphones))
        menu.addAction(act_music)

        # Walk Action
        act_walk = QAction("🚶 Гулять по экрану", self)
        act_walk.triggered.connect(lambda: self._set_manual_state(self.STATE_WALK))
        menu.addAction(act_walk)

        # Talk Action
        act_talk = QAction("💬 Поговорить с Астрой...", self)
        act_talk.triggered.connect(self.open_talk_dialog)
        menu.addAction(act_talk)

        # Wave Action
        act_wave = QAction("👋 Помахать рукой (Привет!)", self)
        act_wave.triggered.connect(self.react_to_click)
        menu.addAction(act_wave)

        # Drumming / Music Action
        act_drums = QAction("🥁 Играть на барабанах" if self.state != self.STATE_DANCE else "⏹️ Остановить барабаны", self)
        act_drums.triggered.connect(lambda: self._set_manual_state(self.STATE_DANCE if self.state != self.STATE_DANCE else self.STATE_IDLE))
        menu.addAction(act_drums)

        # Dance Action
        act_dance = QAction("💃 Сменить танец", self)
        act_dance.triggered.connect(lambda: self.vrm_view.page().runJavaScript("window.cycleDance && window.cycleDance()"))
        menu.addAction(act_dance)

        # Sit Action
        act_sit = QAction("🪑 Сесть отдохнуть", self)
        act_sit.triggered.connect(lambda: self._set_manual_state(self.STATE_SIT))
        menu.addAction(act_sit)

        menu.addSeparator()

        # Jump back to Island
        act_island = QAction("🏝️ Вернуться в Dynamic Island", self)
        act_island.triggered.connect(self.jump_to_island_requested.emit)
        menu.addAction(act_island)

        # Hide
        act_hide = QAction("❌ Спрятать маскота", self)
        act_hide.triggered.connect(self.dismiss_requested.emit)
        menu.addAction(act_hide)

        menu.exec(event.globalPos())

    def set_vrm_model(self, model_file):
        self.current_vrm_model = model_file
        if not model_file or model_file == "robo":
            self.set_character("robo")
            if hasattr(self, 'vrm_view') and self.vrm_view:
                self.vrm_view.hide()
            self.update()
            return

        self.character = "shino"
        if hasattr(self, 'vrm_view') and self.vrm_view:
            self.vrm_view.show()
            self.vrm_view.page().runJavaScript(f"window.switchVRMModel && window.switchVRMModel('{model_file}')")
            self._sync_vrm_state()
        self.update()

    def set_character(self, char_name):
        self.character = char_name
        if hasattr(self, 'vrm_view') and self.vrm_view:
            if self.character == "shino":
                self.vrm_view.show()
                self._sync_vrm_state()
            else:
                self.vrm_view.hide()
        self.update()

    def open_vrm_viewer(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:8098/vrm_viewer.html")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'vrm_view') and self.vrm_view:
            self.vrm_view.resize(self.size())

    def react_to_click(self):
        """Cute interactive reaction when the user clicks Astra"""
        self.spawn_hearts(3)
        if hasattr(self, 'vrm_view') and self.vrm_view:
            self.vrm_view.page().runJavaScript("window.setPetState && window.setPetState('wave')")
        
        greetings = [
            "Привет! Я тут, рядом с тобой ✨",
            "Слушаю тебя! Чем помочь?",
            "Я на связи! Всё под контролем 💖",
            "Какая хорошая музыка сегодня 🎵",
            "Рада тебя видеть! Как настроение?"
        ]
        try:
            import random
            from voice_engine import VoiceEngine
            VoiceEngine.get().speak(random.choice(greetings))
        except Exception:
            pass

    def open_talk_dialog(self):
        """Opens quick interactive speech dialog with Astra"""
        try:
            from PyQt6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self, "Чат с Астрой", "О чём хочешь поговорить с Астрой?")
            if ok and text.strip():
                def _worker():
                    try:
                        from deepseek_brain import DeepSeekBrain
                        from voice_engine import VoiceEngine
                        resp, _ = DeepSeekBrain.get().ask(text.strip())
                        VoiceEngine.get().speak(resp)
                    except Exception as e:
                        print(f"[AstraTalk] error: {e}")
                import threading
                threading.Thread(target=_worker, daemon=True).start()
        except Exception as e:
            print(f"[AstraTalk] Dialog error: {e}")

    def eventFilter(self, watched, event):
        if hasattr(self, 'vrm_view') and self.vrm_view and (watched == self.vrm_view or watched == self.vrm_view.focusProxy()):
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.dragging = False
                    self.drag_start_pos = event.globalPosition().toPoint()
                    self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    return True
                elif event.button() == Qt.MouseButton.RightButton:
                    self.contextMenuEvent(event)
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if (event.buttons() & Qt.MouseButton.LeftButton) and hasattr(self, 'drag_start_pos'):
                    if not self.dragging and (event.globalPosition().toPoint() - self.drag_start_pos).manhattanLength() > 6:
                        self.dragging = True
                        self.state = self.STATE_PICKED_UP
                        self.hurt_timer = 0
                        self.squash_factor = 1.0
                        self._sync_vrm_state()
                    if self.dragging:
                        self.move(event.globalPosition().toPoint() - self.drag_offset)
                        return True
                elif hasattr(self, 'vrm_view') and self.vrm_view:
                    norm_x = (event.position().x() / max(1, self.width())) * 2.0 - 1.0
                    norm_y = (event.position().y() / max(1, self.height())) * 2.0 - 1.0
                    self.vrm_view.page().runJavaScript(f"window.setLookAt && window.setLookAt({norm_x:.2f}, {norm_y:.2f})")
            elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if self.dragging:
                    self.dragging = False
                    if self.y() < self.floor_y - 20:
                        self.state = self.STATE_FALLING
                        self.fall_start_y = self.y()
                        self.vy = 0
                    else:
                        self.move(self.x(), self.floor_y)
                        self.state = self.STATE_IDLE
                    self._sync_vrm_state()
                    return True
                else:
                    self.react_to_click()
                    return True
            elif event.type() == QEvent.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
                self.state = self.STATE_CELEBRATE
                self.spawn_hearts(5)
                self._sync_vrm_state()
                return True
        return super().eventFilter(watched, event)

    def _sync_vrm_state(self):
        if hasattr(self, 'vrm_view') and self.vrm_view and self.character == "shino":
            facing = getattr(self, 'facing_direction', 1)
            self.vrm_view.page().runJavaScript(f"window.setPetState && window.setPetState('{self.state}', {facing})")

    def _sync_vrm_talking(self, talking):
        if hasattr(self, 'vrm_view') and self.vrm_view and self.character == "shino":
            self.vrm_view.page().runJavaScript(f"window.setTalking && window.setTalking({str(talking).lower()})")

    def _set_manual_state(self, new_state):
        self.state = new_state
        if new_state == self.STATE_DANCE:
            self.has_headphones = True
        self._sync_vrm_state()

    # -------------------------------------------------------------------------
    # Paint Event: Authentic Vector TwoCode Full-Body Mascot
    # -------------------------------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # -------------------------------------------------------------
        # Real 3D VRM Mode: If Sendagaya Shino 3D VRM is active, show WebEngine view
        # -------------------------------------------------------------
        if getattr(self, 'character', 'shino') == 'shino' and hasattr(self, 'vrm_view') and self.vrm_view:
            if not self.vrm_view.isVisible():
                self.vrm_view.show()
                self._sync_vrm_state()
            # Draw floating vector particles (hearts, notes, orbit stars) over 3D model
            for pt in self.particles:
                if pt["type"] == "note":
                    col = QColor(pt["color"])
                    col.setAlpha(pt["alpha"])
                    if pt.get("is_double", False):
                        draw_vector_double_note(p, pt["x"], pt["y"], pt["size"] * 1.15, col)
                    else:
                        draw_vector_note(p, pt["x"], pt["y"], pt["size"] * 1.15, col)
                elif pt["type"] == "dizzy_star":
                    col = QColor(pt["color"])
                    col.setAlpha(pt["alpha"])
                    draw_vector_star(p, pt["x"], pt["y"], pt["size"], col)
                elif pt["type"] == "heart":
                    col = QColor(pt["color"])
                    col.setAlpha(pt["alpha"])
                    draw_vector_heart(p, pt["x"], pt["y"], pt["r"], col)
            return

        if hasattr(self, 'vrm_view') and self.vrm_view and self.vrm_view.isVisible():
            self.vrm_view.hide()

        w = self.width()
        h = self.height()
        s = w / 120.0

        p.save()
        # Origin centered at chest
        p.translate(w / 2.0, h / 2.0 - 10 * s)

        # Facing direction flip (horizontal scale)
        squash = getattr(self, "squash_factor", 1.0)
        p.scale(self.facing_direction * squash, (1.0 / squash) if squash != 0 else 1.0)

        # Kinematics based on state
        leg_l_angle = 0.0
        leg_r_angle = 0.0
        arm_l_angle = 0.0
        arm_r_angle = 0.0
        walk_bob = 0.0
        string_sway = 0.0
        head_bob = 0.0
        head_tilt = 0.0

        if self.state == self.STATE_WALK:
            walk_bob = abs(math.sin(self.walk_phase * 2.0)) * 3.5 * s
            leg_l_angle = math.sin(self.walk_phase) * 28.0
            leg_r_angle = -math.sin(self.walk_phase) * 28.0
            arm_l_angle = -math.sin(self.walk_phase) * 24.0
            arm_r_angle = math.sin(self.walk_phase) * 24.0
            string_sway = math.sin(self.walk_phase) * 6.0
            head_bob = math.cos(self.walk_phase * 2.0) * 1.0 * s

        elif self.state == self.STATE_DANCE:
            dance_t = self.anim_tick * 0.20
            style = getattr(self, "dance_style", 0)

            if style == 0:
                # Style 0: Breakbeat / Electro Popping & Stomping
                walk_bob = abs(math.sin(dance_t)) * 5.0 * s
                arm_l_angle = math.sin(dance_t) * 38.0
                arm_r_angle = -math.sin(dance_t) * 38.0
                leg_l_angle = math.sin(dance_t) * 16.0
                leg_r_angle = -math.sin(dance_t) * 16.0
                head_tilt = math.sin(dance_t * 0.5) * 10.0
                head_bob = math.cos(dance_t) * 2.5 * s
                string_sway = math.sin(dance_t) * 6.0

            elif style == 1:
                # Style 1: DJ Head-Bop & Sky Pump
                walk_bob = abs(math.sin(dance_t * 1.4)) * 3.5 * s
                arm_l_angle = -75.0 + math.sin(dance_t) * 8.0  # hand on headphone
                arm_r_angle = -60.0 - abs(math.sin(dance_t * 2.0)) * 28.0  # sky pump
                head_tilt = math.sin(dance_t * 0.7) * 7.0
                head_bob = (math.sin(dance_t * 1.4) + 1.0) * 3.0 * s
                string_sway = math.sin(dance_t * 1.4) * 8.0

            elif style == 2:
                # Style 2: Shuffle Kick / Side-to-Side Hopping
                walk_bob = abs(math.sin(dance_t * 1.8)) * 6.5 * s
                leg_l_angle = math.sin(dance_t * 1.8) * 28.0
                leg_r_angle = -math.sin(dance_t * 1.8) * 28.0
                arm_l_angle = -leg_l_angle * 1.1
                arm_r_angle = -leg_r_angle * 1.1
                head_tilt = math.sin(dance_t * 0.9) * 12.0
                head_bob = math.cos(dance_t * 1.8) * 2.0 * s
                string_sway = math.sin(dance_t * 1.8) * 10.0

            else:
                # Style 3: Torso Twist & Rave Wave
                walk_bob = abs(math.cos(dance_t * 1.2)) * 3.5 * s
                arm_l_angle = math.sin(dance_t * 1.2) * 40.0
                arm_r_angle = math.sin(dance_t * 1.2) * 40.0
                leg_l_angle = math.sin(dance_t * 1.2) * 12.0
                leg_r_angle = math.sin(dance_t * 1.2) * 12.0
                head_tilt = math.sin(dance_t * 1.2) * 9.0
                head_bob = 1.5 * s
                string_sway = math.sin(dance_t * 1.2) * 12.0

        elif self.state == self.STATE_HURT:
            # Comic dizzy sprawling with wobbly head shake
            walk_bob = 9.0 * s
            leg_l_angle = 65.0
            leg_r_angle = 65.0
            arm_l_angle = 45.0 + math.sin(self.anim_tick * 0.25) * 10.0
            arm_r_angle = 45.0 - math.sin(self.anim_tick * 0.25) * 10.0
            head_tilt = math.sin(self.anim_tick * 0.30) * 14.0
            head_bob = math.cos(self.anim_tick * 0.30) * 2.0 * s
            string_sway = math.sin(self.anim_tick * 0.30) * 5.0

        elif self.state == self.STATE_PICKED_UP:
            walk_bob = 0.0
            # Dangling legs and waving arms
            leg_l_angle = math.sin(self.dangle_phase) * 22.0
            leg_r_angle = math.cos(self.dangle_phase) * 22.0
            arm_l_angle = -35.0 + math.sin(self.dangle_phase * 1.5) * 15.0
            arm_r_angle = -35.0 - math.cos(self.dangle_phase * 1.5) * 15.0
            string_sway = math.sin(self.dangle_phase) * 10.0

        elif self.state == self.STATE_FALLING:
            walk_bob = 0.0
            arm_l_angle = -50.0
            arm_r_angle = -50.0
            leg_l_angle = 15.0
            leg_r_angle = -15.0

        elif self.state == self.STATE_SIT:
            walk_bob = 8.0 * s
            leg_l_angle = 70.0
            leg_r_angle = 70.0
            arm_l_angle = 10.0
            arm_r_angle = 10.0
            head_bob = 2.0 * s

        elif self.state == self.STATE_IDLE:
            # Subtle breathing
            breath = math.sin(self.anim_tick * 0.06) * 1.5 * s
            walk_bob = breath
            head_bob = breath * 0.6
            arm_l_angle = math.sin(self.anim_tick * 0.06) * 3.0
            arm_r_angle = -math.sin(self.anim_tick * 0.06) * 3.0

        p.translate(0, -walk_bob)

        # -------------------------------------------------------------
        # 1. Soft Shadow Underneath
        # -------------------------------------------------------------
        if self.state not in [self.STATE_PICKED_UP, self.STATE_FALLING]:
            p.save()
            p.setBrush(QColor(0, 0, 0, 45))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-26 * s, 48 * s + walk_bob, 52 * s, 10 * s))
            p.restore()

        # -------------------------------------------------------------
        # 2. Legs & Pants (Штаны / Joggers) & Sneakers
        # -------------------------------------------------------------
        pants_color = QColor('#272935')  # Stylish dark techwear joggers
        pants_cuff = QColor('#1E202B')
        shoe_white = QColor('#FFFFFF')
        shoe_sole = QColor('#00F0FF')   # Neon cyan sole highlight

        # Left Leg
        p.save()
        p.translate(-9 * s, 26 * s)
        p.rotate(leg_l_angle)
        p.setBrush(QBrush(pants_color))
        p.setPen(QPen(QColor('#1A1B24'), max(1, int(1.2 * s))))
        p.drawRoundedRect(QRectF(-5 * s, 0, 10 * s, 18 * s), 4 * s, 4 * s)
        p.setBrush(QBrush(pants_cuff))
        p.drawRoundedRect(QRectF(-5.5 * s, 15 * s, 11 * s, 4 * s), 2 * s, 2 * s)
        p.setBrush(QBrush(shoe_white))
        p.setPen(QPen(QColor('#CBD5E1'), max(1, int(1.0 * s))))
        p.drawRoundedRect(QRectF(-7 * s, 18 * s, 15 * s, 9 * s), 4 * s, 4 * s)
        p.setBrush(QBrush(shoe_sole))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(-7 * s, 25 * s, 15 * s, 3 * s), 1.5 * s, 1.5 * s)
        p.restore()

        # Right Leg
        p.save()
        p.translate(9 * s, 26 * s)
        p.rotate(leg_r_angle)
        p.setBrush(QBrush(pants_color))
        p.setPen(QPen(QColor('#1A1B24'), max(1, int(1.2 * s))))
        p.drawRoundedRect(QRectF(-5 * s, 0, 10 * s, 18 * s), 4 * s, 4 * s)
        p.setBrush(QBrush(pants_cuff))
        p.drawRoundedRect(QRectF(-5.5 * s, 15 * s, 11 * s, 4 * s), 2 * s, 2 * s)
        p.setBrush(QBrush(shoe_white))
        p.setPen(QPen(QColor('#CBD5E1'), max(1, int(1.0 * s))))
        p.drawRoundedRect(QRectF(-6 * s, 18 * s, 15 * s, 9 * s), 4 * s, 4 * s)
        p.setBrush(QBrush(shoe_sole))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(-6 * s, 25 * s, 15 * s, 3 * s), 1.5 * s, 1.5 * s)
        p.restore()

        # -------------------------------------------------------------
        # 3. Torso & Hoodie / Кофта (Стильное ярко-красное худи)
        # -------------------------------------------------------------
        hoodie_color = QColor('#E11D48')   # Vibrant Techwear Crimson Red
        hoodie_shadow = QColor('#9F1239')  # Deep rich red shadow
        hoodie_pocket = QColor('#BE123C')  # Rich ruby pocket

        # Left Arm (Behind torso)
        p.save()
        p.translate(-20 * s, 6 * s)
        p.rotate(arm_l_angle)
        p.setBrush(QBrush(hoodie_color))
        p.setPen(QPen(hoodie_shadow, max(1, int(1.2 * s))))
        p.drawRoundedRect(QRectF(-4 * s, 0, 8 * s, 18 * s), 4 * s, 4 * s)
        p.setBrush(QBrush(QColor('#FFFFFF')))
        p.setPen(QPen(QColor('#CBD5E1'), max(1, int(1.0 * s))))
        p.drawEllipse(QRectF(-4.5 * s, 16 * s, 9 * s, 9 * s))
        p.restore()

        # Sendagaya Shino Back Hair (flowing blonde strands behind torso)
        hair_sway = math.sin(self.anim_tick * 0.08) * 4.0
        if getattr(self, 'character', 'shino') == 'shino':
            p.save()
            p.translate(0, -16 * s + head_bob)
            p.rotate(head_tilt * 0.5)
            hair_back_grad = QLinearGradient(0, -10 * s, 0, 34 * s)
            hair_back_grad.setColorAt(0.0, QColor('#FEF08A'))
            hair_back_grad.setColorAt(0.55, QColor('#FDE047'))
            hair_back_grad.setColorAt(1.0, QColor('#D97706'))
            p.setBrush(QBrush(hair_back_grad))
            p.setPen(Qt.PenStyle.NoPen)
            back_hair_l = QPainterPath()
            back_hair_l.moveTo(-18 * s, -2 * s)
            back_hair_l.cubicTo(-28 * s + hair_sway, 12 * s, -25 * s + hair_sway * 1.5, 32 * s, -14 * s + hair_sway, 36 * s)
            back_hair_l.cubicTo(-19 * s, 25 * s, -17 * s, 12 * s, -12 * s, 2 * s)
            p.drawPath(back_hair_l)
            back_hair_r = QPainterPath()
            back_hair_r.moveTo(18 * s, -2 * s)
            back_hair_r.cubicTo(28 * s + hair_sway, 12 * s, 25 * s + hair_sway * 1.5, 32 * s, 14 * s + hair_sway, 36 * s)
            back_hair_r.cubicTo(19 * s, 25 * s, 17 * s, 12 * s, 12 * s, 2 * s)
            p.drawPath(back_hair_r)
            p.restore()

        # Main Hoodie Torso
        hoodie_grad = QLinearGradient(0, -2 * s, 0, 28 * s)
        hoodie_grad.setColorAt(0.0, QColor('#F43F5E'))  # Bright scarlet highlight
        hoodie_grad.setColorAt(0.35, QColor('#E11D48')) # Pure rich red
        hoodie_grad.setColorAt(1.0, QColor('#9F1239'))  # Deep shadow red
        p.setBrush(QBrush(hoodie_grad))
        p.setPen(QPen(hoodie_shadow, max(1, int(1.5 * s))))
        p.drawRoundedRect(QRectF(-18 * s, -2 * s, 36 * s, 30 * s), 10 * s, 10 * s)

        # Kangaroo Pocket in Front
        p.setBrush(QBrush(hoodie_pocket))
        p.setPen(QPen(QColor('#881337'), max(1, int(1.0 * s))))
        p.drawRoundedRect(QRectF(-12 * s, 13 * s, 24 * s, 12 * s), 5 * s, 5 * s)

        # Hoodie Collar / Neckband
        p.setBrush(QBrush(QColor('#881337')))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(-11 * s, -3 * s, 22 * s, 5 * s), 2.5 * s, 2.5 * s)

        # Hoodie Drawstrings (pure white with physics sway)
        p.setPen(QPen(QColor('#FFFFFF'), max(1, int(1.6 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(int(-5 * s), int(0 * s), int((-6 + string_sway * 0.3) * s), int(12 * s))
        p.drawLine(int(5 * s), int(0 * s), int((4 + string_sway * 0.3) * s), int(11 * s))

        # Right Arm (In front of torso)
        p.save()
        p.translate(20 * s, 6 * s)
        p.rotate(arm_r_angle)
        p.setBrush(QBrush(hoodie_color))
        p.setPen(QPen(hoodie_shadow, max(1, int(1.2 * s))))
        p.drawRoundedRect(QRectF(-4 * s, 0, 8 * s, 18 * s), 4 * s, 4 * s)
        p.setBrush(QBrush(QColor('#FFFFFF')))
        p.setPen(QPen(QColor('#CBD5E1'), max(1, int(1.0 * s))))
        p.drawEllipse(QRectF(-4.5 * s, 16 * s, 9 * s, 9 * s))
        p.restore()

        # -------------------------------------------------------------
        # 4. Companion Head (Sendagaya Shino 3D VRM / TwoCode Robot)
        # -------------------------------------------------------------
        p.save()
        p.translate(0, -18 * s + head_bob)
        p.rotate(head_tilt)

        if getattr(self, 'character', 'shino') == 'shino':
            # === SENDAGAYA SHINO (ASTRA 3D VRM AVATAR) ===
            # Neck
            p.setBrush(QBrush(QColor('#FCE7F3')))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(QRectF(-4 * s, 8 * s, 8 * s, 6 * s))

            # Face base (smooth cute anime head with chin taper)
            face_path = QPainterPath()
            face_path.moveTo(-19 * s, -12 * s)
            face_path.cubicTo(-21 * s, 2 * s, -17 * s, 14 * s, 0, 18 * s)
            face_path.cubicTo(17 * s, 14 * s, 21 * s, 2 * s, 19 * s, -12 * s)
            face_path.cubicTo(15 * s, -22 * s, -15 * s, -22 * s, -19 * s, -12 * s)

            face_grad = QLinearGradient(0, -18 * s, 0, 18 * s)
            face_grad.setColorAt(0.0, QColor('#FFF7ED'))
            face_grad.setColorAt(0.7, QColor('#FFEAE2'))
            face_grad.setColorAt(1.0, QColor('#FED7AA'))
            p.setBrush(QBrush(face_grad))
            p.setPen(QPen(QColor('#FBCFE8'), max(1, int(1.0 * s))))
            p.drawPath(face_path)

            # Warm Cheeks Blush
            p.setBrush(QColor(255, 130, 160, 120))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-16 * s, 2 * s, 7 * s, 4 * s))
            p.drawEllipse(QRectF(9 * s, 2 * s, 7 * s, 4 * s))

            # Eyes based on state
            if self.state == self.STATE_HURT:
                # Comic dizzy spiral eyes @ @
                p.setPen(QPen(QColor('#D97706'), max(1, int(2.2 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                rot = self.anim_tick * 0.16
                for offset_x in [-9.5 * s, 9.5 * s]:
                    for stp in range(3):
                        angle_start = int((rot + stp * 1.8) * 180 / math.pi) % 360
                        rad = (2.0 + stp * 2.0) * s
                        p.drawArc(QRectF(offset_x - rad, -2.0 * s - rad, rad * 2, rad * 2), angle_start * 16, 120 * 16)
                p.setBrush(QColor(96, 165, 250, 140))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(-15.5 * s, 1.5 * s, 5.0 * s, 3.5 * s))
                p.drawEllipse(QRectF(10.5 * s, 1.5 * s, 5.0 * s, 3.5 * s))
                sw_path = QPainterPath()
                sw_path.moveTo(17 * s, -14 * s)
                sw_path.cubicTo(19 * s, -11 * s, 21 * s, -9 * s, 21 * s, -7 * s)
                sw_path.cubicTo(21 * s, -5 * s, 19 * s, -4 * s, 17 * s, -4 * s)
                sw_path.cubicTo(15 * s, -4 * s, 13 * s, -5 * s, 13 * s, -7 * s)
                sw_path.cubicTo(13 * s, -9 * s, 15 * s, -11 * s, 17 * s, -14 * s)
                p.setBrush(QBrush(QColor('#38BDF8')))
                p.drawPath(sw_path)

            elif self.state in [self.STATE_PICKED_UP, self.STATE_FALLING]:
                # Surprised wide anime eyes (O . O)
                for ex in [-10 * s, 10 * s]:
                    p.setBrush(QBrush(QColor('#FFFFFF')))
                    p.setPen(QPen(QColor('#451A03'), max(1, int(1.2 * s))))
                    p.drawEllipse(QRectF(ex - 4.5 * s, -6 * s, 9 * s, 10 * s))
                    p.setBrush(QBrush(QColor('#D97706')))
                    p.drawEllipse(QRectF(ex - 3.0 * s, -4 * s, 6 * s, 7 * s))
                    p.setBrush(QBrush(QColor('#FFFFFF')))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawEllipse(QRectF(ex - 1.5 * s, -3.5 * s, 2.5 * s, 2.5 * s))
                    p.drawEllipse(QRectF(ex + 0.5 * s, -1.0 * s, 1.2 * s, 1.2 * s))

            elif self.has_headphones and self.state == self.STATE_DANCE:
                # Happy joyful closed eyes ^ ^
                p.setPen(QPen(QColor('#451A03'), max(1, int(2.4 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                path_l = QPainterPath()
                path_l.moveTo(-14 * s, -2 * s)
                path_l.cubicTo(-10 * s, -7 * s, -9 * s, -7 * s, -5 * s, -2 * s)
                p.drawPath(path_l)
                path_r = QPainterPath()
                path_r.moveTo(5 * s, -2 * s)
                path_r.cubicTo(9 * s, -7 * s, 10 * s, -7 * s, 14 * s, -2 * s)
                p.drawPath(path_r)

            elif self.is_blinking:
                p.setPen(QPen(QColor('#451A03'), max(1, int(2.0 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(int(-13 * s), int(-2 * s), int(-6 * s), int(-2 * s))
                p.drawLine(int(6 * s), int(-2 * s), int(13 * s), int(-2 * s))

            else:
                # Normal anime eyes with amber-hazel iris
                for ex, is_left in [(-10 * s, True), (10 * s, False)]:
                    p.setPen(QPen(QColor('#451A03'), max(1, int(2.0 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    lash = QPainterPath()
                    lash.moveTo(ex - 5 * s, -4 * s)
                    lash.cubicTo(ex - 2 * s, -7 * s, ex + 2 * s, -7 * s, ex + 5 * s, -4 * s)
                    p.drawPath(lash)

                    iris_grad = QLinearGradient(ex, -6 * s, ex, 3 * s)
                    iris_grad.setColorAt(0.0, QColor('#78350F'))
                    iris_grad.setColorAt(0.45, QColor('#B45309'))
                    iris_grad.setColorAt(0.85, QColor('#D97706'))
                    iris_grad.setColorAt(1.0, QColor('#F59E0B'))
                    p.setBrush(QBrush(iris_grad))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawRoundedRect(QRectF(ex - 4 * s, -4 * s, 8 * s, 8.5 * s), 4 * s, 4 * s)

                    p.setBrush(QBrush(QColor('#1C1917')))
                    p.drawEllipse(QRectF(ex - 2 * s, -2 * s, 4 * s, 4 * s))

                    p.setBrush(QBrush(QColor('#FFFFFF')))
                    p.drawEllipse(QRectF(ex - 2.5 * s, -3.5 * s, 2.5 * s, 2.5 * s))
                    p.drawEllipse(QRectF(ex + 1.0 * s, 0.5 * s, 1.4 * s, 1.4 * s))

            # Cute Nose
            p.setPen(QPen(QColor('#F472B6'), max(1, int(1.2 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawPoint(QPointF(0, 4 * s))

            # Animated Mouth with Lip-Sync
            if self.state == self.STATE_HURT:
                p.setPen(QPen(QColor('#881337'), max(1, int(1.6 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                m_path = QPainterPath()
                m_path.moveTo(-4 * s, 9 * s)
                m_path.cubicTo(-2 * s, 11 * s, 2 * s, 7 * s, 4 * s, 9 * s)
                p.drawPath(m_path)
            elif self.state in [self.STATE_PICKED_UP, self.STATE_FALLING]:
                p.setBrush(QBrush(QColor('#E11D48')))
                p.setPen(QPen(QColor('#881337'), max(1, int(1.2 * s))))
                p.drawEllipse(QRectF(-2.5 * s, 7.5 * s, 5 * s, 5 * s))
            elif getattr(self, 'is_speaking', False) or (self.state == self.STATE_DANCE and (self.anim_tick % 24 < 12)):
                # Real speech lip-sync visemes
                mouth_open = (math.sin(self.anim_tick * 0.45) + 1.0) * 0.5
                p.setBrush(QBrush(QColor('#F43F5E')))
                p.setPen(QPen(QColor('#881337'), max(1, int(1.2 * s))))
                p.drawEllipse(QRectF(-3.0 * s, 7.5 * s, 6.0 * s, (3.0 + mouth_open * 4.0) * s))
            elif self.state == self.STATE_DANCE:
                p.setBrush(QBrush(QColor('#F43F5E')))
                p.setPen(QPen(QColor('#881337'), max(1, int(1.2 * s))))
                m_path = QPainterPath()
                m_path.moveTo(-4 * s, 8 * s)
                m_path.cubicTo(-2 * s, 12 * s, 2 * s, 12 * s, 4 * s, 8 * s)
                m_path.closeSubpath()
                p.drawPath(m_path)
            else:
                p.setPen(QPen(QColor('#BE185D'), max(1, int(1.5 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                m_path = QPainterPath()
                m_path.moveTo(-3 * s, 8.5 * s)
                m_path.cubicTo(-1 * s, 10.5 * s, 1 * s, 10.5 * s, 3 * s, 8.5 * s)
                p.drawPath(m_path)

            # Sendagaya Shino Blonde Front Bangs
            hair_front_grad = QLinearGradient(0, -22 * s, 0, 8 * s)
            hair_front_grad.setColorAt(0.0, QColor('#FEF08A'))
            hair_front_grad.setColorAt(0.40, QColor('#FDE047'))
            hair_front_grad.setColorAt(1.0, QColor('#D97706'))
            p.setBrush(QBrush(hair_front_grad))
            p.setPen(Qt.PenStyle.NoPen)

            bangs = QPainterPath()
            bangs.moveTo(-20 * s, -12 * s)
            bangs.cubicTo(-18 * s, -24 * s, 18 * s, -24 * s, 20 * s, -12 * s)
            bangs.cubicTo(19 * s, -2 * s, 16 * s + hair_sway * 0.3, 2 * s, 15 * s + hair_sway * 0.4, 7 * s)
            bangs.lineTo(12 * s, -4 * s)
            bangs.cubicTo(10 * s, -1 * s, 6 * s, 0, 4 * s, 2 * s)
            bangs.lineTo(2 * s, -5 * s)
            bangs.cubicTo(0, -1 * s, -2 * s, 0, -4 * s, 2 * s)
            bangs.lineTo(-6 * s, -4 * s)
            bangs.cubicTo(-10 * s, 0, -14 * s + hair_sway * 0.3, 2 * s, -16 * s + hair_sway * 0.4, 7 * s)
            bangs.cubicTo(-18 * s, 0, -19 * s, -6 * s, -20 * s, -12 * s)
            p.drawPath(bangs)

            # Dark Hair Clip
            p.setBrush(QBrush(QColor('#1E1B4B')))
            p.setPen(QPen(QColor('#475569'), max(1, int(0.8 * s))))
            p.drawRoundedRect(QRectF(11 * s, -13 * s, 7 * s, 2.5 * s), 1.2 * s, 1.2 * s)

            # Cyber Cat-Ear Gaming Headphones (RGB glowing)
            if self.has_headphones:
                p.setPen(QPen(QColor('#1E1E24'), max(1, int(3.5 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.setBrush(Qt.BrushStyle.NoBrush)
                band_path = QPainterPath()
                band_path.moveTo(-20 * s, -10 * s)
                band_path.cubicTo(-19 * s, -27 * s, 19 * s, -27 * s, 20 * s, -10 * s)
                p.drawPath(band_path)

                for side, ex in [(-1, -22 * s), (1, 22 * s)]:
                    p.setBrush(QBrush(QColor('#18181B')))
                    p.setPen(QPen(QColor('#27272A'), max(1, int(1.2 * s))))
                    p.drawRoundedRect(QRectF(ex - 3.5 * s, -12 * s, 7 * s, 15 * s), 3.5 * s, 3.5 * s)
                    glow_col = QColor('#00F0FF') if side == -1 else QColor('#FF007F')
                    p.setBrush(QBrush(glow_col))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawEllipse(QRectF(ex - 2 * s, -6 * s, 4 * s, 6 * s))

                for side, ear_x in [(-1, -12 * s), (1, 12 * s)]:
                    ear_path = QPainterPath()
                    ear_path.moveTo(ear_x - 5 * s, -23 * s)
                    ear_path.lineTo(ear_x, -33 * s)
                    ear_path.lineTo(ear_x + 5 * s, -21 * s)
                    ear_path.closeSubpath()
                    p.setBrush(QBrush(QColor('#1E1E24')))
                    p.setPen(QPen(QColor('#27272A'), max(1, int(1.0 * s))))
                    p.drawPath(ear_path)

                    inner_ear = QPainterPath()
                    inner_ear.moveTo(ear_x - 3 * s, -24 * s)
                    inner_ear.lineTo(ear_x, -31 * s)
                    inner_ear.lineTo(ear_x + 3 * s, -22.5 * s)
                    inner_ear.closeSubpath()
                    ear_neon = QColor('#00F0FF') if side == -1 else QColor('#FF007F')
                    p.setBrush(QBrush(ear_neon))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawPath(inner_ear)

        else:
            # === TWOCODE ROBOT HEAD ===
            p.setBrush(QBrush(QColor('#E2E8F0')))
            p.setPen(QPen(QColor('#CBD5E1'), max(1, int(1.2 * s))))
            p.drawRoundedRect(QRectF(-26.5 * s, -6 * s, 5.5 * s, 13 * s), 2.5 * s, 2.5 * s)
            p.drawRoundedRect(QRectF(21.0 * s, -6 * s, 5.5 * s, 13 * s), 2.5 * s, 2.5 * s)

            ant_path = QPainterPath()
            ant_path.moveTo(0, -17 * s)
            ant_path.cubicTo(0, -22 * s, 1.5 * s, -25 * s, 1.0 * s, -28 * s)
            p.setPen(QPen(QColor('#E2E8F0'), max(1, int(2.4 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(ant_path)

            orb_center = QPointF(1.0 * s, -29 * s)
            orb_col = QColor('#1DB954') if self.has_headphones else QColor('#5CE07A')
            p.setBrush(QBrush(orb_col))
            p.setPen(QPen(QColor('#FFFFFF'), max(1, int(0.8 * s))))
            p.drawEllipse(orb_center, 3.8 * s, 3.8 * s)

            head_grad = QLinearGradient(0, -18 * s, 0, 18 * s)
            head_grad.setColorAt(0.0, QColor('#FFFFFF'))
            head_grad.setColorAt(0.65, QColor('#F8FAFC'))
            head_grad.setColorAt(1.0, QColor('#E2E8F0'))
            p.setBrush(QBrush(head_grad))
            p.setPen(QPen(QColor('#CBD5E1'), max(1, int(1.2 * s))))
            p.drawRoundedRect(QRectF(-23 * s, -17 * s, 46 * s, 35 * s), 16 * s, 16 * s)

            visor_rect = QRectF(-18 * s, -11 * s, 36 * s, 24 * s)
            v_grad = QLinearGradient(0, -11 * s, 0, 13 * s)
            v_grad.setColorAt(0.0, QColor('#181820'))
            v_grad.setColorAt(1.0, QColor('#0D0D12'))
            p.setBrush(QBrush(v_grad))
            p.setPen(QPen(QColor('#252530'), max(1, int(0.8 * s))))
            p.drawRoundedRect(visor_rect, 10 * s, 10 * s)

            p.setBrush(QColor(255, 255, 255, 32))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(-12 * s, -9.5 * s, 24 * s, 4 * s), 2 * s, 2 * s)

            if self.state in [self.STATE_PICKED_UP, self.STATE_FALLING]:
                p.setBrush(QColor('#5CE07A'))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(-14 * s, -6 * s, 9 * s, 10 * s))
                p.drawEllipse(QRectF(5 * s, -6 * s, 9 * s, 10 * s))
                p.setBrush(QColor('#FFFFFF'))
                p.drawEllipse(QRectF(-11.5 * s, -4 * s, 3.5 * s, 3.5 * s))
                p.drawEllipse(QRectF(7.5 * s, -4 * s, 3.5 * s, 3.5 * s))
            elif self.state == self.STATE_HURT:
                p.setPen(QPen(QColor('#FFD700'), max(1, int(2.4 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                rot = self.anim_tick * 0.16
                for offset_x in [-9.5 * s, 9.5 * s]:
                    for stp in range(3):
                        angle_start = int((rot + stp * 1.8) * 180 / math.pi) % 360
                        rad = (2.2 + stp * 2.2) * s
                        p.drawArc(QRectF(offset_x - rad, -1.0 * s - rad, rad * 2, rad * 2), angle_start * 16, 120 * 16)
                p.setBrush(QColor(80, 180, 255, 150))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(-15.5 * s, 1.5 * s, 4.0 * s, 3.0 * s))
                p.drawEllipse(QRectF(11.5 * s, 1.5 * s, 4.0 * s, 3.0 * s))
            elif self.has_headphones and self.state == self.STATE_DANCE:
                p.setPen(QPen(QColor('#1DB954'), max(1, int(2.4 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(QRectF(-14 * s, -7 * s, 8 * s, 6 * s), 20 * 16, 140 * 16)
                p.drawArc(QRectF(6 * s, -7 * s, 8 * s, 6 * s), 20 * 16, 140 * 16)
                p.setBrush(QColor(255, 80, 150, 150))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(-15.5 * s, 1.0 * s, 4.5 * s, 3.5 * s))
                p.drawEllipse(QRectF(11.0 * s, 1.0 * s, 4.5 * s, 3.5 * s))
            elif self.is_blinking:
                p.setPen(QPen(QColor('#5CE07A'), max(1, int(2.0 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(int(-13 * s), int(-1 * s), int(-6 * s), int(-1 * s))
                p.drawLine(int(6 * s), int(-1 * s), int(13 * s), int(-1 * s))
            else:
                p.setBrush(QColor('#5CE07A'))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(QRectF(-13.5 * s, -6 * s, 8 * s, 10 * s), 3.5 * s, 3.5 * s)
                p.drawRoundedRect(QRectF(5.5 * s, -6 * s, 8 * s, 10 * s), 3.5 * s, 3.5 * s)
                p.setBrush(QColor('#FFFFFF'))
                p.drawEllipse(QRectF(-11.5 * s, -4.5 * s, 2.5 * s, 2.5 * s))
                p.drawEllipse(QRectF(7.5 * s, -4.5 * s, 2.5 * s, 2.5 * s))

            if self.has_headphones:
                hp_band_col = QColor('#181A20')
                hp_cup_col = QColor('#252834')
                hp_glow_col = QColor('#1DB954')
                band_path = QPainterPath()
                band_path.moveTo(-24 * s, -5 * s)
                band_path.cubicTo(-25 * s, -24 * s, 25 * s, -24 * s, 24 * s, -5 * s)
                p.setPen(QPen(hp_band_col, max(2, int(4.5 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(band_path)

                p.setBrush(QBrush(hp_cup_col))
                p.setPen(QPen(hp_glow_col, max(1, int(1.8 * s))))
                p.drawRoundedRect(QRectF(-29.5 * s, -8 * s, 7.5 * s, 17 * s), 3.5 * s, 3.5 * s)
                p.setBrush(QBrush(hp_glow_col))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(-28 * s, -2.5 * s, 4.5 * s, 6 * s))

                p.setBrush(QBrush(hp_cup_col))
                p.setPen(QPen(hp_glow_col, max(1, int(1.8 * s))))
                p.drawRoundedRect(QRectF(22.0 * s, -8 * s, 7.5 * s, 17 * s), 3.5 * s, 3.5 * s)
                p.setBrush(QBrush(hp_glow_col))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(23.5 * s, -2.5 * s, 4.5 * s, 6 * s))

        p.restore()  # Restore head
        p.restore()  # Restore origin & flip

        # -------------------------------------------------------------
        # 6. Render Floating Particles (Pure Vector Notes & Hearts)
        # -------------------------------------------------------------
        for pt in self.particles:
            if pt["type"] == "note":
                col = QColor(pt["color"])
                col.setAlpha(pt["alpha"])
                if pt.get("is_double", False):
                    draw_vector_double_note(p, pt["x"], pt["y"], pt["size"] * s, col)
                else:
                    draw_vector_note(p, pt["x"], pt["y"], pt["size"] * s, col)
            elif pt["type"] == "heart":
                col = QColor(pt["color"])
                col.setAlpha(pt["alpha"])
                draw_vector_heart(p, pt["x"], pt["y"], pt["r"] * s, col)
            elif pt["type"] == "dizzy_star":
                col = QColor(pt["color"])
                col.setAlpha(pt["alpha"])
                draw_vector_star(p, pt.get("x", self.width() / 2.0), pt.get("y", self.height() / 2.0 - 28), pt["size"] * s, col)
