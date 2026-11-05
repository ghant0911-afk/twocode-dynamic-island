import os
import hashlib
from silero_tts.silero_tts import SileroTTS

CACHE_DIR = r"C:\Users\bear_\.gemini\antigravity\scratch\Dynamic_Island_Work\voice_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

tts = SileroTTS(model_id='v4_ru', language='ru', speaker='baya', sample_rate=48000, put_accent=True, put_yo=True)

phrases = [
    "Я тебя люблю! Любовь в каждом пикселе!",
    "Мы сияем ярче всех звёзд!",
    "Посмотри, какие стильные очки!",
    "Обожаю музыку! Потанцуем под ритм?",
    "Ну пожалуйста! Я же такая милая!",
    "Какое прекрасное настроение!",
    "Лови игривое подмигивание!",
    "Хм, очень интересно! Что там новенького?",
    "Загружаю новую гениальную мысль!",
    "Готова к ретро-играм! В бой!",
    "Ой, щекотно! Не трогай носик!",
    "Ура, победа! Мы это сделали!",
    "Хи-хи, это было весело!",
    "Спокойной ночи, сладких снов!",
    "Бууу! Я сердитый робот!",
    "Ого! Вот это поворот!",
    "Пишу код без единого бага!",
    "Привет! Рада тебя слышать! Как твоё настроение сегодня?",
    "Привет-привет! Я на связи, готова покодить или просто поболтать!",
    "Здравствуй! Чем интересным сегодня займёмся?",
    "Привет! Все системы в норме, остров готов к общению!",
    "Отличная идея, приступаю!",
    "Сделано в лучшем виде!"
]

print(f"Pre-caching {len(phrases)} standard phrases with Silero Baya...")
for i, phrase in enumerate(phrases, 1):
    h = hashlib.md5(phrase.strip().lower().encode('utf-8')).hexdigest()[:12]
    out_path = os.path.join(CACHE_DIR, f"baya_{h}.wav")
    if not os.path.exists(out_path):
        try:
            tts.tts(phrase, out_path)
            print(f"[{i}/{len(phrases)}] Cached: {phrase[:30]}...")
        except Exception as e:
            print(f"[{i}/{len(phrases)}] Error: {e}")
    else:
        print(f"[{i}/{len(phrases)}] Already cached: {phrase[:30]}...")

print("CACHE PRE-WARMING COMPLETE!")
