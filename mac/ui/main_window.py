from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QPushButton, QVBoxLayout, QWidget

from core.mesh_parser import BedMeshData
from ui.components.mesh_view import MeshView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BedMesh Visualizer")
        self.resize(900, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        button_layout = QHBoxLayout()

        btn_copy = QPushButton("📋 Копировать карту")
        btn_copy.clicked.connect(self.on_copy_map)
        button_layout.addWidget(btn_copy)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.mesh_view = MeshView()
        layout.addWidget(self.mesh_view)

    def on_copy_map(self):
        self.mesh_view.copy_to_clipboard()

    def load_mesh(self, data: BedMeshData):
        self.mesh_view.update_mesh(data)
