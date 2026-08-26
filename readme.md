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

Подробности: [архитектура](docs/ARCHITECTURE.md), [webpanel/README.md](webpanel/README.md), [android/README.md](android/README.md).

## Скачать

Из раздела **Releases**:

| Платформа | Артефакт |
|-----------|----------|
| Windows | `Bed.Mesh.Visualizer.exe` |
| macOS | `BedMeshVisualizer_Mac.dmg` |
| Android | `BedMeshVisualizer.apk` |

Клиенты проверяют обновления по своим платформенным тегам; Windows предлагает
установить EXE из приложения, а macOS и Android используют опубликованный
релиз и системный/браузерный установщик.

## Запуск из исходников

**Windows** (`win/pyqt6`):

```powershell
cd win/pyqt6
py -3 main.py
cd ../..
```

**macOS** (`mac`):

```bash
cd mac
python3 main.py
cd ..
```

Зависимости Windows: `win/pyqt6/requirements.txt`. Корневой `requirements.txt`
относится к историческому Streamlit-скрипту и не нужен для PyQt6-клиента.

Android: см. [android/README.md](android/README.md).

## Работа с Git и релизы

Рабочая ветка проекта — `main`. Изменения выполняются непосредственно в
`main`; новые ветки и PR для этого проекта не используются.

Теги релизов: `vX.YYY-win`, `vX.YYY-mac`, `vX.YYY-android`. GitHub Actions
собирает и публикует соответствующий артефакт. Версии находятся в
`win/pyqt6/utils/version.py`, `mac/utils/version.py`,
`android/app/build.gradle.kts` и `webpanel/gkbridge.version`.

Правила вкладов: [CONTRIBUTING.md](CONTRIBUTING.md).

## Веб-панель (gkbridge)

Ставится на принтер из Windows- или Android-приложения (вкладка SSH / **Принтер**).  
После установки: `http://<IP принтера>:8088`.

Панель самообновляется с GitHub: при новой версии в футере появляется кнопка обновления (переустановка из клиента не обязательна).

Сборка, API и выпуск версий панели: [webpanel/README.md](webpanel/README.md).

## Проверки

```powershell
python win/pyqt6/run_tests.py
cd android; .\gradlew.bat :app:testDebugUnitTest; cd ..
cd webpanel; .\build.ps1; cd ..
```

Подробное описание потоков данных и сборки: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
