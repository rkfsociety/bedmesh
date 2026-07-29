# Windows 2D Mesh Zoom and Pan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить масштабирование и перемещение 2D-карты с автоматическим появлением читаемых подписей плотной mesh-сетки.

**Architecture:** Новый `MeshGraphicsView` инкапсулирует навигацию сцены и логический масштаб 1×–12×. `MeshView` размещает в одной сцене чистый и детальный pixmap, переключает их по рассчитанному порогу и формирует tooltip из координат сцены.

**Tech Stack:** Python 3.10+, PyQt6 `QGraphicsView/QGraphicsScene`, NumPy, `unittest`.

## Global Constraints

- Меняется только Windows-клиент `win/pyqt6`.
- Колесо масштабирует карту под курсором.
- Зажатая ЛКМ перемещает увеличенную карту.
- Двойной щелчок возвращает вид целиком.
- Диапазон масштаба — 1×–12×.
- При малом масштабе плотная карта не содержит перекрывающихся подписей.
- Подсказки X/Y/Z работают после масштабирования и перемещения.
- Публичные методы `MeshView.update_mesh`, `set_palette` и `copy_to_clipboard` сохраняются.
- Новые зависимости не добавляются.

---

### Task 1: Навигационный QGraphicsView

**Files:**
- Create: `win/pyqt6/ui/components/mesh_graphics_view.py`
- Modify: `win/pyqt6/ui/components/test_mesh_2d_layout.py`

**Interfaces:**
- Produces: `MeshGraphicsView.zoom_changed = pyqtSignal(float)`
- Produces: `MeshGraphicsView.scene_position_changed = pyqtSignal(float, float)`
- Produces: `MeshGraphicsView.zoom_factor() -> float`
- Produces: `MeshGraphicsView.set_zoom_factor(value: float) -> None`
- Produces: `MeshGraphicsView.reset_view() -> None`

- [ ] **Step 1: Add failing navigation tests**

```python
from mesh_graphics_view import MeshGraphicsView

def test_zoom_is_clamped_and_reset(self):
    view = MeshGraphicsView()
    view.setSceneRect(0, 0, 700, 700)
    view.resize(700, 700)
    view.reset_view()
    self.assertEqual(view.zoom_factor(), 1.0)
    view.set_zoom_factor(50)
    self.assertEqual(view.zoom_factor(), 12.0)
    view.set_zoom_factor(0.01)
    self.assertEqual(view.zoom_factor(), 1.0)
    view.set_zoom_factor(4.0)
    view.reset_view()
    self.assertEqual(view.zoom_factor(), 1.0)

def test_zoom_signal_reports_effective_factor(self):
    view = MeshGraphicsView()
    seen = []
    view.zoom_changed.connect(seen.append)
    view.set_zoom_factor(3.0)
    self.assertEqual(seen[-1], 3.0)
```

- [ ] **Step 2: Run tests and verify RED**

```powershell
$env:QT_QPA_PLATFORM='windows'
Push-Location win\pyqt6\ui\components
py -3 -m unittest test_mesh_2d_layout.py -v
Pop-Location
```

Expected: import error because `mesh_graphics_view.py` does not exist.

- [ ] **Step 3: Implement navigation**

Create `MeshGraphicsView(QGraphicsView)` with:

```python
MIN_ZOOM = 1.0
MAX_ZOOM = 12.0
ZOOM_STEP = 1.25

def set_zoom_factor(self, value: float) -> None:
    target = min(self.MAX_ZOOM, max(self.MIN_ZOOM, float(value)))
    ratio = target / self._zoom_factor
    self.scale(ratio, ratio)
    self._zoom_factor = target
    self.zoom_changed.emit(target)

def reset_view(self) -> None:
    self.resetTransform()
    self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
    self._zoom_factor = 1.0
    self.centerOn(self.sceneRect().center())
    self.zoom_changed.emit(1.0)
```

Configure:

- `QGraphicsView.DragMode.ScrollHandDrag`;
- hidden scrollbars;
- mouse tracking on viewport;
- `wheelEvent` multiplies/divides the logical zoom by `ZOOM_STEP`;
- `mouseDoubleClickEvent` calls `reset_view`;
- `mouseMoveEvent` emits `mapToScene(event.position().toPoint())`.

- [ ] **Step 4: Run tests and verify GREEN**

Run the Task 1 command. Expected: all tests pass.

- [ ] **Step 5: Commit Task 1**

```powershell
git add -- win/pyqt6/ui/components/mesh_graphics_view.py win/pyqt6/ui/components/test_mesh_2d_layout.py
git commit -m "feat(win): add 2d mesh viewport navigation"
```

### Task 2: Два слоя карты и динамические подписи

**Files:**
- Modify: `win/pyqt6/ui/components/mesh_2d_layout.py`
- Modify: `win/pyqt6/ui/components/mesh_view.py`
- Modify: `win/pyqt6/ui/components/test_mesh_2d_layout.py`

**Interfaces:**
- Produces: `detail_zoom_threshold(x_count, y_count, scene_size=700, minimum_cell_screen_px=48, maximum_zoom=12) -> float`
- Consumes: `MeshGraphicsView.zoom_changed` and `scene_position_changed`.
- Preserves: `MeshView.detail_pixmap() -> QPixmap | None`.

- [ ] **Step 1: Add failing threshold and layer tests**

```python
def test_dense_mesh_needs_zoom_before_detail(self):
    self.assertAlmostEqual(detail_zoom_threshold(31, 31), 48 / (700 / 31))

def test_sparse_mesh_shows_detail_at_fit(self):
    self.assertEqual(detail_zoom_threshold(7, 7), 1.0)

def test_dense_layer_switches_after_zoom(self):
    view = MeshView()
    view.resize(700, 700)
    view.update_mesh(make_mesh(31))
    self.assertTrue(view._screen_item.isVisible())
    self.assertFalse(view._detail_item.isVisible())
    view.graphics_view.set_zoom_factor(3.0)
    self.assertFalse(view._screen_item.isVisible())
    self.assertTrue(view._detail_item.isVisible())

def test_tooltip_uses_scene_position_after_zoom(self):
    view = MeshView()
    mesh = make_mesh(31)
    view.update_mesh(mesh)
    text = view.tooltip_for_scene_position(350, 350)
    self.assertIn(f"{mesh.z[15, 15]:+.3f}", text)
```

- [ ] **Step 2: Run tests and verify RED**

Run the Task 1 command. Expected: missing threshold/layer APIs.

- [ ] **Step 3: Implement threshold**

```python
def detail_zoom_threshold(
    x_count: int,
    y_count: int,
    scene_size: int = 700,
    minimum_cell_screen_px: int = 48,
    maximum_zoom: float = 12.0,
) -> float:
    cell_at_fit = min(scene_size / x_count, scene_size / y_count)
    required = minimum_cell_screen_px / max(cell_at_fit, 1e-9)
    return min(maximum_zoom, max(1.0, required))
```

- [ ] **Step 4: Integrate QGraphicsScene in MeshView**

Replace `_MeshLabel` with:

```python
self.graphics_view = MeshGraphicsView()
self._scene = QGraphicsScene(self)
self.graphics_view.setScene(self._scene)
self._screen_item = self._scene.addPixmap(QPixmap())
self._detail_item = self._scene.addPixmap(QPixmap())
self._scene.setSceneRect(0, 0, 700, 700)
```

On `update_mesh`:

- render screen pixmap immediately;
- clear cached detail pixmap;
- set the screen item to 700×700;
- create the detailed item lazily when zoom reaches the threshold;
- scale the detailed item with `QTransform.fromScale(700 / width, 700 / height)`;
- call `reset_view`.

On `zoom_changed`:

- dense map below threshold: show screen item;
- at/above threshold: ensure detailed pixmap exists, show detail item;
- sparse map threshold 1×: show detailed item immediately.

Tooltip receives scene coordinates and calls:

```python
mesh_index_at_position(x, y, 700, 700, 700, 700, x_count, y_count)
```

- [ ] **Step 5: Run tests and verify GREEN**

Run the Task 1 command. Expected: all tests pass.

- [ ] **Step 6: Verify existing 2D/3D behavior**

```powershell
$env:QT_QPA_PLATFORM='windows'
Push-Location win\pyqt6\ui\components
py -3 -m unittest test_mesh_3d_math.py test_mesh_2d_layout.py -v
Pop-Location
```

Expected: all tests pass.

- [ ] **Step 7: Commit Task 2**

```powershell
git add -- win/pyqt6/ui/components/mesh_2d_layout.py win/pyqt6/ui/components/mesh_view.py win/pyqt6/ui/components/test_mesh_2d_layout.py
git commit -m "feat(win): zoom and pan dense 2d mesh"
```

### Task 3: Визуальная и итоговая проверка

**Files:**
- Verification output only: `%TEMP%\bedmesh-zoom-pan-check\fit-31x31.png`
- Verification output only: `%TEMP%\bedmesh-zoom-pan-check\zoomed-31x31.png`

- [ ] **Step 1: Generate fit and zoomed screenshots**

Create a visible offscreen test window with a synthetic 31×31 mesh:

```python
view.resize(700, 700)
view.show()
view.update_mesh(make_mesh(31))
view.grab().save("fit-31x31.png")
view.graphics_view.set_zoom_factor(3.0)
view.graphics_view.centerOn(350, 350)
view.grab().save("zoomed-31x31.png")
```

- [ ] **Step 2: Inspect screenshots**

- `fit-31x31.png`: whole heatmap is visible without text clutter.
- `zoomed-31x31.png`: enlarged cells contain readable values.

- [ ] **Step 3: Run complete Windows verification**

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:QT_QPA_PLATFORM='windows'
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
py -3 -m ruff check mesh_2d_layout.py mesh_graphics_view.py mesh_view.py test_mesh_2d_layout.py
Pop-Location
py -3 -m compileall -q win\pyqt6
git diff --check
git status --short --branch
```

Expected: zero test failures, zero lint errors, clean compilation.

