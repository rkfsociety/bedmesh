from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTextEdit, QPushButton, QHBoxLayout,
    QStackedWidget, QButtonGroup, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal
from ui.components.mesh_view import MeshView
from ui.components.mesh_3d_view import Mesh3DView
from ui.components.config_editor import ConfigEditor
from utils.strings import S


class CenterTabs(QWidget):
    view_mode_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

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
        self.btn_copy.setObjectName("secondaryButton")
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
            "font-family: Consolas, monospace; font-size: 12px; "
            "background: #101a2b; color: #d7e2f2; border: 1px solid #2f4668;"
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
