import asyncio
import threading
import time
import ctypes
from ctypes import wintypes

try:
    import winsdk.windows.media.control as wmc
    import winsdk.windows.storage.streams as streams
    HAS_WINSDK = True
except Exception:
    HAS_WINSDK = False

user32 = ctypes.windll.user32

class RealMediaState:
    def __init__(self):
        self.is_active = False
        self.is_playing = False
        self.title = "Нет активного плеера"
        self.artist = "Включите Яндекс.Музыку, Spotify или YouTube"
        self.app_id = ""
        self.position_sec = 0.0
        self.duration_sec = 0.0
        self.has_thumbnail = False
        self.thumbnail_bytes = None

class WindowsMediaWatcher:
    def __init__(self, on_update_callback=None):
        self.callback = on_update_callback
        self.state = RealMediaState()
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.run(self._async_loop())

    async def _async_loop(self):
        while self.running:
            try:
                await self._query_media()
            except Exception as e:
                pass
            await asyncio.sleep(0.5)

    async def _query_media(self):
        if not HAS_WINSDK:
            self._fallback_window_titles()
            return

        try:
            mgr = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
            session = mgr.get_current_session()
            if not session:
                sessions = mgr.get_sessions()
                if sessions and len(sessions) > 0:
                    session = sessions[0]

            if session:
                app_id = session.source_app_user_model_id or ""
                playback_info = session.get_playback_info()
                status = playback_info.playback_status if playback_info else 0
                is_playing = (status == 4 or status == 5) # Playing

                props = await session.try_get_media_properties_async()
                title = props.title if props and props.title else ""
                artist = props.artist if props and props.artist else ""

                timeline = session.get_timeline_properties()
                pos = timeline.position.total_seconds() if timeline and timeline.position else 0.0
                dur = timeline.end_time.total_seconds() if timeline and timeline.end_time else 0.0

                if not title:
                    self._fallback_window_titles()
                    return

                # Clean up app display names
                display_artist = artist
                if not display_artist:
                    if "yandex" in app_id.lower():
                        display_artist = "Яндекс.Музыка"
                    elif "spotify" in app_id.lower():
                        display_artist = "Spotify"
                    elif "chrome" in app_id.lower():
                        display_artist = "Google Chrome"
                    else:
                        display_artist = app_id.split("!")[-1] if "!" in app_id else app_id

                self.state.is_active = True
                self.state.is_playing = is_playing
                self.state.title = title
                self.state.artist = display_artist
                self.state.app_id = app_id
                self.state.position_sec = pos
                self.state.duration_sec = dur

                if self.callback:
                    self.callback(self.state)
            else:
                self._fallback_window_titles()
        except Exception:
            self._fallback_window_titles()

    def _fallback_window_titles(self):
        # Fallback to scanning visible window titles
        found_title = None
        found_artist = ""

        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        GetWindowText = user32.GetWindowTextW
        GetWindowTextLength = user32.GetWindowTextLengthW
        IsWindowVisible = user32.IsWindowVisible

        def enum_cb(hwnd, lParam):
            nonlocal found_title, found_artist
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    t = buff.value
                    t_lower = t.lower()
                    if "spotify" in t_lower and t not in ("Spotify Free", "Spotify Premium"):
                        found_title = t
                        found_artist = "Spotify"
                        return False
                    elif " - youtube" in t_lower:
                        clean = t.replace(" - YouTube", "").replace(" - Google Chrome", "").replace(" - Yandex", "")
                        found_title = clean
                        found_artist = "YouTube"
                        return False
                    elif "яндекс музыка" in t_lower or "yandex music" in t_lower:
                        found_title = t
                        found_artist = "Яндекс Музыка"
                        return False
            return True

        try:
            EnumWindows(EnumWindowsProc(enum_cb), 0)
        except Exception:
            pass

        if found_title:
            self.state.is_active = True
            self.state.is_playing = True
            self.state.title = found_title
            self.state.artist = found_artist
            if self.callback:
                self.callback(self.state)
        else:
            self.state.is_active = False
            self.state.title = "Нет активного трека"
            self.state.artist = "Запустите Яндекс.Музыку или Spotify"
            if self.callback:
                self.callback(self.state)

if __name__ == '__main__':
    def on_up(state):
        print(f"[MEDIA] Active={state.is_active} Playing={state.is_playing} | '{state.title}' by '{state.artist}' | {state.position_sec:.1f}/{state.duration_sec:.1f}s")

    w = WindowsMediaWatcher(on_up)
    time.sleep(1.5)
    w.running = False
