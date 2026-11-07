import os

assets_dir = 'D:/Dynamic_Island_Work/assets'

svgs = {
    'robo-reading.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <!-- Antenna -->
        <line x1="50" y1="20" x2="50" y2="8" stroke="#D9653B" stroke-width="4" stroke-linecap="round"/>
        <circle cx="50" cy="7" r="5" fill="#30D158"/>
        <!-- Head -->
        <rect x="20" y="20" width="60" height="48" rx="18" fill="#FFFFFF" stroke="#E6E0D8" stroke-width="2"/>
        <!-- Screen Face -->
        <rect x="26" y="26" width="48" height="36" rx="12" fill="#181715"/>
        <!-- Reading Glasses -->
        <circle cx="38" cy="42" r="8" fill="none" stroke="#60A5FA" stroke-width="2"/>
        <circle cx="62" cy="42" r="8" fill="none" stroke="#60A5FA" stroke-width="2"/>
        <line x1="46" y1="42" x2="54" y2="42" stroke="#60A5FA" stroke-width="2"/>
        <!-- Eyes looking down at book -->
        <ellipse cx="38" cy="44" rx="3.5" ry="4" fill="#60A5FA"/>
        <ellipse cx="62" cy="44" rx="3.5" ry="4" fill="#60A5FA"/>
        <!-- Book in hands -->
        <path d="M30 76 Q50 70 70 76 L68 92 Q50 86 32 92 Z" fill="#D9653B"/>
        <path d="M50 72 L50 88" stroke="#FFFFFF" stroke-width="2"/>
        <line x1="36" y1="80" x2="46" y2="78" stroke="#FFF" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="36" y1="84" x2="46" y2="82" stroke="#FFF" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="54" y1="78" x2="64" y2="80" stroke="#FFF" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="54" y1="82" x2="64" y2="84" stroke="#FFF" stroke-width="1.5" stroke-linecap="round"/>
    </svg>''',

    'robo-thinking.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <!-- Glowing Idea Bulb on Antenna -->
        <line x1="50" y1="20" x2="50" y2="12" stroke="#D9653B" stroke-width="4" stroke-linecap="round"/>
        <circle cx="50" cy="8" r="7" fill="#FBBF24"/>
        <path d="M47 3 L53 3 M44 5 L46 7 M56 7 L54 5" stroke="#F59E0B" stroke-width="2" stroke-linecap="round"/>
        <!-- Head -->
        <rect x="20" y="22" width="60" height="48" rx="18" fill="#FFFFFF" stroke="#E6E0D8" stroke-width="2"/>
        <!-- Screen Face -->
        <rect x="26" y="28" width="48" height="36" rx="12" fill="#181715"/>
        <!-- Thinking Squinting Eyes looking up -->
        <ellipse cx="40" cy="40" rx="4" ry="5" fill="#F59E0B"/>
        <ellipse cx="60" cy="40" rx="4" ry="5" fill="#F59E0B"/>
        <!-- Cute Thinking Eyebrows -->
        <line x1="34" y1="33" x2="44" y2="36" stroke="#F59E0B" stroke-width="2.5" stroke-linecap="round"/>
        <line x1="56" y1="36" x2="66" y2="33" stroke="#F59E0B" stroke-width="2.5" stroke-linecap="round"/>
        <!-- Hand on Chin -->
        <circle cx="56" cy="66" r="6" fill="#FFFFFF" stroke="#E6E0D8" stroke-width="2"/>
        <path d="M42 56 Q50 60 56 56" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round"/>
    </svg>''',

    'robo-music.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <!-- DJ Headphones Arch -->
        <path d="M16 46 A34 34 0 0 1 84 46" fill="none" stroke="#8B5CF6" stroke-width="6" stroke-linecap="round"/>
        <rect x="12" y="38" width="10" height="20" rx="5" fill="#A78BFA"/>
        <rect x="78" y="38" width="10" height="20" rx="5" fill="#A78BFA"/>
        <!-- Antenna -->
        <line x1="50" y1="20" x2="50" y2="10" stroke="#D9653B" stroke-width="4" stroke-linecap="round"/>
        <circle cx="50" cy="8" r="5" fill="#EC4899"/>
        <!-- Head -->
        <rect x="22" y="22" width="56" height="46" rx="17" fill="#FFFFFF" stroke="#E6E0D8" stroke-width="2"/>
        <!-- Screen Face -->
        <rect x="28" y="28" width="44" height="34" rx="11" fill="#181715"/>
        <!-- Joyful Singing/Dancing Curved Eyes -->
        <path d="M34 44 Q40 37 46 44" fill="none" stroke="#EC4899" stroke-width="3.5" stroke-linecap="round"/>
        <path d="M54 44 Q60 37 66 44" fill="none" stroke="#EC4899" stroke-width="3.5" stroke-linecap="round"/>
        <!-- Cute Smile -->
        <path d="M45 52 Q50 56 55 52" fill="none" stroke="#EC4899" stroke-width="2.5" stroke-linecap="round"/>
        <!-- Musical notes -->
        <path d="M84 20 L84 10 L94 13 L94 23 M84 15 L94 18" stroke="#10B981" stroke-width="2" fill="none"/>
        <circle cx="82" cy="21" r="3" fill="#10B981"/>
        <circle cx="92" cy="24" r="3" fill="#10B981"/>
    </svg>''',

    'robo-party.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <!-- Party Hat -->
        <polygon points="50,2 38,24 62,24" fill="#F59E0B"/>
        <circle cx="50" cy="2" r="4" fill="#EF4444"/>
        <line x1="42" y1="12" x2="58" y2="12" stroke="#3B82F6" stroke-width="2"/>
        <line x1="40" y1="18" x2="60" y2="18" stroke="#10B981" stroke-width="2"/>
        <!-- Head -->
        <rect x="20" y="24" width="60" height="48" rx="18" fill="#FFFFFF" stroke="#E6E0D8" stroke-width="2"/>
        <!-- Screen Face -->
        <rect x="26" y="30" width="48" height="36" rx="12" fill="#181715"/>
        <!-- Starry Happy Eyes -->
        <path d="M38 42 L39 46 L43 47 L39 48 L38 52 L37 48 L33 47 L37 46 Z" fill="#30D158"/>
        <path d="M62 42 L63 46 L67 47 L63 48 L62 52 L61 48 L57 47 L61 46 Z" fill="#30D158"/>
        <!-- Big Smile -->
        <path d="M42 54 Q50 62 58 54" fill="none" stroke="#30D158" stroke-width="3" stroke-linecap="round"/>
        <!-- Confetti -->
        <circle cx="14" cy="26" r="3" fill="#EC4899"/>
        <rect x="80" y="28" width="5" height="5" fill="#3B82F6" transform="rotate(25 82 30)"/>
        <circle cx="86" cy="60" r="3" fill="#F59E0B"/>
        <circle cx="16" cy="64" r="3" fill="#10B981"/>
    </svg>'''
}

for name, content in svgs.items():
    p = os.path.join(assets_dir, name)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print('Generated', name)
