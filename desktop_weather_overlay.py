"""
Desktop Weather Wallpaper Overlay for Windows (macOS Sonoma / iOS 17 aesthetic).
Completely non-clickable (WS_EX_TRANSPARENT), pinned to desktop wallpaper level (HWND_BOTTOM).
Auto-syncs live with Apple Status Bar (weather_config.json).
"""

import sys
import os
import json
import math
import random
import datetime
import urllib.request
import urllib.parse
import ctypes
from ctypes import wintypes

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPainterPath, QColor, QFont, QPen, QBrush, QLinearGradient
)

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

WEATHER_TRANSLATIONS = {
    "sunny": "Солнечно",
    "clear": "Ясно",
    "partly cloudy": "Переменная облачность",
    "cloudy": "Облачно",
    "overcast": "Пасмурно",
    "mist": "Дымка",
    "patchy rain possible": "Местами дождь",
    "patchy snow possible": "Местами снег",
    "thundery outbreaks possible": "Возможна гроза",
    "light rain": "Небольшой дождь",
    "moderate rain": "Умеренный дождь",
    "heavy rain": "Сильный дождь",
    "light rain shower": "Кратковременный дождь",
    "moderate or heavy rain shower": "Ливневый дождь",
    "light snow": "Небольшой снег",
    "moderate snow": "Умеренный снег",
    "heavy snow": "Снегопад",
    "fog": "Туман",
    "blizzard": "Метель",
    "freezing drizzle": "Замерзающая морось"
}

def translate_weather(desc_en: str) -> str:
    cleaned = desc_en.strip().lower()
    for en_key, ru_val in WEATHER_TRANSLATIONS.items():
        if en_key in cleaned:
            return ru_val
    return desc_en.capitalize()


class Particle:
    """Atmospheric weather particle (Rain, Snow, or Sunny Motes)."""
    def __init__(self, w, h, p_type="rain"):
        self.w = w
        self.h = h
        self.p_type = p_type
        self.reset(random_y=True)

    def reset(self, random_y=False):
        self.x = random.uniform(0, self.w)
        self.y = random.uniform(0, self.h) if random_y else random.uniform(-20, 0)
        self.angle = random.uniform(0, math.pi * 2)

        if self.p_type == "rain":
            self.len = random.uniform(8, 16)
            self.speed = random.uniform(4.5, 9.0)
            self.opacity = random.uniform(0.2, 0.55)
        elif self.p_type == "snow":
            self.radius = random.uniform(1.2, 3.2)
            self.speed = random.uniform(1.0, 2.2)
            self.sway_speed = random.uniform(0.02, 0.05)
            self.sway_amp = random.uniform(0.5, 1.5)
            self.opacity = random.uniform(0.3, 0.7)
        else:  # sun / ambient motes
            self.radius = random.uniform(1.0, 2.2)
            self.speed = random.uniform(0.2, 0.6)
            self.opacity = random.uniform(0.15, 0.45)

    def update(self):
        if self.p_type == "rain":
            self.y += self.speed
            self.x -= 0.6
            if self.y > self.h or self.x < 0:
                self.reset(random_y=False)
        elif self.p_type == "snow":
            self.y += self.speed
            self.angle += self.sway_speed
            self.x += math.sin(self.angle) * self.sway_amp
            if self.y > self.h or self.x < 0 or self.x > self.w:
                self.reset(random_y=False)
        else:
            self.y -= self.speed
            self.angle += 0.02
            self.x += math.cos(self.angle) * 0.3
            if self.y < 0 or self.x < 0 or self.x > self.w:
                self.reset(random_y=False)
                self.y = self.h + 5


class DesktopWeatherOverlay(QWidget):
    """
    Apple Sonoma Liquid Glass Wallpaper Weather Widget.
    - 100% Non-Clickable (WS_EX_TRANSPARENT).
    - Always pinned to desktop wallpaper level (HWND_BOTTOM).
    - Auto-synchronizes with Apple Status Bar (weather_config.json).
    - Adaptive weather particle atmosphere (Rain / Snow / Sun / Clear).
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
        self.overlay_settings = self._load_overlay_settings()

        self.setWindowTitle("Desktop Weather Wallpaper Overlay")

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

        self.widget_w = 480
        self.widget_h = 190
        self.setFixedSize(self.widget_w, self.widget_h)

        # Weather state
        self.city = self._read_saved_city()
        self.temp_num = "+16°"
        self.icon = "🌦️"
        self.desc = "Определение погоды..."
        self.humidity = "--%"
        self.wind = "-- км/ч"
        self.pressure = "-- мм"
        self.particle_type = "rain"

        # Initialize particles
        self.particles = [Particle(self.widget_w, self.widget_h, self.particle_type) for _ in range(20)]

        # Position on screen
        self._position_on_desktop()

        # Timers
        # 1. Weather updater (every 15 min or configured)
        mins = self.overlay_settings.get("update_interval_minutes", 15)
        self.weather_timer = QTimer(self)
        self.weather_timer.setInterval(max(1, mins) * 60 * 1000)
        self.weather_timer.timeout.connect(self._fetch_weather)
        self.weather_timer.start()

        # 2. Config watcher (every 3 seconds to catch city changes from Apple Status Bar)
        self.config_watcher = QTimer(self)
        self.config_watcher.setInterval(3000)
        self.config_watcher.timeout.connect(self._check_config_change)
        self.config_watcher.start()

        # 3. Particle & Clock animation (30 FPS)
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

    def _load_overlay_settings(self):
        default_settings = {
            "enabled": True,
            "position": "center_top",
            "custom_x": None,
            "custom_y": None,
            "opacity": 0.85,
            "particles": True,
            "update_interval_minutes": 15
        }
        if os.path.exists(self.overlay_config_path):
            try:
                with open(self.overlay_config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_settings.update(data)
            except Exception:
                pass
        else:
            try:
                with open(self.overlay_config_path, "w", encoding="utf-8") as f:
                    json.dump(default_settings, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return default_settings

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_win32_clickthrough()
        self._keep_on_bottom()

    def _apply_win32_clickthrough(self):
        """Win32 WS_EX_TRANSPARENT enables 100% click-through hit testing."""
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

    def _position_on_desktop(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return

        geom = screen.availableGeometry()
        pos = self.overlay_settings.get("position", "center_top")
        custom_x = self.overlay_settings.get("custom_x")
        custom_y = self.overlay_settings.get("custom_y")

        if pos == "custom" and custom_x is not None and custom_y is not None:
            self.move(int(custom_x), int(custom_y))
            return

        if pos == "top_left":
            self.move(80, 80)
        elif pos == "top_right":
            self.move(geom.width() - self.widget_w - 80, 80)
        elif pos == "bottom_left":
            self.move(80, geom.height() - self.widget_h - 80)
        elif pos == "bottom_right":
            self.move(geom.width() - self.widget_w - 80, geom.height() - self.widget_h - 80)
        else:
            # Default center-top (macOS Sonoma / iOS 17 Lockscreen aesthetic)
            x = (geom.width() - self.widget_w) // 2
            y = 75
            self.move(x, y)

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
        current_saved = self._read_saved_city()
        if current_saved != self.city:
            self.city = current_saved
            self._fetch_weather()

    def _fetch_weather(self):
        try:
            encoded = urllib.parse.quote(self.city)
            url = f"https://wttr.in/{encoded}?format=%c;%t;%C;%h;%w;%p;%P&lang=ru"
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                raw = resp.read().decode("utf-8").strip()
                parts = raw.split(";")
                if len(parts) >= 3:
                    self.icon = parts[0].strip() or "⛅"
                    temp_raw = parts[1].strip() or "+16°C"
                    self.temp_num = temp_raw.replace("C", "")
                    raw_desc = parts[2].strip() or "Ясно"
                    self.desc = translate_weather(raw_desc)
                    self.humidity = parts[3].strip() if len(parts) > 3 else "70%"
                    self.wind = parts[4].strip() if len(parts) > 4 else "3.0 м/с"
                    if len(parts) > 6:
                        raw_press = parts[6].strip()
                        if "hPa" in raw_press:
                            val = int(raw_press.replace("hPa", "").strip())
                            self.pressure = f"{int(val * 0.750062)} мм"
                        else:
                            self.pressure = raw_press

                    desc_l = raw_desc.lower()
                    if any(k in desc_l for k in ["snow", "снег", "метель", "blizzard"]):
                        new_type = "snow"
                    elif any(k in desc_l for k in ["rain", "shower", "drizzle", "дождь", "ливень"]):
                        new_type = "rain"
                    else:
                        new_type = "sun"

                    if new_type != self.particle_type:
                        self.particle_type = new_type
                        self.particles = [Particle(self.widget_w, self.widget_h, self.particle_type) for _ in range(20)]

                    self.update()
        except Exception:
            pass

    def _tick(self):
        if self.overlay_settings.get("particles", True):
            for p in self.particles:
                p.update()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Clear backing store completely
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        rect = QRectF(self.rect())

        # Apple macOS Liquid Frosted Glass Capsule
        path = QPainterPath()
        path.addRoundedRect(rect.adjusted(2, 2, -2, -2), 24, 24)

        # Liquid translucent glass
        glass_grad = QLinearGradient(0, 0, 0, self.widget_h)
        glass_grad.setColorAt(0.0, QColor(18, 18, 22, 160))
        glass_grad.setColorAt(1.0, QColor(12, 12, 16, 195))
        painter.fillPath(path, QBrush(glass_grad))

        # Delicate glass border with highlight
        pen = QPen(QColor(255, 255, 255, 38))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawPath(path)

        # Atmospheric Weather Particles
        if self.overlay_settings.get("particles", True):
            if self.particle_type == "rain":
                rain_pen = QPen()
                rain_pen.setWidthF(1.2)
                for p in self.particles:
                    rain_pen.setColor(QColor(180, 220, 255, int(p.opacity * 255)))
                    painter.setPen(rain_pen)
                    painter.drawLine(int(p.x), int(p.y), int(p.x - 1), int(p.y + p.len))
            elif self.particle_type == "snow":
                painter.setPen(Qt.PenStyle.NoPen)
                for p in self.particles:
                    painter.setBrush(QColor(245, 250, 255, int(p.opacity * 255)))
                    painter.drawEllipse(QPointF(p.x, p.y), p.radius, p.radius)
            else:
                # Sun / ambient dust motes
                painter.setPen(Qt.PenStyle.NoPen)
                for p in self.particles:
                    painter.setBrush(QColor(255, 235, 170, int(p.opacity * 255)))
                    painter.drawEllipse(QPointF(p.x, p.y), p.radius, p.radius)

        # Header: Time & Date
        now = datetime.datetime.now()
        weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        day_str = weekdays[now.weekday()]
        mon_str = months[now.month - 1]
        time_str = now.strftime("%H:%M")
        date_text = f"{time_str} · {day_str}, {now.day} {mon_str}"

        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        painter.setPen(QColor(255, 255, 255, 175))
        painter.drawText(QRectF(22, 14, self.widget_w - 44, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, date_text)

        # Massive Apple Temperature
        f_temp = QFont("Segoe UI", 48, QFont.Weight.Bold)
        painter.setFont(f_temp)
        painter.setPen(QColor(255, 255, 255, 250))
        painter.drawText(QRectF(20, 36, 180, 68), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.temp_num)

        # Weather Icon next to temp
        f_icon = QFont("Segoe UI Emoji", 36)
        painter.setFont(f_icon)
        painter.drawText(QRectF(175, 42, 60, 60), Qt.AlignmentFlag.AlignCenter, self.icon)

        # City & Condition
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255, 245))
        painter.drawText(QRectF(245, 42, 215, 28), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"📍 {self.city}")

        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        painter.setPen(QColor(255, 255, 255, 195))
        painter.drawText(QRectF(245, 72, 215, 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.desc)

        # Bottom Environmental Pills (Humidity, Wind, Pressure)
        pills_y = 120
        pill_h = 32
        pill_w = (self.widget_w - 44 - 16) / 3

        stats = [
            ("💧", f"Влажность: {self.humidity}"),
            ("💨", f"Ветер: {self.wind}"),
            ("⏱", f"Давление: {self.pressure}")
        ]

        for i, (ic, val) in enumerate(stats):
            px = 22 + i * (pill_w + 8)
            p_rect = QRectF(px, pills_y, pill_w, pill_h)

            p_path = QPainterPath()
            p_path.addRoundedRect(p_rect, 10, 10)
            painter.fillPath(p_path, QBrush(QColor(255, 255, 255, 14)))
            painter.setPen(QPen(QColor(255, 255, 255, 24), 1.0))
            painter.drawPath(p_path)

            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.setPen(QColor(255, 255, 255, 215))
            painter.drawText(p_rect, Qt.AlignmentFlag.AlignCenter, f"{ic} {val}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = DesktopWeatherOverlay()
    overlay.show()
    sys.exit(app.exec())
