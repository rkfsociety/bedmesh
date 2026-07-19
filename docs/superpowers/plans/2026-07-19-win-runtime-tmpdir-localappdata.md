# Win PyInstaller runtime-tmpdir → LocalAppData Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Распаковка onefile `_MEI*` при старте Win exe идёт в `%LOCALAPPDATA%\rkfsociety\BedMesh Visualizer\runtime\`, а не рядом с exe (Desktop).

**Architecture:** Флаг PyInstaller `--runtime-tmpdir` в CI указывает на LocalAppData (bootloader раскрывает `%LOCALAPPDATA%`). В bat автообновления перед стартом удаляются только каталоги `_MEI*` в папке exe (хвосты сборок с `--runtime-tmpdir .`). Версия `0.169-win`.

**Tech Stack:** GitHub Actions + PyInstaller onefile, Python 3.10, stdlib `unittest`.

## Global Constraints

- runtime path (verbatim): `%LOCALAPPDATA%\rkfsociety\BedMesh Visualizer\runtime`
- Не использовать `%APPDATA%` (Roaming) для `_MEI*`
- Чистить `_MEI*` только в `base_dir` exe при автообновлении; не чистить Desktop произвольно при обычном запуске
- macOS / Android / webpanel — вне scope
- Spec: `docs/superpowers/specs/2026-07-19-win-runtime-tmpdir-localappdata-design.md`

## File map

| File | Role |
|---|---|
| `win/pyqt6/utils/updater.py` | генерация bat: cleanup `_MEI*` у exe + актуальный комментарий про LocalAppData |
| `win/pyqt6/utils/test_updater_bat.py` | unit-тест содержимого bat |
| `.github/workflows/build_win_pyqt6.yml` | `--runtime-tmpdir` + body релиза |
| `win/pyqt6/utils/version.py` | `0.169-win` |

---

### Task 1: Updater bat — чистка `_MEI*` у exe + тест

**Files:**
- Modify: `win/pyqt6/utils/updater.py`
- Create: `win/pyqt6/utils/test_updater_bat.py`

**Interfaces:**
- Produces: `def _build_replace_bat_content(*, current_exe: str, new_exe_path: str, current_exe_name: str) -> str` — полный текст bat (строки с `\n`; запись в файл по-прежнему с `newline="\r\n"` и cp866)
- Consumes: те же пути, что сейчас пишет `_run_replace_script`

- [ ] **Step 1: Write failing test**

Создать `win/pyqt6/utils/test_updater_bat.py`:

```python
import os
import unittest

from updater import _build_replace_bat_content


class TestReplaceBatContent(unittest.TestCase):
    def test_cleans_mei_dirs_next_to_exe(self):
        base = r"C:\Users\roman\Desktop"
        content = _build_replace_bat_content(
            current_exe=os.path.join(base, "Bed.Mesh.Visualizer.exe"),
            new_exe_path=os.path.join(base, "BedMesh_Update_Temp.exe"),
            current_exe_name="Bed.Mesh.Visualizer.exe",
        )
        self.assertIn(r'for /d %%D in ("' + base + r'\_MEI*") do rd /s /q "%%~fD"', content)
        self.assertIn("LOCALAPPDATA", content)
        self.assertNotIn("--runtime-tmpdir .", content)

    def test_still_moves_update_exe(self):
        content = _build_replace_bat_content(
            current_exe=r"C:\app\Bed.Mesh.Visualizer.exe",
            new_exe_path=r"C:\app\BedMesh_Update_Temp.exe",
            current_exe_name="Bed.Mesh.Visualizer.exe",
        )
        self.assertIn(r'move /y "C:\app\BedMesh_Update_Temp.exe" "C:\app\Bed.Mesh.Visualizer.exe"', content)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test — expect FAIL**

Run (из `win/pyqt6/utils`):

```bash
python -m unittest test_updater_bat.py -v
```

Expected: FAIL — `ImportError` / нет `_build_replace_bat_content`.

- [ ] **Step 3: Implement `_build_replace_bat_content` и переключить `_run_replace_script`**

В `win/pyqt6/utils/updater.py` добавить функцию и использовать её в `_run_replace_script`.

Содержимое bat (логика):

1. `@echo off` / `setlocal` / `set tries=0`
2. `taskkill` текущего exe
3. `timeout /t 4`
4. loop: `del` current exe until gone
5. `move /y` new → current; если new ещё есть — `del`
6. **NEW:** `for /d %%D in ("{base_dir}\_MEI*") do rd /s /q "%%~fD" >nul 2>&1`  
   где `base_dir = os.path.dirname(current_exe)`
7. Комментарий (ASCII/через Python-строку, в bat как `rem`): runtime теперь LocalAppData, чистим только legacy `_MEI` у exe
8. `timeout /t 3`
9. startloop / start exe / tasklist retry как сейчас
10. `endlocal` / `del "%~f0"`

Пример тела хелпера:

```python
def _build_replace_bat_content(*, current_exe: str, new_exe_path: str, current_exe_name: str) -> str:
    base_dir = os.path.dirname(current_exe)
    lines = [
        "@echo off",
        "setlocal",
        "set tries=0",
        f'taskkill /f /im "{current_exe_name}" >nul 2>&1',
        "timeout /t 4 /nobreak > nul",
        ":loop",
        f'del /f /q "{current_exe}" >nul 2>&1',
        f'if exist "{current_exe}" (timeout /t 1 /nobreak > nul & goto loop)',
        f'move /y "{new_exe_path}" "{current_exe}" >nul',
        f'if exist "{new_exe_path}" del /f /q "{new_exe_path}" >nul 2>&1',
        "rem Legacy _MEI* next to exe (old --runtime-tmpdir .). New runtime: %LOCALAPPDATA%\\rkfsociety\\BedMesh Visualizer\\runtime",
        f'for /d %%D in ("{base_dir}\\_MEI*") do rd /s /q "%%~fD" >nul 2>&1',
        "timeout /t 3 /nobreak > nul",
        ":startloop",
        'set "RUNNING="',
        f'start "" "{current_exe}" >nul 2>&1',
        "timeout /t 2 /nobreak > nul",
        (
            f'for /f "tokens=*" %%p in (\'tasklist /fi "imagename eq {current_exe_name}" '
            f'^| find /i "{current_exe_name}" \') do set RUNNING=1'
        ),
        "if defined RUNNING goto started",
        "set /a tries+=1",
        "if %tries% GEQ 6 goto started",
        "goto startloop",
        ":started",
        "endlocal",
        'del "%~f0"',
        "",
    ]
    return "\n".join(lines)
```

В `_run_replace_script`:

```python
content = _build_replace_bat_content(
    current_exe=current_exe,
    new_exe_path=new_exe_path,
    current_exe_name=current_exe_name,
)
with open(bat_path, "w", encoding="cp866", newline="\r\n") as f:
    f.write(content)
```

Остальной код `_run_replace_script` (QMessageBox, Popen, `os._exit`) без изменений.

- [ ] **Step 4: Run test — expect PASS**

```bash
python -m unittest test_updater_bat.py -v
```

Expected: `OK` (2 tests).

- [ ] **Step 5: Commit**

```bash
git add win/pyqt6/utils/updater.py win/pyqt6/utils/test_updater_bat.py
git commit -m "fix(win): cleanup legacy _MEI next to exe on auto-update"
```

---

### Task 2: CI runtime-tmpdir + version 0.169-win

**Files:**
- Modify: `.github/workflows/build_win_pyqt6.yml`
- Modify: `win/pyqt6/utils/version.py`

**Interfaces:**
- Consumes: runtime path из Global Constraints
- Produces: сборка с новым `--runtime-tmpdir`; `VERSION = "0.169-win"`

- [ ] **Step 1: Сменить флаг PyInstaller**

В `.github/workflows/build_win_pyqt6.yml` шаг «Собрать exe», заменить строку:

```yaml
            --runtime-tmpdir . \
```

на:

```yaml
            --runtime-tmpdir "%LOCALAPPDATA%\rkfsociety\BedMesh Visualizer\runtime" \
```

(в bash-блоке workflow кавычки сохранить как в примере; путь с пробелами обязателен.)

- [ ] **Step 2: Обновить body релиза в том же workflow**

```yaml
          body: |
            ## Bed Mesh Visualizer ${{ github.ref_name }}

            Обновление с версии 0.168.

            ### 🛠️ Исправления
            - **Runtime**: распаковка `_MEI*` больше не на Desktop рядом с exe —
              `%LOCALAPPDATA%\rkfsociety\BedMesh Visualizer\runtime\`.
            - Автообновление подчищает старые `_MEI*` рядом с exe.

            ## Скачать
            - `Bed.Mesh.Visualizer.exe` — Windows (64-bit)
```

- [ ] **Step 3: Bump version**

`win/pyqt6/utils/version.py`:

```python
VERSION = "0.169-win"
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build_win_pyqt6.yml win/pyqt6/utils/version.py
git commit -m "fix(win): extract PyInstaller _MEI under LocalAppData, bump 0.169"
```

---

### Task 3: Локальная проверка (без полного PyInstaller, если нет времени CI)

**Files:** none (verify only)

- [ ] **Step 1: Повторить unit-тесты updater**

```bash
cd win/pyqt6/utils && python -m unittest test_updater_bat.py -v
```

Expected: PASS.

- [ ] **Step 2: Ручная приёмка после тега/CI (хозяин или агент с артефактом)**

1. Скачать `Bed.Mesh.Visualizer.exe` из `v0.169-win`.
2. Положить на Desktop, запустить.
3. На Desktop **нет** новой `_MEI*`.
4. Есть `%LOCALAPPDATA%\rkfsociety\BedMesh Visualizer\runtime\_MEI*\python310.dll`.
5. Нет диалога `Failed to load Python DLL`.

Тег/пуш релиза — только по явному запросу хозяина (в этом плане не создавать тег автоматически).

---

## Spec coverage (self-review)

| Spec requirement | Task |
|---|---|
| `--runtime-tmpdir` → LocalAppData path | Task 2 |
| Не Roaming `%APPDATA%` для MEI | Task 2 (путь LOCALAPPDATA) |
| Updater чистит `_MEI*` у exe | Task 1 |
| Bump 0.169-win + release notes | Task 2 |
| Не чистить Desktop `_MEI` при обычном запуске | соблюдено (только bat update) |
| mac/android вне scope | не трогаем |

Placeholder scan: нет TBD/TODO. Имена `_build_replace_bat_content` согласованы между Task 1 steps.
