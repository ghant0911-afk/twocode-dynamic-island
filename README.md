# Minimalist Transparent Status Bar for Windows

An ultra-clean, transparent, floating desktop status bar for Windows 10 and 11, inspired by modern mobile and desktop operating system status lines.

---

## Key Features

- **100% Transparent Floating Island**: Clean typography with subtle drop-shadows that float seamlessly over any wallpaper.
- **Top-Right Auto-Hide Dock**: Stays docked at the top-right corner. Fades to 8% opacity when idle and smoothly brightens to 98% on hover.
- **Real-Time System Telemetry**: Live CPU and RAM usage tracking with high-load dynamic warnings (>80% CPU).
- **Windows Media Controller**: Direct integration with Windows System Media Transport Controls (SMTC) to display current track and artist seamlessly.
- **Weather Module**: Lightweight live weather indicators with 3-day forecast flyout and city search engine.
- **Desktop Weather Wallpaper Overlay (macOS Sonoma / iOS 17 Aesthetic)**:
  - Frosted liquid glass capsule floating directly on your desktop wallpaper.
  - **100% Non-Clickable / Click-Through**: Built with Win32 `WS_EX_TRANSPARENT` & `HWND_BOTTOM` so all mouse clicks, drag selections, and desktop right-clicks pass through with zero interference.
  - **Live Auto-Sync**: Automatically detects city changes chosen in the status bar.
  - **Atmospheric Particles**: Real-time subtle 30 FPS weather physics (rain, snow, sunny ambient motes).
  - Can be toggled on/off from the Tools tab (☕) or run standalone with `launch_weather_overlay.vbs`.
- **Interactive Flyout Widgets**:
  - ⛅ **Weather**: Current temperature, humidity, wind, and forecast.
  - 🎵 **Media Player**: Track info, progress bar, play/pause, next/previous controls.
  - ⚡ **Task Manager**: Top resource-consuming processes with a one-click RAM optimization trigger.
  - 📅 **Calendar & Notes**: Monthly view with quick persistent local note-taking.
  - ☕ **Utility Kit**: Caffeine keep-awake mode, Windows Snipping Tool launcher, and clipboard history.
- **Intuitive Gestures**:
  - **Mouse Wheel Scroll**: Adjust system volume up or down directly over the bar.
  - **Double Click**: Toggle media playback (play/pause).
  - **Right Click**: Quick context menu to toggle modules, settings, or exit.

---

## Installation & Setup

### Prerequisites
- Windows 10 or Windows 11
- Python 3.10 or higher

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Launch
Run in terminal:
```bash
python apple_status_bar.py
```

Or double-click `start.bat` for a quick launcher.
For silent background execution without a command prompt window, double-click `launch.vbs`.

---

## Technical Stack
- **PyQt6**: Core UI framework, frameless window, transparent canvas, smooth property animations.
- **psutil**: System hardware statistics (CPU, memory, battery).
- **winsdk**: Windows Runtime API integration for media sessions.
- **Win32 API**: Low-level input simulation (volume, media keys) and thread execution state management.

---

## License
MIT License. Free for personal and commercial use.
