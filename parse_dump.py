import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from bs4 import BeautifulSoup
with open('D:/Dynamic_Island_Work/twocode_dump.html', encoding='utf-8', errors='replace') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

for sec in soup.find_all(['section', 'div']):
    c = ' '.join(sec.get('class', []))
    if any(k in c for k in ['hero', 'island', 'mockup', 'interactive', 'feature', 'card']):
        t = sec.get_text(separator=' | ', strip=True)[:150]
        if len(t) > 20:
            print(f'[{c}] -> {t}')
