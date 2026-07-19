# Win: PyInstaller `_MEI*` в LocalAppData — design

Дата: 2026-07-19  
Статус: approved for planning  
Область: Windows onefile (`build_win_pyqt6.yml`, `win/pyqt6/utils/updater.py`)

## Цель

Папка `_MEIxxxxxx`, куда onefile-сборка распаковывает Python/DLL при старте, не должна появляться рядом с exe (часто Desktop). Перенести runtime-tmpdir в Local AppData.

## Проблема

В CI стоит `--runtime-tmpdir .`. Bootloader создаёт `_MEI*` в CWD/рядом с exe. При запуске с рабочего стола:

- мусор `_MEI*` на Desktop;
- после автообновления возможна гонка с AV → `Failed to load Python DLL …\python310.dll`.

## Решение

### runtime-tmpdir

В `.github/workflows/build_win_pyqt6.yml` заменить:

```text
--runtime-tmpdir .
```

на:

```text
--runtime-tmpdir "%LOCALAPPDATA%\rkfsociety\BedMesh Visualizer\runtime"
```

Bootloader на Windows раскрывает `%LOCALAPPDATA%` через `ExpandEnvironmentStringsW` и создаёт недостающие каталоги. `_MEIxxxxxx` окажется внутри `runtime\`.

**Не** использовать `%APPDATA%` (Roaming): распаковка — десятки МБ temp, не для roaming-профиля. Settings/cache остаются в Roaming как сейчас.

### Updater (хвосты старых сборок)

В `updater_pyqt6.bat` перед стартом нового exe — удалить только каталоги `_MEI*` **в папке exe** (где жили после `--runtime-tmpdir .`). Не трогать произвольные файлы на Desktop. Не чистить LocalAppData runtime при обновлении (bootloader сам создаёт новый `_MEI*`).

### Версия / релиз

- `win/pyqt6/utils/version.py` → `0.169-win`
- Тег/релиз `v0.169-win`, в body: runtime `_MEI*` перенесён в LocalAppData; на Desktop больше не появляется.

## Вне scope

- macOS / Android / webpanel
- Автоочистка уже лежащих на Desktop `_MEI*` при обычном (не update) запуске
- Смена пути Roaming AppData для settings/cache
- Удаление `--runtime-tmpdir` в пользу системного `%TEMP%`

## Критерии приёмки

1. После сборки с новым флагом запуск exe с Desktop **не** создаёт `_MEI*` на Desktop.
2. Появляется каталог вида  
   `%LOCALAPPDATA%\rkfsociety\BedMesh Visualizer\runtime\_MEIxxxxxx\` с `python310.dll`.
3. Автообновление по-прежнему заменяет exe и перезапускает приложение; старые `_MEI*` рядом с exe подчищаются bat-скриптом.
4. Приложение стартует без диалога `Failed to load Python DLL`.
