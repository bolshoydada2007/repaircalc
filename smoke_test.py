# Smoke-тест: проверяет, что проект жив целиком — база, тесты, API.
# Запуск: .venv\Scripts\python.exe smoke_test.py

import subprocess
import sys


def run(cmd: list[str], label: str) -> bool:
    print(f"[ ] {label}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[OK] {label}")
        return True
    print(f"[FAIL] {label}")
    print(result.stdout[-1500:])
    print(result.stderr[-1500:])
    return False


ok = True
ok &= run([sys.executable, "-m", "pytest", "tests", "-q"], "Тесты pytest")
ok &= run([sys.executable, "-m", "pytest", "tests/test_api.py", "-q"],
          "Эндпоинт расчёта")

print()
print("SMOKE OK — проект готов к демо" if ok else "SMOKE FAIL — см. вывод выше")
sys.exit(0 if ok else 1)
