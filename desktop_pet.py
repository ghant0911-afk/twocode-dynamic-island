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

    def __init__(self, parent=None, size=130):
        super().__init__(parent)
        self.setWindowTitle("TwoCode Desktop Robo")

        # Window Flags for desktop pet
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self.pet_size = size
        self.setFixedSize(self.pet_size, self.pet_size + 40)

        # Mascot Appearance & Wardrobe
        self.has_headphones = False
        self.forced_music = False
        self.state = self.STATE_IDLE
        self.facing_direction = 1  # 1 = Right, -1 = Left

        # Animation Ticks & Kinematics
        self.anim_tick = 0
        self.walk_phase = 0.0
        self.walk_speed = 2.0
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
        self.ai_timer = QTimer(self)
        self.ai_timer.setInterval(4000)
        self.ai_timer.timeout.connect(self._ai_decide_next_action)

        # Optimized 30 FPS Physics & Render Loop (33ms) - buttery smooth and 0% CPU
        self.loop_timer = QTimer(self)
        self.loop_timer.setInterval(33)
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
        if is_playing and self.state == self.STATE_IDLE:
            if random.random() < 0.6:
                self.state = self.STATE_DANCE
        elif not is_playing and self.state == self.STATE_DANCE:
            self.state = self.STATE_IDLE

    def set_forced_headphones(self, enabled: bool):
        self.forced_music = enabled
        self.has_headphones = enabled
        if enabled and self.state == self.STATE_IDLE:
            self.state = self.STATE_DANCE

    def _ai_decide_next_action(self):
        if self.state in [self.STATE_PICKED_UP, self.STATE_FALLING, self.STATE_CELEBRATE]:
            return

        # If music is playing, prefer dancing or groovy strolling
        if self.has_headphones:
            choices = [self.STATE_DANCE, self.STATE_WALK, self.STATE_DANCE, self.STATE_IDLE]
            self.state = random.choice(choices)
            if self.state == self.STATE_WALK:
                self.facing_direction = random.choice([-1, 1])
            self.ai_timer.setInterval(random.randint(3000, 6000))
            return

        # Regular state choices
        r = random.random()
        if r < 0.45:
            self.state = self.STATE_WALK
            self.facing_direction = random.choice([-1, 1])
            self.ai_timer.setInterval(random.randint(4000, 8000))
        elif r < 0.80:
            self.state = self.STATE_IDLE
            self.ai_timer.setInterval(random.randint(3000, 6000))
        else:
            self.state = self.STATE_SIT
            self.ai_timer.setInterval(random.randint(4000, 7000))

    def setVisible(self, visible: bool):
        super().setVisible(visible)
        if visible:
            if not self.loop_timer.isActive():
                self.loop_timer.start(33)
            if not self.ai_timer.isActive():
                self.ai_timer.start(4000)
        else:
            self.loop_timer.stop()
            self.ai_timer.stop()

    def _physics_step(self):
        if not self.isVisible():
            return

        self.anim_tick += 1

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

        # Handle States
        if self.state == self.STATE_PICKED_UP:
            self.dangle_phase += 0.25
            self.update()
            return

        elif self.state == self.STATE_FALLING:
            self.vy += self.gravity
            new_y = int(self.y() + self.vy)
            if new_y >= self.floor_y:
                new_y = self.floor_y
                self.vy = 0
                self.state = self.STATE_IDLE
                self.spawn_hearts(3)
            if new_y != self.y():
                self.move(self.x(), new_y)
            self.update()
            return

        elif self.state == self.STATE_WALK:
            self.walk_phase += 0.20
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
            if self.anim_tick % 20 == 0:
                self.spawn_note()

        elif self.state == self.STATE_CELEBRATE:
            # Jumping celebration
            if self.anim_tick % 15 == 0:
                self.spawn_hearts(2)
            if self.anim_tick > 80:
                self.state = self.STATE_IDLE

        need_paint = (
            self.state in [self.STATE_WALK, self.STATE_DANCE, self.STATE_PICKED_UP, self.STATE_FALLING, self.STATE_CELEBRATE]
            or self.is_blinking
            or len(self.particles) > 0
        )
        if need_paint:
            self.update()

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
            if self.y() < self.floor_y:
                self.state = self.STATE_FALLING
                self.vy = 0
            else:
                self.move(self.x(), self.floor_y)
                self.state = self.STATE_IDLE
                self.spawn_hearts(2)
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

        # Music Headphones Toggle
        act_music = QAction("🎧 Наушники: Вкл" if not self.has_headphones else "🎧 Снять наушники", self)
        act_music.triggered.connect(lambda: self.set_forced_headphones(not self.has_headphones))
        menu.addAction(act_music)

        # Walk Action
        act_walk = QAction("🚶 Гулять по экрану", self)
        act_walk.triggered.connect(lambda: self._set_manual_state(self.STATE_WALK))
        menu.addAction(act_walk)

        # Dance Action
        act_dance = QAction("🕺 Танцевать под бит", self)
        act_dance.triggered.connect(lambda: self._set_manual_state(self.STATE_DANCE))
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

    def _set_manual_state(self, new_state):
        self.state = new_state
        if new_state == self.STATE_DANCE:
            self.has_headphones = True

    # -------------------------------------------------------------------------
    # Paint Event: Authentic Vector TwoCode Full-Body Mascot
    # -------------------------------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        s = w / 120.0

        p.save()
        # Origin centered at chest
        p.translate(w / 2.0, h / 2.0 - 10 * s)

        # Facing direction flip (horizontal scale)
        p.scale(self.facing_direction, 1.0)

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

        elif self.state == self.STATE_DANCE or (self.has_headphones and self.state == self.STATE_IDLE):
            dance_t = self.anim_tick * 0.18
            walk_bob = abs(math.sin(dance_t)) * 4.5 * s
            arm_l_angle = math.sin(dance_t) * 20.0
            arm_r_angle = -math.sin(dance_t) * 20.0
            string_sway = math.sin(dance_t) * 5.0
            head_tilt = math.sin(dance_t * 0.5) * 8.0
            head_bob = math.cos(dance_t) * 2.0 * s

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
        # 4. TwoCode Robot Head (with optional Headphones)
        # -------------------------------------------------------------
        p.save()
        p.translate(0, -18 * s + head_bob)
        p.rotate(head_tilt)

        # Ear Pods
        p.setBrush(QBrush(QColor('#E2E8F0')))
        p.setPen(QPen(QColor('#CBD5E1'), max(1, int(1.2 * s))))
        p.drawRoundedRect(QRectF(-26.5 * s, -6 * s, 5.5 * s, 13 * s), 2.5 * s, 2.5 * s)
        p.drawRoundedRect(QRectF(21.0 * s, -6 * s, 5.5 * s, 13 * s), 2.5 * s, 2.5 * s)

        # Curved Antenna
        ant_path = QPainterPath()
        ant_path.moveTo(0, -17 * s)
        ant_path.cubicTo(0, -22 * s, 1.5 * s, -25 * s, 1.0 * s, -28 * s)
        p.setPen(QPen(QColor('#E2E8F0'), max(1, int(2.4 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(ant_path)

        # Antenna Glowing Orb
        orb_center = QPointF(1.0 * s, -29 * s)
        orb_col = QColor('#1DB954') if self.has_headphones else QColor('#5CE07A')
        p.setBrush(QBrush(orb_col))
        p.setPen(QPen(QColor('#FFFFFF'), max(1, int(0.8 * s))))
        p.drawEllipse(orb_center, 3.8 * s, 3.8 * s)

        # Head Body
        head_grad = QLinearGradient(0, -18 * s, 0, 18 * s)
        head_grad.setColorAt(0.0, QColor('#FFFFFF'))
        head_grad.setColorAt(0.65, QColor('#F8FAFC'))
        head_grad.setColorAt(1.0, QColor('#E2E8F0'))
        p.setBrush(QBrush(head_grad))
        p.setPen(QPen(QColor('#CBD5E1'), max(1, int(1.2 * s))))
        p.drawRoundedRect(QRectF(-23 * s, -17 * s, 46 * s, 35 * s), 16 * s, 16 * s)

        # Dark Visor
        visor_rect = QRectF(-18 * s, -11 * s, 36 * s, 24 * s)
        v_grad = QLinearGradient(0, -11 * s, 0, 13 * s)
        v_grad.setColorAt(0.0, QColor('#181820'))
        v_grad.setColorAt(1.0, QColor('#0D0D12'))
        p.setBrush(QBrush(v_grad))
        p.setPen(QPen(QColor('#252530'), max(1, int(0.8 * s))))
        p.drawRoundedRect(visor_rect, 10 * s, 10 * s)

        # Visor Upper Glass Reflection
        p.setBrush(QColor(255, 255, 255, 32))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(-12 * s, -9.5 * s, 24 * s, 4 * s), 2 * s, 2 * s)

        # Visor Eyes Rendering based on state
        if self.state in [self.STATE_PICKED_UP, self.STATE_FALLING]:
            # Surprised wide eyes O O
            p.setBrush(QColor('#5CE07A'))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-14 * s, -6 * s, 9 * s, 10 * s))
            p.drawEllipse(QRectF(5 * s, -6 * s, 9 * s, 10 * s))
            p.setBrush(QColor('#FFFFFF'))
            p.drawEllipse(QRectF(-11.5 * s, -4 * s, 3.5 * s, 3.5 * s))
            p.drawEllipse(QRectF(7.5 * s, -4 * s, 3.5 * s, 3.5 * s))

        elif self.has_headphones or self.state == self.STATE_DANCE:
            # Happy closed music eyes ^ ^ + pink blush
            p.setPen(QPen(QColor('#1DB954'), max(1, int(2.4 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(-14 * s, -7 * s, 8 * s, 6 * s), 20 * 16, 140 * 16)
            p.drawArc(QRectF(6 * s, -7 * s, 8 * s, 6 * s), 20 * 16, 140 * 16)
            # Music blush
            p.setBrush(QColor(255, 80, 150, 150))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-15.5 * s, 1.0 * s, 4.5 * s, 3.5 * s))
            p.drawEllipse(QRectF(11.0 * s, 1.0 * s, 4.5 * s, 3.5 * s))

        elif self.state == self.STATE_SIT:
            # Relaxed sleepy eyes - -
            p.setPen(QPen(QColor('#5CE07A'), max(1, int(2.2 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(-13 * s), int(-1 * s), int(-6 * s), int(-1 * s))
            p.drawLine(int(6 * s), int(-1 * s), int(13 * s), int(-1 * s))

        elif self.is_blinking:
            # Blinking closed line eyes
            p.setPen(QPen(QColor('#5CE07A'), max(1, int(2.0 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(-13 * s), int(-1 * s), int(-6 * s), int(-1 * s))
            p.drawLine(int(6 * s), int(-1 * s), int(13 * s), int(-1 * s))

        else:
            # Normal TwoCode oval emerald eyes with pupil gleam
            p.setBrush(QColor('#5CE07A'))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(-13.5 * s, -6 * s, 8 * s, 10 * s), 3.5 * s, 3.5 * s)
            p.drawRoundedRect(QRectF(5.5 * s, -6 * s, 8 * s, 10 * s), 3.5 * s, 3.5 * s)
            p.setBrush(QColor('#FFFFFF'))
            p.drawEllipse(QRectF(-11.5 * s, -4.5 * s, 2.5 * s, 2.5 * s))
            p.drawEllipse(QRectF(7.5 * s, -4.5 * s, 2.5 * s, 2.5 * s))

        # -------------------------------------------------------------
        # 5. Over-Ear Headphones (If music is playing or forced)
        # -------------------------------------------------------------
        if self.has_headphones:
            hp_band_col = QColor('#181A20')
            hp_cup_col = QColor('#252834')
            hp_glow_col = QColor('#1DB954')  # Spotify green ring

            # Headband Arch over top of head
            band_path = QPainterPath()
            band_path.moveTo(-24 * s, -5 * s)
            band_path.cubicTo(-25 * s, -24 * s, 25 * s, -24 * s, 24 * s, -5 * s)
            p.setPen(QPen(hp_band_col, max(2, int(4.5 * s)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(band_path)

            # Left Headphone Cup
            p.setBrush(QBrush(hp_cup_col))
            p.setPen(QPen(hp_glow_col, max(1, int(1.8 * s))))
            p.drawRoundedRect(QRectF(-29.5 * s, -8 * s, 7.5 * s, 17 * s), 3.5 * s, 3.5 * s)
            # Left cup glowing center ring
            p.setBrush(QBrush(hp_glow_col))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-28 * s, -2.5 * s, 4.5 * s, 6 * s))

            # Right Headphone Cup
            p.setBrush(QBrush(hp_cup_col))
            p.setPen(QPen(hp_glow_col, max(1, int(1.8 * s))))
            p.drawRoundedRect(QRectF(22.0 * s, -8 * s, 7.5 * s, 17 * s), 3.5 * s, 3.5 * s)
            # Right cup glowing center ring
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
