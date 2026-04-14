import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from core.mesh_parser import BedMeshData

class MeshView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.view = pg.GraphicsLayoutWidget()
        layout.addWidget(self.view)

        self.plot = self.view.addPlot()
        self.plot.setAspectLocked(True)
        self.plot.invertY(True)
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')
        self.plot.showGrid(x=True, y=True, alpha=0.3)

        self.img = pg.ImageItem()
        self.plot.addItem(self.img)

        self.colorbar = pg.ColorBarItem(
            values=(-0.05, 0.05),
            colorMap=pg.colormap.get('viridis')
        )
        self.colorbar.setImageItem(self.img)

    def update_mesh(self, data: BedMeshData):  # ← ИСПРАВЛЕНО
        self.img.setImage(data.z)
        x_range = data.max_x - data.min_x
        y_range = data.max_y - data.min_y
        self.img.setRect(data.min_x, data.min_y, x_range, y_range)
        self.colorbar.setLevels([data.z.min(), data.z.max()])
        self.plot.setLimits(xMin=data.min_x, xMax=data.max_x,
                            yMin=data.min_y, yMax=data.max_y)