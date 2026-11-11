# -*- coding: utf-8 -*-
"""
Voice Engine & Wake Word Listener for TwoCode Dynamic Island Pro.
Features:
- Silero Neural TTS (Baya 48 kHz) with instant cache playback & SAPI fallback.
- Microphone Wake Word Listener ("Байя", "Привет", "Остров") with echo feedback suppression.
"""

import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import re
import sys
import time
import hashlib
import threading
from PyQt6.QtCore import QObject, pyqtSignal

APP_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_CACHE_DIR = os.path.join(APP_DIR, "voice_cache")
os.makedirs(VOICE_CACHE_DIR, exist_ok=True)

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

try:
    import win32com.client
    HAS_SAPI = True
except Exception:
    HAS_SAPI = False

try:
    import speech_recognition as sr
    import sounddevice as sd
    import numpy as np
    HAS_AUDIO_INPUT = True
except ImportError:
    HAS_AUDIO_INPUT = False


class VoiceBridge(QObject):
    speaking_state_changed = pyqtSignal(bool)
    mic_state_changed = pyqtSignal(bool)
    wake_word_detected = pyqtSignal(str)
    voice_phrase_recognized = pyqtSignal(str)

voice_bridge = VoiceBridge()


class VoiceEngine:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = VoiceEngine()
        return cls._instance

    def __init__(self):
        self.enabled = True
        self.is_speaking = False
        self.cache_dir = VOICE_CACHE_DIR
        self.tts = None
        self.silero_model = None
        self.device = None
        self._init_mixer()
        threading.Thread(target=self._init_silero, daemon=True).start()

    def _init_mixer(self):
        if not HAS_PYGAME:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=48000)
        except Exception:
            pass

    def _init_silero(self):
        try:
            import torch
            torch.set_num_threads(1)
            self.device = torch.device('cpu')

            # 1. Fast local package loading (100% offline, ~1.5s, 0 network calls)
            local_model_path = os.path.join(self.cache_dir, "silero_models", "v4_ru.pt")
            if os.path.exists(local_model_path):
                importer = torch.package.PackageImporter(local_model_path)
                self.silero_model = importer.load_pickle('tts_models', 'model')
                self.silero_model.to(self.device)
                print("[VoiceEngine] Silero Neural TTS (Baya 48kHz) loaded from project cache!")
                return

            # 2. Check global torch hub cache
            hub_model_path = os.path.expanduser("~/.cache/torch/hub/snakers4_silero-models_master/src/silero/model/v4_ru.pt")
            if os.path.exists(hub_model_path):
                importer = torch.package.PackageImporter(hub_model_path)
                self.silero_model = importer.load_pickle('tts_models', 'model')
                self.silero_model.to(self.device)
                print("[VoiceEngine] Silero Neural TTS loaded from torch hub cache!")
                return

            # 3. Check local directory via torch.hub (without network)
            hub_dir = os.path.expanduser("~/.cache/torch/hub/snakers4_silero-models_master")
            if os.path.exists(hub_dir):
                self.silero_model, _ = torch.hub.load(
                    repo_or_dir=hub_dir,
                    model='silero_tts',
                    language='ru',
                    speaker='v4_ru',
                    source='local',
                    trust_repo=True
                )
                self.silero_model.to(self.device)
                print("[VoiceEngine] Silero Neural TTS loaded from local hub dir!")
                return

            print("[VoiceEngine] Silero weights not found locally, using SAPI fallback.")
            self.silero_model = None
        except Exception as e:
            print(f"[VoiceEngine] Silero init error: {e}")
            self.silero_model = None

    def speak(self, text: str):
        if not self.enabled or not text:
            return

        clean = re.sub(r'[*_`#~\[\]()>]', ' ', text)
        clean = re.sub(r'https?://\S+', 'ссылка', clean)
        clean = re.sub(r'<\/?b>|<\/?i>|<\/?br>|<\/?p>', ' ', clean)
        clean = re.sub(r'[^\w\s\.,!\?\-—]', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if not clean:
            return

        h = hashlib.md5(clean.lower().encode('utf-8')).hexdigest()[:12]
        cache_file = os.path.join(self.cache_dir, f"baya_{h}.wav")

        def _play_file(filepath):
            try:
                import winsound
                self.is_speaking = True
                voice_bridge.speaking_state_changed.emit(True)
                winsound.PlaySound(filepath, winsound.SND_FILENAME)
            except Exception:
                try:
                    import soundfile as sf
                    import sounddevice as sd
                    data, fs = sf.read(filepath)
                    self.is_speaking = True
                    voice_bridge.speaking_state_changed.emit(True)
                    sd.play(data, fs)
                    sd.wait()
                except Exception:
                    pass
            finally:
                self.is_speaking = False
                voice_bridge.speaking_state_changed.emit(False)

        def _worker():
            if os.path.exists(cache_file):
                _play_file(cache_file)
                return

            if self.silero_model is None:
                self._init_silero()

            if self.silero_model:
                try:
                    import soundfile as sf
                    audio = self.silero_model.apply_tts(
                        text=clean,
                        speaker='baya',
                        sample_rate=48000,
                        put_accent=True,
                        put_yo=True
                    )
                    sf.write(cache_file, audio.numpy(), 48000)
                    _play_file(cache_file)
                    return
                except Exception as e:
                    print(f"[VoiceEngine] Silero Baya TTS generation error: {e}")

            # Fallback to SAPI
            try:
                if HAS_SAPI:
                    sapi = win32com.client.Dispatch("SAPI.SpVoice")
                    self.is_speaking = True
                    voice_bridge.speaking_state_changed.emit(True)
                    sapi.Speak(clean, 0)
            except Exception:
                pass
            finally:
                self.is_speaking = False
                voice_bridge.speaking_state_changed.emit(False)

        threading.Thread(target=_worker, daemon=True).start()


class VoiceInputEngine:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = VoiceInputEngine()
        return cls._instance

    def __init__(self):
        self.enabled = False  # Default to False until user toggles or activates
        self.is_active_dictation = False
        self.dialogue_active_until = 0.0
        self.ignore_until = 0.0
        self.sample_rate = 16000
        self.block_size = 2048
        self.energy_threshold = 750
        self.recognizer = sr.Recognizer() if HAS_AUDIO_INPUT else None
        self._thread = None
        self._stop_event = threading.Event()
        # Do NOT start audio stream at startup to prevent PortAudio WASAPI resource holding

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        voice_bridge.mic_state_changed.emit(self.enabled)
        if self.enabled:
            self.start()
        else:
            self.stop()

    def toggle(self):
        self.set_enabled(not self.enabled)
        return self.enabled

    def start(self):
        if not HAS_AUDIO_INPUT:
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _listen_loop(self):
        if not HAS_AUDIO_INPUT or not self.enabled:
            return
        ring_buffer = []
        is_speaking_phrase = False
        silence_chunks = 0
        max_silence_chunks = 8

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16', blocksize=self.block_size) as stream:
                while not self._stop_event.is_set() and self.enabled:
                    now = time.time()
                    if VoiceEngine.get().is_speaking or now < self.ignore_until:
                        time.sleep(0.08)
                        ring_buffer.clear()
                        is_speaking_phrase = False
                        continue

                    data, _ = stream.read(self.block_size)
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    amplitude = np.mean(np.abs(audio_chunk))

                    if not is_speaking_phrase and amplitude < self.energy_threshold:
                        self.energy_threshold = max(450, int(self.energy_threshold * 0.98 + (amplitude * 2.2) * 0.02))

                    if amplitude > self.energy_threshold * 1.35:
                        if not is_speaking_phrase:
                            is_speaking_phrase = True
                            silence_chunks = 0
                            ring_buffer = ring_buffer[-2:] if len(ring_buffer) >= 2 else []
                        ring_buffer.append(audio_chunk)
                        silence_chunks = 0
                    elif is_speaking_phrase:
                        ring_buffer.append(audio_chunk)
                        silence_chunks += 1
                        if silence_chunks >= max_silence_chunks:
                            is_speaking_phrase = False
                            silence_chunks = 0
                            if len(ring_buffer) >= 5:
                                audio_frames = np.concatenate(ring_buffer)
                                ring_buffer.clear()
                                self._dispatch_recognition(audio_frames)
                            else:
                                ring_buffer.clear()
                    else:
                        ring_buffer.append(audio_chunk)
                        if len(ring_buffer) > 3:
                            ring_buffer.pop(0)
        except Exception:
            pass

    def _dispatch_recognition(self, audio_frames):
        def _worker():
            try:
                import io
                import wave
                wav_io = io.BytesIO()
                with wave.open(wav_io, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(audio_frames.tobytes())
                wav_io.seek(0)

                with sr.AudioFile(wav_io) as source:
                    audio_data = self.recognizer.record(source)
                    text = self.recognizer.recognize_google(audio_data, language="ru-RU")
                    if not text:
                        return

                    text_clean = text.lower().strip()
                    wake_words = ["байя", "баия", "привет", "остров", "робот", "двушка"]
                    has_wake = any(w in text_clean for w in wake_words)
                    now = time.time()

                    if has_wake:
                        self.dialogue_active_until = now + 15.0
                        voice_bridge.wake_word_detected.emit(text)
                    elif now < self.dialogue_active_until:
                        self.dialogue_active_until = now + 15.0
                        voice_bridge.voice_phrase_recognized.emit(text)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()
