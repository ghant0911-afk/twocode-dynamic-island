import sys
import os
import psutil
import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QLabel, QGraphicsOpacityEffect, QFrame,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, QPoint, QRectF, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QCursor
)

try:
    from media_engine import WindowsMediaWatcher
    HAS_MEDIA = True
except Exception:
    HAS_MEDIA = False


class AppleStatusBar(QWidget):
    """
    Apple-Grade Top-Right Transparent Status Bar for Windows.
    - Positioned at Top-Right of the screen.
    - Auto-hides when idle, smoothly appears on hover.
    - Fully transparent liquid glass (Acrylic / Mica feel).
    - Modules: Weather, Seamless Music, PC Telemetry (CPU/RAM/Power), Date & Clock.
    - Audio and Network icons removed by design.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apple Status Bar")

        # Window Flags: non-activating desktop overlay
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

        # Settings
        self.idle_opacity = 0.08
        self.active_opacity = 0.98
        self.is_hovered = False

        # Telemetry State
        self.cpu_pct = 0.0
        self.ram_pct = 0.0
        self.battery_info = None
        self.music_title = "Нет активного трека"
        self.music_artist = ""
        self.is_playing = False
        self.weather_temp = "+2°C"
        self.weather_desc = "Облачно"

        # Opacity Animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(self.active_opacity)
        self.setGraphicsEffect(self.opacity_effect)

        self.anim_opacity = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_opacity.setDuration(220)
        self.anim_opacity.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Auto-hide timer
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(1200)
        self.hide_timer.timeout.connect(self._fade_to_idle)

        # Update Timers
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._update_clock_and_telemetry)
        self.clock_timer.start()

        # Connect to Windows Media Engine
        self.media_watcher = None
        if HAS_MEDIA:
            try:
                self.media_watcher = WindowsMediaWatcher(on_update_callback=self._on_media_update)
            except Exception as e:
                print(f"[AppleStatusBar] Media watcher note: {e}")

        self._build_ui()
        self._reposition_top_right()
        self._update_clock_and_telemetry()

    def _apply_shadow(self, widget):
        sh = QGraphicsDropShadowEffect(widget)
        sh.setColor(QColor(0, 0, 0, 220))
        sh.setBlurRadius(8)
        sh.setOffset(0, 1)
        widget.setGraphicsEffect(sh)

    def _build_ui(self):
        self.setFixedHeight(34)
        self.setMinimumWidth(520)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        # 1. Weather Module
        self.lbl_weather = QLabel(f"⛅ {self.weather_temp}", self)
        self.lbl_weather.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        self._apply_shadow(self.lbl_weather)
        layout.addWidget(self.lbl_weather)

        # Separator 1
        sep1 = self._create_separator()
        layout.addWidget(sep1)

        # 2. Seamless Music Module (Inline typography without heavy frame)
        self.lbl_music = QLabel(f"🎵 {self.music_title}", self)
        self.lbl_music.setStyleSheet("color: #E2E8F0; font-size: 11px; font-weight: 500;")
        self.lbl_music.setMaximumWidth(200)
        self._apply_shadow(self.lbl_music)
        layout.addWidget(self.lbl_music)

        # Separator 2
        sep2 = self._create_separator()
        layout.addWidget(sep2)

        # 3. PC Telemetry Module (CPU & RAM)
        self.lbl_cpu = QLabel("CPU --%", self)
        self.lbl_cpu.setStyleSheet("color: #30D158; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace;")
        self._apply_shadow(self.lbl_cpu)
        layout.addWidget(self.lbl_cpu)

        self.lbl_ram = QLabel("RAM --%", self)
        self.lbl_ram.setStyleSheet("color: #64D2FF; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace;")
        self._apply_shadow(self.lbl_ram)
        layout.addWidget(self.lbl_ram)

        # Separator 3
        sep3 = self._create_separator()
        layout.addWidget(sep3)

        # 4. Power / Battery (if laptop or desktop AC)
        self.lbl_power = QLabel("⚡ AC", self)
        self.lbl_power.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        self._apply_shadow(self.lbl_power)
        layout.addWidget(self.lbl_power)

        # Separator 4
        sep4 = self._create_separator()
        layout.addWidget(sep4)

        # 5. Calendar & Clock
        self.lbl_clock = QLabel("12:00", self)
        self.lbl_clock.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700; font-family: 'SF Pro Display', 'Segoe UI', sans-serif;")
        self._apply_shadow(self.lbl_clock)
        layout.addWidget(self.lbl_clock)

    def _create_separator(self):
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setFixedWidth(1)
        sep.setFixedHeight(14)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.18); border: none;")
        return sep

    def _reposition_top_right(self):
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            # Calculate dynamic width based on contents
            self.adjustSize()
            w = max(520, self.sizeHint().width() + 20)
            self.setFixedWidth(w)
            x = avail.right() - w - 12
            y = avail.top() + 6
            self.move(x, y)

    def _update_clock_and_telemetry(self):
        now = datetime.datetime.now()
        # Russian day of week mapping
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        months = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
        day_str = weekdays[now.weekday()]
        mon_str = months[now.month - 1]
        time_str = now.strftime("%H:%M")
        self.lbl_clock.setText(f"{day_str}, {now.day} {mon_str} · {time_str}")

        # Telemetry
        self.cpu_pct = psutil.cpu_percent()
        self.ram_pct = psutil.virtual_memory().percent
        self.lbl_cpu.setText(f"CPU {int(self.cpu_pct)}%")
        self.lbl_ram.setText(f"RAM {int(self.ram_pct)}%")

        # Battery / AC
        batt = psutil.sensors_battery()
        if batt:
            pct = int(batt.percent)
            plugged = "⚡ " if batt.power_plugged else ""
            self.lbl_power.setText(f"{plugged}{pct}%")
        else:
            self.lbl_power.setText("⚡ AC")

        self.lbl_weather.setText(f"⛅ {self.weather_temp}")

    def _on_media_update(self, state):
        if state and state.is_active and state.title:
            self.is_playing = state.is_playing
            self.music_title = state.title
            self.music_artist = state.artist
            display_title = self.music_title
            if len(display_title) > 22:
                display_title = display_title[:20] + "…"
            status_icon = "▶ " if self.is_playing else "⏸ "
            self.lbl_music.setText(f"{status_icon}{display_title}")
        else:
            self.is_playing = False
            self.lbl_music.setText("🎵 Музыка выкл.")
        self._reposition_top_right()

    # -------------------------------------------------------------------------
    # Auto-Hide on Hover Mechanics
    # -------------------------------------------------------------------------
    def enterEvent(self, event):
        self.hide_timer.stop()
        self._fade_to_active()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hide_timer.start()
        super().leaveEvent(event)

    def _fade_to_active(self):
        self.is_hovered = True
        self.anim_opacity.stop()
        self.anim_opacity.setStartValue(self.opacity_effect.opacity())
        self.anim_opacity.setEndValue(self.active_opacity)
        self.anim_opacity.start()

    def _fade_to_idle(self):
        self.is_hovered = False
        self.anim_opacity.stop()
        self.anim_opacity.setStartValue(self.opacity_effect.opacity())
        self.anim_opacity.setEndValue(self.idle_opacity)
        self.anim_opacity.start()

    # -------------------------------------------------------------------------
    # 100% Completely Transparent Island Rendering
    # -------------------------------------------------------------------------
    def paintEvent(self, event):
        # 100% Completely Transparent Island: zero background fill, zero box border!
        # Only crisp typography, micro-icons and separators floating cleanly over desktop.
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    bar = AppleStatusBar()
    bar.show()
    sys.exit(app.exec())
