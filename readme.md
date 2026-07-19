# Bed Mesh Visualizer

Анализ карты стола (bed mesh) для 3D-принтеров на Klipper/GoKlipper (в т.ч. Anycubic Kobra S1).

Клиенты: **Windows**, **macOS**, **Android**. На принтер ставится лёгкая **веб-панель** (`gkbridge`).

## Возможности

**Desktop (Windows / macOS)**

- Автоимпорт `printer_mutable.cfg` (JSON и текстовый формат)
- 2D и 3D визуализация рельефа стола
- Мастер выравнивания: пошаговые инструкции (обороты / мм по Z)
- Подключение к принтеру по SSH (без USB)

**Веб-панель на принтере** (`http://<IP>:8088`)

- Статус печати, температуры, пауза / стоп
- Живая камера, история событий
- Вкладка **Стол**: цветная карта mesh (heatmap), сводка min/max/range, кнопка «Обновить»

**Android**

- SSH-загрузка конфигов, 2D / псевдо-3D, статистика и коррекции
- Редактор секций конфига с бекапами на принтере
- Вкладка **Принтер**: постоянный SSH (dropbear) и установка веб-панели gkbridge

Подробности: [webpanel/README.md](webpanel/README.md), [android/README.md](android/README.md).

## Скачать

Из раздела **Releases**:

| Платформа | Артефакт |
|-----------|----------|
| Windows | `Bed.Mesh.Visualizer.exe` |
| macOS | `BedMeshVisualizer_Mac.dmg` |
| Android | `BedMeshVisualizer.apk` |

Приложение само проверяет обновления при запуске и предлагает установить их в один клик.

## Запуск из исходников

**Windows** (`win/pyqt6`):

```powershell
py -3 main.py
```

**macOS** (`mac`):

```bash
python3 main.py
```

Зависимости: `win/pyqt6/requirements.txt` (или корневой `requirements.txt`).

Android: см. [android/README.md](android/README.md).

## Ветки и релизы

| Ветка | Назначение |
|-------|------------|
| `main` | общий код, веб-панель (`webpanel/`), документация |
| `windows` | Windows-сборка и UI |
| `mac` | macOS-сборка и UI |
| `android` | Android-приложение |

Теги релизов: `vX.YYY-win`, `vX.YYY-mac`, `vX.YYY-android`.  
GitHub Actions собирает артефакт и прикрепляет его к релизу.

Правила вкладов: [CONTRIBUTING.md](CONTRIBUTING.md).

## Веб-панель (gkbridge)

Ставится на принтер из Windows- или Android-приложения (вкладка SSH / **Принтер**).  
После установки: `http://<IP принтера>:8088`.

Панель самообновляется с GitHub: при новой версии в футере появляется кнопка обновления (переустановка из клиента не обязательна).

Сборка, API и выпуск версий панели: [webpanel/README.md](webpanel/README.md).
