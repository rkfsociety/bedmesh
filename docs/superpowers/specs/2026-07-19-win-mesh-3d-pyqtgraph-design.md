# Win: псевдо-3D карта mesh (pyqtgraph OpenGL) — design

Дата: 2026-07-19  
Статус: approved for planning  
Область: `win/pyqt6` (вкладка Карта)

## Цель

Добавить режим **3D** визуализации bed mesh с вращением мышью (orbit/zoom), рядом с существующим 2D heatmap. Переключатель **2D | 3D** на вкладке карты.

## Контекст

- Сейчас Windows рисует только 2D (`MeshView` + `QPainter`).
- README обещает «2D и 3D»; на Android в README тоже заявлена изометрия, но в коде её нет.
- Выбран стек: **pyqtgraph OpenGL** (`GLViewWidget` + `GLSurfacePlotItem`), не matplotlib и не самописный QOpenGL.

## UI и поведение

На вкладке **Карта**, рядом с кнопкой «Копировать»:

- переключатель **2D | 3D** (`QButtonGroup` / две кнопки);
- по умолчанию **2D**;
- выбор сохраняется в `settings.json` как `mesh_view_mode`: `"2d"` | `"3d"`.

| Режим | Виджет | Копирование | Подписи Z на ячейках |
|-------|--------|-------------|----------------------|
| 2D | текущий `MeshView` | pixmap в буфер (как сейчас) | да |
| 3D | `GLViewWidget` | кнопка **disabled**, tooltip «только в 2D» | нет |

**3D взаимодействие** (штат pyqtgraph):

- ЛКМ + drag — орбита;
- колесо — зум;
- Ctrl + ЛКМ — пан.

Цвета поверхности — из существующих `PALETTES` / `build_lut` (`mesh_palette` в настройках; UI выбора палитры вне scope).

Если OpenGL не инициализируется при первом переключении на 3D:

- показать `QMessageBox` с краткой ошибкой;
- принудительно оставить / вернуть **2D**;
- не ронять старт всего приложения.

## Архитектура

### Новые / изменяемые файлы

| Файл | Роль |
|------|------|
| `win/pyqt6/ui/components/mesh_3d_view.py` | Обёртка: `GLViewWidget` + `GLSurfacePlotItem`, `update_mesh(data)`, палитра, z-scale |
| `win/pyqt6/ui/panels/center_tabs.py` | Переключатель, `QStackedWidget` (2D/3D), wiring copy/mode |
| `win/pyqt6/utils/app_config.py` | Дефолт `mesh_view_mode: "2d"` |
| `win/pyqt6/app.py` | Проброс палитры; при загрузке mesh обновлять оба вида (если 3D создан) |
| `win/pyqt6/requirements.txt` | `pyqtgraph`, `PyOpenGL` |
| `.github/workflows/build_win_pyqt6.yml` | При необходимости `--hidden-import` для OpenGL / `pyqtgraph.opengl` |

### Ленивое создание 3D

`Mesh3DView` / `GLViewWidget` создаётся **при первом** выборе режима `"3d"`. До этого OpenGL-контекст не поднимается — старт приложения не зависит от драйверов.

### Данные и масштаб

- Вход: тот же `BedMeshData` (`x`, `y`, `z`, counts).
- Визуальный **z-scale** (множитель высоты) — константа в `mesh_3d_view` (или одна настройка без UI), чтобы рельеф был читаем; числа в правой панели (min/max/mm) **не** масштабируются.
- Центр камеры / distance выставляются по размеру сетки при первом `update_mesh`.

### Поток обновления

1. `BedMeshApp._process_file` → `mesh_view.update_mesh(data)` (2D всегда).
2. Если 3D-виджет уже создан → `mesh_3d_view.update_mesh(data)`.
3. Смена режима только переключает `QStackedWidget` + сохраняет `mesh_view_mode`.

## Зависимости и сборка

- Runtime: `pyqtgraph`, `PyOpenGL` (добавить в `win/pyqt6/requirements.txt`).
- PyInstaller onefile: проверить, что `pyqtgraph.opengl` и биндинги OpenGL попадают в exe; при падении импорта в собранном билде — добавить явные `--hidden-import`.
- Требование к машине пользователя: рабочие OpenGL-драйверы (типичные для Win10/11 с GPU/интегрой).

## Версия

При поставке фичи: bump `win/pyqt6/utils/version.py` → `0.170-win` (релизный тег `v0.170-win` — по обычному процессу релизов).

## Вне scope

- macOS / Android / online Streamlit
- UI выбора палитры
- Подписи значений Z на 3D-гранях
- Скриншот 3D в буфер
- Мастер коррекции винтов
- Выбор палитры / z-scale в UI

## Критерии приёмки

1. После загрузки mesh на вкладке Карта есть переключатель 2D/3D; по умолчанию 2D.
2. В 3D поверхность отражает рельеф `z`; цвет согласован с текущей палитрой.
3. Мышью можно вращать и зумить сцену.
4. Режим сохраняется между запусками (`mesh_view_mode`).
5. При недоступном OpenGL приложение не падает: диалог + остаёмся в 2D.
6. Кнопка «Копировать» в 3D неактивна; в 2D работает как раньше.
7. Собранный `Bed.Mesh.Visualizer.exe` стартует и показывает 3D на машине с нормальным OpenGL.

## Риски

- PyInstaller может не подхватить OpenGL без `hiddenimports` — проверка на CI/локальной сборке.
- Старые GPU / remote desktop без GL → fallback на 2D (ожидаемо).
- Размер exe вырастет из‑за pyqtgraph/PyOpenGL.
