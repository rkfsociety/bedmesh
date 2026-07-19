# SSH download cache AppData Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Скачанные по SSH cfg сохранять в `AppData/.../BedMesh Visualizer/cache/`, а не в CWD (часто Desktop).

**Architecture:** Добавить `get_cache_dir()` / `default_download_local_path()` рядом с логикой AppData в `AppConfig` (Win и Mac зеркально). `download_cfg_via_ssh` при пустом `local_path` пишет в этот путь и создаёт папку `cache`. Явный `local_path` не меняем. Desktop не чистим.

**Tech Stack:** Python 3, PyQt6 `QStandardPaths`, stdlib `unittest` (pytest в репо нет).

## Global Constraints

- Кэш: `…/BedMesh Visualizer/cache/` (подпапка `cache` внутри той же базы, что `AppConfig.base_dir`)
- Имена файлов без изменений: `download_{basename(remote_path)}` (fallback `temp_download.cfg`)
- Старые файлы на Desktop не удалять
- Android / webpanel / UI настройки пути — вне scope
- Win и Mac — одинаковое поведение по смыслу

## File map

| File | Role |
|---|---|
| `win/pyqt6/utils/app_config.py` | `get_cache_dir()`, `default_download_local_path()` |
| `win/pyqt6/core/ssh_client.py` | default target → cache |
| `win/pyqt6/utils/test_cache_paths.py` | unit-тесты путей (Win) |
| `mac/utils/app_config.py` | те же хелперы (Mac fallback) |
| `mac/core/ssh_client.py` | default target → cache |
| `mac/utils/test_cache_paths.py` | unit-тесты путей (Mac) |

---

### Task 1: Windows — хелперы пути кэша + тесты

**Files:**
- Modify: `win/pyqt6/utils/app_config.py`
- Create: `win/pyqt6/utils/test_cache_paths.py`

**Interfaces:**
- Produces: `def get_app_data_dir() -> str` — каталог AppData приложения (как `AppConfig.base_dir`), `makedirs` ok
- Produces: `def get_cache_dir() -> str` — `os.path.join(get_app_data_dir(), "cache")`, `makedirs` ok
- Produces: `def default_download_local_path(remote_path: str) -> str` — `join(get_cache_dir(), f"download_{basename or 'temp_download.cfg'}")`
- Consumes: `QStandardPaths.AppDataLocation` + fallback `%APPDATA%\rkfsociety\BedMesh Visualizer`

- [ ] **Step 1: Write failing tests**

Создать `win/pyqt6/utils/test_cache_paths.py`:

```python
import os
import tempfile
import unittest
from unittest.mock import patch

from app_config import default_download_local_path, get_cache_dir


class TestCachePaths(unittest.TestCase):
    def test_default_download_uses_cache_subdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app_config.get_app_data_dir", return_value=tmp):
                path = default_download_local_path("/userdata/app/gk/printer.cfg")
                self.assertEqual(path, os.path.join(tmp, "cache", "download_printer.cfg"))
                self.assertTrue(os.path.isdir(os.path.join(tmp, "cache")))

    def test_default_download_mutable_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app_config.get_app_data_dir", return_value=tmp):
                path = default_download_local_path("/userdata/app/gk/printer_mutable.cfg")
                self.assertEqual(
                    path,
                    os.path.join(tmp, "cache", "download_printer_mutable.cfg"),
                )

    def test_get_cache_dir_creates_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app_config.get_app_data_dir", return_value=tmp):
                cache = get_cache_dir()
                self.assertEqual(cache, os.path.join(tmp, "cache"))
                self.assertTrue(os.path.isdir(cache))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests — expect FAIL**

```powershell
cd F:\github\bedmesh\win\pyqt6\utils
python test_cache_paths.py -v
```

Expected: FAIL — `ImportError` или `AttributeError` (функций ещё нет).

- [ ] **Step 3: Implement helpers in `app_config.py`**

Добавить в `win/pyqt6/utils/app_config.py` (модульный уровень, до или после класса `AppConfig`):

```python
def get_app_data_dir() -> str:
    base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not base_dir:
        base_dir = os.path.join(os.getenv("APPDATA") or os.getcwd(), "rkfsociety", "BedMesh Visualizer")
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def get_cache_dir() -> str:
    cache_dir = os.path.join(get_app_data_dir(), "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def default_download_local_path(remote_path: str) -> str:
    base_name = os.path.basename(remote_path) or "temp_download.cfg"
    return os.path.join(get_cache_dir(), f"download_{base_name}")
```

В `AppConfig.__init__` заменить дублирование базы на:

```python
base_dir = get_app_data_dir()
```

(остальной `__init__` без изменений по смыслу).

- [ ] **Step 4: Run tests — expect PASS**

```powershell
cd F:\github\bedmesh\win\pyqt6\utils
python test_cache_paths.py -v
```

Expected: `OK` (3 tests).

- [ ] **Step 5: Commit**

```powershell
git add win/pyqt6/utils/app_config.py win/pyqt6/utils/test_cache_paths.py
git commit -m "feat(win): AppData cache path helpers for SSH downloads"
```

---

### Task 2: Windows — `download_cfg_via_ssh` пишет в cache

**Files:**
- Modify: `win/pyqt6/core/ssh_client.py` (блок `download_cfg_via_ssh`, ~строки 135–157)

**Interfaces:**
- Consumes: `from utils.app_config import default_download_local_path`
- Produces: при `local_path is None` — `target = default_download_local_path(remote_path)` (абсолютный путь в `cache/`)

- [ ] **Step 1: Wire default path**

В `win/pyqt6/core/ssh_client.py`:

1. Добавить импорт:

```python
from utils.app_config import default_download_local_path
```

2. В `download_cfg_via_ssh` заменить:

```python
target = local_path or f"download_{os.path.basename(remote_path) or TEMP_FILE_NAME}"
```

на:

```python
target = local_path or default_download_local_path(remote_path)
```

`TEMP_FILE_NAME` остаётся в модуле для совместимости / других мест; `default_download_local_path` уже использует тот же fallback `"temp_download.cfg"`.

- [ ] **Step 2: Smoke-check без SSH**

```powershell
cd F:\github\bedmesh\win\pyqt6
python -c "from utils.app_config import default_download_local_path; p=default_download_local_path('/userdata/app/gk/printer.cfg'); print(p); assert 'cache' in p.replace('/','\\\\') or p.lower().find('cache')>=0; assert p.endswith('download_printer.cfg')"
```

Expected: печать абсолютного пути с `\cache\download_printer.cfg`, без исключения.

- [ ] **Step 3: Commit**

```powershell
git add win/pyqt6/core/ssh_client.py
git commit -m "fix(win): store SSH cfg downloads under AppData/cache"
```

---

### Task 3: macOS — хелперы + тесты + ssh_client

**Files:**
- Modify: `mac/utils/app_config.py`
- Create: `mac/utils/test_cache_paths.py`
- Modify: `mac/core/ssh_client.py`

**Interfaces:**
- Produces: те же три функции, что в Task 1; Mac fallback базы: `~/Library/Application Support/rkfsociety/BedMesh Visualizer`
- Consumes в ssh: `from utils.app_config import default_download_local_path`

- [ ] **Step 1: Write failing tests**

Создать `mac/utils/test_cache_paths.py` — тот же код, что в Task 1 Step 1 (импорты `from app_config import ...`).

- [ ] **Step 2: Run tests — expect FAIL**

```powershell
cd F:\github\bedmesh\mac\utils
python test_cache_paths.py -v
```

Expected: FAIL (функций нет). На Windows-машине PyQt6 может отсутствовать в PATH для `mac/` — если импорт Qt падает, тесты с `patch("app_config.get_app_data_dir")` всё равно требуют успешного импорта модуля. В этом случае: реализовать хелперы сначала (Step 3), затем гонять тесты; либо запускать на macOS CI/локально.

- [ ] **Step 3: Implement helpers in `mac/utils/app_config.py`**

```python
def get_app_data_dir() -> str:
    base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not base_dir:
        home = os.path.expanduser("~")
        base_dir = os.path.join(home, "Library", "Application Support", "rkfsociety", "BedMesh Visualizer")
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def get_cache_dir() -> str:
    cache_dir = os.path.join(get_app_data_dir(), "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def default_download_local_path(remote_path: str) -> str:
    base_name = os.path.basename(remote_path) or "temp_download.cfg"
    return os.path.join(get_cache_dir(), f"download_{base_name}")
```

В `AppConfig.__init__`: `base_dir = get_app_data_dir()`.

- [ ] **Step 4: Wire `mac/core/ssh_client.py`**

Импорт:

```python
from utils.app_config import default_download_local_path
```

В `download_cfg_via_ssh`:

```python
target = local_path or default_download_local_path(remote_path)
```

- [ ] **Step 5: Run tests — expect PASS**

```powershell
cd F:\github\bedmesh\mac\utils
python test_cache_paths.py -v
```

Expected: `OK` (3 tests), если окружение может импортировать PyQt6.

- [ ] **Step 6: Commit**

```powershell
git add mac/utils/app_config.py mac/utils/test_cache_paths.py mac/core/ssh_client.py
git commit -m "fix(mac): store SSH cfg downloads under Application Support/cache"
```

---

### Task 4: Приёмка по spec (ручная)

**Files:** none (проверка поведения)

- [ ] **Step 1: Проверить критерии из spec**

| Критерий | Как проверить |
|---|---|
| download `printer.cfg` → `…/cache/download_printer.cfg` | SSH Download в UI Win; убедиться, что файл появился в `%APPDATA%\rkfsociety\BedMesh Visualizer\cache\`, а не на Desktop |
| fallback `printer_mutable.cfg` → тот же cache | если mesh пустой в printer.cfg — второй файл в той же папке |
| settings/logs не в `cache` | `settings.json` и `debug.log` остаются в корне AppData приложения |
| явный `local_path` | не ломаем: если когда-либо передают путь — пишем туда (код-ветка `local_path or …`) |

- [ ] **Step 2: Не удалять файлы с Desktop**

Убедиться, что код нигде не вызывает `os.remove` для Desktop/`download_printer*.cfg` вне cache.

- [ ] **Step 3: Final note in commit only if docs needed**

Документацию README не менять, если нет упоминания Desktop-путей. Если в README есть «скачивает на рабочий стол» — поправить одной строкой отдельным коммитом `docs: …`. Иначе шаг пропустить.

---

## Spec coverage (self-review)

| Spec requirement | Task |
|---|---|
| Путь `…/cache/` под AppData base | Task 1, 3 |
| default имена `download_*` | Task 1, 3 (`default_download_local_path`) |
| `makedirs` cache | Task 1, 3 (`get_cache_dir`) |
| `local_path` явный без изменений | Task 2, 3 |
| Win + Mac | Task 1–2, Task 3 |
| Не чистить Desktop | Task 4 + Global Constraints |
| settings/logs вне cache | Task 1/3: cache только подпапка; AppConfig.file_path без изменений смысла |

Placeholder scan: нет TBD/TODO. Сигнатуры `get_app_data_dir` / `get_cache_dir` / `default_download_local_path` согласованы между Task 1–3.
