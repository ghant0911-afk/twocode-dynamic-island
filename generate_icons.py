import os

assets_dir = 'D:/Dynamic_Island_Work/assets'

icons = {
    'spotify.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
        <rect width="48" height="48" rx="12" fill="#1DB954"/>
        <path d="M33.6 28.5c-.4 0-.8-.1-1.1-.3-5.2-3.2-11.8-3.9-19.5-2.1-.8.2-1.6-.3-1.8-1.1-.2-.8.3-1.6 1.1-1.8 8.6-2 15.9-1.2 21.8 2.4.7.4 1 1.4.5 2.1-.2.5-.5.8-.9.8z" fill="#0F2E1B"/>
        <path d="M36.1 23.4c-.5 0-1-.2-1.4-.4-6.3-3.9-15.8-5-23.2-2.7-.9.3-1.9-.2-2.2-1.1-.3-.9.2-1.9 1.1-2.2 8.5-2.6 19-1.3 26.2 3.1.8.5 1.1 1.6.6 2.4-.3.6-.8.9-1.1.9z" fill="#0F2E1B"/>
        <path d="M36.9 18.2c-.6 0-1.1-.2-1.6-.5-7.4-4.4-19.7-4.8-26.8-2.7-1.1.3-2.3-.3-2.6-1.4-.3-1.1.3-2.3 1.4-2.6 8.3-2.5 21.8-2 30.3 3.1 1 .6 1.3 1.9.7 2.9-.4.7-1 .7-1.4.7z" fill="#0F2E1B"/>
    </svg>''',
    
    'focus.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="13" r="8" stroke="#D9653B" stroke-width="2" fill="#251610"/>
        <line x1="12" y1="9" x2="12" y2="13" stroke="#FF8C5A" stroke-width="2" stroke-linecap="round"/>
        <line x1="12" y1="13" x2="15" y2="13" stroke="#FF8C5A" stroke-width="2" stroke-linecap="round"/>
        <line x1="12" y1="1" x2="12" y2="3.5" stroke="#FF8C5A" stroke-width="2" stroke-linecap="round"/>
        <line x1="10" y1="1" x2="14" y2="1" stroke="#FF8C5A" stroke-width="2" stroke-linecap="round"/>
    </svg>''',

    'settings-tile.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
        <rect width="48" height="48" rx="12" fill="#7C68EE"/>
        <circle cx="24" cy="24" r="6" fill="none" stroke="#FFFFFF" stroke-width="3"/>
        <path d="M24 10v4m0 20v4m-14-14h4m20 0h4m-4.2-9.8-2.8 2.8m-14 14-2.8 2.8m0-19.6 2.8 2.8m14 14 2.8 2.8" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round"/>
    </svg>''',

    'home.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#A09D98" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 9.5l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
        <polyline points="9 22 9 12 15 12 15 22"/>
    </svg>''',

    'apps.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#A09D98" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="2"/>
        <rect x="14" y="3" width="7" height="7" rx="2"/>
        <rect x="14" y="14" width="7" height="7" rx="2"/>
        <rect x="3" y="14" width="7" height="7" rx="2"/>
    </svg>''',

    'volume.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#A09D98" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
    </svg>''',

    'mute.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#E55353" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
        <line x1="23" y1="9" x2="17" y2="15"/>
        <line x1="17" y1="9" x2="23" y2="15"/>
    </svg>''',

    'gear.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#A09D98" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>''',

    'chevron-up.svg': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#A09D98" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="18 15 12 9 6 15"/>
    </svg>'''
}

for name, content in icons.items():
    p = os.path.join(assets_dir, name)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print('Saved', name)
