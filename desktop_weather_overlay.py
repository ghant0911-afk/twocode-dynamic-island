"""
Fullscreen Atmospheric Weather Wallpaper Overlay for Windows.
- 100% Non-Clickable / Click-Through across entire screen (WS_EX_TRANSPARENT).
- Pinned to desktop wallpaper layer (HWND_BOTTOM).
- Real-time weather detection from user's city (weather_config.json):
  * Rain / Shower / Drizzle -> Dynamic falling angled raindrops across entire desktop wallpaper.
  * Snow / Blizzard -> Drifting soft snowflakes across entire desktop.
  * Sunny / Clear / Clouds -> Completely invisible / zero particles ("в солнце ничего"), 0% CPU.
- Zero textual clutter: pure cinematic desktop atmosphere.
"""

import sys
import os
import json
import math
import random
import urllib.request
import urllib.parse
import ctypes
from ctypes import wintypes

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

user32 = ctypes.windll.user32

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

HWND_BOTTOM = 1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010


class RainDrop:
    """Atmospheric Raindrop with 3-depth parallax layers."""
    def __init__(self, w, h, layer=1):
        self.w = w
        self.h = h
        self.layer = layer  # 0: distant (faint), 1: midground, 2: foreground (bright)
        self.reset(random_y=True)

    def reset(self, random_y=False):
        self.x = random.uniform(-100, self.w + 100)
        self.y = random.uniform(0, self.h) if random_y else random.uniform(-60, 0)
        
        if self.layer == 0:
            self.length = random.uniform(12, 20)
            self.speed = random.uniform(14, 20)
            self.slant = random.uniform(3, 5)
        elif self.layer == 1:
            self.length = random.uniform(22, 36)
            self.speed = random.uniform(22, 30)
            self.slant = random.uniform(5, 8)
        else:
            self.length = random.uniform(38, 56)
            self.speed = random.uniform(32, 42)
            self.slant = random.uniform(8, 12)

    def update(self):
        self.y += self.speed
        self.x -= self.slant * (self.speed / 24.0)
        if self.y > self.h or self.x < -120 or self.x > self.w + 120:
            self.reset(random_y=False)


class Snowflake:
    """Soft Drifting Snowflake with swaying sine wave motion."""
    def __init__(self, w, h, layer=1):
        self.w = w
        self.h = h
        self.layer = layer
        self.reset(random_y=True)

    def reset(self, random_y=False):
        self.x = random.uniform(0, self.w)
        self.y = random.uniform(0, self.h) if random_y else random.uniform(-20, 0)
        self.angle = random.uniform(0, math.pi * 2)

        if self.layer == 0:
            self.radius = random.uniform(1.2, 2.2)
            self.speed = random.uniform(1.0, 1.8)
            self.sway_speed = random.uniform(0.015, 0.03)
            self.sway_amp = random.uniform(0.5, 1.0)
        elif self.layer == 1:
            self.radius = random.uniform(2.4, 4.0)
            self.speed = random.uniform(1.8, 2.8)
            self.sway_speed = random.uniform(0.02, 0.04)
            self.sway_amp = random.uniform(1.0, 1.8)
        else:
            self.radius = random.uniform(4.2, 6.5)
            self.speed = random.uniform(2.8, 3.8)
            self.sway_speed = random.uniform(0.03, 0.05)
            self.sway_amp = random.uniform(1.6, 2.5)

    def update(self):
        self.y += self.speed
        self.angle += self.sway_speed
        self.x += math.sin(self.angle) * self.sway_amp
        if self.y > self.h or self.x < -20 or self.x > self.w + 20:
            self.reset(random_y=False)


class FullscreenWeatherWallpaperOverlay(QWidget):
    """
    100% Non-Clickable Fullscreen Desktop Weather Atmosphere.
    Covers entire primary screen (1920x1080), completely click-through everywhere.
    """

    def __init__(self, script_dir=None):
        super().__init__(None)
        self.script_dir = script_dir or os.path.dirname(os.path.abspath(__file__))

        self.config_paths = [
            os.path.join(self.script_dir, "weather_config.json"),
            r"C:\Users\bear_\.gemini\antigravity\scratch\apple-status-bar-windows\weather_config.json",
            r"C:\Users\bear_\.gemini\antigravity\scratch\twocode-dynamic-island\weather_config.json"
        ]
        self.overlay_config_path = os.path.join(self.script_dir, "wallpaper_weather_config.json")

        self.setWindowTitle("Fullscreen Weather Wallpaper Overlay")

        # Win32 & Qt Window Flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Fullscreen geometry covering entire monitor
        screen = QApplication.primaryScreen()
        geom = screen.geometry() if screen else None
        self.screen_w = geom.width() if geom else 1920
        self.screen_h = geom.height() if geom else 1080
        self.setGeometry(0, 0, self.screen_w, self.screen_h)

        # Weather state
        self.city = self._read_saved_city()
        self.weather_mode = "rain"  # "rain", "snow", "clear"
        self.raw_condition = "Небольшой дождь"

        # Particles (Pre-allocated across 3 depth planes)
        self._init_particles()

        # Pre-configured Pens & Brushes for ultra-fast rendering (<0.5% CPU)
        self.rain_pens = [
            QPen(QColor(190, 220, 255, 60), 1.0),   # Far
            QPen(QColor(200, 230, 255, 110), 1.2),  # Mid
            QPen(QColor(215, 240, 255, 170), 1.8)   # Near
        ]
        self.snow_brushes = [
            QBrush(QColor(240, 248, 255, 80)),
            QBrush(QColor(245, 250, 255, 140)),
            QBrush(QColor(255, 255, 255, 200))
        ]

        # Timers
        # 1. Weather updater (every 15 min)
        self.weather_timer = QTimer(self)
        self.weather_timer.setInterval(15 * 60 * 1000)
        self.weather_timer.timeout.connect(self._fetch_weather)
        self.weather_timer.start()

        # 2. Config watcher (every 3 seconds to catch city changes live)
        self.config_watcher = QTimer(self)
        self.config_watcher.setInterval(3000)
        self.config_watcher.timeout.connect(self._check_config_change)
        self.config_watcher.start()

        # 3. Particle Animation (30 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(33)
        self.anim_timer.timeout.connect(self._tick)
        self.anim_timer.start()

        # 4. Z-Order enforcer (pins to HWND_BOTTOM)
        self.z_timer = QTimer(self)
        self.z_timer.setInterval(2500)
        self.z_timer.timeout.connect(self._keep_on_bottom)
        self.z_timer.start()

        # Initial fetch
        self._fetch_weather()

    def _init_particles(self):
        w, h = self.screen_w, self.screen_h
        
        # 240 raindrops: 90 far, 100 mid, 50 near
        self.raindrops = (
            [RainDrop(w, h, layer=0) for _ in range(90)] +
            [RainDrop(w, h, layer=1) for _ in range(100)] +
            [RainDrop(w, h, layer=2) for _ in range(50)]
        )

        # 160 snowflakes: 70 far, 60 mid, 30 near
        self.snowflakes = (
            [Snowflake(w, h, layer=0) for _ in range(70)] +
            [Snowflake(w, h, layer=1) for _ in range(60)] +
            [Snowflake(w, h, layer=2) for _ in range(30)]
        )

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_win32_clickthrough()
        self._keep_on_bottom()

    def _apply_win32_clickthrough(self):
        """Win32 WS_EX_TRANSPARENT enables 100% click-through hit testing everywhere."""
        hwnd = int(self.winId())
        if hwnd:
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd,
                GWL_EXSTYLE,
                ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )

    def _keep_on_bottom(self):
        """Maintains position at HWND_BOTTOM on wallpaper layer."""
        self.lower()
        hwnd = int(self.winId())
        if hwnd:
            user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

    def _read_saved_city(self):
        for p in self.config_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "city" in data and data["city"]:
                            return data["city"]
                except Exception:
                    pass
        return "Сочи"

    def _check_config_change(self):
        # 1. Check city
        current_saved = self._read_saved_city()
        if current_saved != self.city:
            self.city = current_saved
            self._fetch_weather()
            return

        # 2. Check force_mode if set
        if os.path.exists(self.overlay_config_path):
            try:
                with open(self.overlay_config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    force = data.get("force_mode")
                    if force in ["rain", "snow", "clear"] and force != self.weather_mode:
                        self.weather_mode = force
                        self.update()
            except Exception:
                pass

    def _fetch_weather(self):
        # Check if force_mode is requested in config
        if os.path.exists(self.overlay_config_path):
            try:
                with open(self.overlay_config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    force = data.get("force_mode")
                    if force in ["rain", "snow", "clear"]:
                        self.weather_mode = force
                        self.update()
                        return
            except Exception:
                pass

        try:
            encoded = urllib.parse.quote(self.city)
            url = f"https://wttr.in/{encoded}?format=%c;%t;%C;%w&lang=ru"
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                raw = resp.read().decode("utf-8").strip()
                parts = raw.split(";")
                if len(parts) >= 3:
                    cond = parts[2].strip().lower()
                    self.raw_condition = parts[2].strip()

                    # Classify condition
                    snow_keys = ["snow", "blizzard", "снег", "метель", "крупа", "flurries", "sleet"]
                    rain_keys = ["rain", "shower", "drizzle", "дождь", "ливень", "гроза", "морось"]

                    if any(k in cond for k in snow_keys):
                        self.weather_mode = "snow"
                    elif any(k in cond for k in rain_keys):
                        self.weather_mode = "rain"
                    else:
                        # Sunny, clear, overcast without precipitation -> Nothing!
                        self.weather_mode = "clear"

                    self.update()
        except Exception:
            pass

    def _tick(self):
        if self.weather_mode == "rain":
            for drop in self.raindrops:
                drop.update()
            self.update()
        elif self.weather_mode == "snow":
            for flake in self.snowflakes:
                flake.update()
            self.update()
        else:
            # Clear / Sun -> zero updates, zero CPU
            pass

    def paintEvent(self, event):
        painter = QPainter(self)

        # Clear entire screen backing store
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        if self.weather_mode == "clear":
            # "в солнце ничего" -> Completely clean transparent screen!
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.weather_mode == "rain":
            # Group draw by layer to minimize state switches
            for drop in self.raindrops:
                painter.setPen(self.rain_pens[drop.layer])
                painter.drawLine(
                    int(drop.x), int(drop.y),
                    int(drop.x - drop.slant), int(drop.y + drop.length)
                )
        elif self.weather_mode == "snow":
            painter.setPen(Qt.PenStyle.NoPen)
            for flake in self.snowflakes:
                painter.setBrush(self.snow_brushes[flake.layer])
                painter.drawEllipse(QPointF(flake.x, flake.y), flake.radius, flake.radius)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = FullscreenWeatherWallpaperOverlay()
    overlay.show()
    sys.exit(app.exec())
