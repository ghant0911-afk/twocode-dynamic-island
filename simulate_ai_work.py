import time
import urllib.request
import json
import sys

# Гарантируем UTF-8 вывод в любой консоли Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

API_URL = "http://127.0.0.1:28282"

def post(endpoint, data):
    try:
        req = urllib.request.Request(
            f"{API_URL}{endpoint}",
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print(f"Ошибка связи с островом ({endpoint}):", e)
        return None

def main():
    print("======================================================")
    print(" [AI-AGENT] ЗАПУСК СИМУЛЯЦИИ И ТЕСТИРОВАНИЯ ОСТРОВА")
    print("======================================================")
    print("Подключение к локальному IPC API http://127.0.0.1:28282...\n")

    time.sleep(1)

    # 1. Шаг: Агент начинает работу
    print("1. [AI СТАРТ] Агент начал анализ проекта...")
    res = post("/api/status", {
        "status": "working",
        "agent": "Antigravity",
        "action": "Анализ репозитория и кода..."
    })
    print("   Ответ острова:", res)
    time.sleep(3)

    # 2. Шаг: Агент пишет код
    print("2. [AI КОДИНГ] Агент рефакторит main.py...")
    res = post("/api/status", {
        "status": "working",
        "agent": "Antigravity",
        "action": "Рефакторинг main.py и стилей..."
    })
    print("   Ответ острова:", res)
    time.sleep(3)

    # 3. Шаг: Агент прогоняет тесты
    print("3. [AI ТЕСТЫ] Прогон автоматических тестов...")
    res = post("/api/status", {
        "status": "working",
        "agent": "Antigravity",
        "action": "Unit тесты: 12/12 пройдено..."
    })
    print("   Ответ острова:", res)
    time.sleep(3)

    # 4. Шаг: Финал и победный чим
    print("4. [AI УСПЕХ] Задача полностью завершена!")
    res = post("/api/done", {
        "message": "Все тесты пройдены на 100%! Код идеален!"
    })
    print("   Ответ острова:", res)

    print("\n[OK] Все тесты успешно выполнены! Остров отреагировал на все шаги.")

if __name__ == '__main__':
    main()
