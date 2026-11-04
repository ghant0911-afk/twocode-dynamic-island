import time
import urllib.request
import json
import threading
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

API_URL = "http://127.0.0.1:28282"

def simulate_user_click_allow():
    time.sleep(1.2)
    print("   [ПОЛЬЗОВАТЕЛЬ] Нажимает зеленую кнопку (Allow) в Dynamic Island...")
    req = urllib.request.Request(
        f"{API_URL}/api/decision",
        data=json.dumps({"decision": "allow"}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=3) as r:
        print("   [ОСТРОВ] Клик зарегистрирован:", r.read().decode('utf-8'))

def test_approval():
    print("======================================================")
    print(" [ТЕСТ] ИНТЕРАКТИВНОЕ ОДОБРЕНИЕ (ALLOW / DENY)")
    print("======================================================")

    # 1. Запрос разрешения
    t = threading.Thread(target=simulate_user_click_allow)
    t.start()

    print("1. [AI АГЕНТ] Запрашивает: 'Allow: git push origin main?'...")
    req = urllib.request.Request(
        f"{API_URL}/api/ask",
        data=json.dumps({
            "agent": "Claude Code",
            "question": "git push origin main?",
            "command": "git push origin main",
            "timeout": 5
        }).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        res = json.loads(r.read().decode('utf-8'))
        print("2. [AI АГЕНТ] Получил результат одобрения:", res)
        assert res.get("approved") is True, "Одобрение должно быть True!"

    t.join()
    print("[OK] Тест интерактивного одобрения успешно пройден на 100%!")

if __name__ == '__main__':
    test_approval()
