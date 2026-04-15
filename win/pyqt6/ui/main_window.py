from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from ui.components.mesh_view import MeshView
from core.mesh_parser import BedMeshData
import numpy as np

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BedMesh Visualizer")
        self.resize(900, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 🎨 Кнопки управления
        btn_layout = QHBoxLayout()
        
        btn_copy = QPushButton("📋 Копировать карту")
        btn_copy.clicked.connect(self.on_copy_map)
        btn_layout.addWidget(btn_copy)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 🗺️ Область карты
        self.mesh_view = MeshView()
        layout.addWidget(self.mesh_view)

    def on_copy_map(self):
        """Обработчик кнопки копирования"""
        self.mesh_view.copy_to_clipboard()

    def load_mesh(self, data: BedMeshData):
        """Публичный метод для обновления карты"""
        self.mesh_view.update_mesh(data)