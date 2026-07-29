# Windows 3D Mesh Rendering and Camera Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Исправить отрисовку цветной 3D-поверхности bed mesh в Windows-версии и реализовать предсказуемое управление камерой мышью.

**Architecture:** Чистые функции в `mesh_3d_math.py` валидируют данные и готовят согласованные массивы поверхности и параметры камеры. Отдельный `Mesh3DGLView` инкапсулирует ввод камеры, а `Mesh3DView` остаётся координатором ленивой OpenGL-инициализации, обновления поверхности, сетки и состояния ошибки.

**Tech Stack:** Python 3.12, PyQt6, pyqtgraph 0.14, PyOpenGL, NumPy, unittest.

## Global Constraints

- Область изменений: только `win/pyqt6` и документация этой задачи.
- ЛКМ + перемещение вращает камеру.
- ПКМ + перемещение сдвигает камеру в плоскости вида.
- Колесо плавно масштабирует с ограничениями.
- Двойной щелчок восстанавливает автоматически рассчитанный начальный вид.
- Палитра и значения mesh остаются согласованными с 2D-режимом.
- Ошибки данных или OpenGL не должны завершать приложение.
- Белая поверхность-заглушка 2×2 не должна отображаться.
- Новая ветка не создаётся; работа продолжается в текущей `main`.
- Пуш выполняется только по отдельной прямой команде пользователя.

---

## File Map

- Modify: `win/pyqt6/ui/components/mesh_3d_math.py`
  - Валидация и подготовка X/Y/Z/цветов.
  - Расчёт начального положения и границ камеры.
- Modify: `win/pyqt6/ui/components/test_mesh_3d_math.py`
  - Регрессия формы цветов 7×7 и прямоугольной карты.
  - Тесты расчёта камеры и ограниченного зума.
- Create: `win/pyqt6/ui/components/mesh_3d_camera.py`
  - Подкласс `GLViewWidget` с выбранной схемой мыши и сбросом камеры.
- Create: `win/pyqt6/ui/components/test_mesh_3d_camera.py`
  - Проверка маршрутизации ЛКМ/ПКМ, колеса и двойного щелчка.
- Modify: `win/pyqt6/ui/components/mesh_3d_view.py`
  - Ленивое создание камеры, поверхности и адаптивной сетки.
  - Передача только валидного плоского массива цветов.
  - Ошибка вместо белой заглушки.
- Create: `win/pyqt6/ui/components/test_mesh_3d_view.py`
  - Интеграционная проверка payload без реального OpenGL-рендера.

---

### Task 1: Подготовка поверхности и математика камеры

**Files:**
- Modify: `win/pyqt6/ui/components/mesh_3d_math.py`
- Modify: `win/pyqt6/ui/components/test_mesh_3d_math.py`

**Interfaces:**
- Produces: `SurfacePayload`, `CameraFit`.
- Produces: `prepare_surface(x, y, z, palette_key) -> SurfacePayload`.
- Produces: `fit_camera(payload) -> CameraFit`.
- Produces: `clamp_zoom_distance(current, wheel_delta, minimum, maximum) -> float`.

- [ ] **Step 1: Написать падающие тесты формы и порядка данных поверхности**

Добавить импорты и тесты:

```python
from ui.components.mesh_3d_math import (
    CameraFit,
    SurfacePayload,
    clamp_zoom_distance,
    fit_camera,
    prepare_surface,
)

def test_prepare_surface_flattens_7_by_7_vertex_colors(self):
    x = np.linspace(10.0, 240.0, 7)
    y = np.linspace(10.0, 240.0, 7)
    z = np.linspace(-0.1, 0.9, 49).reshape(7, 7)

    payload = prepare_surface(x, y, z, "soft")

    self.assertEqual(payload.z.shape, (7, 7))
    self.assertEqual(payload.colors.shape, (49, 4))
    self.assertEqual(payload.x.shape, (7,))
    self.assertEqual(payload.y.shape, (7,))

def test_prepare_surface_preserves_color_order_for_rectangular_mesh(self):
    x = np.array([0.0, 10.0, 20.0])
    y = np.array([0.0, 5.0])
    z = np.array([[0.0, 0.1, 0.2], [0.3, 0.4, 0.5]])

    payload = prepare_surface(x, y, z, "soft")
    expected = np.transpose(colors_from_z(z, "soft"), (1, 0, 2)).reshape(-1, 4)

    self.assertEqual(payload.z.shape, (3, 2))
    np.testing.assert_allclose(payload.colors, expected)

def test_prepare_surface_rejects_mismatched_shape(self):
    with self.assertRaisesRegex(ValueError, "shape"):
        prepare_surface(
            np.array([0.0, 1.0, 2.0]),
            np.array([0.0, 1.0]),
            np.zeros((3, 3)),
            "soft",
        )
```

- [ ] **Step 2: Запустить тесты и подтвердить ожидаемое падение**

Run:

```powershell
py -3.12 win\pyqt6\ui\components\test_mesh_3d_math.py
```

Expected: `ImportError` для новых интерфейсов или `AttributeError`, потому что подготовка поверхности ещё не реализована.

- [ ] **Step 3: Реализовать dataclass и подготовку массивов**

Добавить в `mesh_3d_math.py`:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SurfacePayload:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    colors: np.ndarray
    span_x: float
    span_y: float
    center_z: float
    spacing_x: float
    spacing_y: float

@dataclass(frozen=True)
class CameraFit:
    center: tuple[float, float, float]
    distance: float
    minimum_distance: float
    maximum_distance: float

def prepare_surface(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    palette_key: str,
) -> SurfacePayload:
    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    z_values = np.asarray(z, dtype=float)
    if x_values.ndim != 1 or y_values.ndim != 1:
        raise ValueError("x and y must be one-dimensional")
    expected_shape = (len(y_values), len(x_values))
    if z_values.shape != expected_shape:
        raise ValueError(f"z shape {z_values.shape} does not match {expected_shape}")
    if len(x_values) < 2 or len(y_values) < 2:
        raise ValueError("3D mesh requires at least 2 x 2 points")
    if not (
        np.all(np.isfinite(x_values))
        and np.all(np.isfinite(y_values))
        and np.all(np.isfinite(z_values))
    ):
        raise ValueError("3D mesh contains non-finite values")

    x_centered = x_values - float(np.mean(x_values))
    y_centered = y_values - float(np.mean(y_values))
    z_visual = scaled_z(z_values).T
    colors = np.transpose(colors_from_z(z_values, palette_key), (1, 0, 2))
    colors_flat = np.ascontiguousarray(colors.reshape(-1, 4))
    span_x = max(float(np.ptp(x_values)), 1.0)
    span_y = max(float(np.ptp(y_values)), 1.0)
    return SurfacePayload(
        x=x_centered,
        y=y_centered,
        z=z_visual,
        colors=colors_flat,
        span_x=span_x,
        span_y=span_y,
        center_z=float(np.mean(z_visual)),
        spacing_x=span_x / (len(x_values) - 1),
        spacing_y=span_y / (len(y_values) - 1),
    )
```

- [ ] **Step 4: Написать падающие тесты камеры и масштаба**

Добавить:

```python
def test_fit_camera_centers_surface_and_sets_safe_limits(self):
    payload = prepare_surface(
        np.linspace(10.0, 240.0, 7),
        np.linspace(20.0, 220.0, 5),
        np.zeros((5, 7)),
        "soft",
    )

    fit = fit_camera(payload)

    self.assertEqual(fit.center[:2], (0.0, 0.0))
    self.assertAlmostEqual(fit.center[2], payload.center_z)
    self.assertAlmostEqual(fit.distance, 230.0 * 1.8)
    self.assertLess(fit.minimum_distance, fit.distance)
    self.assertGreater(fit.maximum_distance, fit.distance)

def test_clamp_zoom_distance_obeys_limits(self):
    self.assertEqual(clamp_zoom_distance(100.0, 100000, 20.0, 500.0), 20.0)
    self.assertEqual(clamp_zoom_distance(100.0, -100000, 20.0, 500.0), 500.0)
    self.assertLess(clamp_zoom_distance(100.0, 120, 20.0, 500.0), 100.0)
    self.assertGreater(clamp_zoom_distance(100.0, -120, 20.0, 500.0), 100.0)
```

- [ ] **Step 5: Реализовать расчёт камеры и ограниченный зум**

Добавить:

```python
def fit_camera(payload: SurfacePayload) -> CameraFit:
    distance = max(payload.span_x, payload.span_y, 1.0) * 1.8
    return CameraFit(
        center=(0.0, 0.0, payload.center_z),
        distance=distance,
        minimum_distance=distance * 0.08,
        maximum_distance=distance * 8.0,
    )

def clamp_zoom_distance(
    current: float,
    wheel_delta: int,
    minimum: float,
    maximum: float,
) -> float:
    proposed = float(current) * (0.999 ** int(wheel_delta))
    return min(max(proposed, float(minimum)), float(maximum))
```

- [ ] **Step 6: Запустить тесты модуля**

Run:

```powershell
py -3.12 win\pyqt6\ui\components\test_mesh_3d_math.py
```

Expected: все тесты `OK`.

- [ ] **Step 7: Закоммитить математику**

```powershell
git add -- win/pyqt6/ui/components/mesh_3d_math.py win/pyqt6/ui/components/test_mesh_3d_math.py
git commit -m "fix(win): prepare valid 3D mesh surface data"
```

---

### Task 2: Предсказуемое управление камерой

**Files:**
- Create: `win/pyqt6/ui/components/mesh_3d_camera.py`
- Create: `win/pyqt6/ui/components/test_mesh_3d_camera.py`

**Interfaces:**
- Consumes: `CameraFit`, `clamp_zoom_distance`.
- Produces: `Mesh3DGLView.set_home_view(fit: CameraFit, reset: bool) -> None`.
- Produces: `Mesh3DGLView.reset_camera() -> None`.

- [ ] **Step 1: Написать тестовый каркас и падающие тесты drag-событий**

Создать `test_mesh_3d_camera.py`:

```python
import os
import sys
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtWidgets import QApplication

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui.components.mesh_3d_camera import Mesh3DGLView

_APP = QApplication.instance() or QApplication([])

class FakeMouseEvent:
    def __init__(self, position, buttons):
        self._position = QPointF(*position)
        self._buttons = buttons
        self.accepted = False

    def position(self):
        return self._position

    def buttons(self):
        return self._buttons

    def accept(self):
        self.accepted = True

class TestMesh3DCamera(unittest.TestCase):
    def setUp(self):
        self.view = Mesh3DGLView()
        self.view.orbit = Mock()
        self.view.pan = Mock()

    def test_left_drag_orbits(self):
        self.view.mousePressEvent(FakeMouseEvent((10, 10), Qt.MouseButton.LeftButton))
        self.view.mouseMoveEvent(FakeMouseEvent((14, 16), Qt.MouseButton.LeftButton))
        self.view.orbit.assert_called_once_with(-4.0, 6.0)
        self.view.pan.assert_not_called()

    def test_right_drag_pans_in_view_plane(self):
        self.view.mousePressEvent(FakeMouseEvent((10, 10), Qt.MouseButton.RightButton))
        self.view.mouseMoveEvent(FakeMouseEvent((14, 16), Qt.MouseButton.RightButton))
        self.view.pan.assert_called_once_with(4.0, 6.0, 0, relative="view")
        self.view.orbit.assert_not_called()
```

- [ ] **Step 2: Запустить тест и подтвердить отсутствие класса**

Run:

```powershell
py -3.12 win\pyqt6\ui\components\test_mesh_3d_camera.py
```

Expected: `ModuleNotFoundError: ui.components.mesh_3d_camera`.

- [ ] **Step 3: Создать класс камеры с ЛКМ и ПКМ**

Создать `mesh_3d_camera.py` с классом:

```python
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QVector3D
import pyqtgraph.opengl as gl

from ui.components.mesh_3d_math import CameraFit, clamp_zoom_distance

class Mesh3DGLView(gl.GLViewWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mouse_position = None
        self._home_fit: CameraFit | None = None

    def mousePressEvent(self, event):
        self._mouse_position = event.position()
        event.accept()

    def mouseMoveEvent(self, event):
        current = event.position()
        if self._mouse_position is None:
            self._mouse_position = current
        delta = current - self._mouse_position
        self._mouse_position = current
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.orbit(-delta.x(), delta.y())
        elif event.buttons() & Qt.MouseButton.RightButton:
            self.pan(delta.x(), delta.y(), 0, relative="view")
        event.accept()
```

- [ ] **Step 4: Добавить падающие тесты home-view, колеса и двойного щелчка**

Дополнить тестовый файл объектами `FakeWheelEvent`, `FakeDoubleClickEvent` и тестами:

```python
from PyQt6.QtCore import QPoint
from ui.components.mesh_3d_math import CameraFit

class FakeWheelEvent:
    def __init__(self, delta):
        self._delta = delta
        self.accepted = False

    def angleDelta(self):
        return QPoint(0, self._delta)

    def accept(self):
        self.accepted = True

def test_wheel_zooms_within_home_limits(self):
    fit = CameraFit((0.0, 0.0, 2.0), 100.0, 20.0, 500.0)
    self.view.set_home_view(fit, reset=True)
    self.view.wheelEvent(FakeWheelEvent(120))
    self.assertLess(self.view.opts["distance"], 100.0)
    self.assertGreaterEqual(self.view.opts["distance"], 20.0)

def test_double_click_restores_home_view(self):
    fit = CameraFit((0.0, 0.0, 2.0), 100.0, 20.0, 500.0)
    self.view.set_home_view(fit, reset=True)
    self.view.opts["distance"] = 250.0
    self.view.opts["azimuth"] = 10.0
    event = FakeMouseEvent((0, 0), Qt.MouseButton.LeftButton)

    self.view.mouseDoubleClickEvent(event)

    self.assertEqual(self.view.opts["distance"], 100.0)
    self.assertEqual(self.view.opts["azimuth"], -60.0)
    self.assertEqual(self.view.opts["elevation"], 25.0)
    self.assertTrue(event.accepted)
```

- [ ] **Step 5: Реализовать home-view, ограниченный зум и сброс**

Дополнить `Mesh3DGLView`:

```python
    def set_home_view(self, fit: CameraFit, reset: bool) -> None:
        self._home_fit = fit
        if reset:
            self.reset_camera()

    def reset_camera(self) -> None:
        if self._home_fit is None:
            return
        self.opts["center"] = QVector3D(*self._home_fit.center)
        self.opts["distance"] = self._home_fit.distance
        self.opts["azimuth"] = -60.0
        self.opts["elevation"] = 25.0
        self.update()

    def wheelEvent(self, event):
        if self._home_fit is None:
            return super().wheelEvent(event)
        delta = event.angleDelta().x() or event.angleDelta().y()
        self.opts["distance"] = clamp_zoom_distance(
            self.opts["distance"],
            delta,
            self._home_fit.minimum_distance,
            self._home_fit.maximum_distance,
        )
        self.update()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.reset_camera()
        event.accept()
```

- [ ] **Step 6: Запустить тесты камеры и математики**

Run:

```powershell
py -3.12 win\pyqt6\ui\components\test_mesh_3d_camera.py
py -3.12 win\pyqt6\ui\components\test_mesh_3d_math.py
```

Expected: оба набора завершаются с `OK`.

- [ ] **Step 7: Закоммитить управление камерой**

```powershell
git add -- win/pyqt6/ui/components/mesh_3d_camera.py win/pyqt6/ui/components/test_mesh_3d_camera.py
git commit -m "feat(win): add predictable 3D camera controls"
```

---

### Task 3: Интеграция поверхности, камеры и адаптивной сетки

**Files:**
- Modify: `win/pyqt6/ui/components/mesh_3d_view.py`
- Create: `win/pyqt6/ui/components/test_mesh_3d_view.py`

**Interfaces:**
- Consumes: `prepare_surface`, `fit_camera`, `Mesh3DGLView`.
- Preserves: `Mesh3DView.ensure_ready() -> bool`.
- Changes: `Mesh3DView.update_mesh(data, *, reset_camera: bool = True) -> None`.

- [ ] **Step 1: Написать падающий интеграционный тест с объектами-заглушками**

Создать `test_mesh_3d_view.py`:

```python
import os
import sys
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt6.QtWidgets import QApplication

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.mesh_parser import BedMeshData
from ui.components.mesh_3d_view import Mesh3DView

_APP = QApplication.instance() or QApplication([])

def sample_mesh():
    return BedMeshData(
        x=np.linspace(10.0, 240.0, 7),
        y=np.linspace(10.0, 240.0, 7),
        z=np.linspace(-0.1, 0.9, 49).reshape(7, 7),
        x_count=7,
        y_count=7,
        min_x=10.0,
        max_x=240.0,
        min_y=10.0,
        max_y=240.0,
    )

class TestMesh3DView(unittest.TestCase):
    def test_update_mesh_sends_flat_colors_and_fits_grid(self):
        widget = Mesh3DView()
        widget._ready = True
        widget._surface = Mock()
        widget._grid = Mock()
        widget._gl_view = Mock()

        widget.update_mesh(sample_mesh())

        kwargs = widget._surface.setData.call_args.kwargs
        self.assertEqual(kwargs["z"].shape, (7, 7))
        self.assertEqual(kwargs["colors"].shape, (49, 4))
        widget._grid.setSize.assert_called_once_with(x=230.0, y=230.0)
        widget._grid.setSpacing.assert_called_once()
        widget._gl_view.set_home_view.assert_called_once()
        self.assertTrue(widget._gl_view.set_home_view.call_args.kwargs["reset"])

    def test_palette_refresh_does_not_reset_camera(self):
        widget = Mesh3DView()
        widget._ready = True
        widget._surface = Mock()
        widget._grid = Mock()
        widget._gl_view = Mock()
        widget._data = sample_mesh()

        widget.set_palette("classic")

        self.assertFalse(widget._gl_view.set_home_view.call_args.kwargs["reset"])
```

- [ ] **Step 2: Запустить тест и подтвердить несовместимость текущей реализации**

Run:

```powershell
py -3.12 win\pyqt6\ui\components\test_mesh_3d_view.py
```

Expected: FAIL — цвета имеют форму `(7, 7, 4)`, отсутствует `_grid` или `set_home_view`.

- [ ] **Step 3: Переработать ленивую инициализацию без белой поверхности**

Изменить `ensure_ready()`:

```python
from utils.logger import get_logger

# в __init__
self._logger = get_logger(__name__)
self._grid = None
self._gl = None

# внутри ensure_ready
from ui.components.mesh_3d_camera import Mesh3DGLView

self._gl = gl
view = Mesh3DGLView()
view.setBackgroundColor((30, 30, 30))
grid = gl.GLGridItem()
view.addItem(grid)
view.hide()
self._layout.addWidget(view)
self._gl_view = view
self._grid = grid
self._surface = None
self._ready = True
self._placeholder.setText("3D: нет данных")
```

Не создавать `GLSurfacePlotItem` с `z=np.zeros((2, 2))`.

- [ ] **Step 4: Реализовать обновление поверхности и состояния ошибки**

Заменить тело `update_mesh` на поток:

```python
def update_mesh(self, data: BedMeshData, *, reset_camera: bool = True) -> None:
    self._data = data
    if not self._ready or self._gl_view is None or self._grid is None:
        return
    try:
        payload = prepare_surface(data.x, data.y, data.z, self._palette_key)
        if self._surface is None:
            self._surface = self._gl.GLSurfacePlotItem(
                shader="shaded",
                smooth=False,
                computeNormals=True,
            )
            self._gl_view.addItem(self._surface)
        self._surface.setData(
            x=payload.x,
            y=payload.y,
            z=payload.z,
            colors=payload.colors,
        )
        self._grid.setSize(x=payload.span_x, y=payload.span_y)
        self._grid.setSpacing(x=payload.spacing_x, y=payload.spacing_y)
        self._gl_view.set_home_view(fit_camera(payload), reset=reset_camera)
        self._placeholder.hide()
        self._gl_view.show()
        self._gl_view.update()
    except Exception as exc:
        self._logger.exception("Не удалось обновить 3D-карту")
        self._gl_view.hide()
        self._placeholder.setText(f"3D недоступен:\\n{exc}")
        self._placeholder.show()
```

Изменить `set_palette`:

```python
if self._ready and self._data is not None:
    self.update_mesh(self._data, reset_camera=False)
```

- [ ] **Step 5: Запустить три целевых набора тестов**

Run:

```powershell
py -3.12 win\pyqt6\ui\components\test_mesh_3d_math.py
py -3.12 win\pyqt6\ui\components\test_mesh_3d_camera.py
py -3.12 win\pyqt6\ui\components\test_mesh_3d_view.py
```

Expected: все тесты завершаются с `OK`; Qt может вывести безопасное предупреждение offscreen OpenGL, но traceback отсутствует.

- [ ] **Step 6: Закоммитить интеграцию**

```powershell
git add -- win/pyqt6/ui/components/mesh_3d_view.py win/pyqt6/ui/components/test_mesh_3d_view.py
git commit -m "fix(win): render full 3D mesh surface"
```

---

### Task 4: Полная регрессия и живая проверка Windows

**Files:**
- Verify: `win/pyqt6`

**Interfaces:**
- Consumes готовые интерфейсы Tasks 1–3.
- Не создаёт новых продуктовых интерфейсов.

- [ ] **Step 1: Запустить все Windows-тесты**

Run:

```powershell
py -3.12 -m unittest discover -s win\pyqt6 -p "test_*.py" -v
```

Expected: exit code `0`, все тесты `OK`.

- [ ] **Step 2: Проверить синтаксис изменённых модулей**

Run:

```powershell
py -3.12 -m py_compile `
  win\pyqt6\ui\components\mesh_3d_math.py `
  win\pyqt6\ui\components\mesh_3d_camera.py `
  win\pyqt6\ui\components\mesh_3d_view.py
```

Expected: exit code `0`, вывод отсутствует.

- [ ] **Step 3: Перезапустить dev-версию с отдельным журналом**

Завершить только ранее запущенные процессы этого приложения, затем:

```powershell
$stdoutPath = "C:\github\bedmesh\.codex-bedmesh-3d.stdout.log"
$stderrPath = "C:\github\bedmesh\.codex-bedmesh-3d.stderr.log"
Start-Process -FilePath "py.exe" `
  -ArgumentList "-3.12", "main.py" `
  -WorkingDirectory "C:\github\bedmesh\win\pyqt6" `
  -RedirectStandardOutput $stdoutPath `
  -RedirectStandardError $stderrPath
```

Expected: появляется окно `BedMesh Visualizer`, приложение отвечает.

- [ ] **Step 4: Проверить реальную карту**

В приложении загрузить сохранённую конфигурацию принтера и переключиться в 3D:

- поверхность занимает координатную сетку;
- видны цвета и рельеф всех 49 точек;
- ЛКМ вращает;
- ПКМ перемещает;
- колесо приближает и отдаляет без потери сцены;
- двойной щелчок возвращает весь стол в кадр;
- возврат 2D → 3D сохраняет рабочую поверхность.

- [ ] **Step 5: Проверить журнал после взаимодействия**

Run:

```powershell
rg -n "Traceback|IndexError|ERROR|exception caught here" `
  C:\github\bedmesh\.codex-bedmesh-3d.stderr.log
```

Expected: совпадений, относящихся к 3D-отрисовке, нет.

- [ ] **Step 6: Проверить чистоту рабочей области**

Run:

```powershell
git status --short --branch
git log -4 --oneline
```

Expected: рабочая область чистая; `main` содержит отдельные коммиты Tasks 1–3 и документации, но не отправлена без новой команды пользователя.
