import sys
import os
import json
import ctypes
from ctypes import wintypes
import psutil
from datetime import datetime

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint, QSize
)
from PyQt6.QtGui import (
    QColor, QFont, QCursor, QPainter, QBrush, QPen, QLinearGradient,
    QIcon, QPixmap
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QProgressBar, QLineEdit, QSystemTrayIcon, QMenu,
    QGraphicsDropShadowEffect, QStackedWidget, QSlider, QScrollArea,
    QFrame
)

# --- Windows Multimedia & DWM APIs ---
user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

# Windows Virtual Keys
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3


def safe_launch(target):
    """Safely launches an app, shortcut (.lnk), url, or command without crashing."""
    if not target:
        return
    try:
        clean = target.strip()
        if clean.lower().startswith("start "):
            clean = clean[6:].strip()
        clean = clean.strip('"').strip("'")

        # 1. URL or web link
        if "://" in clean or clean.startswith("mailto:"):
            import webbrowser
            webbrowser.open(clean)
            return

        # 2. Local file / shortcut (.lnk, .exe)
        if os.path.exists(clean):
            os.startfile(clean)
            return

        # 3. Windows system command / URI
        try:
            os.startfile(clean)
        except Exception:
            import subprocess
            subprocess.Popen(f'start "" {target}', shell=True)
    except Exception as e:
        print("Launch error:", e)


def global_excepthook(exctype, value, tb):
    import traceback
    traceback.print_exception(exctype, value, tb)


sys.excepthook = global_excepthook


def send_vk(vk_code):
    user32.keybd_event(vk_code, 0, 0, 0)
    user32.keybd_event(vk_code, 0, 2, 0)


def make_window_topmost(hwnd):
    HWND_TOPMOST = -1
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)


def apply_acrylic_effect(hwnd):
    try:
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        backdrop_acrylic = ctypes.c_int(3)
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(backdrop_acrylic), ctypes.sizeof(backdrop_acrylic))
    except Exception:
        pass


def get_active_media_title():
    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    GetWindowText = user32.GetWindowTextW
    GetWindowTextLength = user32.GetWindowTextLengthW
    IsWindowVisible = user32.IsWindowVisible

    media_title = None

    def enum_cb(hwnd, lParam):
        nonlocal media_title
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                t = buff.value
                t_lower = t.lower()
                if "spotify" in t_lower and t != "Spotify Free" and t != "Spotify Premium":
                    media_title = f"Spotify: {t}"
                    return False
                elif " - youtube" in t_lower:
                    clean = t.replace(" - YouTube", "").replace(" - Google Chrome", "").replace(" - Microsoft​ Edge", "")
                    media_title = f"YouTube: {clean[:26]}"
                    return False
                elif "яндекс музыка" in t_lower or "yandex music" in t_lower:
                    media_title = f"Музыка: {t[:26]}"
                    return False
        return True

    try:
        EnumWindows(EnumWindowsProc(enum_cb), 0)
    except Exception:
        pass

    return media_title or "Звук Windows"


# =========================================================================
# CONFIG HELPER
# =========================================================================
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "opacity": 78,
    "accent_color": "#007AFF",
    "buttons": [
        {"title": "Проводник", "icon": "📁", "color1": "#0A84FF", "color2": "#0056B3", "cmd": "start explorer"},
        {"title": "Браузер", "icon": "🌐", "color1": "#5E5CE6", "color2": "#3634A3", "cmd": "start https://google.com"},
        {"title": "Диспетчер", "icon": "📈", "color1": "#30D158", "color2": "#1E8236", "cmd": "start taskmgr"},
        {"title": "Скриншот", "icon": "✂️", "color1": "#FF375F", "color2": "#B31238", "cmd": "start ms-screenclip:"},
        {"title": "Калькулятор", "icon": "🧮", "color1": "#FF9F0A", "color2": "#C97800", "cmd": "start calc"},
        {"title": "Блокнот", "icon": "📝", "color1": "#FFD60A", "color2": "#D49B00", "cmd": "start notepad"}
    ]
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# =========================================================================
# ЧИСТАЯ ПЛИТКА ПРИЛОЖЕНИЯ (БЕЗ ПОДПИСЕЙ-ПОДЗАГОЛОВКОВ)
# =========================================================================
class ToolTile(QPushButton):
    def __init__(self, icon_emoji, bg_start, bg_end, title, on_click, accent_color):
        super().__init__()
        self.setFixedSize(68, 62)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clicked.connect(on_click)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 5, 2, 4)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Яркий икон-бейдж
        icon_badge = QLabel(icon_emoji)
        icon_badge.setFixedSize(32, 32)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {bg_start}, stop:1 {bg_end});
                border-radius: 9px;
                font-size: 15px;
            }}
        """)
        layout.addWidget(icon_badge)

        # Только аккуратное название приложения (без лишнего текста)
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("color: #FFFFFF; font-size: 10px; font-weight: 600; font-family: 'Segoe UI';")
        layout.addWidget(lbl_title)

        self.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 11px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.14);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.22);
            }
        """)


# =========================================================================
# ГЛАВНОЕ ОКНО DYNAMIC ISLAND
# =========================================================================
class DynamicIsland(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dynamic Island Windows")
        self.cfg = load_config()

        screen = QApplication.primaryScreen().geometry()
        self.screen_w = screen.width()

        # Размеры
        self.COLLAPSED_W = 115
        self.COLLAPSED_H = 22
        self.TOP_OFFSET = 3

        self.EXPANDED_W = 490
        self.EXPANDED_H = 240

        self.is_expanded = False
        self.is_pinned = False
        self.leave_counter = 0

        # Флаги окна
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(0, 0)

        # СВЕРХШУСТРАЯ ПЛАВНАЯ АНИМАЦИЯ (150 мс, мгновенный отклик)
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(150)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self.on_anim_finished)

        self.init_ui()

        self.expanded_view.hide()
        self.collapsed_view.show()
        self.set_collapsed_geometry()

        # Быстрый опрос курсора: каждые 16 мс (~60 fps) для моментального срабатывания
        self.hover_timer = QTimer(self)
        self.hover_timer.setInterval(16)
        self.hover_timer.timeout.connect(self.check_cursor_hover)
        self.hover_timer.start()

        # Таймер обновления часов и статусов
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self.update_periodic)
        self.clock_timer.start()

        self.setup_tray_icon()

    def set_collapsed_geometry(self):
        x = (self.screen_w - self.COLLAPSED_W) // 2
        self.setGeometry(x, self.TOP_OFFSET, self.COLLAPSED_W, self.COLLAPSED_H)
        self.resize(self.COLLAPSED_W, self.COLLAPSED_H)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 0, 6, 4)
        self.main_layout.setSpacing(0)

        # ==========================================
        # 1. КОМПАКТНАЯ КАПЕЛЬКА
        # ==========================================
        self.collapsed_view = QWidget(self)
        self.collapsed_view.setFixedHeight(self.COLLAPSED_H)
        c_layout = QHBoxLayout(self.collapsed_view)
        c_layout.setContentsMargins(8, 0, 8, 0)
        c_layout.setSpacing(6)

        self.c_dot = QLabel("🟢")
        self.c_dot.setStyleSheet("font-size: 7px;")
        c_layout.addWidget(self.c_dot)

        self.c_title = QLabel("Island")
        self.c_title.setStyleSheet("color: #FFFFFF; font-size: 10px; font-weight: 700; font-family: 'Segoe UI';")
        c_layout.addWidget(self.c_title)

        c_layout.addStretch()

        self.c_cpu = QLabel("0%")
        self.c_cpu.setStyleSheet(f"color: {self.cfg['accent_color']}; font-size: 10px; font-weight: 600; font-family: 'Consolas', monospace;")
        c_layout.addWidget(self.c_cpu)

        self.main_layout.addWidget(self.collapsed_view)

        # ==========================================
        # 2. РАЗВЕРНУТАЯ ПАНЕЛЬ С ДВУМЯ ВКЛАДКАМИ
        # ==========================================
        self.expanded_view = QWidget(self)
        e_layout = QVBoxLayout(self.expanded_view)
        e_layout.setContentsMargins(4, 5, 4, 4)
        e_layout.setSpacing(5)

        # Верхняя строка: Заголовок + Часы + Настройки ⚙️ + Закрепить 📌 + Закрыть ✕
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)

        self.exp_title = QLabel("✨ Dynamic Island")
        self.exp_title.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold; font-family: 'Segoe UI';")
        header.addWidget(self.exp_title)

        self.lbl_clock = QLabel("")
        self.lbl_clock.setStyleSheet("color: #8E8E93; font-size: 11px; font-family: 'Consolas', monospace;")
        header.addWidget(self.lbl_clock)

        header.addStretch()

        # Кнопка Настроек ⚙️
        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setFixedSize(22, 22)
        self.btn_settings.setToolTip("Настройки (прозрачность, цвет, кнопки)")
        self.btn_settings.setStyleSheet(self.header_button_style(subtle=True))
        self.btn_settings.clicked.connect(self.toggle_settings)
        header.addWidget(self.btn_settings)

        # Кнопка Закрепить 📌
        self.btn_pin = QPushButton("📌")
        self.btn_pin.setFixedSize(22, 22)
        self.btn_pin.setToolTip("Закрепить (не сворачивать)")
        self.btn_pin.setStyleSheet(self.header_button_style(subtle=True))
        self.btn_pin.clicked.connect(self.toggle_pin)
        header.addWidget(self.btn_pin)

        # Кнопка Закрыть ✕
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setToolTip("Закрыть")
        btn_close.setStyleSheet(self.header_button_style(danger=True))
        btn_close.clicked.connect(QApplication.instance().quit)
        header.addWidget(btn_close)

        e_layout.addLayout(header)

        # СТЕК СТРАНИЦ: 0 - ГЛАВНЫЙ ЭКРАН, 1 - НАСТРОЙКИ
        self.pages = QStackedWidget(self)

        # --- СТРАНИЦА 0: ГЛАВНЫЙ ЭКРАН ---
        self.page_main = QWidget()
        page_main_layout = QVBoxLayout(self.page_main)
        page_main_layout.setContentsMargins(0, 0, 0, 0)
        page_main_layout.setSpacing(6)

        # Нагрузка процессора и памяти
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        cpu_col = QVBoxLayout()
        cpu_col.setSpacing(2)
        self.lbl_cpu = QLabel("CPU: 0%")
        self.lbl_cpu.setStyleSheet("color: #A0A0A5; font-size: 10px;")
        self.bar_cpu = QProgressBar()
        self.bar_cpu.setFixedHeight(4)
        self.bar_cpu.setTextVisible(False)
        self.bar_cpu.setStyleSheet(self.progress_style(self.cfg['accent_color']))
        cpu_col.addWidget(self.lbl_cpu)
        cpu_col.addWidget(self.bar_cpu)
        stats_layout.addLayout(cpu_col)

        ram_col = QVBoxLayout()
        ram_col.setSpacing(2)
        self.lbl_ram = QLabel("RAM: 0%")
        self.lbl_ram.setStyleSheet("color: #A0A0A5; font-size: 10px;")
        self.bar_ram = QProgressBar()
        self.bar_ram.setFixedHeight(4)
        self.bar_ram.setTextVisible(False)
        self.bar_ram.setStyleSheet(self.progress_style("#34C759"))
        ram_col.addWidget(self.lbl_ram)
        ram_col.addWidget(self.bar_ram)
        stats_layout.addLayout(ram_col)

        page_main_layout.addLayout(stats_layout)

        # Контейнер для сетки кнопок (динамический)
        self.grid_container = QWidget()
        self.tools_grid = QGridLayout(self.grid_container)
        self.tools_grid.setContentsMargins(0, 0, 0, 0)
        self.tools_grid.setSpacing(6)
        self.rebuild_tools_grid()
        page_main_layout.addWidget(self.grid_container)

        # Медиа-плеер
        media_box = QHBoxLayout()
        media_box.setSpacing(5)

        self.lbl_media = QLabel("🎵 Звук Windows")
        self.lbl_media.setStyleSheet("color: #A0A0A5; font-size: 10px;")
        media_box.addWidget(self.lbl_media)

        media_box.addStretch()

        btn_prev = QPushButton("⏮")
        btn_prev.setFixedSize(26, 24)
        btn_prev.setStyleSheet(self.header_button_style())
        btn_prev.clicked.connect(lambda: send_vk(VK_MEDIA_PREV_TRACK))
        media_box.addWidget(btn_prev)

        btn_play = QPushButton("⏯")
        btn_play.setFixedSize(28, 24)
        btn_play.setStyleSheet(self.header_button_style(highlight=True))
        btn_play.clicked.connect(lambda: send_vk(VK_MEDIA_PLAY_PAUSE))
        media_box.addWidget(btn_play)

        btn_next = QPushButton("⏭")
        btn_next.setFixedSize(26, 24)
        btn_next.setStyleSheet(self.header_button_style())
        btn_next.clicked.connect(lambda: send_vk(VK_MEDIA_NEXT_TRACK))
        media_box.addWidget(btn_next)

        btn_voldown = QPushButton("🔉")
        btn_voldown.setFixedSize(26, 24)
        btn_voldown.setStyleSheet(self.header_button_style())
        btn_voldown.clicked.connect(lambda: send_vk(VK_VOLUME_DOWN))
        media_box.addWidget(btn_voldown)

        btn_volup = QPushButton("🔊")
        btn_volup.setFixedSize(26, 24)
        btn_volup.setStyleSheet(self.header_button_style())
        btn_volup.clicked.connect(lambda: send_vk(VK_VOLUME_UP))
        media_box.addWidget(btn_volup)

        page_main_layout.addLayout(media_box)

        # Строка быстрого поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск в Google или запуск...")
        self.search_input.setFixedHeight(24)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: #FFFFFF;
                padding-left: 8px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.cfg['accent_color']};
                background: rgba(255, 255, 255, 0.12);
            }}
        """)
        self.search_input.returnPressed.connect(self.execute_search)
        page_main_layout.addWidget(self.search_input)

        self.pages.addWidget(self.page_main)

        # --- СТРАНИЦА 1: НАСТРОЙКИ (ПРОЗРАЧНОСТЬ, ЦВЕТ, КНОПКИ) ---
        self.page_settings = QWidget()
        page_set_layout = QVBoxLayout(self.page_settings)
        page_set_layout.setContentsMargins(4, 0, 4, 0)
        page_set_layout.setSpacing(6)

        # Регулировка прозрачности
        op_box = QHBoxLayout()
        self.lbl_opacity = QLabel(f"Прозрачность: {self.cfg['opacity']}%")
        self.lbl_opacity.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        op_box.addWidget(self.lbl_opacity)

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(30, 100)
        self.slider_opacity.setValue(self.cfg['opacity'])
        self.slider_opacity.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: rgba(255, 255, 255, 0.15);
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.cfg['accent_color']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #FFFFFF;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }}
        """)
        self.slider_opacity.valueChanged.connect(self.on_opacity_dragged)
        self.slider_opacity.sliderReleased.connect(self.on_opacity_released)
        op_box.addWidget(self.slider_opacity)
        page_set_layout.addLayout(op_box)

        # Выбор цвета темы
        color_box = QHBoxLayout()
        color_box.setSpacing(6)
        lbl_colors = QLabel("Цвет акцента:")
        lbl_colors.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        color_box.addWidget(lbl_colors)

        colors = [
            ("#007AFF", "Синий"),
            ("#AF52DE", "Фиолетовый"),
            ("#30D158", "Зеленый"),
            ("#FF9500", "Оранжевый"),
            ("#FF2D55", "Малиновый"),
            ("#64D2FF", "Неон")
        ]

        for hex_col, name in colors:
            btn_col = QPushButton()
            btn_col.setFixedSize(18, 18)
            btn_col.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            border_w = "2px solid #FFF" if hex_col.lower() == self.cfg['accent_color'].lower() else "1px solid rgba(255,255,255,0.3)"
            btn_col.setStyleSheet(f"background: {hex_col}; border-radius: 9px; border: {border_w};")
            btn_col.clicked.connect(lambda _, c=hex_col: self.on_accent_changed(c))
            color_box.addWidget(btn_col)

        color_box.addStretch()
        page_set_layout.addLayout(color_box)

        # Управление кнопками: список с удалением
        scroll = QScrollArea()
        scroll.setFixedHeight(65)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px;")

        self.btn_list_widget = QWidget()
        self.btn_list_layout = QVBoxLayout(self.btn_list_widget)
        self.btn_list_layout.setContentsMargins(4, 2, 4, 2)
        self.btn_list_layout.setSpacing(2)
        self.rebuild_settings_btn_list()
        scroll.setWidget(self.btn_list_widget)
        page_set_layout.addWidget(scroll)

        # Форма быстрого добавления новой кнопки
        add_box = QHBoxLayout()
        add_box.setSpacing(4)

        self.in_title = QLineEdit()
        self.in_title.setPlaceholderText("Имя (напр. Steam)")
        self.in_title.setFixedHeight(22)
        self.in_title.setStyleSheet("background: rgba(255,255,255,0.08); color: #FFF; border-radius: 4px; padding: 2px 4px; font-size: 10px;")
        add_box.addWidget(self.in_title)

        self.in_cmd = QLineEdit()
        self.in_cmd.setPlaceholderText("Команда/Путь")
        self.in_cmd.setFixedHeight(22)
        self.in_cmd.setStyleSheet("background: rgba(255,255,255,0.08); color: #FFF; border-radius: 4px; padding: 2px 4px; font-size: 10px;")
        add_box.addWidget(self.in_cmd)

        self.in_icon = QLineEdit()
        self.in_icon.setPlaceholderText("Иконка (🎮)")
        self.in_icon.setFixedWidth(50)
        self.in_icon.setFixedHeight(22)
        self.in_icon.setStyleSheet("background: rgba(255,255,255,0.08); color: #FFF; border-radius: 4px; padding: 2px 4px; font-size: 10px;")
        add_box.addWidget(self.in_icon)

        btn_add = QPushButton("+ Добавить")
        btn_add.setFixedHeight(22)
        btn_add.setStyleSheet(f"background: {self.cfg['accent_color']}; color: #FFF; border-radius: 4px; font-size: 10px; font-weight: bold; padding: 0 8px;")
        btn_add.clicked.connect(self.on_add_button)
        add_box.addWidget(btn_add)

        page_set_layout.addLayout(add_box)

        # Кнопка возврата на главный экран
        btn_back = QPushButton("← Готово / Назад")
        btn_back.setFixedHeight(22)
        btn_back.setStyleSheet("background: rgba(255,255,255,0.1); color: #FFF; border-radius: 4px; font-size: 10px; font-weight: 600;")
        btn_back.clicked.connect(self.toggle_settings)
        page_set_layout.addWidget(btn_back)

        self.pages.addWidget(self.page_settings)
        e_layout.addWidget(self.pages)

        self.main_layout.addWidget(self.expanded_view)

    def make_launcher(self, target_cmd):
        return lambda: safe_launch(target_cmd)

    # --- Перестройка сетки кнопок ---
    def rebuild_tools_grid(self):
        # Очистить старую сетку
        while self.tools_grid.count():
            item = self.tools_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Построить кнопки из конфига
        buttons = self.cfg.get("buttons", [])
        for i, b in enumerate(buttons):
            r, c = divmod(i, 6)
            if len(buttons) > 6:
                r, c = divmod(i, (len(buttons) + 1) // 2)
            else:
                r, c = divmod(i, 6)

            cmd = b.get("cmd", "")
            tile = ToolTile(
                b.get("icon", "📦"),
                b.get("color1", "#0A84FF"),
                b.get("color2", "#0056B3"),
                b.get("title", "App"),
                self.make_launcher(cmd),
                self.cfg["accent_color"]
            )
            self.tools_grid.addWidget(tile, r, c)

    def rebuild_settings_btn_list(self):
        while self.btn_list_layout.count():
            item = self.btn_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        buttons = self.cfg.get("buttons", [])
        for idx, b in enumerate(buttons):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(f"{b.get('icon', '📦')} {b.get('title', 'App')} ({b.get('cmd', '')})")
            lbl.setStyleSheet("color: #E0E0E5; font-size: 10px;")
            row.addWidget(lbl)
            row.addStretch()

            btn_del = QPushButton("❌")
            btn_del.setFixedSize(18, 18)
            btn_del.setToolTip("Удалить кнопку")
            btn_del.setStyleSheet("background: rgba(255, 59, 48, 0.3); border-radius: 4px; color: #FF3B30; font-size: 9px;")
            btn_del.clicked.connect(lambda _, i=idx: self.delete_button(i))
            row.addWidget(btn_del)

            w_row = QWidget()
            w_row.setLayout(row)
            self.btn_list_layout.addWidget(w_row)

    def on_add_button(self):
        title = self.in_title.text().strip()
        cmd = self.in_cmd.text().strip()
        icon = self.in_icon.text().strip() or "📦"

        if title and cmd:
            new_btn = {
                "title": title,
                "icon": icon,
                "color1": self.cfg["accent_color"],
                "color2": "#1C1C24",
                "cmd": cmd.strip()
            }
            self.cfg.setdefault("buttons", []).append(new_btn)
            save_config(self.cfg)
            self.rebuild_tools_grid()
            self.rebuild_settings_btn_list()
            self.in_title.clear()
            self.in_cmd.clear()
            self.in_icon.clear()

    def delete_button(self, idx):
        if 0 <= idx < len(self.cfg.get("buttons", [])):
            self.cfg["buttons"].pop(idx)
            save_config(self.cfg)
            self.rebuild_tools_grid()
            self.rebuild_settings_btn_list()

    def on_opacity_dragged(self, val):
        self.cfg["opacity"] = val
        self.lbl_opacity.setText(f"Прозрачность: {val}%")
        self.update()

    def on_opacity_released(self):
        save_config(self.cfg)

    def on_accent_changed(self, color_hex):
        self.cfg["accent_color"] = color_hex
        save_config(self.cfg)
        self.bar_cpu.setStyleSheet(self.progress_style(color_hex))
        self.c_cpu.setStyleSheet(f"color: {color_hex}; font-size: 10px; font-weight: 600; font-family: 'Consolas', monospace;")
        self.rebuild_tools_grid()
        self.update()

    def toggle_settings(self):
        curr = self.pages.currentIndex()
        next_page = 1 if curr == 0 else 0
        self.pages.setCurrentIndex(next_page)
        if next_page == 1:
            self.is_pinned = True
            self.btn_pin.setStyleSheet(f"background: {self.cfg['accent_color']}; border-radius: 5px; color: #FFF;")
        else:
            self.is_pinned = False
            self.btn_pin.setStyleSheet(self.header_button_style(subtle=True))

    # --- Мгновенный отклик курсора (Hover) ---
    def check_cursor_hover(self):
        cursor_pos = QCursor.pos()
        geo = self.geometry()

        if geo.contains(cursor_pos):
            self.leave_counter = 0
            if not self.is_expanded:
                self.expand()
        else:
            if self.is_expanded and not self.is_pinned:
                self.leave_counter += 1
                # 18 * 16ms = ~280ms задержка перед закрытием
                if self.leave_counter >= 18:
                    self.collapse()

    def expand(self):
        self.is_expanded = True
        self.collapsed_view.hide()
        self.expanded_view.show()

        target_x = (self.screen_w - self.EXPANDED_W) // 2
        target_rect = QRect(target_x, 4, self.EXPANDED_W, self.EXPANDED_H)

        self.anim.stop()
        self.anim.setDuration(150)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        self.anim.start()

    def collapse(self):
        self.is_expanded = False
        self.expanded_view.hide()
        self.collapsed_view.show()

        target_x = (self.screen_w - self.COLLAPSED_W) // 2
        target_rect = QRect(target_x, self.TOP_OFFSET, self.COLLAPSED_W, self.COLLAPSED_H)

        self.anim.stop()
        self.anim.setDuration(130)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        self.anim.start()

    def on_anim_finished(self):
        if not self.is_expanded:
            self.resize(self.COLLAPSED_W, self.COLLAPSED_H)

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        if self.is_pinned:
            self.btn_pin.setStyleSheet(f"background: {self.cfg['accent_color']}; border-radius: 5px; color: #FFF;")
        else:
            self.btn_pin.setStyleSheet(self.header_button_style(subtle=True))

    def execute_search(self):
        text = self.search_input.text().strip()
        if text:
            import urllib.parse
            url = "https://www.google.com/search?q=" + urllib.parse.quote(text)
            os.system(f"start {url}")
            self.search_input.clear()
            if not self.is_pinned:
                self.collapse()

    def update_periodic(self):
        now = datetime.now()
        self.lbl_clock.setText(now.strftime("%H:%M:%S"))

        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent

            self.c_cpu.setText(f"{int(cpu)}%")
            self.lbl_cpu.setText(f"CPU: {int(cpu)}%")
            self.bar_cpu.setValue(int(cpu))

            self.lbl_ram.setText(f"RAM: {int(ram)}%")
            self.bar_ram.setValue(int(ram))

            if self.is_expanded:
                title = get_active_media_title()
                self.lbl_media.setText(f"🎵 {title}")
        except Exception:
            pass

    # --- Рисование красивого полупрозрачного стекла (БЕЗ РЕЗКИХ ОБОДКОВ) ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        opacity_val = self.cfg.get("opacity", 78) / 100.0
        alpha_base = int(255 * opacity_val)
        alpha_top = int(alpha_base * 0.92)

        # Полностью убираем контур/ободок — чистое бесшовное стекло
        painter.setPen(Qt.PenStyle.NoPen)

        if not self.is_expanded:
            corner_radius = 11
            gradient = QLinearGradient(0, 0, 0, rect.height())
            gradient.setColorAt(0.0, QColor(24, 24, 30, alpha_top))
            gradient.setColorAt(1.0, QColor(10, 10, 14, alpha_base))

            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(rect, corner_radius, corner_radius)
        else:
            corner_radius = 18
            gradient = QLinearGradient(0, 0, 0, rect.height())
            gradient.setColorAt(0.0, QColor(24, 24, 30, alpha_top))
            gradient.setColorAt(1.0, QColor(10, 10, 14, alpha_base))

            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(rect, corner_radius, corner_radius)

    def setup_tray_icon(self):
        self.tray = QSystemTrayIcon(self)

        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(self.cfg.get("accent_color", "#007AFF")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(4, 10, 24, 12, 6, 6)
        p.end()

        self.tray.setIcon(QIcon(pix))
        self.tray.setToolTip("Dynamic Island Windows")

        menu = QMenu()
        act_show = menu.addAction("Развернуть / Свернуть")
        act_show.triggered.connect(lambda: self.expand() if not self.is_expanded else self.collapse())
        act_set = menu.addAction("Настройки")
        act_set.triggered.connect(self.toggle_settings)
        act_pin = menu.addAction("Закрепить (Pin)")
        act_pin.triggered.connect(self.toggle_pin)
        menu.addSeparator()
        act_quit = menu.addAction("Выход")
        act_quit.triggered.connect(QApplication.instance().quit)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def header_button_style(self, subtle=False, danger=False, highlight=False):
        if danger:
            return """
                QPushButton {
                    background: rgba(255, 59, 48, 0.25);
                    border: 1px solid rgba(255, 59, 48, 0.4);
                    border-radius: 5px;
                    color: #FF6961;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background: rgba(255, 59, 48, 0.55);
                    color: #FFFFFF;
                }
            """
        if highlight:
            return f"""
                QPushButton {{
                    background: {self.cfg['accent_color']};
                    border-radius: 5px;
                    color: #FFFFFF;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    opacity: 0.85;
                }}
            """
        bg = "rgba(255, 255, 255, 0.06)" if subtle else "rgba(255, 255, 255, 0.1)"
        return f"""
            QPushButton {{
                background: {bg};
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.2);
            }}
        """

    def progress_style(self, color):
        return f"""
            QProgressBar {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 2px;
            }}
        """


def main():
    app = QApplication(sys.argv)
    island = DynamicIsland()
    island.show()
    hwnd = int(island.winId())
    make_window_topmost(hwnd)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
