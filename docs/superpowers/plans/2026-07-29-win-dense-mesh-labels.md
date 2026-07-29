# Windows Dense Mesh Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Сделать плотную 2D-карту Windows читаемой, сохранив доступ к точным значениям каждой точки и детальное копирование.

**Architecture:** Чистый модуль рассчитывает режим подписей, размер детального холста и соответствие координат курсора ячейке. `MeshView` использует эти функции при создании экранного и детального pixmap, а специальный `QLabel` сообщает позицию мыши для подсказки.

**Tech Stack:** Python 3.10+, PyQt6, NumPy, `unittest`, QImage/QPainter.

## Global Constraints

- Меняется только Windows-клиент `win/pyqt6`.
- Экранный холст остаётся 700×700 пикселей.
- Перекрытие подписей недопустимо: если минимальный шрифт не помещается, экранные подписи скрываются.
- Значения Z форматируются со знаком и тремя знаками после запятой.
- Детальный холст ограничивается 4096×4096 пикселей.
- 3D-режим, парсер, статистика и палитры не меняются.
- Новые зависимости не добавляются.

---

### Task 1: Политика компоновки плотной карты

**Files:**
- Create: `win/pyqt6/ui/components/mesh_2d_layout.py`
- Create: `win/pyqt6/ui/components/test_mesh_2d_layout.py`

**Interfaces:**
- Produces: `choose_label_font_px(cell_width, cell_height, text_width_at_px, text_height_at_px, preferred_px=15, minimum_px=7, padding_px=4) -> int | None`
- Produces: `detail_canvas_size(x_count, y_count, minimum_cell_px=96, base_size=700, maximum_size=4096) -> tuple[int, int]`
- Produces: `mesh_index_at_position(mouse_x, mouse_y, viewport_width, viewport_height, pixmap_width, pixmap_height, x_count, y_count) -> tuple[int, int] | None`

- [ ] **Step 1: Write failing layout tests**

```python
import unittest

from mesh_2d_layout import (
    choose_label_font_px,
    detail_canvas_size,
    mesh_index_at_position,
)


class Mesh2DLayoutTests(unittest.TestCase):
    def test_sparse_cells_keep_labels(self):
        self.assertEqual(
            choose_label_font_px(100, 100, 90, 18),
            15,
        )

    def test_dense_cells_hide_labels(self):
        self.assertIsNone(
            choose_label_font_px(700 / 31, 700 / 31, 90, 18),
        )

    def test_detail_canvas_grows_and_is_capped(self):
        self.assertEqual(detail_canvas_size(31, 31), (2976, 2976))
        self.assertEqual(detail_canvas_size(100, 100), (4096, 4096))

    def test_mouse_position_accounts_for_centering_and_y_inversion(self):
        self.assertIsNone(mesh_index_at_position(0, 0, 900, 700, 700, 700, 31, 31))
        self.assertEqual(mesh_index_at_position(100, 0, 900, 700, 700, 700, 31, 31), (30, 0))
        self.assertEqual(mesh_index_at_position(799, 699, 900, 700, 700, 700, 31, 31), (0, 30))
        self.assertEqual(mesh_index_at_position(450, 350, 900, 700, 700, 700, 31, 31), (15, 15))
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
Push-Location win\pyqt6\ui\components
py -3 -m unittest test_mesh_2d_layout.py -v
Pop-Location
```

Expected: import error because `mesh_2d_layout.py` does not exist.

- [ ] **Step 3: Implement pure layout functions**

```python
import math


def choose_label_font_px(
    cell_width: float,
    cell_height: float,
    text_width_at_px: float,
    text_height_at_px: float,
    preferred_px: int = 15,
    minimum_px: int = 7,
    padding_px: int = 4,
) -> int | None:
    available_width = max(0.0, cell_width - padding_px)
    available_height = max(0.0, cell_height - padding_px)
    scale = min(
        1.0,
        available_width / max(text_width_at_px, 1.0),
        available_height / max(text_height_at_px, 1.0),
    )
    font_px = min(preferred_px, math.floor(preferred_px * scale))
    return font_px if font_px >= minimum_px else None


def detail_canvas_size(
    x_count: int,
    y_count: int,
    minimum_cell_px: int = 96,
    base_size: int = 700,
    maximum_size: int = 4096,
) -> tuple[int, int]:
    width = min(maximum_size, max(base_size, x_count * minimum_cell_px))
    height = min(maximum_size, max(base_size, y_count * minimum_cell_px))
    return width, height


def mesh_index_at_position(
    mouse_x: float,
    mouse_y: float,
    viewport_width: float,
    viewport_height: float,
    pixmap_width: float,
    pixmap_height: float,
    x_count: int,
    y_count: int,
) -> tuple[int, int] | None:
    left = (viewport_width - pixmap_width) / 2
    top = (viewport_height - pixmap_height) / 2
    local_x = mouse_x - left
    local_y = mouse_y - top
    if not (0 <= local_x < pixmap_width and 0 <= local_y < pixmap_height):
        return None
    column = min(x_count - 1, int(local_x * x_count / pixmap_width))
    drawn_row = min(y_count - 1, int(local_y * y_count / pixmap_height))
    return y_count - 1 - drawn_row, column
```

- [ ] **Step 4: Run tests and verify GREEN**

Run the Task 1 command. Expected: 4 tests pass.

- [ ] **Step 5: Commit Task 1**

```powershell
git add -- win/pyqt6/ui/components/mesh_2d_layout.py win/pyqt6/ui/components/test_mesh_2d_layout.py
git commit -m "test(win): define dense mesh layout policy"
```

### Task 2: Адаптивный экранный рендер и подсказки

**Files:**
- Modify: `win/pyqt6/ui/components/mesh_view.py`
- Modify: `win/pyqt6/ui/components/test_mesh_2d_layout.py`

**Interfaces:**
- Consumes: функции из `mesh_2d_layout.py`.
- Produces: `MeshView.render_mesh(data, width, height, force_labels=False) -> QPixmap`
- Produces: `MeshView.tooltip_for_position(x, y) -> str | None`

- [ ] **Step 1: Add failing renderer tests**

Добавить Qt-тесты, создающие `QApplication`, `BedMeshData` 7×7 и 31×31, затем проверить:

```python
def test_sparse_render_uses_labels(self):
    view = MeshView()
    view.update_mesh(make_mesh(7))
    self.assertTrue(view._screen_labels_visible)

def test_dense_render_hides_labels(self):
    view = MeshView()
    view.update_mesh(make_mesh(31))
    self.assertFalse(view._screen_labels_visible)

def test_tooltip_returns_original_matrix_value(self):
    view = MeshView()
    mesh = make_mesh(31)
    view.resize(700, 700)
    view.show()
    view.update_mesh(mesh)
    text = view.tooltip_for_position(350, 350)
    self.assertIn("Z:", text)
    self.assertIn(f"{mesh.z[15, 15]:+.3f}", text)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
Push-Location win\pyqt6\ui\components
py -3 -m unittest test_mesh_2d_layout.py -v
Pop-Location
```

Expected: attribute failures for `_screen_labels_visible` and `tooltip_for_position`.

- [ ] **Step 3: Implement adaptive rendering**

Изменить `MeshView`:

- хранить `self._data`;
- вынести создание pixmap в `render_mesh`;
- измерять строку `+0.000` через `QFontMetrics`;
- вызывать `choose_label_font_px`;
- не вызывать `drawText`, когда функция вернула `None`;
- сохранять результат в `self._screen_labels_visible`.

Добавить `_MeshLabel(QLabel)` с сигналом позиции мыши. `MeshView` связывает сигнал с
обработчиком, вызывает `mesh_index_at_position`, читает `data.x`, `data.y`, `data.z`
и устанавливает tooltip вида:

```text
Точка [15, 15]
X: 125.000 мм
Y: 125.000 мм
Z: +0.012 мм
```

- [ ] **Step 4: Run tests and verify GREEN**

Run the Task 2 command. Expected: all layout and renderer tests pass.

- [ ] **Step 5: Run existing mesh tests**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
Push-Location win\pyqt6\ui\components
py -3 -m unittest test_mesh_3d_math.py test_mesh_2d_layout.py -v
Pop-Location
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 2**

```powershell
git add -- win/pyqt6/ui/components/mesh_view.py win/pyqt6/ui/components/test_mesh_2d_layout.py
git commit -m "fix(win): keep dense mesh heatmaps readable"
```

### Task 3: Детальное копирование и визуальная проверка

**Files:**
- Modify: `win/pyqt6/ui/components/mesh_view.py`
- Modify: `win/pyqt6/ui/components/test_mesh_2d_layout.py`
- Create during verification only, do not commit: PNG files under `%TEMP%\bedmesh-dense-mesh-check\`

**Interfaces:**
- Consumes: `detail_canvas_size`.
- Produces: `MeshView.detail_pixmap() -> QPixmap | None`.

- [ ] **Step 1: Add failing detail-pixmap test**

```python
def test_detail_pixmap_grows_and_keeps_labels(self):
    view = MeshView()
    view.update_mesh(make_mesh(31))
    detail = view.detail_pixmap()
    self.assertEqual((detail.width(), detail.height()), (2976, 2976))
    self.assertTrue(view._detail_labels_visible)
```

- [ ] **Step 2: Run test and verify RED**

Run the Task 2 test command. Expected: `detail_pixmap` is missing.

- [ ] **Step 3: Implement detailed clipboard rendering**

Добавить `detail_pixmap`, который вызывает `detail_canvas_size` и `render_mesh` с
`force_labels=True`. Изменить `copy_to_clipboard`, чтобы он помещал этот pixmap в
буфер вместо экранного.

- [ ] **Step 4: Run tests and verify GREEN**

Run the Task 2 test command. Expected: all tests pass.

- [ ] **Step 5: Generate visual fixtures**

Одноразовым Python-скриптом создать:

```text
%TEMP%\bedmesh-dense-mesh-check\sparse-7x7.png
%TEMP%\bedmesh-dense-mesh-check\dense-screen-31x31.png
%TEMP%\bedmesh-dense-mesh-check\dense-detail-31x31.png
```

Сетка должна содержать плавный рельеф и несколько локальных экстремумов, чтобы были
видны как геометрия heatmap, так и контраст текста.

- [ ] **Step 6: Inspect all PNG files**

Открыть каждый PNG через средство просмотра изображений и подтвердить:

- `sparse-7x7.png`: все подписи читаемы;
- `dense-screen-31x31.png`: текст отсутствует, цвета и границы ячеек читаемы;
- `dense-detail-31x31.png`: все подписи помещаются в ячейки.

- [ ] **Step 7: Run the complete Windows verification**

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:QT_QPA_PLATFORM='offscreen'
Push-Location win\pyqt6\core
py -3 test_parser.py
Pop-Location
Push-Location win\pyqt6\utils
py -3 test_cache_paths.py
py -3 test_updater_bat.py
py -3 test_updater_platform.py
Pop-Location
Push-Location win\pyqt6\ui\components
py -3 -m unittest test_mesh_3d_math.py test_mesh_2d_layout.py -v
Pop-Location
git diff --check
```

Expected: every test passes and `git diff --check` reports no errors.

- [ ] **Step 8: Commit Task 3**

```powershell
git add -- win/pyqt6/ui/components/mesh_view.py win/pyqt6/ui/components/test_mesh_2d_layout.py
git commit -m "feat(win): copy dense mesh with full detail"
```

