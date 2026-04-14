from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox

class RightPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("📊 Статистика")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.stats_group = QGroupBox()
        self.stats_group.setEnabled(False)
        stats_layout = QVBoxLayout(self.stats_group)
        stats_layout.setContentsMargins(8, 8, 8, 8)

        self.lbl_min = QLabel("Мин: —")
        self.lbl_max = QLabel("Макс: —")
        self.lbl_avg = QLabel("Среднее: —")
        self.lbl_range = QLabel("Разброс: —")
        self.lbl_points = QLabel("Точек: —")

        for lbl in [self.lbl_min, self.lbl_max, self.lbl_avg, self.lbl_range, self.lbl_points]:
            lbl.setStyleSheet("font-family: Consolas, monospace;")
            stats_layout.addWidget(lbl)

        layout.addWidget(self.stats_group)
        layout.addStretch()

    def update_stats(self, stats: dict):  # ← ИСПРАВЛЕНО
        self.stats_group.setEnabled(True)
        self.lbl_min.setText(f"Мин: {stats['min']:+.4f} мм")
        self.lbl_max.setText(f"Макс: {stats['max']:+.4f} мм")
        self.lbl_avg.setText(f"Среднее: {stats['mean']:+.4f} мм")
        self.lbl_range.setText(f"Разброс: {stats['range']:.4f} мм")
        self.lbl_points.setText(f"Точек: {stats['count']}")