import time
import urllib.request
import json
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

API_URL = "http://127.0.0.1:28282"

def post(endpoint, data):
    req = urllib.request.Request(
        f"{API_URL}{endpoint}",
        data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode('utf-8'))

def main():
    print("==================================================================")
    print(" 🚀 ДЕМОНСТРАЦИОННЫЙ ТЕСТОВЫЙ ПРОГОН TWOCODE DYNAMIC ISLAND 🚀")
    print("==================================================================")
    print("Смотрите в верхнюю часть экрана на остров!\n")
    time.sleep(1)

    # 1. СТАРТ РАБОТЫ АГЕНТА: Редактирование файла checkout.ts
    print("▶ 1. [АГЕНТ В РАБОТЕ]")
    print("     Проект: webshop | Агент: Claude Code")
    print("     Действие: Editing checkout.ts")
    print("     Дифф: - const total = 0  /  + const total = sum(items)")
    post("/api/status", {
        "status": "working",
        "project": "webshop",
        "agent": "Claude Code",
        "action": "Editing checkout.ts",
        "file": "checkout.ts",
        "step": "1/2",
        "expand": True,
        "diff": {
            "del": "- const total = 0",
            "add": "+ const total = sum(items)"
        }
    })
    print("     -> Остров развернулся, Robo сфокусирован, виден дифф с красной и зеленой подсветкой.\n")
    time.sleep(4.5)

    # 2. ЗАПРОС ОДОБРЕНИЯ У ПОЛЬЗОВАТЕЛЯ
    print("▶ 2. [ЗАПРОС ОДОБРЕНИЯ]")
    print("     Вопрос: Allow: git push origin main?")
    print("     -> Прозвучал сигнал привлечения внимания (Alert Chime)")
    print("     -> Появились кнопки [ Allow ] (салатовая) и [ Deny ] (темная)")
    
    # Отправляем запрос ask в фоновом потоке, так как сервер ожидает решения
    import threading
    def send_ask():
        post("/api/ask", {
            "agent": "Claude Code",
            "question": "git push origin main?",
            "command": "git push origin main",
            "timeout": 10
        })
    
    t = threading.Thread(target=send_ask)
    t.start()
    
    time.sleep(3.5)

    # 3. ПОЛЬЗОВАТЕЛЬ НАЖИМАЕТ ALLOW
    print("▶ 3. [ПОЛЬЗОВАТЕЛЬ ОДОБРЯЕТ ДЕЙСТВИЕ]")
    print("     -> Нажата кнопка (Allow)")
    post("/api/decision", {"decision": "allow"})
    t.join()
    print("     -> Robo получил глазки-сердечки (robo-heart.svg) ❤️")
    print("     -> Статус: Allowed, continuing...\n")
    time.sleep(3.5)

    # 4. ФИНАЛИЗАЦИЯ И ПОБЕДНЫЙ КОЛОКОЛЬЧИК
    print("▶ 4. [УСПЕШНОЕ ЗАВЕРШЕНИЕ ЗАДАЧИ]")
    print("     -> Проигрывается победный чим (Success Chime) 🔔")
    print("     -> Robo улыбается (robo-happy.svg) 🤖")
    print("     -> Сообщение: Stripe checkout is live. 48 tests passed.")
    post("/api/done", {
        "message": "Stripe checkout is live. 48 tests passed."
    })
    print("     -> Статус: Done ✅\n")
    time.sleep(5)

    print("==================================================================")
    print(" [100% УСПЕХ] Тестовый сценарий успешно завершен с кодом 0!")
    print("==================================================================")

if __name__ == '__main__':
    main()
