import sys
import os
import psutil
import datetime
import ctypes
import json
import urllib.request
import urllib.parse

from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QPushButton,
    QProgressBar, QScrollArea, QLineEdit, QListWidget, QListWidgetItem,
    QStackedWidget, QMenu
)
from PyQt6.QtCore import (
    Qt, QPoint, QRectF, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal,
    QThread
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QCursor, QWheelEvent,
    QMouseEvent, QAction
)

# Win32 Virtual Keys
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3

# Win32 Thread Execution State (Caffeine Mode)
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

try:
    from media_engine import WindowsMediaWatcher
    HAS_MEDIA = True
except Exception:
    HAS_MEDIA = False


class CitySearchWorker(QThread):
    """
    Asynchronous city search worker using Open-Meteo Geocoding API.
    Provides fast, free autocomplete for cities worldwide in Russian.
    """
    results_ready = pyqtSignal(list)

    def __init__(self, query=""):
        super().__init__()
        self.query = query.strip()

    def run(self):
        if not self.query or len(self.query) < 2:
            self.results_ready.emit([])
            return

        encoded = urllib.parse.quote(self.query)
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=6&language=ru&format=json"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                raw_results = data.get('results', [])
                items = []
                for r in raw_results:
                    name = r.get('name', '')
                    admin1 = r.get('admin1', '')
                    country = r.get('country', '')
                    subtitle = f"{admin1}, {country}" if admin1 else country
                    items.append({
                        "name": name,
                        "subtitle": subtitle,
                        "display": f"{name} ({subtitle})" if subtitle else name
                    })
                self.results_ready.emit(items)
                return
        except Exception:
            pass
        self.results_ready.emit([])


class WeatherWorker(QThread):
    """
    Background worker that queries live weather from wttr.in
    for the chosen city with zero UI freezes.
    """
    weather_fetched = pyqtSignal(dict)

    def __init__(self, city=""):
        super().__init__()
        self.city = city.strip()

    def run(self):
        target_city = self.city
        if not target_city:
            try:
                req = urllib.request.Request('http://ip-api.com/json', headers={'User-Agent': 'curl/7.68.0'})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    target_city = data.get('city', 'Moscow')
            except Exception:
                target_city = "Moscow"

        city_display = target_city
        if target_city.lower() in ("moscow", "москва"):
            city_display = "Москва"
        elif target_city.lower() in ("saint petersburg", "санкт-петербург", "spb"):
            city_display = "Санкт-Петербург"
        elif target_city.lower() in ("novosibirsk", "новосибирск"):
            city_display = "Новосибирск"
        elif target_city.lower() in ("ekaterinburg", "екатеринбург"):
            city_display = "Екатеринбург"
        elif target_city.lower() in ("kazan", "казань"):
            city_display = "Казань"
        elif target_city.lower() in ("voronezh", "воронеж"):
            city_display = "Воронеж"

        encoded = urllib.parse.quote(target_city)
        url = f"https://wttr.in/{encoded}?format=%c;%t;%C;%h;%w&lang=ru"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read().decode('utf-8').strip()
                parts = raw.split(';')
                if len(parts) >= 3:
                    icon = parts[0].strip() or "⛅"
                    temp = parts[1].strip() or "+2°C"
                    desc = parts[2].strip() or "Ясно"
                    hum = parts[3].strip() if len(parts) > 3 else "70%"
                    wind = parts[4].strip() if len(parts) > 4 else "3.0 м/с"
                    self.weather_fetched.emit({
                        "city": city_display,
                        "raw_city": target_city,
                        "icon": icon,
                        "temp": temp,
                        "desc": desc,
                        "humidity": hum,
                        "wind": wind,
                        "success": True
                    })
                    return
        except Exception:
            pass

        self.weather_fetched.emit({
            "city": city_display,
            "raw_city": target_city,
            "icon": "⛅",
            "temp": "+2°C",
            "desc": "Облачно",
            "humidity": "74%",
            "wind": "3.2 м/с",
            "success": False
        })


class ClickableLabel(QLabel):
    """
    Native PyQt6 subclassed QLabel ensuring 100% reliable click interception
    without fragile monkey-patching on C++ vtable.
    """
    clicked = pyqtSignal(int)

    def __init__(self, tab_idx: int, text: str = "", parent=None):
        super().__init__(text, parent)
        self.tab_idx = tab_idx
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tab_idx)
            event.accept()
            return
        super().mousePressEvent(event)


class AppleStatusFlyout(QWidget):
    """
    Apple macOS-grade Frosted Glass Dropdown Flyout.
    Contains 5 modular views:
    0: Weather & City Search Engine
    1: Apple Music Controller
    2: Mini Task Manager (Top Processes & RAM Flush)
    3: Calendar & Quick Notes
    4: Quick Tools (Caffeine, Snipping, Clipboard History)
    """

    def __init__(self, parent_bar=None):
        super().__init__(None)
        self.parent_bar = parent_bar
        self.setWindowTitle("Apple Status Flyout")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setFixedWidth(340)
        self.current_tab = 0

        # Drop shadow for flyout
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 200))
        self.shadow.setBlurRadius(24)
        self.shadow.setOffset(0, 8)
        self.setGraphicsEffect(self.shadow)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Header with Navigation & Tab Switch Pills
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        self.lbl_flyout_title = QLabel("Погода", self)
        self.lbl_flyout_title.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700; font-family: 'Segoe UI', sans-serif;")
        header_layout.addWidget(self.lbl_flyout_title)

        header_layout.addStretch()

        # Direct Tab Switch Pills in the Header
        self.tab_pills = []
        pill_items = [("⛅", 0), ("🎵", 1), ("⚡", 2), ("📅", 3), ("☕", 4)]
        for ic, idx in pill_items:
            btn = QPushButton(ic, self)
            btn.setFixedSize(26, 22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, t=idx: self.show_tab(t))
            self.tab_pills.append(btn)
            header_layout.addWidget(btn)

        self.btn_close = QPushButton("✕", self)
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.10);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 11px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.22);
            }
        """)
        self.btn_close.clicked.connect(self.hide)
        header_layout.addWidget(self.btn_close)
        main_layout.addLayout(header_layout)

        # Stacked Pages
        self.stack = QStackedWidget(self)
        main_layout.addWidget(self.stack)

        # Page 0: Weather & City Search
        self.page_weather = self._create_weather_page()
        self.stack.addWidget(self.page_weather)

        # Page 1: Music
        self.page_music = self._create_music_page()
        self.stack.addWidget(self.page_music)

        # Page 2: Task Manager
        self.page_tasks = self._create_tasks_page()
        self.stack.addWidget(self.page_tasks)

        # Page 3: Calendar & Notes
        self.page_calendar = self._create_calendar_page()
        self.stack.addWidget(self.page_calendar)

        # Page 4: Tools & Clipboard
        self.page_tools = self._create_tools_page()
        self.stack.addWidget(self.page_tools)

        self._update_tab_pills(0)

    def _update_tab_pills(self, active_idx):
        for idx, btn in enumerate(self.tab_pills):
            if idx == active_idx:
                btn.setStyleSheet("background: #0A84FF; color: #FFFFFF; border-radius: 6px; font-size: 11px; font-weight: bold; border: none;")
            else:
                btn.setStyleSheet("background: rgba(255, 255, 255, 0.08); color: rgba(255, 255, 255, 0.7); border-radius: 6px; font-size: 11px; border: 1px solid rgba(255, 255, 255, 0.12);")

    # -------------------------------------------------------------------------
    # Page 0: Weather with Live City Search Engine
    # -------------------------------------------------------------------------
    def _create_weather_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        # 1. Search Bar Card
        search_card = QFrame(w)
        search_card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 10px;
                padding: 2px 4px;
            }
        """)
        s_layout = QHBoxLayout(search_card)
        s_layout.setContentsMargins(6, 2, 4, 2)
        s_layout.setSpacing(6)

        lbl_icon = QLabel("🔍", search_card)
        lbl_icon.setStyleSheet("font-size: 11px;")
        s_layout.addWidget(lbl_icon)

        self.input_search = QLineEdit(search_card)
        self.input_search.setPlaceholderText("Поиск города (напр. Воронеж, Сочи)...")
        self.input_search.setStyleSheet("background: transparent; color: #FFFFFF; border: none; font-size: 11px; font-weight: 500;")
        self.input_search.textChanged.connect(self._on_search_text_changed)
        self.input_search.returnPressed.connect(self._on_search_enter)
        s_layout.addWidget(self.input_search)

        self.btn_clear_search = QPushButton("✕", search_card)
        self.btn_clear_search.setFixedSize(18, 18)
        self.btn_clear_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_search.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.12);
                color: #FFFFFF;
                border-radius: 9px;
                font-size: 9px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.25);
            }
        """)
        self.btn_clear_search.clicked.connect(self._clear_search)
        s_layout.addWidget(self.btn_clear_search)

        self.btn_search = QPushButton("Найти", search_card)
        self.btn_search.setFixedHeight(22)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.setStyleSheet("""
            QPushButton {
                background: #0A84FF;
                color: #FFFFFF;
                border-radius: 6px;
                font-size: 10px;
                font-weight: bold;
                padding: 0 8px;
                border: none;
            }
            QPushButton:hover {
                background: #0071E3;
            }
        """)
        self.btn_search.clicked.connect(self._on_search_enter)
        s_layout.addWidget(self.btn_search)

        layout.addWidget(search_card)

        # 2. Autocomplete Results Dropdown List
        self.list_search_results = QListWidget(w)
        self.list_search_results.setFixedHeight(120)
        self.list_search_results.setStyleSheet("""
            QListWidget {
                background: rgba(28, 28, 34, 0.98);
                border: 1px solid rgba(10, 132, 255, 0.50);
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 11px;
                padding: 2px;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: rgba(10, 132, 255, 0.35);
                color: #FFFFFF;
            }
            QListWidget::item:selected {
                background: #0A84FF;
                color: #FFFFFF;
            }
        """)
        self.list_search_results.itemClicked.connect(self._on_search_item_clicked)
        self.list_search_results.hide()
        layout.addWidget(self.list_search_results)

        # 3. Popular City Quick Chips (2 clean rows)
        chips_frame = QFrame(w)
        chips_frame.setStyleSheet("background: transparent; border: none;")
        chips_vbox = QVBoxLayout(chips_frame)
        chips_vbox.setContentsMargins(0, 0, 0, 0)
        chips_vbox.setSpacing(4)

        chip_rows = [
            ["Москва", "СПб", "Новосибирск", "Екб", "Казань"],
            ["Воронеж", "Сочи", "Краснодар", "Уфа", "Самара"]
        ]
        chip_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.88);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                font-size: 10px;
                padding: 2px 4px;
            }
            QPushButton:hover {
                background: #0A84FF;
                color: #FFFFFF;
                border: none;
            }
        """
        for row in chip_rows:
            r_lay = QHBoxLayout()
            r_lay.setContentsMargins(0, 0, 0, 0)
            r_lay.setSpacing(4)
            for c_name in row:
                btn_chip = QPushButton(c_name, chips_frame)
                btn_chip.setFixedHeight(21)
                btn_chip.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_chip.setStyleSheet(chip_style)
                btn_chip.clicked.connect(lambda checked, city=c_name: self._select_city(city))
                r_lay.addWidget(btn_chip)
            chips_vbox.addLayout(r_lay)

        layout.addWidget(chips_frame)

        # 4. Main Weather Card
        weather_card = QFrame(w)
        weather_card.setStyleSheet("background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 12px; padding: 8px;")
        card_layout = QVBoxLayout(weather_card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(6)

        # Top row: icon + big temp + city name
        top_row = QHBoxLayout()
        self.lbl_w_icon = QLabel("⛅", weather_card)
        self.lbl_w_icon.setStyleSheet("font-size: 34px;")
        top_row.addWidget(self.lbl_w_icon)

        temp_col = QVBoxLayout()
        self.lbl_w_temp = QLabel("+2°C", weather_card)
        self.lbl_w_temp.setStyleSheet("color: #FFFFFF; font-size: 24px; font-weight: 800;")
        self.lbl_w_desc = QLabel("Определение погоды...", weather_card)
        self.lbl_w_desc.setStyleSheet("color: rgba(255, 255, 255, 0.70); font-size: 11px;")
        temp_col.addWidget(self.lbl_w_temp)
        temp_col.addWidget(self.lbl_w_desc)
        top_row.addLayout(temp_col)
        top_row.addStretch()
        card_layout.addLayout(top_row)

        # Details Grid: Humidity, Wind, Barometer
        grid_layout = QHBoxLayout()
        grid_layout.setContentsMargins(0, 2, 0, 0)

        self.lbl_w_hum = QLabel("💧 Влажность\n--%", weather_card)
        self.lbl_w_hum.setStyleSheet("color: #FFFFFF; font-size: 10px; text-align: center;")
        grid_layout.addWidget(self.lbl_w_hum)

        self.lbl_w_wind = QLabel("💨 Ветер\n-- м/с", weather_card)
        self.lbl_w_wind.setStyleSheet("color: #FFFFFF; font-size: 10px; text-align: center;")
        grid_layout.addWidget(self.lbl_w_wind)

        self.lbl_w_press = QLabel("🧭 Барометр\n754 мм", weather_card)
        self.lbl_w_press.setStyleSheet("color: #FFFFFF; font-size: 10px; text-align: center;")
        grid_layout.addWidget(self.lbl_w_press)
        card_layout.addLayout(grid_layout)

        layout.addWidget(weather_card)

        # 5. 3-Day Forecast Pills
        forecast_box = QHBoxLayout()
        forecast_box.setSpacing(6)
        for day, t, ic in [("Сегодня", "+4°", "🌦️"), ("Завтра", "+5°", "🌤️"), ("Вс", "+3°", "⛅")]:
            pill = QFrame(w)
            pill.setStyleSheet("background: rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 4px;")
            p_lay = QVBoxLayout(pill)
            p_lay.setContentsMargins(4, 2, 4, 2)
            p_lay.setSpacing(1)
            lbl_d = QLabel(day, pill)
            lbl_d.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 10px;")
            lbl_ic = QLabel(f"{ic} {t}", pill)
            lbl_ic.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: bold;")
            p_lay.addWidget(lbl_d, alignment=Qt.AlignmentFlag.AlignCenter)
            p_lay.addWidget(lbl_ic, alignment=Qt.AlignmentFlag.AlignCenter)
            forecast_box.addWidget(pill)
        layout.addLayout(forecast_box)

        # Search worker & debounce timer
        self.search_worker = None
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(280)
        self.search_timer.timeout.connect(self._execute_search)

        return w

    def _on_search_text_changed(self, text):
        text = text.strip()
        if len(text) < 2:
            self.list_search_results.hide()
            return
        self.search_timer.stop()
        self.search_timer.start()

    def _execute_search(self):
        query = self.input_search.text().strip()
        if len(query) < 2:
            self.list_search_results.hide()
            return
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
        self.search_worker = CitySearchWorker(query)
        self.search_worker.results_ready.connect(self._on_search_results_ready)
        self.search_worker.start()

    def _on_search_results_ready(self, results):
        self.list_search_results.clear()
        if not results:
            item = QListWidgetItem("Ничего не найдено")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_search_results.addItem(item)
            self.list_search_results.show()
            return

        for r in results:
            item = QListWidgetItem(f"📍 {r['display']}")
            item.setData(Qt.ItemDataRole.UserRole, r['name'])
            self.list_search_results.addItem(item)
        self.list_search_results.show()

    def _on_search_item_clicked(self, item):
        city = item.data(Qt.ItemDataRole.UserRole)
        if city:
            self._select_city(city)

    def _on_search_enter(self):
        if self.list_search_results.isVisible() and self.list_search_results.count() > 0:
            first_item = self.list_search_results.item(0)
            city = first_item.data(Qt.ItemDataRole.UserRole)
            if city:
                self._select_city(city)
                return
        text = self.input_search.text().strip()
        if text:
            self._select_city(text)

    def _clear_search(self):
        self.input_search.clear()
        self.list_search_results.hide()

    def _select_city(self, city_name):
        mapping = {"СПб": "Санкт-Петербург", "Екб": "Екатеринбург"}
        target_city = mapping.get(city_name, city_name)
        self.input_search.setText(target_city)
        self.list_search_results.hide()
        if self.parent_bar:
            self.parent_bar.set_custom_city(target_city)

    # -------------------------------------------------------------------------
    # Page 1: Music Player
    # -------------------------------------------------------------------------
    def _create_music_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(10)

        # Track Info Card
        track_card = QFrame(w)
        track_card.setStyleSheet("background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 12px; padding: 10px;")
        t_lay = QVBoxLayout(track_card)
        t_lay.setSpacing(4)

        self.lbl_m_track = QLabel("Нет активного трека", track_card)
        self.lbl_m_track.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700;")
        t_lay.addWidget(self.lbl_m_track)

        self.lbl_m_artist = QLabel("Воспроизведите музыку в любом приложении", track_card)
        self.lbl_m_artist.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-size: 11px;")
        t_lay.addWidget(self.lbl_m_artist)

        self.progress_music = QProgressBar(track_card)
        self.progress_music.setFixedHeight(4)
        self.progress_music.setTextVisible(False)
        self.progress_music.setValue(35)
        self.progress_music.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 2px;
                border: none;
            }
            QProgressBar::chunk {
                background: #0A84FF;
                border-radius: 2px;
            }
        """)
        t_lay.addWidget(self.progress_music)
        layout.addWidget(track_card)

        # Controls
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(12)

        self.btn_prev = QPushButton("⏮", w)
        self.btn_play = QPushButton("▶", w)
        self.btn_next = QPushButton("⏭", w)

        for btn in (self.btn_prev, self.btn_play, self.btn_next):
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.12);
                    color: #FFFFFF;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 18px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.25);
                }
            """)

        self.btn_play.setFixedSize(44, 44)
        self.btn_play.setStyleSheet("""
            QPushButton {
                background: #0A84FF;
                color: #FFFFFF;
                border-radius: 22px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0071E3;
            }
        """)

        self.btn_prev.clicked.connect(lambda: user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0))
        self.btn_play.clicked.connect(lambda: user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0))
        self.btn_next.clicked.connect(lambda: user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0))

        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_prev)
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.btn_next)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)
        return w

    # -------------------------------------------------------------------------
    # Page 2: Mini Task Manager
    # -------------------------------------------------------------------------
    def _create_tasks_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(10)

        # Overview Stats Card
        stats_card = QFrame(w)
        stats_card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 12px;
                padding: 10px;
            }
        """)
        s_lay = QVBoxLayout(stats_card)
        s_lay.setContentsMargins(10, 8, 10, 8)
        s_lay.setSpacing(8)

        # CPU row with progress bar
        cpu_row = QHBoxLayout()
        lbl_cpu_title = QLabel("Загрузка CPU:", stats_card)
        lbl_cpu_title.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 11px;")
        self.lbl_task_cpu = QLabel("0%", stats_card)
        self.lbl_task_cpu.setStyleSheet("color: #30D158; font-weight: bold; font-size: 12px; font-family: 'Consolas', monospace;")
        cpu_row.addWidget(lbl_cpu_title)
        cpu_row.addStretch()
        cpu_row.addWidget(self.lbl_task_cpu)
        s_lay.addLayout(cpu_row)

        self.bar_cpu = QProgressBar(stats_card)
        self.bar_cpu.setFixedHeight(6)
        self.bar_cpu.setTextVisible(False)
        self.bar_cpu.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.10);
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background: #30D158;
                border-radius: 3px;
            }
        """)
        s_lay.addWidget(self.bar_cpu)

        # RAM row with progress bar
        ram_row = QHBoxLayout()
        lbl_ram_title = QLabel("Использование RAM:", stats_card)
        lbl_ram_title.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 11px;")
        self.lbl_task_ram = QLabel("0%", stats_card)
        self.lbl_task_ram.setStyleSheet("color: #64D2FF; font-weight: bold; font-size: 12px; font-family: 'Consolas', monospace;")
        ram_row.addWidget(lbl_ram_title)
        ram_row.addStretch()
        ram_row.addWidget(self.lbl_task_ram)
        s_lay.addLayout(ram_row)

        self.bar_ram = QProgressBar(stats_card)
        self.bar_ram.setFixedHeight(6)
        self.bar_ram.setTextVisible(False)
        self.bar_ram.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.10);
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background: #64D2FF;
                border-radius: 3px;
            }
        """)
        s_lay.addWidget(self.bar_ram)

        layout.addWidget(stats_card)

        # Process List Card
        lbl_procs_header = QLabel("Топ процессов по памяти:", w)
        lbl_procs_header.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px; font-weight: 600;")
        layout.addWidget(lbl_procs_header)

        self.list_procs = QListWidget(w)
        self.list_procs.setFixedHeight(120)
        self.list_procs.setStyleSheet("""
            QListWidget {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                color: #FFFFFF;
                font-size: 11px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px 6px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
                font-family: 'Consolas', monospace;
            }
        """)
        layout.addWidget(self.list_procs)

        # Action: Flush RAM Button
        self.btn_flush_ram = QPushButton("⚡ Очистить кэш RAM", w)
        self.btn_flush_ram.setFixedHeight(32)
        self.btn_flush_ram.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_flush_ram.setStyleSheet("""
            QPushButton {
                background: rgba(48, 209, 88, 0.16);
                color: #30D158;
                border: 1px solid rgba(48, 209, 88, 0.35);
                border-radius: 8px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(48, 209, 88, 0.28);
                border: 1px solid rgba(48, 209, 88, 0.60);
            }
        """)
        self.btn_flush_ram.clicked.connect(self._flush_memory)
        layout.addWidget(self.btn_flush_ram)

        return w

    def _flush_memory(self):
        try:
            import gc
            gc.collect()
            kernel32.SetProcessWorkingSetSize(-1, -1, -1)
            self.btn_flush_ram.setText("✓ Память оптимизирована!")
            QTimer.singleShot(1500, lambda: self.btn_flush_ram.setText("⚡ Очистить кэш RAM"))
        except Exception as e:
            self.btn_flush_ram.setText(f"Ошибка: {e}")

    def update_tasks_view(self):
        cpu = int(psutil.cpu_percent())
        ram = int(psutil.virtual_memory().percent)
        self.lbl_task_cpu.setText(f"{cpu}%")
        self.lbl_task_ram.setText(f"{ram}%")
        if hasattr(self, 'bar_cpu'):
            self.bar_cpu.setValue(cpu)
        if hasattr(self, 'bar_ram'):
            self.bar_ram.setValue(ram)

        self.list_procs.clear()
        procs = []
        for p in psutil.process_iter(['name', 'memory_percent']):
            try:
                procs.append((p.info['name'] or 'process', p.info['memory_percent'] or 0.0))
            except Exception:
                pass
        procs.sort(key=lambda x: x[1], reverse=True)
        for name, m_pct in procs[:5]:
            item = QListWidgetItem(f"{name[:18]:<18} · {m_pct:.1f}% RAM")
            self.list_procs.addItem(item)

    # -------------------------------------------------------------------------
    # Page 3: Calendar & Notes
    # -------------------------------------------------------------------------
    def _create_calendar_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(8)

        now = datetime.datetime.now()
        lbl_date_header = QLabel(now.strftime("%B %Y").capitalize(), w)
        lbl_date_header.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl_date_header)

        # Quick Note Box
        lbl_note_title = QLabel("Быстрые заметки:", w)
        lbl_note_title.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        layout.addWidget(lbl_note_title)

        self.txt_quick_notes = QLineEdit(w)
        self.txt_quick_notes.setPlaceholderText("Нажмите Enter чтобы сохранить...")
        self.txt_quick_notes.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                color: #FFFFFF;
                padding: 6px;
                font-size: 11px;
            }
        """)
        self.txt_quick_notes.returnPressed.connect(self._save_quick_note)
        layout.addWidget(self.txt_quick_notes)

        self.list_notes = QListWidget(w)
        self.list_notes.setFixedHeight(110)
        self.list_notes.setStyleSheet("""
            QListWidget {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                color: #FFFFFF;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            }
        """)
        layout.addWidget(self.list_notes)
        self._load_cached_notes()
        return w

    def _save_quick_note(self):
        text = self.txt_quick_notes.text().strip()
        if text:
            time_str = datetime.datetime.now().strftime("%H:%M")
            self.list_notes.insertItem(0, f"• [{time_str}] {text}")
            self.txt_quick_notes.clear()
            self._save_cached_notes()

    def _load_cached_notes(self):
        try:
            cache_file = os.path.join(os.path.dirname(__file__), "notes_cache.json")
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    notes = json.load(f)
                    for n in notes[:10]:
                        self.list_notes.addItem(n)
        except Exception:
            pass

    def _save_cached_notes(self):
        try:
            cache_file = os.path.join(os.path.dirname(__file__), "notes_cache.json")
            notes = [self.list_notes.item(i).text() for i in range(self.list_notes.count())]
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(notes[:20], f, ensure_ascii=False)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Page 4: Tools & Clipboard
    # -------------------------------------------------------------------------
    def _create_tools_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(10)

        # Quick Actions Grid
        grid = QHBoxLayout()
        grid.setSpacing(8)

        self.btn_caffeine = QPushButton("☕ Не спать: Выкл", w)
        self.btn_caffeine.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_caffeine.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.18);
            }
        """)
        self.btn_caffeine.clicked.connect(self._toggle_caffeine_click)
        grid.addWidget(self.btn_caffeine)

        self.btn_snip = QPushButton("✂️ Ножницы", w)
        self.btn_snip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_snip.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.18);
            }
        """)
        self.btn_snip.clicked.connect(self._open_snipping_tool)
        grid.addWidget(self.btn_snip)
        layout.addLayout(grid)

        # Clipboard History Header
        lbl_clip = QLabel("📋 Последние скопированные элементы:", w)
        lbl_clip.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11px;")
        layout.addWidget(lbl_clip)

        self.list_clipboard = QListWidget(w)
        self.list_clipboard.setFixedHeight(120)
        self.list_clipboard.setStyleSheet("""
            QListWidget {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                color: #FFFFFF;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.10);
            }
        """)
        self.list_clipboard.itemClicked.connect(self._copy_item_back)
        layout.addWidget(self.list_clipboard)
        return w

    def _toggle_caffeine_click(self):
        if self.parent_bar:
            active = self.parent_bar.toggle_caffeine()
            if active:
                self.btn_caffeine.setText("☕ Не спать: ВКЛ")
                self.btn_caffeine.setStyleSheet("""
                    QPushButton {
                        background: rgba(10, 132, 255, 0.25);
                        color: #0A84FF;
                        border: 1px solid #0A84FF;
                        border-radius: 10px;
                        padding: 8px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                """)
            else:
                self.btn_caffeine.setText("☕ Не спать: Выкл")
                self.btn_caffeine.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08);
                        color: #FFFFFF;
                        border: 1px solid rgba(255, 255, 255, 0.12);
                        border-radius: 10px;
                        padding: 8px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                """)

    def _open_snipping_tool(self):
        try:
            os.system("start ms-screenclip:")
        except Exception:
            pass

    def _copy_item_back(self, item):
        text = item.text()
        QApplication.clipboard().setText(text)

    def add_clipboard_item(self, text):
        clean = text.strip().replace("\n", " ")
        if len(clean) > 35:
            clean = clean[:33] + "…"
        if self.list_clipboard.count() > 0 and self.list_clipboard.item(0).text() == clean:
            return
        self.list_clipboard.insertItem(0, clean)
        if self.list_clipboard.count() > 10:
            self.list_clipboard.takeItem(self.list_clipboard.count() - 1)

    # -------------------------------------------------------------------------
    # Public Show Navigation
    # -------------------------------------------------------------------------
    def show_tab(self, tab_idx, global_trigger_pos=None):
        self.current_tab = tab_idx
        titles = {
            0: "Погода",
            1: "Музыка",
            2: "Диспетчер задач",
            3: "Календарь и Заметки",
            4: "Инструменты"
        }
        title = titles.get(tab_idx, "Apple Status")
        self.lbl_flyout_title.setText(title)

        # 1. STRICT TAB ISOLATION: Explicitly hide all other pages, show ONLY active page
        for i in range(self.stack.count()):
            page = self.stack.widget(i)
            if i == tab_idx:
                page.setVisible(True)
                page.show()
                page.raise_()
            else:
                page.setVisible(False)
                page.hide()

        self.stack.setCurrentIndex(tab_idx)
        self._update_tab_pills(tab_idx)

        # 2. Page-specific data updates
        if tab_idx == 2:
            self.update_tasks_view()
        elif tab_idx == 0:
            if self.parent_bar:
                self.input_search.setText(self.parent_bar.weather_city)
                self.list_search_results.hide()
            self.input_search.clearFocus()
        elif tab_idx == 3:
            self._load_cached_notes()

        # 3. Dynamic Auto-Resize to fit each tab cleanly
        self.adjustSize()
        self.update()

        # 4. Position cleanly beneath trigger
        if global_trigger_pos:
            x = global_trigger_pos.x() - (self.width() // 2)
            y = global_trigger_pos.y()
            screen = QApplication.primaryScreen()
            if screen:
                geom = screen.availableGeometry()
                if x + self.width() > geom.right() - 8:
                    x = geom.right() - self.width() - 8
                if x < geom.left() + 8:
                    x = geom.left() + 8
            self.move(x, y)

        self.show()
        self.raise_()

    def leaveEvent(self, event):
        cursor = QCursor.pos()
        if not self.rect().contains(self.mapFromGlobal(cursor)):
            if self.parent_bar and not self.parent_bar.geometry().contains(cursor):
                if hasattr(self.parent_bar, "flyout_leave_timer"):
                    self.parent_bar.flyout_leave_timer.start(350)
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # macOS Liquid Frosted Glass Dark Fill
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)

        painter.fillPath(path, QBrush(QColor(22, 22, 26, 240)))
        pen = QPen(QColor(255, 255, 255, 30))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)


class AppleStatusBar(QWidget):
    """
    Apple-Grade Top-Right 100% Transparent Status Bar for Windows.
    - 100% completely transparent island background with DWM alpha=1 hit-testing.
    - Floating crisp typography with native drop-shadows.
    - Physical slide-up animation: smoothly slides up off-screen when idle.
    - Physical slide-down animation: smoothly slides down into view on hover near top edge.
    - Full contiguous spatial click mapping (zero dead spots).
    - Flyout auto-closes as soon as cursor leaves both the card and the bar.
    - Searchable weather engine for any city worldwide with autocomplete.
    - Modules: Weather, Music, PC Telemetry (CPU/RAM), Tools, Date & Clock.
    - Power / AC icon removed.
    """
    media_updated = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apple Status Bar")
        self.media_updated.connect(self._on_media_update)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        # State
        self.is_hovered = False
        self.is_slid_down = True
        self.caffeine_active = False

        # Geometry positions
        self.x_dock = 0
        self.y_visible = 6
        self.y_hidden = -31

        # Telemetry State
        self.cpu_pct = 0.0
        self.ram_pct = 0.0
        self.music_title = "Нет активного трека"
        self.music_artist = ""
        self.is_playing = False

        # Weather State
        self.weather_city = self._load_weather_city()
        self.weather_temp = "--°C"
        self.weather_icon = "⛅"
        self.weather_desc = "Загрузка..."
        self.weather_worker = None

        # Position Animation (Physical Slide Up / Down)
        self.anim_pos = QPropertyAnimation(self, b"pos")
        self.anim_pos.setDuration(240)
        self.anim_pos.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Auto-hide timer: slides up after 1.2s when idle
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(1200)
        self.hide_timer.timeout.connect(self._slide_up)

        # Flyout auto-close timer (350ms): closes flyout when cursor leaves flyout + bar
        self.flyout_leave_timer = QTimer(self)
        self.flyout_leave_timer.setSingleShot(True)
        self.flyout_leave_timer.setInterval(350)
        self.flyout_leave_timer.timeout.connect(self._on_flyout_leave_timeout)

        # Start visible for 6 seconds on initial launch so user sees it, then slide up
        QTimer.singleShot(6000, lambda: self._slide_up() if not self.is_hovered else None)

        # Active hover polling timer (100ms) - checks top bezel hotspot, window rect, and flyout
        self.hover_timer = QTimer(self)
        self.hover_timer.setInterval(100)
        self.hover_timer.timeout.connect(self._check_mouse_hover)
        self.hover_timer.start()

        # Weather refresh timer (every 20 minutes)
        self.weather_timer = QTimer(self)
        self.weather_timer.setInterval(20 * 60 * 1000)
        self.weather_timer.timeout.connect(self._fetch_weather)
        self.weather_timer.start()

        # Flyout Window
        self.flyout = AppleStatusFlyout(parent_bar=self)

        # Update Timers
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._update_clock_and_telemetry)
        self.clock_timer.start()

        # Clipboard listener
        try:
            QApplication.clipboard().dataChanged.connect(self._on_clipboard_change)
        except Exception:
            pass

        # Connect to Windows Media Engine
        self.media_watcher = None
        if HAS_MEDIA:
            try:
                self.media_watcher = WindowsMediaWatcher(on_update_callback=self.media_updated.emit)
            except Exception as e:
                print(f"[AppleStatusBar] Media watcher note: {e}")

        self._build_ui()
        self._reposition_top_right()
        self._update_clock_and_telemetry()
        self._fetch_weather()

    def _apply_shadow(self, widget):
        sh = QGraphicsDropShadowEffect(widget)
        sh.setColor(QColor(0, 0, 0, 220))
        sh.setBlurRadius(8)
        sh.setOffset(0, 1)
        widget.setGraphicsEffect(sh)

    def _build_ui(self):
        self.setFixedHeight(34)
        self.setMinimumWidth(500)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        # 1. Weather Module (ClickableLabel)
        self.lbl_weather = ClickableLabel(0, f"{self.weather_icon} {self.weather_temp}", self)
        self.lbl_weather.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600; padding: 2px 4px;")
        self._apply_shadow(self.lbl_weather)
        self.lbl_weather.clicked.connect(lambda idx: self._open_flyout(idx, self.lbl_weather))
        layout.addWidget(self.lbl_weather)

        layout.addWidget(self._create_separator())

        # 2. Seamless Music Module (ClickableLabel)
        self.lbl_music = ClickableLabel(1, f"🎵 {self.music_title}", self)
        self.lbl_music.setStyleSheet("color: #E2E8F0; font-size: 11px; font-weight: 500; padding: 2px 4px;")
        self.lbl_music.setMaximumWidth(210)
        self._apply_shadow(self.lbl_music)
        self.lbl_music.clicked.connect(lambda idx: self._open_flyout(idx, self.lbl_music))
        layout.addWidget(self.lbl_music)

        layout.addWidget(self._create_separator())

        # 3. PC Telemetry Module (CPU & RAM) (ClickableLabel)
        self.lbl_cpu = ClickableLabel(2, "CPU --%", self)
        self.lbl_cpu.setStyleSheet("color: #30D158; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace; padding: 2px 3px;")
        self._apply_shadow(self.lbl_cpu)
        self.lbl_cpu.clicked.connect(lambda idx: self._open_flyout(idx, self.lbl_cpu))
        layout.addWidget(self.lbl_cpu)

        self.lbl_ram = ClickableLabel(2, "RAM --%", self)
        self.lbl_ram.setStyleSheet("color: #64D2FF; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace; padding: 2px 3px;")
        self._apply_shadow(self.lbl_ram)
        self.lbl_ram.clicked.connect(lambda idx: self._open_flyout(idx, self.lbl_cpu))
        layout.addWidget(self.lbl_ram)

        layout.addWidget(self._create_separator())

        # 4. Quick Tools (Caffeine & Tools) (ClickableLabel)
        self.lbl_tools = ClickableLabel(4, "☕", self)
        self.lbl_tools.setStyleSheet("color: #FFFFFF; font-size: 12px; padding: 2px 6px;")
        self._apply_shadow(self.lbl_tools)
        self.lbl_tools.clicked.connect(lambda idx: self._open_flyout(idx, self.lbl_tools))
        layout.addWidget(self.lbl_tools)

        layout.addWidget(self._create_separator())

        # 5. Calendar & Clock (ClickableLabel)
        self.lbl_clock = ClickableLabel(3, "12:00", self)
        self.lbl_clock.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700; font-family: 'SF Pro Display', 'Segoe UI', sans-serif; padding: 2px 6px;")
        self._apply_shadow(self.lbl_clock)
        self.lbl_clock.clicked.connect(lambda idx: self._open_flyout(idx, self.lbl_clock))
        layout.addWidget(self.lbl_clock)

    def _create_separator(self):
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setFixedWidth(1)
        sep.setFixedHeight(14)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.20); border: none;")
        return sep

    # -------------------------------------------------------------------------
    # Full Spatial Click Dispatcher across Bar
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            # 1. Weather: from left edge to music x
            if pos.x() < self.lbl_music.x():
                self._open_flyout(0, self.lbl_weather)
            # 2. Music: from music x to CPU x
            elif pos.x() >= self.lbl_music.x() and pos.x() < self.lbl_cpu.x():
                self._open_flyout(1, self.lbl_music)
            # 3. CPU & RAM: from CPU x to tools x
            elif pos.x() >= self.lbl_cpu.x() and pos.x() < self.lbl_tools.x():
                self._open_flyout(2, self.lbl_cpu)
            # 4. Tools (☕): from tools x to clock x
            elif pos.x() >= self.lbl_tools.x() and pos.x() < self.lbl_clock.x():
                self._open_flyout(4, self.lbl_tools)
            # 5. Calendar & Clock: from clock x to right edge
            else:
                self._open_flyout(3, self.lbl_clock)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            # Only double-click over the music area triggers play/pause
            if pos.x() >= self.lbl_music.x() and pos.x() < self.lbl_cpu.x():
                user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
                user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    # -------------------------------------------------------------------------
    # Weather Management
    # -------------------------------------------------------------------------
    def _load_weather_city(self) -> str:
        try:
            cfg = os.path.join(os.path.dirname(__file__), "weather_config.json")
            if os.path.exists(cfg):
                with open(cfg, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("city", "Воронеж")
        except Exception:
            pass
        return "Воронеж"

    def _save_weather_city(self, city: str):
        try:
            cfg = os.path.join(os.path.dirname(__file__), "weather_config.json")
            with open(cfg, "w", encoding="utf-8") as f:
                json.dump({"city": city}, f, ensure_ascii=False)
        except Exception:
            pass

    def set_custom_city(self, city: str):
        self.weather_city = city
        self._save_weather_city(city)
        if hasattr(self, 'flyout') and self.flyout:
            self.flyout.lbl_w_desc.setText(f"Загрузка для {city}...")
        self._fetch_weather()

    def _fetch_weather(self):
        if self.weather_worker and self.weather_worker.isRunning():
            return
        self.weather_worker = WeatherWorker(city=self.weather_city)
        self.weather_worker.weather_fetched.connect(self._on_weather_fetched)
        self.weather_worker.start()

    def _on_weather_fetched(self, data: dict):
        self.weather_icon = data.get("icon", "⛅")
        self.weather_temp = data.get("temp", "+2°C")
        self.weather_desc = data.get("desc", "Ясно")
        self.weather_city = data.get("city", self.weather_city)

        self.lbl_weather.setText(f"{self.weather_icon} {self.weather_temp}")

        # Update Flyout Weather Page
        self.flyout.lbl_w_icon.setText(self.weather_icon)
        self.flyout.lbl_w_temp.setText(self.weather_temp)
        self.flyout.lbl_w_desc.setText(f"{self.weather_desc} · {self.weather_city}")
        self.flyout.lbl_w_hum.setText(f"💧 Влажность\n{data.get('humidity', '--%')}")
        self.flyout.lbl_w_wind.setText(f"💨 Ветер\n{data.get('wind', '-- м/с')}")
        self.flyout.input_search.setText(self.weather_city)

        self._reposition_top_right()

    # -------------------------------------------------------------------------
    # Flyout Opening & Auto-Hide
    # -------------------------------------------------------------------------
    def _open_flyout(self, tab_idx, trigger_widget):
        if self.flyout.isVisible() and self.flyout.current_tab == tab_idx:
            self.flyout.hide()
            return
        if not self.is_slid_down:
            self._slide_down()
        self.hide_timer.stop()
        self.flyout_leave_timer.stop()

        # Fixed anchor Y at visible bar bottom + 8px gap (never overlaps status bar!)
        anchor_y = self.y_visible + self.height() + 8
        anchor_x = self.x_dock + trigger_widget.x() + (trigger_widget.width() // 2)

        self.flyout.show_tab(tab_idx, QPoint(anchor_x, anchor_y))
        self.flyout.show()
        self.flyout.raise_()
        self.flyout.activateWindow()

    def _on_flyout_leave_timeout(self):
        if not self.flyout.isVisible():
            return
        cursor = QCursor.pos()
        in_flyout = self.flyout.geometry().contains(cursor)
        in_bar = self.geometry().contains(cursor)
        if not (in_flyout or in_bar):
            self.flyout.hide()
            if self.is_slid_down and not self.hide_timer.isActive():
                self.hide_timer.start()

    # -------------------------------------------------------------------------
    # Positioning & Slide Up/Down Mechanics
    # -------------------------------------------------------------------------
    def _reposition_top_right(self):
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            self.adjustSize()
            w = max(500, self.sizeHint().width() + 20)
            self.setFixedWidth(w)
            self.x_dock = avail.right() - w - 16
            self.y_visible = avail.top() + 6
            self.y_hidden = avail.top() - self.height() + 3
            current_y = self.y_visible if self.is_slid_down else self.y_hidden
            self.move(self.x_dock, current_y)

    def _slide_down(self):
        if self.is_slid_down:
            return
        self.is_slid_down = True
        self.is_hovered = True
        self.anim_pos.stop()
        self.anim_pos.setStartValue(self.pos())
        self.anim_pos.setEndValue(QPoint(self.x_dock, self.y_visible))
        self.anim_pos.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_pos.setDuration(240)
        self.anim_pos.start()

    def _slide_up(self):
        if not self.is_slid_down:
            return
        if self.flyout.isVisible():
            return
        self.is_slid_down = False
        self.is_hovered = False
        self.anim_pos.stop()
        self.anim_pos.setStartValue(self.pos())
        self.anim_pos.setEndValue(QPoint(self.x_dock, self.y_hidden))
        self.anim_pos.setEasingCurve(QEasingCurve.Type.InCubic)
        self.anim_pos.setDuration(280)
        self.anim_pos.start()

    def _check_mouse_hover(self):
        cursor = QCursor.pos()
        # Top-right hover hotspot: top edge of screen above bar or within dock bounds
        in_top_bezel = (cursor.y() <= 12 and cursor.x() >= (self.x_dock - 60) and cursor.x() <= (self.x_dock + self.width() + 60))
        in_bar = self.geometry().contains(cursor)
        in_flyout = self.flyout.isVisible() and self.flyout.geometry().contains(cursor)

        # 1. Flyout Auto-Hide: when cursor leaves BOTH flyout and bar
        if self.flyout.isVisible():
            if in_flyout or in_bar:
                self.flyout_leave_timer.stop()
            else:
                if not self.flyout_leave_timer.isActive():
                    self.flyout_leave_timer.start()

        # 2. Bar Slide-Up: when cursor leaves everything
        if in_top_bezel or in_bar or in_flyout:
            self.hide_timer.stop()
            if not self.is_slid_down:
                self._slide_down()
        else:
            if self.is_slid_down and not self.flyout.isVisible() and not self.hide_timer.isActive():
                self.hide_timer.start()

    def enterEvent(self, event):
        self.hide_timer.stop()
        self._slide_down()
        super().enterEvent(event)

    def leaveEvent(self, event):
        cursor = QCursor.pos()
        if self.rect().contains(self.mapFromGlobal(cursor)):
            super().leaveEvent(event)
            return
        if not self.flyout.isVisible():
            self.hide_timer.start()
        super().leaveEvent(event)

    # -------------------------------------------------------------------------
    # Telemetry Updates
    # -------------------------------------------------------------------------
    def _update_clock_and_telemetry(self):
        now = datetime.datetime.now()
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

        # Dynamic High CPU warning pulse
        if self.cpu_pct > 80:
            self.lbl_cpu.setStyleSheet("color: #FF453A; font-size: 11px; font-weight: 800; font-family: 'Consolas', monospace; padding: 2px 3px;")
        else:
            self.lbl_cpu.setStyleSheet("color: #30D158; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace; padding: 2px 3px;")

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

            # Update flyout page
            self.flyout.lbl_m_track.setText(self.music_title)
            self.flyout.lbl_m_artist.setText(self.music_artist or "Воспроизведение Windows")
            self.flyout.btn_play.setText("⏸" if self.is_playing else "▶")
        else:
            self.is_playing = False
            self.lbl_music.setText("🎵 Музыка выкл.")
            self.flyout.lbl_m_track.setText("Нет активного трека")
        self._reposition_top_right()

    def _on_clipboard_change(self):
        text = QApplication.clipboard().text()
        if text and len(text.strip()) > 0:
            self.flyout.add_clipboard_item(text)

    def toggle_caffeine(self) -> bool:
        self.caffeine_active = not self.caffeine_active
        if self.caffeine_active:
            kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
            self.lbl_tools.setStyleSheet("color: #0A84FF; font-size: 12px; font-weight: bold; padding: 2px 6px;")
        else:
            kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            self.lbl_tools.setStyleSheet("color: #FFFFFF; font-size: 12px; padding: 2px 6px;")
        return self.caffeine_active

    # -------------------------------------------------------------------------
    # Scroll-to-Control & Gestures
    # -------------------------------------------------------------------------
    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta > 0:
            user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
            user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
        elif delta < 0:
            user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
            user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(28, 28, 32, 0.95);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #0A84FF;
            }
        """)
        act_weather = QAction("⛅ Прогноз погоды", self)
        act_weather.triggered.connect(lambda: self._open_flyout(0, self.lbl_weather))
        menu.addAction(act_weather)

        act_music = QAction("🎵 Музыкальный плеер", self)
        act_music.triggered.connect(lambda: self._open_flyout(1, self.lbl_music))
        menu.addAction(act_music)

        act_tasks = QAction("⚡ Диспетчер задач", self)
        act_tasks.triggered.connect(lambda: self._open_flyout(2, self.lbl_cpu))
        menu.addAction(act_tasks)

        act_calendar = QAction("📅 Календарь и Заметки", self)
        act_calendar.triggered.connect(lambda: self._open_flyout(3, self.lbl_clock))
        menu.addAction(act_calendar)

        act_caffeine = QAction("☕ Режим Не спать (Caffeine)", self)
        act_caffeine.triggered.connect(self.toggle_caffeine)
        menu.addAction(act_caffeine)

        menu.addSeparator()

        act_quit = QAction("✕ Закрыть статус-бар", self)
        act_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(act_quit)

        menu.exec(event.globalPos())

    def paintEvent(self, event):
        # 100% Completely Transparent Island, but alpha=1 allows Windows DWM hit-testing
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    bar = AppleStatusBar()
    bar.show()
    sys.exit(app.exec())
