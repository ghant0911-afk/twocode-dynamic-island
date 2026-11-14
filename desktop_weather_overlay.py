"""
Fullscreen Interactive Atmospheric Weather Wallpaper for Windows.
- 100% Non-Clickable / Click-Through across entire screen (WS_EX_TRANSPARENT).
- Pinned to desktop wallpaper layer (HWND_BOTTOM).
- Real-time weather detection from user's city (weather_config.json):
  * RAIN:
    - Falling raindrops across entire screen.
    - Interactive Window Edge Dripping: Water streams running down window borders and dripping from bottom corners.
    - Window Top Splashes: Rain splashing on active window tops.
    - Puddles & Ripples: Dynamic reflective puddle at bottom with expanding concentric ripples and water splashes.
  * SNOW:
    - Soft drifting snowflakes swaying with wind.
    - Snowdrifts (Сугробы): Organic snow blanket accumulating along bottom taskbar floor.
    - Window Snowcaps: Fluffy snowcaps resting on top of active floating window frames.
  * SUNNY / CLEAR:
    - Completely clean wallpaper, 0% CPU overhead.
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
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient

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


# -----------------------------------------------------------------------------
# Particle & Physics Classes
# -----------------------------------------------------------------------------
class RainDrop:
    def __init__(self, w, h, layer=1):
        self.w = w
        self.h = h
        self.layer = layer
        self.reset(random_y=True)

    def reset(self, random_y=False):
        self.x = random.uniform(-100, self.w + 100)
        self.y = random.uniform(0, self.h - 50) if random_y else random.uniform(-60, 0)
        
        if self.layer == 0:
            self.length = random.uniform(12, 20)
            self.speed = random.uniform(16, 22)
            self.slant = random.uniform(3, 5)
        elif self.layer == 1:
            self.length = random.uniform(22, 36)
            self.speed = random.uniform(24, 32)
            self.slant = random.uniform(5, 8)
        else:
            self.length = random.uniform(38, 56)
            self.speed = random.uniform(34, 44)
            self.slant = random.uniform(8, 12)

    def update(self):
        self.y += self.speed
        self.x -= self.slant * (self.speed / 24.0)
        if self.y > self.h - 45 or self.x < -120 or self.x > self.w + 120:
            hit_x = self.x
            hit_y = self.y
            self.reset(random_y=False)
            return True, hit_x, hit_y
        return False, 0, 0


class Snowflake:
    def __init__(self, w, h, layer=1):
        self.w = w
        self.h = h
        self.layer = layer
        self.reset(random_y=True)

    def reset(self, random_y=False):
        self.x = random.uniform(0, self.w)
        self.y = random.uniform(0, self.h - 40) if random_y else random.uniform(-20, 0)
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
        if self.y > self.h - 35 or self.x < -20 or self.x > self.w + 20:
            self.reset(random_y=False)


class Ripple:
    """Expanding puddle water ring."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.r = 2.0
        self.max_r = random.uniform(14.0, 28.0)
        self.growth = random.uniform(1.2, 2.0)
        self.alpha = 190.0

    def update(self):
        self.r += self.growth
        self.alpha -= (190.0 / (self.max_r / self.growth))
        return self.alpha > 0 and self.r < self.max_r


class SplashDrop:
    """Bouncing splash droplet."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2.5, 2.5)
        self.vy = random.uniform(-4.5, -1.5)
        self.gravity = 0.35
        self.alpha = 220.0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.alpha -= 10.0
        return self.alpha > 0


class WindowDrip:
    """Drop falling straight down from window bottom edge or corner."""
    def __init__(self, x, start_y, floor_y):
        self.x = x
        self.y = start_y
        self.floor_y = floor_y
        self.speed = random.uniform(18.0, 28.0)
        self.len = random.uniform(14.0, 26.0)

    def update(self):
        self.y += self.speed
        return self.y < self.floor_y


# -----------------------------------------------------------------------------
# Fullscreen Weather Wallpaper Engine
# -----------------------------------------------------------------------------
class FullscreenWeatherWallpaperOverlay(QWidget):
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

        # Win32 & Qt Window Flags: 100% Non-Clickable / Click-Through
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        screen = QApplication.primaryScreen()
        geom = screen.geometry() if screen else None
        self.screen_w = geom.width() if geom else 1920
        self.screen_h = geom.height() if geom else 1080
        self.setGeometry(0, 0, self.screen_w, self.screen_h)

        # Weather state
        self.city = self._read_saved_city()
        self.weather_mode = "snow"  # Default follows live city
        self.raw_condition = "Снег"

        # Particles & Effects
        self._init_particles()
        self.ripples = []
        self.splash_drops = []
        self.window_drips = []

        # Detected user window rectangles: [(x, y, w, h)]
        self.active_window_rects = []

        # Pre-calculated Bottom Floor Geometry (Puddles & Snowdrifts)
        self.puddle_y = self.screen_h - 45
        self._init_floor_shapes()

        # Visual styling pens & brushes
        self.rain_pens = [
            QPen(QColor(190, 220, 255, 65), 1.0),
            QPen(QColor(200, 230, 255, 115), 1.2),
            QPen(QColor(215, 240, 255, 180), 1.8)
        ]
        self.snow_brushes = [
            QBrush(QColor(240, 248, 255, 80)),
            QBrush(QColor(245, 250, 255, 145)),
            QBrush(QColor(255, 255, 255, 210))
        ]

        # Timers
        # 1. Weather updater (every 15 min)
        self.weather_timer = QTimer(self)
        self.weather_timer.setInterval(15 * 60 * 1000)
        self.weather_timer.timeout.connect(self._fetch_weather)
        self.weather_timer.start()

        # 2. Config watcher (every 3 seconds)
        self.config_watcher = QTimer(self)
        self.config_watcher.setInterval(3000)
        self.config_watcher.timeout.connect(self._check_config_change)
        self.config_watcher.start()

        # 3. Window tracker (every 1.5s: detects active windows on screen)
        self.window_tracker = QTimer(self)
        self.window_tracker.setInterval(1500)
        self.window_tracker.timeout.connect(self._scan_windows)
        self.window_tracker.start()

        # 4. Simulation & Animation (30 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(33)
        self.anim_timer.timeout.connect(self._tick)
        self.anim_timer.start()

        # 5. Z-Order enforcer (pins to HWND_BOTTOM)
        self.z_timer = QTimer(self)
        self.z_timer.setInterval(2500)
        self.z_timer.timeout.connect(self._keep_on_bottom)
        self.z_timer.start()

        # Initial scans
        self._fetch_weather()
        self._scan_windows()

    def _init_particles(self):
        w, h = self.screen_w, self.screen_h
        self.raindrops = (
            [RainDrop(w, h, layer=0) for _ in range(85)] +
            [RainDrop(w, h, layer=1) for _ in range(95)] +
            [RainDrop(w, h, layer=2) for _ in range(45)]
        )
        self.snowflakes = (
            [Snowflake(w, h, layer=0) for _ in range(70)] +
            [Snowflake(w, h, layer=1) for _ in range(65)] +
            [Snowflake(w, h, layer=2) for _ in range(35)]
        )

    def _init_floor_shapes(self):
        w, h = self.screen_w, self.screen_h

        # 1. Puddle surface wave (Rain)
        self.puddle_path = QPainterPath()
        self.puddle_path.moveTo(0, h)
        self.puddle_path.lineTo(0, self.puddle_y)
        for x in range(0, w + 20, 25):
            py = self.puddle_y + math.sin(x * 0.012) * 5 + math.cos(x * 0.03) * 3
            self.puddle_path.lineTo(x, py)
        self.puddle_path.lineTo(w, h)
        self.puddle_path.closeSubpath()

        # 2. Organic Snowdrift Dunes (Snow)
        self.snowdrift_path = QPainterPath()
        self.snowdrift_path.moveTo(0, h)
        for x in range(0, w + 15, 15):
            drift_h = math.sin(x * 0.007) * 18 + math.cos(x * 0.018) * 12 + math.sin(x * 0.04) * 6 + 28
            self.snowdrift_path.lineTo(x, h - drift_h)
        self.snowdrift_path.lineTo(w, h)
        self.snowdrift_path.closeSubpath()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_win32_clickthrough()
        self._keep_on_bottom()

    def _apply_win32_clickthrough(self):
        hwnd = int(self.winId())
        if hwnd:
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd,
                GWL_EXSTYLE,
                ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )

    def _keep_on_bottom(self):
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
        return "Москва"

    def _scan_windows(self):
        """Scans visible floating windows to attach snowcaps and dripping edges."""
        rects = []
        def enum_cb(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
                return True
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w <= 180 or h <= 120 or w >= self.screen_w:
                return True

            title = ctypes.create_unicode_buffer(128)
            user32.GetWindowTextW(hwnd, title, 128)
            cls = ctypes.create_unicode_buffer(128)
            user32.GetClassNameW(hwnd, cls, 128)

            if cls.value in ['Progman', 'WorkerW', 'Shell_TrayWnd']:
                return True
            if 'Overlay' in title.value or 'Apple Status Bar' in title.value:
                return True

            rects.append((rect.left, rect.top, w, h))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        self.active_window_rects = rects[:6]  # Keep top floating windows

    def _check_config_change(self):
        # 1. City check
        current_saved = self._read_saved_city()
        if current_saved != self.city:
            self.city = current_saved
            self._fetch_weather()
            return

        # 2. Force mode check
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

                    snow_keys = ["snow", "blizzard", "снег", "метель", "крупа", "flurries", "sleet"]
                    rain_keys = ["rain", "shower", "drizzle", "дождь", "ливень", "гроза", "морось"]

                    if any(k in cond for k in snow_keys):
                        self.weather_mode = "snow"
                    elif any(k in cond for k in rain_keys):
                        self.weather_mode = "rain"
                    else:
                        self.weather_mode = "clear"

                    self.update()
        except Exception:
            pass

    def _tick(self):
        if self.weather_mode == "rain":
            # 1. Update rain drops and check bottom impact
            for drop in self.raindrops:
                hit, hx, hy = drop.update()
                if hit:
                    # Spawn puddle ripple
                    if len(self.ripples) < 30 and random.random() < 0.45:
                        self.ripples.append(Ripple(hx, random.uniform(self.puddle_y + 4, self.screen_h - 6)))
                    # Spawn tiny splash droplets
                    if len(self.splash_drops) < 40 and random.random() < 0.35:
                        for _ in range(2):
                            self.splash_drops.append(SplashDrop(hx, self.puddle_y))

            # 2. Window edge drips ("С окон льется")
            for wx, wy, ww, wh in self.active_window_rects:
                # Spawn drips from bottom corners and bottom edge
                if len(self.window_drips) < 35 and random.random() < 0.30:
                    drip_x = random.choice([wx + 4, wx + ww - 4, wx + ww * 0.35, wx + ww * 0.70])
                    self.window_drips.append(WindowDrip(drip_x, wy + wh, self.puddle_y))
                # Spawn occasional top edge splash
                if len(self.splash_drops) < 40 and random.random() < 0.20:
                    sx = wx + random.uniform(10, ww - 10)
                    self.splash_drops.append(SplashDrop(sx, wy))

            # 3. Update existing drips, ripples, and splashes
            self.ripples = [r for r in self.ripples if r.update()]
            self.splash_drops = [s for s in self.splash_drops if s.update()]
            survived_drips = []
            for d in self.window_drips:
                if d.update():
                    survived_drips.append(d)
                else:
                    # Hit puddle -> spawn ripple!
                    if len(self.ripples) < 30:
                        self.ripples.append(Ripple(d.x, self.puddle_y + 4))
            self.window_drips = survived_drips
            self.update()

        elif self.weather_mode == "snow":
            for flake in self.snowflakes:
                flake.update()
            self.update()
        else:
            # Clear / Sun -> zero CPU
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Clear entire screen
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        if self.weather_mode == "clear":
            return

        w, h = self.screen_w, self.screen_h

        # =====================================================================
        # 1. RAIN MODE: Falling drops + Puddles + Ripples + Window Drips
        # =====================================================================
        if self.weather_mode == "rain":
            # A. PUDDLES (Лужи на дне экрана над панелью задач)
            puddle_grad = QLinearGradient(0, self.puddle_y, 0, h)
            puddle_grad.setColorAt(0.0, QColor(140, 195, 245, 60))
            puddle_grad.setColorAt(1.0, QColor(110, 175, 230, 95))
            painter.fillPath(self.puddle_path, QBrush(puddle_grad))

            # Puddle top glossy water highlight
            p_pen = QPen(QColor(225, 245, 255, 125), 1.5)
            painter.setPen(p_pen)
            painter.drawPath(self.puddle_path)

            # B. PUDDLE RIPPLES (Круги на воде)
            ripple_pen = QPen()
            ripple_pen.setWidthF(1.0)
            for rip in self.ripples:
                ripple_pen.setColor(QColor(220, 240, 255, int(rip.alpha)))
                painter.setPen(ripple_pen)
                # Perspective elliptical ripple
                painter.drawEllipse(QPointF(rip.x, rip.y), rip.r, rip.r * 0.32)

            # C. SPLASH DROPLETS (Брызги от капель)
            splash_pen = QPen()
            for s in self.splash_drops:
                splash_pen.setColor(QColor(230, 245, 255, int(s.alpha)))
                splash_pen.setWidthF(1.5)
                painter.setPen(splash_pen)
                painter.drawPoint(QPointF(s.x, s.y))

            # D. WINDOW DRIPPING ("С окон льется")
            drip_pen = QPen(QColor(215, 240, 255, 210), 2.0)
            painter.setPen(drip_pen)
            for wx, wy, ww, wh in self.active_window_rects:
                # Water beads sliding down left & right window borders
                for ex in [wx, wx + ww]:
                    painter.drawLine(int(ex), int(wy + 8), int(ex), int(wy + 24))
                    painter.drawLine(int(ex), int(wy + wh * 0.45), int(ex), int(wy + wh * 0.45 + 20))
                    painter.drawLine(int(ex), int(wy + wh - 22), int(ex), int(wy + wh))

            # Falling drips coming off bottom of windows
            for d in self.window_drips:
                painter.drawLine(int(d.x), int(d.y), int(d.x), int(d.y + d.len))

            # E. RAINDROPS ACROSS SCREEN
            for drop in self.raindrops:
                painter.setPen(self.rain_pens[drop.layer])
                painter.drawLine(
                    int(drop.x), int(drop.y),
                    int(drop.x - drop.slant), int(drop.y + drop.length)
                )

        # =====================================================================
        # 2. SNOW MODE: Falling flakes + Snowdrifts + Window Snowcaps
        # =====================================================================
        elif self.weather_mode == "snow":
            # A. SNOWDRIFTS (Сугробы на дне экрана над панелью задач)
            drift_grad = QLinearGradient(0, h - 60, 0, h)
            drift_grad.setColorAt(0.0, QColor(245, 250, 255, 225))
            drift_grad.setColorAt(1.0, QColor(225, 238, 252, 245))
            painter.fillPath(self.snowdrift_path, QBrush(drift_grad))

            # Top fluffy rim highlight on snowdrifts
            drift_rim_pen = QPen(QColor(255, 255, 255, 255), 2.5)
            painter.setPen(drift_rim_pen)
            painter.drawPath(self.snowdrift_path)

            # B. WINDOW TOP SNOWCAPS (Сугробы на крышках окон)
            cap_brush = QBrush(QColor(245, 250, 255, 235))
            cap_pen = QPen(QColor(255, 255, 255, 255), 1.5)
            for wx, wy, ww, wh in self.active_window_rects:
                cap_path = QPainterPath()
                cap_path.moveTo(wx, wy + 2)
                for step in range(0, ww + 10, 12):
                    cur_x = wx + step
                    mid_factor = math.sin((step / max(1, ww)) * math.pi)
                    cap_thick = mid_factor * 10.0 + math.sin(step * 0.12) * 2.0 + 4.0
                    cap_path.lineTo(cur_x, wy - cap_thick)
                cap_path.lineTo(wx + ww, wy + 2)
                cap_path.closeSubpath()
                painter.fillPath(cap_path, cap_brush)
                painter.setPen(cap_pen)
                painter.drawPath(cap_path)

            # C. FALLING SNOWFLAKES ACROSS SCREEN
            painter.setPen(Qt.PenStyle.NoPen)
            for flake in self.snowflakes:
                painter.setBrush(self.snow_brushes[flake.layer])
                painter.drawEllipse(QPointF(flake.x, flake.y), flake.radius, flake.radius)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = FullscreenWeatherWallpaperOverlay()
    overlay.show()
    sys.exit(app.exec())
