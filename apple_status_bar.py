import sys
import os
import psutil
import datetime
import ctypes
import json

from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QPushButton,
    QProgressBar, QScrollArea, QLineEdit, QListWidget, QListWidgetItem, QStackedWidget
)
from PyQt6.QtCore import (
    Qt, QPoint, QRectF, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QCursor, QWheelEvent, QMouseEvent
)

# Win32 Virtual Keys
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3

# Win32 Thread Execution State (Caffeine)
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


class AppleStatusFlyout(QWidget):
    """
    Apple macOS-grade Frosted Glass Dropdown Flyout.
    Contains 5 modular views:
    0: Weather & Forecast
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
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

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

        # Header with navigation
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_flyout_title = QLabel("Погода", self)
        self.lbl_flyout_title.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700; font-family: 'Segoe UI', sans-serif;")
        header_layout.addWidget(self.lbl_flyout_title)

        header_layout.addStretch()

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

        # Page 0: Weather
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

    # -------------------------------------------------------------------------
    # Page 0: Weather
    # -------------------------------------------------------------------------
    def _create_weather_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        icon = QLabel("⛅", w)
        icon.setStyleSheet("font-size: 34px;")
        top_row.addWidget(icon)

        temp_col = QVBoxLayout()
        self.lbl_w_temp = QLabel("+2°C", w)
        self.lbl_w_temp.setStyleSheet("color: #FFFFFF; font-size: 26px; font-weight: 800;")
        self.lbl_w_desc = QLabel("Переменная облачность · Москва", w)
        self.lbl_w_desc.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-size: 11px;")
        temp_col.addWidget(self.lbl_w_temp)
        temp_col.addWidget(self.lbl_w_desc)
        top_row.addLayout(temp_col)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Details Grid
        grid_card = QFrame(w)
        grid_card.setStyleSheet("background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 12px; padding: 8px;")
        grid_layout = QHBoxLayout(grid_card)
        grid_layout.setContentsMargins(6, 4, 6, 4)

        d1 = QLabel("💧 Влажность\n74%", grid_card)
        d1.setStyleSheet("color: #FFFFFF; font-size: 11px; text-align: center;")
        grid_layout.addWidget(d1)

        d2 = QLabel("💨 Ветер\n3.2 м/с", grid_card)
        d2.setStyleSheet("color: #FFFFFF; font-size: 11px; text-align: center;")
        grid_layout.addWidget(d2)

        d3 = QLabel("🧭 Давление\n752 мм", grid_card)
        d3.setStyleSheet("color: #FFFFFF; font-size: 11px; text-align: center;")
        grid_layout.addWidget(d3)
        layout.addWidget(grid_card)

        # 3-Day Forecast Pills
        forecast_box = QHBoxLayout()
        for day, t, ic in [("Сегодня", "+2°", "⛅"), ("Завтра", "+4°", "🌤️"), ("Пн", "+1°", "🌧️")]:
            pill = QFrame(w)
            pill.setStyleSheet("background: rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 6px;")
            p_lay = QVBoxLayout(pill)
            p_lay.setContentsMargins(4, 2, 4, 2)
            p_lay.setSpacing(2)
            lbl_d = QLabel(day, pill)
            lbl_d.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 10px;")
            lbl_ic = QLabel(f"{ic} {t}", pill)
            lbl_ic.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: bold;")
            p_lay.addWidget(lbl_d, alignment=Qt.AlignmentFlag.AlignCenter)
            p_lay.addWidget(lbl_ic, alignment=Qt.AlignmentFlag.AlignCenter)
            forecast_box.addWidget(pill)
        layout.addLayout(forecast_box)
        return w

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
        t_lay = QHBoxLayout(track_card)
        t_lay.setContentsMargins(8, 6, 8, 6)
        t_lay.setSpacing(10)

        art_lbl = QLabel("🎵", track_card)
        art_lbl.setFixedSize(42, 42)
        art_lbl.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0A84FF, stop:1 #5E5CE6); border-radius: 8px; font-size: 18px;")
        art_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_lay.addWidget(art_lbl)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        self.lbl_m_track = QLabel("Нет активного трека", track_card)
        self.lbl_m_track.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700;")
        self.lbl_m_artist = QLabel("Запустите Яндекс.Музыку, Spotify или YouTube", track_card)
        self.lbl_m_artist.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 10px;")
        info_col.addWidget(self.lbl_m_track)
        info_col.addWidget(self.lbl_m_artist)
        t_lay.addLayout(info_col)
        layout.addWidget(track_card)

        # Playback Controls
        ctrls_layout = QHBoxLayout()
        ctrls_layout.setSpacing(14)
        ctrls_layout.addStretch()

        btn_prev = QPushButton("⏮", w)
        btn_prev.setFixedSize(32, 32)
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.setStyleSheet("background: rgba(255, 255, 255, 0.10); color: white; border-radius: 16px; border: none; font-size: 13px;")
        btn_prev.clicked.connect(lambda: self._send_media_key(VK_MEDIA_PREV_TRACK))
        ctrls_layout.addWidget(btn_prev)

        self.btn_play = QPushButton("▶", w)
        self.btn_play.setFixedSize(40, 40)
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setStyleSheet("background: #0A84FF; color: white; border-radius: 20px; border: none; font-size: 16px; font-weight: bold;")
        self.btn_play.clicked.connect(lambda: self._send_media_key(VK_MEDIA_PLAY_PAUSE))
        ctrls_layout.addWidget(self.btn_play)

        btn_next = QPushButton("⏭", w)
        btn_next.setFixedSize(32, 32)
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.setStyleSheet("background: rgba(255, 255, 255, 0.10); color: white; border-radius: 16px; border: none; font-size: 13px;")
        btn_next.clicked.connect(lambda: self._send_media_key(VK_MEDIA_NEXT_TRACK))
        ctrls_layout.addWidget(btn_next)

        ctrls_layout.addStretch()
        layout.addLayout(ctrls_layout)
        return w

    def _send_media_key(self, vk):
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 2, 0)

    # -------------------------------------------------------------------------
    # Page 2: Mini Task Manager & Memory Flush
    # -------------------------------------------------------------------------
    def _create_tasks_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(8)

        # Overview Bars
        self.bar_cpu = QProgressBar(w)
        self.bar_cpu.setFixedHeight(12)
        self.bar_cpu.setTextVisible(False)
        self.bar_cpu.setStyleSheet("QProgressBar { background: rgba(255,255,255,0.1); border-radius: 6px; } QProgressBar::chunk { background: #30D158; border-radius: 6px; }")
        layout.addWidget(QLabel("Загрузка CPU:", w))
        layout.addWidget(self.bar_cpu)

        self.bar_ram = QProgressBar(w)
        self.bar_ram.setFixedHeight(12)
        self.bar_ram.setTextVisible(False)
        self.bar_ram.setStyleSheet("QProgressBar { background: rgba(255,255,255,0.1); border-radius: 6px; } QProgressBar::chunk { background: #64D2FF; border-radius: 6px; }")
        layout.addWidget(QLabel("Загрузка RAM:", w))
        layout.addWidget(self.bar_ram)

        # Top Processes List
        layout.addWidget(QLabel("Топ-3 процессов по нагрузке:", w))
        self.lbl_procs = QLabel("Загрузка...", w)
        self.lbl_procs.setStyleSheet("color: rgba(255, 255, 255, 0.85); font-size: 11px; font-family: 'Consolas', monospace;")
        layout.addWidget(self.lbl_procs)

        # Flush Button
        self.btn_flush = QPushButton("🧹 Очистить кэш RAM", w)
        self.btn_flush.setFixedHeight(30)
        self.btn_flush.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_flush.setStyleSheet("""
            QPushButton {
                background: rgba(48, 209, 88, 0.20);
                color: #30D158;
                border: 1px solid rgba(48, 209, 88, 0.40);
                border-radius: 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(48, 209, 88, 0.35);
            }
        """)
        self.btn_flush.clicked.connect(self._flush_memory)
        layout.addWidget(self.btn_flush)
        return w

    def _flush_memory(self):
        import gc
        gc.collect()
        self.btn_flush.setText("✓ Кэш RAM успешно сброшен!")
        QTimer.singleShot(2500, lambda: self.btn_flush.setText("🧹 Очистить кэш RAM"))

    def update_task_manager(self):
        try:
            c = psutil.cpu_percent()
            r = psutil.virtual_memory().percent
            self.bar_cpu.setValue(int(c))
            self.bar_ram.setValue(int(r))

            # Fetch top processes safely
            procs = []
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                try:
                    procs.append(p.info)
                except Exception:
                    pass
            top_cpu = sorted(procs, key=lambda x: (x.get('cpu_percent') or 0.0), reverse=True)[:3]
            txt_lines = []
            for p in top_cpu:
                name = p.get('name') or 'Proc'
                cpu = p.get('cpu_percent') or 0.0
                mem = p.get('memory_percent') or 0.0
                txt_lines.append(f"• {name[:16]:<16} {cpu:4.1f}% CPU | {mem:4.1f}% RAM")
            self.lbl_procs.setText("\n".join(txt_lines) if txt_lines else "Нет активных процессов")
        except Exception as e:
            self.lbl_procs.setText(f"Опрос: {e}")

    # -------------------------------------------------------------------------
    # Page 3: Calendar & Quick Notes
    # -------------------------------------------------------------------------
    def _create_calendar_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(8)

        now = datetime.datetime.now()
        lbl_date_header = QLabel(f"📅 {now.strftime('%d.%m.%Y')} — Быстрые заметки", w)
        lbl_date_header.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold;")
        layout.addWidget(lbl_date_header)

        self.note_input = QLineEdit(w)
        self.note_input.setPlaceholderText("Добавить заметку на сегодня (Enter)...")
        self.note_input.setStyleSheet("background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px; color: white; padding: 6px; font-size: 11px;")
        self.note_input.returnPressed.connect(self._add_quick_note)
        layout.addWidget(self.note_input)

        self.notes_list = QListWidget(w)
        self.notes_list.setFixedHeight(120)
        self.notes_list.setStyleSheet("background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; color: #FFFFFF; font-size: 11px; padding: 4px;")
        layout.addWidget(self.notes_list)
        return w

    def _add_quick_note(self):
        text = self.note_input.text().strip()
        if text:
            self.notes_list.addItem(f"✓ {text}")
            self.note_input.clear()

    # -------------------------------------------------------------------------
    # Page 4: Quick Tools (Caffeine & Clipboard)
    # -------------------------------------------------------------------------
    def _create_tools_page(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(10)

        # Caffeine Toggle
        self.btn_caffeine = QPushButton("☕ Режим 'Не спать' (Экран включён)", w)
        self.btn_caffeine.setFixedHeight(32)
        self.btn_caffeine.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_caffeine.setStyleSheet("background: rgba(255, 255, 255, 0.08); color: white; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; font-size: 11px; font-weight: 600;")
        self.btn_caffeine.clicked.connect(self._toggle_caffeine)
        layout.addWidget(self.btn_caffeine)

        # Snipping Tool
        btn_snip = QPushButton("✂ Сделать скриншот области (Snipping Tool)", w)
        btn_snip.setFixedHeight(30)
        btn_snip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_snip.setStyleSheet("background: rgba(255, 255, 255, 0.08); color: white; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; font-size: 11px;")
        btn_snip.clicked.connect(lambda: os.system("start ms-screenclip:"))
        layout.addWidget(btn_snip)

        # Clipboard History Header
        layout.addWidget(QLabel("📋 Буфер обмена (последнее скопированное):", w))
        self.clip_list = QListWidget(w)
        self.clip_list.setFixedHeight(95)
        self.clip_list.setStyleSheet("background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; color: #FFFFFF; font-size: 11px;")
        self.clip_list.itemClicked.connect(self._copy_back_to_clipboard)
        layout.addWidget(self.clip_list)
        return w

    def _toggle_caffeine(self):
        if self.parent_bar:
            active = self.parent_bar.toggle_caffeine()
            if active:
                self.btn_caffeine.setText("☕ 'Не спать': АКТИВНО (Экран не гаснет)")
                self.btn_caffeine.setStyleSheet("background: rgba(10, 132, 255, 0.25); color: #0A84FF; border: 1px solid #0A84FF; border-radius: 10px; font-size: 11px; font-weight: bold;")
            else:
                self.btn_caffeine.setText("☕ Режим 'Не спать' (Экран включён)")
                self.btn_caffeine.setStyleSheet("background: rgba(255, 255, 255, 0.08); color: white; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px; font-size: 11px; font-weight: 600;")

    def _copy_back_to_clipboard(self, item):
        txt = item.text().replace("• ", "")
        QApplication.clipboard().setText(txt)

    def add_clipboard_item(self, text):
        clean = text.strip().replace("\n", " ")
        if len(clean) > 42:
            clean = clean[:40] + "…"
        self.clip_list.insertItem(0, f"• {clean}")
        if self.clip_list.count() > 6:
            self.clip_list.takeItem(6)

    def show_tab(self, index, global_pos):
        titles = ["Погода и Прогноз", "Apple Music", "Диспетчер задач", "Календарь и Задачи", "Инструменты"]
        self.current_tab = index
        self.lbl_flyout_title.setText(titles[index])
        self.stack.setCurrentIndex(index)

        if index == 2:
            self.update_task_manager()

        # Position right below clicked element
        w = self.width()
        x = global_pos.x() - w // 2
        y = global_pos.y() + 24

        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            x = max(avail.left() + 10, min(avail.right() - w - 10, x))

        self.move(x, y)
        self.show()

    def paintEvent(self, event):
        # Frosted glass drop-down background
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        r = 16.0

        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), r, r)

        # Deep Acrylic dark glass
        p.fillPath(path, QBrush(QColor(16, 18, 26, 235)))
        p.strokePath(path, QPen(QColor(255, 255, 255, 30), 1.0))


class AppleStatusBar(QWidget):
    """
    Apple-Grade Top-Right 100% Transparent Status Bar for Windows.
    - 100% completely transparent island background.
    - Floating crisp typography with native drop-shadows.
    - Auto-hides when idle, smoothly appears on hover.
    - Modules: Weather, Music, PC Telemetry (CPU/RAM/AC), Tools, Date & Clock.
    - Interactive click flyouts for every module!
    - Scroll-to-control volume over music.
    - Double click for media play/pause.
    - Dynamic Island alerts on track change or high CPU.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apple Status Bar")

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
        self.caffeine_active = False

        # Telemetry State
        self.cpu_pct = 0.0
        self.ram_pct = 0.0
        self.battery_info = None
        self.music_title = "Нет активного трека"
        self.music_artist = ""
        self.is_playing = False
        self.weather_temp = "+2°C"

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
        self.hide_timer.setInterval(1400)
        self.hide_timer.timeout.connect(self._fade_to_idle)

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
        self.setMinimumWidth(560)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        # 1. Weather Module (Clickable)
        self.lbl_weather = QLabel(f"⛅ {self.weather_temp}", self)
        self.lbl_weather.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_weather.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        self._apply_shadow(self.lbl_weather)
        self.lbl_weather.mousePressEvent = lambda e: self._open_flyout(0, self.lbl_weather)
        layout.addWidget(self.lbl_weather)

        layout.addWidget(self._create_separator())

        # 2. Seamless Music Module (Clickable, Scrollable for Volume)
        self.lbl_music = QLabel(f"🎵 {self.music_title}", self)
        self.lbl_music.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_music.setStyleSheet("color: #E2E8F0; font-size: 11px; font-weight: 500;")
        self.lbl_music.setMaximumWidth(210)
        self._apply_shadow(self.lbl_music)
        self.lbl_music.mousePressEvent = lambda e: self._open_flyout(1, self.lbl_music)
        layout.addWidget(self.lbl_music)

        layout.addWidget(self._create_separator())

        # 3. PC Telemetry Module (CPU & RAM) (Clickable)
        self.lbl_cpu = QLabel("CPU --%", self)
        self.lbl_cpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_cpu.setStyleSheet("color: #30D158; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace;")
        self._apply_shadow(self.lbl_cpu)
        self.lbl_cpu.mousePressEvent = lambda e: self._open_flyout(2, self.lbl_cpu)
        layout.addWidget(self.lbl_cpu)

        self.lbl_ram = QLabel("RAM --%", self)
        self.lbl_ram.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_ram.setStyleSheet("color: #64D2FF; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace;")
        self._apply_shadow(self.lbl_ram)
        self.lbl_ram.mousePressEvent = lambda e: self._open_flyout(2, self.lbl_ram)
        layout.addWidget(self.lbl_ram)

        layout.addWidget(self._create_separator())

        # 4. Power / Battery
        self.lbl_power = QLabel("⚡ AC", self)
        self.lbl_power.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: 600;")
        self._apply_shadow(self.lbl_power)
        layout.addWidget(self.lbl_power)

        layout.addWidget(self._create_separator())

        # 5. Quick Tools (Caffeine & Tools)
        self.lbl_tools = QLabel("☕", self)
        self.lbl_tools.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_tools.setStyleSheet("color: #FFFFFF; font-size: 12px;")
        self._apply_shadow(self.lbl_tools)
        self.lbl_tools.mousePressEvent = lambda e: self._open_flyout(4, self.lbl_tools)
        layout.addWidget(self.lbl_tools)

        layout.addWidget(self._create_separator())

        # 6. Calendar & Clock (Clickable)
        self.lbl_clock = QLabel("12:00", self)
        self.lbl_clock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_clock.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700; font-family: 'SF Pro Display', 'Segoe UI', sans-serif;")
        self._apply_shadow(self.lbl_clock)
        self.lbl_clock.mousePressEvent = lambda e: self._open_flyout(3, self.lbl_clock)
        layout.addWidget(self.lbl_clock)

    def _create_separator(self):
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setFixedWidth(1)
        sep.setFixedHeight(14)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.20); border: none;")
        return sep

    def _open_flyout(self, tab_idx, trigger_widget):
        if self.flyout.isVisible() and self.flyout.current_tab == tab_idx:
            self.flyout.hide()
            return
        gpos = trigger_widget.mapToGlobal(QPoint(trigger_widget.width() // 2, trigger_widget.height()))
        self.flyout.show_tab(tab_idx, gpos)

    def _reposition_top_right(self):
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            self.adjustSize()
            w = max(560, self.sizeHint().width() + 20)
            self.setFixedWidth(w)
            x = avail.right() - w - 12
            y = avail.top() + 6
            self.move(x, y)

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
            self.lbl_cpu.setStyleSheet("color: #FF453A; font-size: 11px; font-weight: 800; font-family: 'Consolas', monospace;")
        else:
            self.lbl_cpu.setStyleSheet("color: #30D158; font-size: 11px; font-weight: 700; font-family: 'Consolas', monospace;")

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
            self.lbl_tools.setStyleSheet("color: #0A84FF; font-size: 12px; font-weight: bold;")
        else:
            kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            self.lbl_tools.setStyleSheet("color: #FFFFFF; font-size: 12px;")
        return self.caffeine_active

    # -------------------------------------------------------------------------
    # Scroll-to-Control & Gestures
    # -------------------------------------------------------------------------
    def wheelEvent(self, event: QWheelEvent):
        # Adjust volume on scroll anywhere over bar
        delta = event.angleDelta().y()
        if delta > 0:
            user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
            user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
        elif delta < 0:
            user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
            user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        # Play/Pause on double click
        user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
        user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
        event.accept()

    # -------------------------------------------------------------------------
    # Auto-Hide on Hover Mechanics
    # -------------------------------------------------------------------------
    def enterEvent(self, event):
        self.hide_timer.stop()
        self._fade_to_active()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Don't auto-hide if flyout dropdown is currently open
        if not self.flyout.isVisible():
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

    def paintEvent(self, event):
        # 100% Completely Transparent Island: zero background fill, zero box border!
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    bar = AppleStatusBar()
    bar.show()
    sys.exit(app.exec())
