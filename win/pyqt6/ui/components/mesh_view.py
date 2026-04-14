from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MeshView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("🌐 3D/2D визуализация Bed Mesh"))