# Win Mesh 3D (pyqtgraph OpenGL) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** На вкладке Карта Windows-клиента добавить режим 3D (pyqtgraph `GLViewWidget` + `GLSurfacePlotItem`) с орбитой/зумом мышью и переключателем 2D|3D.

**Architecture:** Чистые хелперы цвета/масштаба Z без OpenGL → ленивый `Mesh3DView` (GL поднимается при первом выборе 3D) → `CenterTabs` со `QStackedWidget` и сохранением `mesh_view_mode` → deps + PyInstaller hiddenimports + bump `0.170-win`.

**Tech Stack:** PyQt6, numpy, pyqtgraph, PyOpenGL, unittest, PyInstaller onefile (CI).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-19-win-mesh-3d-pyqtgraph-design.md`
- Режим по умолчанию: `mesh_view_mode: "2d"`
- Копирование в 3D: кнопка disabled + tooltip «только в 2D»
- OpenGL fail → QMessageBox + остаёмся в 2D; не ронять старт приложения
- macOS / Android / online — вне scope
- Версия при поставке: `0.170-win`
- Палитра: существующие ключи `classic` / `soft` / `icefire` через `build_lut`

## File map

| File | Role |
|---|---|
| `win/pyqt6/ui/components/mesh_3d_math.py` | Чистые функции: visual Z, colors из LUT (без GL) |
| `win/pyqt6/ui/components/test_mesh_3d_math.py` | Unit-тесты math |
| `win/pyqt6/ui/components/mesh_3d_view.py` | Ленивый `GLViewWidget` + `GLSurfacePlotItem` |
| `win/pyqt6/ui/panels/center_tabs.py` | 2D\|3D toggle, stack, copy disable |
| `win/pyqt6/utils/app_config.py` | дефолт `mesh_view_mode` |
| `win/pyqt6/app.py` | restore mode, save on change, sync mesh/palette to 3D |
| `win/pyqt6/requirements.txt` | pyqtgraph, PyOpenGL |
| `.github/workflows/build_win_pyqt6.yml` | hiddenimports OpenGL |
| `win/pyqt6/utils/version.py` | `0.170-win` |

---

### Task 1: Math helpers + тесты (без OpenGL)

**Files:**
- Create: `win/pyqt6/ui/components/mesh_3d_math.py`
- Create: `win/pyqt6/ui/components/test_mesh_3d_math.py`

**Interfaces:**
- Produces:
  - `Z_VISUAL_SCALE: float = 40.0` — множитель высоты для отображения
  - `def scaled_z(z: np.ndarray, scale: float = Z_VISUAL_SCALE) -> np.ndarray`
  - `def colors_from_z(z: np.ndarray, palette_key: str) -> np.ndarray` — shape `(ny, nx, 4)` float64 в диапазоне `[0, 1]` (RGBA), по нормализованному Z и `build_lut`
- Consumes: `ui.components.palettes.build_lut`

- [ ] **Step 1: Write failing test**

Создать `win/pyqt6/ui/components/test_mesh_3d_math.py`:

```python
import unittest

import numpy as np

from mesh_3d_math import Z_VISUAL_SCALE, colors_from_z, scaled_z


class TestMesh3DMath(unittest.TestCase):
    def test_scaled_z_multiplies(self):
        z = np.array([[0.0, 0.1], [-0.05, 0.02]], dtype=float)
        out = scaled_z(z, scale=10.0)
        np.testing.assert_allclose(out, z * 10.0)

    def test_default_scale_constant(self):
        z = np.ones((2, 2))
        np.testing.assert_allclose(scaled_z(z), z * Z_VISUAL_SCALE)

    def test_colors_shape_and_range(self):
        z = np.linspace(-0.2, 0.3, 12).reshape(3, 4)
        c = colors_from_z(z, "soft")
        self.assertEqual(c.shape, (3, 4, 4))
        self.assertTrue(np.all(c >= 0.0) and np.all(c <= 1.0))
        # min Z → cooler end, max Z → warmer (R channel higher at max than at min for soft)
        self.assertGreater(c[2, 3, 0], c[0, 0, 0])

    def test_colors_unknown_palette_falls_back(self):
        z = np.zeros((2, 2))
        c = colors_from_z(z, "no-such-palette")
        self.assertEqual(c.shape, (2, 2, 4))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test — expect FAIL**

```powershell
cd F:\github\bedmesh\win\pyqt6\ui\components
py -3 -m unittest test_mesh_3d_math.py -v
```

Expected: `ModuleNotFoundError: No module named 'mesh_3d_math'` (или ImportError).

- [ ] **Step 3: Implement math module**

Создать `win/pyqt6/ui/components/mesh_3d_math.py`:

```python
import numpy as np

from ui.components.palettes import build_lut

Z_VISUAL_SCALE = 40.0


def scaled_z(z: np.ndarray, scale: float = Z_VISUAL_SCALE) -> np.ndarray:
    return np.asarray(z, dtype=float) * float(scale)


def colors_from_z(z: np.ndarray, palette_key: str) -> np.ndarray:
    """RGBA float colors in [0, 1], shape (ny, nx, 4), for GLSurfacePlotItem."""
    z = np.asarray(z, dtype=float)
    z_min = float(np.min(z))
    z_max = float(np.max(z))
    norm = (z - z_min) / (z_max - z_min + 1e-9)
    idx = (norm * 255).astype(np.uint8)
    lut = build_lut(palette_key)  # (256, 4) uint8
    rgba_u8 = lut[idx]
    return rgba_u8.astype(np.float64) / 255.0
```

Если импорт `ui.components.palettes` ломает unittest при запуске из `components/`, использовать относительный импорт в тесте через `sys.path` как в других тестах проекта **или** запускать из `win/pyqt6`:

Предпочтительный запуск (и импорт в тесте):

В `test_mesh_3d_math.py` заменить импорт на:

```python
import os
import sys
import unittest

import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui.components.mesh_3d_math import Z_VISUAL_SCALE, colors_from_z, scaled_z
```

И в `mesh_3d_math.py` оставить `from ui.components.palettes import build_lut`.

- [ ] **Step 4: Run test — expect PASS**

```powershell
cd F:\github\bedmesh\win\pyqt6
py -3 -m unittest ui.components.test_mesh_3d_math -v
```

Expected: все тесты `OK`.

- [ ] **Step 5: Commit**

```powershell
git add win/pyqt6/ui/components/mesh_3d_math.py win/pyqt6/ui/components/test_mesh_3d_math.py
git commit -m "feat(win): mesh 3D color/scale helpers"
```

---

### Task 2: Зависимости pyqtgraph + PyOpenGL

**Files:**
- Modify: `win/pyqt6/requirements.txt`

**Interfaces:**
- Produces: pip-пакеты, доступные приложению и CI

- [ ] **Step 1: Update requirements**

Содержимое `win/pyqt6/requirements.txt` должно быть:

```text
PyQt6
numpy
paramiko
requests
pyqtgraph
PyOpenGL
```

- [ ] **Step 2: Install locally**

```powershell
cd F:\github\bedmesh\win\pyqt6
py -3 -m pip install -r requirements.txt
py -3 -c "import pyqtgraph; import OpenGL; from pyqtgraph.opengl import GLViewWidget, GLSurfacePlotItem; print(pyqtgraph.__version__)"
```

Expected: версия pyqtgraph печатается без traceback.

- [ ] **Step 3: Commit**

```powershell
git add win/pyqt6/requirements.txt
git commit -m "chore(win): add pyqtgraph and PyOpenGL deps"
```

---

### Task 3: `Mesh3DView` — ленивый OpenGL виджет

**Files:**
- Create: `win/pyqt6/ui/components/mesh_3d_view.py`

**Interfaces:**
- Consumes: `BedMeshData`, `scaled_z`, `colors_from_z`
- Produces класс `Mesh3DView(QWidget)`:
  - `def set_palette(self, palette_key: str) -> None`
  - `def update_mesh(self, data: BedMeshData) -> None`
  - `def ensure_ready(self) -> bool` — создать GL при первом вызове; `True` если готов, `False` если OpenGL недоступен (виджет остаётся пустым placeholder)
  - `def is_ready(self) -> bool`

- [ ] **Step 1: Implement `mesh_3d_view.py`**

```python
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from core.mesh_parser import BedMeshData
from ui.components.mesh_3d_math import colors_from_z, scaled_z

# pyqtgraph/OpenGL импортируются лениво внутри ensure_ready()


class Mesh3DView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._palette_key = "soft"
        self._data: BedMeshData | None = None
        self._gl_view = None
        self._surface = None
        self._ready = False
        self._failed = False

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._placeholder = QLabel("3D: не инициализировано")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("background: #1e1e1e; color: #888; border: 1px solid #444;")
        self._layout.addWidget(self._placeholder)

    def is_ready(self) -> bool:
        return self._ready

    def set_palette(self, palette_key: str) -> None:
        self._palette_key = palette_key or "classic"
        if self._ready and self._data is not None:
            self.update_mesh(self._data)

    def ensure_ready(self) -> bool:
        if self._ready:
            return True
        if self._failed:
            return False
        try:
            import pyqtgraph.opengl as gl  # noqa: WPS433
            import numpy as np

            view = gl.GLViewWidget()
            view.setBackgroundColor((30, 30, 30))
            view.opts["distance"] = 40
            view.opts["elevation"] = 25
            view.opts["azimuth"] = -60

            grid = gl.GLGridItem()
            grid.setSize(x=20, y=20)
            grid.setSpacing(x=1, y=1)
            view.addItem(grid)

            # Пустая поверхность; данные придут в update_mesh
            z0 = np.zeros((2, 2))
            surface = gl.GLSurfacePlotItem(
                z=z0,
                shader="shaded",
                smooth=False,
                computeNormals=True,
            )
            view.addItem(surface)

            self._layout.removeWidget(self._placeholder)
            self._placeholder.hide()
            self._layout.addWidget(view)
            self._gl_view = view
            self._surface = surface
            self._ready = True
            if self._data is not None:
                self.update_mesh(self._data)
            return True
        except Exception as e:
            self._failed = True
            self._placeholder.setText(f"3D недоступен:\n{e}")
            return False

    def update_mesh(self, data: BedMeshData) -> None:
        self._data = data
        if not self._ready or self._surface is None:
            return
        import numpy as np

        z = np.asarray(data.z, dtype=float)
        z_vis = scaled_z(z)
        cols = colors_from_z(z, self._palette_key)

        # x/y в мм сетки; центрируем вокруг 0 для удобной орбиты
        x = np.asarray(data.x, dtype=float)
        y = np.asarray(data.y, dtype=float)
        x_c = x - float(np.mean(x))
        y_c = y - float(np.mean(y))

        self._surface.setData(x=x_c, y=y_c, z=z_vis, colors=cols)

        # Камера: расстояние от размера стола
        span = max(float(np.ptp(x)), float(np.ptp(y)), 1.0)
        if self._gl_view is not None:
            self._gl_view.opts["distance"] = span * 1.8
            self._gl_view.opts["center"] = self._gl_view.opts.get("center")  # keep
            # pyqtgraph uses Vector for center:
            from pyqtgraph import Vector

            self._gl_view.opts["center"] = Vector(0, 0, float(np.mean(z_vis)))
            self._gl_view.update()
```

Примечание исполнителю: если сигнатура `GLSurfacePlotItem.setData` / конструктор в установленной версии pyqtgraph отличается (например, нет `colors=`), свериться с `help(gl.GLSurfacePlotItem)` и передать цвета через поддерживаемый API той же версии (часто `colors=` на `setData` или vertex colors). Не менять UX спеки.

- [ ] **Step 2: Smoke import (без GUI display)**

```powershell
cd F:\github\bedmesh\win\pyqt6
py -3 -c "from ui.components.mesh_3d_view import Mesh3DView; print('ok', Mesh3DView)"
```

Expected: `ok <class ...Mesh3DView>`

- [ ] **Step 3: Commit**

```powershell
git add win/pyqt6/ui/components/mesh_3d_view.py
git commit -m "feat(win): lazy Mesh3DView with GLSurfacePlotItem"
```

---

### Task 4: `CenterTabs` — переключатель 2D|3D

**Files:**
- Modify: `win/pyqt6/ui/panels/center_tabs.py`

**Interfaces:**
- Consumes: `MeshView`, `Mesh3DView`
- Produces:
  - сигнал `view_mode_changed = pyqtSignal(str)` с `"2d"` / `"3d"`
  - `def set_view_mode(self, mode: str) -> None`
  - `def get_view_mode(self) -> str`
  - `def update_mesh_views(self, data) -> None` — обновляет 2D всегда; 3D если ready
  - `def set_mesh_palette(self, key: str) -> None`
  - атрибут `mesh_view` (2D) сохраняется для обратной совместимости
  - атрибут `mesh_3d_view: Mesh3DView | None` — создаётся при первом `"3d"`

- [ ] **Step 1: Rewrite mesh tab section in `center_tabs.py`**

Заменить импорты и конструктор вкладки Карта + добавить методы. Полный целевой файл:

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTextEdit, QPushButton, QHBoxLayout,
    QStackedWidget, QButtonGroup,
)
from PyQt6.QtCore import pyqtSignal, Qt
from ui.components.mesh_view import MeshView
from ui.components.mesh_3d_view import Mesh3DView
from ui.components.config_editor import ConfigEditor
from utils.strings import S
from PyQt6.QtWidgets import QMessageBox


class CenterTabs(QWidget):
    view_mode_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self._advanced_visible = True
        self._view_mode = "2d"
        self.mesh_3d_view: Mesh3DView | None = None
        self._last_mesh = None

        self.mesh_tab = QWidget()
        m_layout = QVBoxLayout(self.mesh_tab)
        m_layout.setContentsMargins(0, 0, 0, 0)

        btn_row = QHBoxLayout()
        self.btn_copy = QPushButton(S.get("mesh.copy_btn"))
        self.btn_copy.setFixedSize(180, 28)
        self.btn_copy.clicked.connect(self._on_copy_mesh)
        btn_row.addWidget(self.btn_copy)

        self.btn_2d = QPushButton("2D")
        self.btn_3d = QPushButton("3D")
        self.btn_2d.setCheckable(True)
        self.btn_3d.setCheckable(True)
        self.btn_2d.setChecked(True)
        self.btn_2d.setFixedWidth(48)
        self.btn_3d.setFixedWidth(48)
        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)
        mode_group.addButton(self.btn_2d)
        mode_group.addButton(self.btn_3d)
        self.btn_2d.clicked.connect(lambda: self.set_view_mode("2d"))
        self.btn_3d.clicked.connect(lambda: self.set_view_mode("3d"))
        btn_row.addWidget(self.btn_2d)
        btn_row.addWidget(self.btn_3d)
        btn_row.addStretch()
        m_layout.addLayout(btn_row)

        self._mesh_stack = QStackedWidget()
        self.mesh_view = MeshView()
        self._mesh_stack.addWidget(self.mesh_view)
        m_layout.addWidget(self._mesh_stack)
        self.tabs.addTab(self.mesh_tab, S.get("mesh.tab_title"))

        self.config_tab = QWidget()
        c_layout = QVBoxLayout(self.config_tab)
        c_layout.setContentsMargins(0, 0, 0, 0)
        self.config_editor = ConfigEditor()
        c_layout.addWidget(self.config_editor)
        self.tabs.addTab(self.config_tab, S.get("config.tab_title"))

        self.raw_tab = QWidget()
        r_layout = QVBoxLayout(self.raw_tab)
        r_layout.setContentsMargins(5, 5, 5, 5)
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px; background: #1e1e1e; color: #d4d4d4;"
        )
        r_layout.addWidget(self.raw_text)
        self.tabs.addTab(self.raw_tab, S.get("raw.tab_title"))

        self.set_advanced_visible(False)

    def get_view_mode(self) -> str:
        return self._view_mode

    def set_mesh_palette(self, key: str) -> None:
        self.mesh_view.set_palette(key)
        if self.mesh_3d_view is not None:
            self.mesh_3d_view.set_palette(key)

    def update_mesh_views(self, data) -> None:
        self._last_mesh = data
        self.mesh_view.update_mesh(data)
        if self.mesh_3d_view is not None and self.mesh_3d_view.is_ready():
            self.mesh_3d_view.update_mesh(data)

    def set_view_mode(self, mode: str) -> None:
        mode = "3d" if mode == "3d" else "2d"
        if mode == "3d":
            if self.mesh_3d_view is None:
                self.mesh_3d_view = Mesh3DView()
                self._mesh_stack.addWidget(self.mesh_3d_view)
            if not self.mesh_3d_view.ensure_ready():
                QMessageBox.warning(
                    self,
                    "3D недоступен",
                    "Не удалось инициализировать OpenGL.\nОстаёмся в режиме 2D.",
                )
                self.btn_2d.setChecked(True)
                self.btn_3d.setChecked(False)
                mode = "2d"
            else:
                if self._last_mesh is not None:
                    self.mesh_3d_view.update_mesh(self._last_mesh)
                self._mesh_stack.setCurrentWidget(self.mesh_3d_view)
                self.btn_3d.setChecked(True)
                self.btn_2d.setChecked(False)
        if mode == "2d":
            self._mesh_stack.setCurrentWidget(self.mesh_view)
            self.btn_2d.setChecked(True)
            self.btn_3d.setChecked(False)

        self._view_mode = mode
        self.btn_copy.setEnabled(mode == "2d")
        self.btn_copy.setToolTip("" if mode == "2d" else "Копирование доступно только в 2D")
        self.view_mode_changed.emit(mode)

    def set_advanced_visible(self, visible: bool):
        visible = bool(visible)
        if visible == self._advanced_visible:
            return
        self._advanced_visible = visible

        def _tab_index(widget: QWidget) -> int:
            try:
                return self.tabs.indexOf(widget)
            except Exception:
                return -1

        if not visible:
            cur = self.tabs.currentWidget()
            if cur in (self.config_tab, self.raw_tab):
                self.tabs.setCurrentWidget(self.mesh_tab)
            idx_raw = _tab_index(self.raw_tab)
            if idx_raw >= 0:
                self.tabs.removeTab(idx_raw)
            idx_cfg = _tab_index(self.config_tab)
            if idx_cfg >= 0:
                self.tabs.removeTab(idx_cfg)
            return

        if _tab_index(self.config_tab) < 0:
            self.tabs.insertTab(1, self.config_tab, S.get("config.tab_title"))
        if _tab_index(self.raw_tab) < 0:
            self.tabs.insertTab(2, self.raw_tab, S.get("raw.tab_title"))

    def _on_copy_mesh(self):
        if self._view_mode != "2d":
            return
        self.mesh_view.copy_to_clipboard()
```

- [ ] **Step 2: Manual smoke (опционально в этой задаче)**

```powershell
cd F:\github\bedmesh\win\pyqt6
py -3 -c "from PyQt6.QtWidgets import QApplication; import sys; app=QApplication(sys.argv); from ui.panels.center_tabs import CenterTabs; w=CenterTabs(); print(w.get_view_mode())"
```

Expected: печатает `2d`.

- [ ] **Step 3: Commit**

```powershell
git add win/pyqt6/ui/panels/center_tabs.py
git commit -m "feat(win): 2D/3D toggle on mesh tab"
```

---

### Task 5: `AppConfig` + `BedMeshApp` wiring

**Files:**
- Modify: `win/pyqt6/utils/app_config.py`
- Modify: `win/pyqt6/app.py`

**Interfaces:**
- Consumes: `CenterTabs.view_mode_changed`, `update_mesh_views`, `set_mesh_palette`, `set_view_mode`
- Produces: персистентный `mesh_view_mode` в settings.json

- [ ] **Step 1: Add default in `app_config.py`**

В `self.defaults` добавить ключ (рядом с `"debug_mode"`):

```python
"mesh_view_mode": "2d",
```

Полный блок `defaults` после правки:

```python
        self.defaults = {
            "ssh_ip": "192.168.",
            "ssh_port": "2222",
            "ssh_user": "root",
            "ssh_pass": "rockchip",
            "ssh_path": "/userdata/app/gk/printer.cfg",
            "debug_mode": "true",
            "mesh_view_mode": "2d",
            "window_geometry": ""
        }
```

- [ ] **Step 2: Wire `app.py`**

В `_init_ui` заменить прямую установку палитры и вызовы `mesh_view.update_mesh` на методы CenterTabs.

После создания панелей:

```python
        # Применяем палитру и режим карты из настроек
        self.center_tabs.set_mesh_palette(self.settings.get("mesh_palette", "soft"))
        self.center_tabs.view_mode_changed.connect(self._on_view_mode_changed)
```

Удалить строку:

```python
        self.center_tabs.mesh_view.set_palette(self.settings.get("mesh_palette", "soft"))
```

Добавить метод:

```python
    def _on_view_mode_changed(self, mode: str):
        self.settings["mesh_view_mode"] = mode
        self.config.save()
```

В конце `_init_ui` (после коннектов) восстановить режим **без** принудительного GL на старте, если сохранён 2d; если сохранён 3d — вызвать `set_view_mode("3d")` (ленивый GL):

```python
        saved_mode = self.settings.get("mesh_view_mode", "2d")
        if saved_mode == "3d":
            self.center_tabs.set_view_mode("3d")
```

В `_process_file` (оба места, где сейчас `self.center_tabs.mesh_view.update_mesh(...)`) заменить на:

```python
                self.center_tabs.update_mesh_views(data)
```

и аналогично для `alt_data`:

```python
                            self.center_tabs.update_mesh_views(alt_data)
```

- [ ] **Step 3: Commit**

```powershell
git add win/pyqt6/utils/app_config.py win/pyqt6/app.py
git commit -m "feat(win): persist mesh_view_mode and sync 3D updates"
```

---

### Task 6: CI hiddenimports + version bump

**Files:**
- Modify: `.github/workflows/build_win_pyqt6.yml`
- Modify: `win/pyqt6/utils/version.py`

**Interfaces:**
- Produces: exe со включённым OpenGL/pyqtgraph; версия `0.170-win`

- [ ] **Step 1: Bump version**

`win/pyqt6/utils/version.py`:

```python
VERSION = "0.170-win"
```

- [ ] **Step 2: Add PyInstaller hidden imports**

В `.github/workflows/build_win_pyqt6.yml` в команду `python -m PyInstaller ...` добавить флаги (перед `win/pyqt6/main.py`):

```bash
            --hidden-import OpenGL \
            --hidden-import OpenGL.platform.win32 \
            --hidden-import pyqtgraph.opengl \
            --collect-submodules OpenGL \
```

Итоговый фрагмент `run:` (сохранить существующие `--add-data` и `--runtime-tmpdir`):

```yaml
      - name: Собрать exe (PyQt6)
        shell: bash
        run: |
          python -m PyInstaller --onefile --noconsole \
            --name "Bed.Mesh.Visualizer" \
            --icon "win/pyqt6/icon.ico" \
            --add-data "win/pyqt6/ui/locale;ui/locale" \
            --add-data "win/pyqt6/icon.ico;." \
            --add-data "webpanel/gkbridge;resources" \
            --add-data "webpanel/camera;resources/camera" \
            --add-data "win/pyqt6/resources/boot.sh;resources" \
            --runtime-tmpdir "%LOCALAPPDATA%\rkfsociety\BedMesh Visualizer\runtime" \
            --hidden-import OpenGL \
            --hidden-import OpenGL.platform.win32 \
            --hidden-import pyqtgraph.opengl \
            --collect-submodules OpenGL \
            win/pyqt6/main.py
```

Если в workflow есть body релиза с упоминанием версии — обновить текст на `0.170-win` и коротко: «3D карта mesh (OpenGL, orbit/zoom)».

- [ ] **Step 3: Run unit tests**

```powershell
cd F:\github\bedmesh\win\pyqt6
py -3 -m unittest ui.components.test_mesh_3d_math utils.test_cache_paths utils.test_updater_bat -v
```

Expected: `OK`.

- [ ] **Step 4: Manual acceptance (локально)**

```powershell
cd F:\github\bedmesh\win\pyqt6
py -3 main.py
```

Проверить по спеке:
1. Переключатель 2D|3D на вкладке Карта; дефолт 2D.
2. После SSH/загрузки cfg — 3D показывает рельеф; мышь крутит/зумит.
3. Копировать в 3D disabled.
4. Перезапуск сохраняет режим.
5. (Если возможно) симулировать fail GL не обязательно на этой машине.

- [ ] **Step 5: Commit**

```powershell
git add win/pyqt6/utils/version.py .github/workflows/build_win_pyqt6.yml
git commit -m "chore(win): bump 0.170-win, PyInstaller OpenGL imports"
```

---

## Spec coverage checklist

| Requirement | Task |
|---|---|
| Переключатель 2D\|3D, дефолт 2D | Task 4 |
| Persist `mesh_view_mode` | Task 5 |
| GLSurfacePlotItem + palette colors | Task 1, 3 |
| Mouse orbit/zoom (pyqtgraph default) | Task 3 |
| Lazy GL + MessageBox fallback | Task 3, 4 |
| Copy disabled in 3D | Task 4 |
| deps + CI hiddenimports | Task 2, 6 |
| Version `0.170-win` | Task 6 |
| No Z labels / no 3D screenshot | YAGNI (не делаем) |
| Mac/Android out of scope | — |

## Self-review notes

- Нет TBD/placeholder в шагах.
- Сигнатуры `ensure_ready` / `update_mesh_views` / `set_view_mode` согласованы между Task 3–5.
- Тесты без GUI покрывают math; GL проверяется ручным smoke + acceptance.
