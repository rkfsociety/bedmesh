# SSH download: кэш cfg в AppData — design

Дата: 2026-07-19  
Статус: approved for planning  
Область: `win/pyqt6`, `mac` (desktop SSH download)

## Цель

Сохранять скачанные по SSH cfg (`download_printer.cfg`, `download_printer_mutable.cfg` и аналоги) не в текущую рабочую директорию (часто Desktop), а в подпапку `cache` внутри AppData приложения.

## Проблема

`download_cfg_via_ssh` при `local_path is None` пишет относительный путь:

`download_{basename(remote_path)}`

Файл оказывается в CWD процесса. При запуске с рабочего стола / ярлыка — на Desktop.

## Решение

### Путь кэша

Та же база, что у `AppConfig.base_dir`, плюс `cache`:

| Платформа | Путь |
|-----------|------|
| Windows | `%APPDATA%\rkfsociety\BedMesh Visualizer\cache\` |
| macOS | `~/Library/Application Support/rkfsociety/BedMesh Visualizer/cache/` |

Fallback базы — как в существующих `AppConfig` / `logger` (env / home), без новой схемы имён.

### Поведение `download_cfg_via_ssh`

1. Если передан абсолютный/явный `local_path` — поведение без изменений (писать туда).
2. Если `local_path` не задан:
   - `os.makedirs(cache_dir, exist_ok=True)`
   - цель: `os.path.join(cache_dir, f"download_{basename or TEMP_FILE_NAME}")`
3. Возвращать полный путь к локальному файлу (как сейчас возвращается `target`).

### Хелпер пути

Небольшой общий способ получить `cache_dir` (предпочтительно рядом с уже используемой AppData-логикой — `AppConfig.base_dir` или тонкий helper в utils), чтобы Win и Mac не разъехались по строкам путей.

Рекомендуемый минимум: функция вроде `get_cache_dir()` / использование `AppConfig().base_dir + "/cache"`, вызываемая из `download_cfg_via_ssh` когда `local_path` пуст.

### Миграция / очистка

- Старые файлы на Desktop **не удаляем** автоматически.
- Существующие файлы в CWD не трогаем.

## Scope

- **В scope:** `win/pyqt6/core/ssh_client.py`, `mac/core/ssh_client.py`, при необходимости общий/зеркальный helper в `utils` (Win + Mac).
- **Вне scope:** Android, webpanel, ручной «Открыть файл», удаление мусора с Desktop, UI-настройка пути кэша.

## Критерии приёмки

1. После SSH-скачивания `printer.cfg` файл лежит в `.../BedMesh Visualizer/cache/download_printer.cfg`, не на Desktop.
2. Fallback на `printer_mutable.cfg` кладёт `download_printer_mutable.cfg` туда же.
3. Настройки (`settings.json`) и логи продолжают жить в прежнем AppData root (не в `cache`).
4. Win и Mac ведут себя одинаково по смыслу пути.

## Риски

- Если QApplication org/app name ещё не выставлены к моменту первого download, `QStandardPaths.AppDataLocation` может отличаться от папки settings — mitigation: тот же fallback, что в `AppConfig`, либо брать путь через уже созданный `AppConfig.base_dir` / тот же helper.
