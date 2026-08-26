# Архитектура Bed Mesh Visualizer

Документ описывает фактическую структуру репозитория и состояние `main`.
Платформенные клиенты частично дублируют код, поэтому изменения общего
поведения нужно проверять отдельно для Windows, macOS и Android.

## Компоненты

| Компонент | Технологии | Точка входа | Назначение |
|---|---|---|---|
| Windows | Python, PyQt6, pyqtgraph/OpenGL, Paramiko | `win/pyqt6/main.py` | Desktop-клиент, live-калибровка, SSH/SFTP, cfg и обновления |
| macOS | Python, PyQt6, pyqtgraph/OpenGL, Paramiko | `mac/main.py` | Desktop-клиент с картой, cfg, SSH/SFTP и обновлениями |
| Android | Kotlin, Jetpack Compose, SSHJ | `android/.../MainActivity.kt` | SSH, карта, cfg, бекапы и установка сервисов |
| Веб-панель | Go, vanilla JS, `go:embed` | `webpanel/gkbridge.go` | HTTP-панель статуса, управления, камеры и mesh |

Корневые `Bed_Mesh_Viz_Online.py` и spec-файлы — исторический Streamlit/
PyInstaller-слой. Актуальные desktop entrypoint’ы находятся в `win/pyqt6`
и `mac`; CI собирает именно их.

## Поток данных mesh

1. Desktop или Android подключается к принтеру по SSH (по умолчанию порт
   `2222`) и читает `/userdata/app/gk/printer.cfg`.
2. Если в основном cfg нет сохранённых `points`, клиент пробует
   `/userdata/app/gk/printer_mutable.cfg`.
3. Парсеры принимают JSON mutable-файла и текстовую секцию `[bed_mesh ...]`
   с `probe_count`, `mesh_min`, `mesh_max` и многострочным `points`.
4. Клиенты строят 2D/3D-представление, статистику и подсказки по коррекции.
   Windows дополнительно получает live snapshots во время калибровки.
5. `gkbridge` получает данные через Unix-сокет `/tmp/unix_uds1`; endpoint
   `/mesh` использует живой mesh и те же cfg-fallback’и.

## Клиенты и хранение

Windows и macOS имеют вкладки карты, редактора конфигурации и RAW-данных,
SSH-панель и правую панель анализа. Windows дополнительно поддерживает
load-cell калибровку, live mesh и установку постоянного SSH, `gkbridge` и
камеры через `/useremain/boot.sh`.

Android имеет вкладки SSH, Карта, Config, Принтер и RAW. Настройки хранятся
в SharedPreferences, загрузки — в cache приложения. Удалённые бекапы имеют
вид `<printer.cfg>.bedmesh_bak_*`; перед отправкой конфигурация загружается
во временный путь и проверяется.

Вкладка Android «Принтер» устанавливает dropbear из `/tmp/ssh` в
`/useremain/ssh`, hook в `run.sh` и `gkbridge` в `/useremain/gkbridge`.
Панель доступна на `http://<IP>:8088` и открывается во встроенном WebView.

## Веб-панель

`gkbridge` по умолчанию слушает `:8088` и обращается к `/tmp/unix_uds1`.
Основные endpoint’ы: `/`, `/status`, `/mesh`, `/control`, `/gcode`, `/logs`,
`/version`, `/update/check`, `/update/apply`, `/health`. Полная таблица API:
[webpanel/README.md](../webpanel/README.md).

Бинарник панели собирается под Linux ARMv7 и коммитится в
`webpanel/gkbridge`, поскольку desktop-клиенты включают его в ресурсы.

## Сборка и проверки

```powershell
# Windows unit-тесты из корня
python win/pyqt6/run_tests.py

# Android
cd android
.\gradlew.bat :app:assembleDebug
.\gradlew.bat :app:assembleRelease
cd ..

# gkbridge: запускать из webpanel
cd webpanel
.\build.ps1
cd ..
```

Workflow’ы находятся в `.github/workflows`: `build_win_pyqt6.yml` собирает
PyInstaller onefile и SHA-256 на Python 3.10; `build_mac.yml` публикует DMG;
`build_android.yml` публикует release APK. Версии задаются отдельно:
Windows — `win/pyqt6/utils/version.py`, macOS — `mac/utils/version.py`,
Android — `android/app/build.gradle.kts`, панель — `webpanel/gkbridge.version`.
Updater’ы выбирают релизы по платформенному суффиксу тега.

## Связанные документы

- [Корневой README](../readme.md)
- [Android README](../android/README.md)
- [Webpanel README](../webpanel/README.md)
- [UI reference](ui-reference/README.md)
- [Windows reliability plan](plans/windows-reliability-improvements.md)
