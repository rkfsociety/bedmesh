from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

class RightPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background-color: #101a2b;
                color: #e8eef8;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel { color: #e8eef8; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        title = QLabel("📊 АНАЛИЗ МЕША")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #e8eef8; border-bottom: 1px solid #304765; padding-bottom: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(10)
        
        self.card_min, self.lbl_min = self._create_card("Мин", "0.000", "#00ffff")
        self.card_max, self.lbl_max = self._create_card("Макс", "0.000", "#ff0000")
        self.card_range, self.lbl_range = self._create_card("Размах", "0.000", "#ffaa00")
        self.card_mean, self.lbl_mean = self._create_card("Среднее", "0.000", "#ffffff")
        self.card_var, self.lbl_var = self._create_card("Варианс", "0.000", "#ffffff")
        self.card_rms, self.lbl_rms = self._create_card("RMS", "0.000", "#ffffff")

        stats_grid.addWidget(self.card_min, 0, 0)
        stats_grid.addWidget(self.card_max, 0, 1)
        stats_grid.addWidget(self.card_range, 1, 0)
        stats_grid.addWidget(self.card_mean, 1, 1)
        stats_grid.addWidget(self.card_var, 2, 0)
        stats_grid.addWidget(self.card_rms, 2, 1)
        
        layout.addLayout(stats_grid)

        # --- Коррекция + Шейпер рядом ---
        side_row = QHBoxLayout()
        side_row.setSpacing(12)

        # Левая колонка: коррекция стола
        corr_col = QVBoxLayout()
        corr_col.setSpacing(6)

        corr_title = QLabel("🔧 КОРРЕКЦИЯ")
        corr_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #bbb; margin-top: 10px;")
        corr_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corr_col.addWidget(corr_title)

        self.lbl_correction_info = QLabel("(от среднего, кручение валов)")
        self.lbl_correction_info.setStyleSheet("font-size: 10px; color: #666;")
        self.lbl_correction_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corr_col.addWidget(self.lbl_correction_info)

        self.card_fl, self.lbl_fl_mm, self.lbl_fl_turns = self._create_correction_card("ПЕРЕДНИЙ ЛЕВЫЙ", 0.0, 0.0, "ВВЕРХ")
        self.card_fr, self.lbl_fr_mm, self.lbl_fr_turns = self._create_correction_card("ПЕРЕДНИЙ ПРАВЫЙ", 0.0, 0.0, "ВВЕРХ")
        self.card_bc, self.lbl_bc_mm, self.lbl_bc_turns = self._create_correction_card("ЗАДНИЙ ЦЕНТР", 0.0, 0.0, "ВНИЗ")

        corr_col.addWidget(self.card_fl)
        corr_col.addWidget(self.card_fr)
        corr_col.addWidget(self.card_bc)
        corr_col.addStretch()

        # Правая колонка: шейпер
        shaper_col = QVBoxLayout()
        shaper_col.setSpacing(6)

        shaper_title = QLabel("⚡ ШЕЙПЕР")
        shaper_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #bbb; margin-top: 10px;")
        shaper_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shaper_col.addWidget(shaper_title)

        shaper_sub = QLabel("(рек. ускорение)")
        shaper_sub.setStyleSheet("font-size: 10px; color: #666;")
        shaper_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shaper_col.addWidget(shaper_sub)

        self._shaper_block = QWidget()
        self._shaper_block.setStyleSheet("background-color: #16243a; border: 1px solid #304765; border-radius: 7px;")
        shaper_layout = QVBoxLayout(self._shaper_block)
        shaper_layout.setSpacing(6)
        shaper_layout.setContentsMargins(8, 8, 8, 8)

        self._lbl_shaper_x = QLabel("X: —")
        self._lbl_shaper_x.setStyleSheet("font-size: 11px; color: #ccc;")
        self._lbl_shaper_y = QLabel("Y: —")
        self._lbl_shaper_y.setStyleSheet("font-size: 11px; color: #ccc;")

        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #3a3a3a;")

        self._lbl_shaper_rec = QLabel("Нет данных")
        self._lbl_shaper_rec.setStyleSheet("font-size: 10px; color: #888;")
        self._lbl_shaper_rec.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_shaper_rec.setWordWrap(False)

        self._lbl_shaper_accel = QLabel("")
        self._lbl_shaper_accel.setStyleSheet("font-size: 16px; font-weight: bold; color: #4ade80;")
        self._lbl_shaper_accel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        shaper_layout.addWidget(self._lbl_shaper_x)
        shaper_layout.addWidget(self._lbl_shaper_y)
        shaper_layout.addWidget(sep)
        shaper_layout.addWidget(self._lbl_shaper_rec)
        shaper_layout.addWidget(self._lbl_shaper_accel)

        shaper_col.addWidget(self._shaper_block)
        shaper_col.addStretch()

        side_row.addLayout(corr_col, stretch=1)
        side_row.addLayout(shaper_col, stretch=1)
        layout.addLayout(side_row)

        # --- Update / version status (bottom) ---
        self._update_release_data = None
        self._on_update_clicked = None

        upd_wrap = QWidget()
        upd_wrap.setStyleSheet("background-color: #111d31; border-top: 1px solid #304765;")
        upd_l = QVBoxLayout(upd_wrap)
        upd_l.setContentsMargins(8, 10, 8, 10)
        upd_l.setSpacing(6)

        self.lbl_version_status = QLabel("v?")
        self.lbl_version_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_version_status.setStyleSheet("font-size: 11px; color: #9aa0a6;")
        upd_l.addWidget(self.lbl_version_status)

        self.btn_update = QPushButton("Проверить обновления")
        self.btn_update.setObjectName("secondaryButton")
        self.btn_update.setFixedHeight(28)
        self.btn_update.clicked.connect(self._handle_update_clicked)
        self.btn_update.setStyleSheet("")
        upd_l.addWidget(self.btn_update)

        layout.addWidget(upd_wrap)
        layout.addStretch()

    def set_version_status(self, text: str):
        self.lbl_version_status.setText(text)

    def set_update_handler(self, handler):
        self._on_update_clicked = handler

    def set_update_available(self, release_data: dict, latest_tag: str | None = None, current_version: str | None = None):
        self._update_release_data = release_data
        latest = (latest_tag or (release_data.get("tag_name") if isinstance(release_data, dict) else None) or "").strip()
        if latest.lower().startswith("v"):
            latest = latest[1:]
        if current_version:
            self.lbl_version_status.setText(f"Требуется обновление (v{current_version} → v{latest})" if latest else "Требуется обновление")
        else:
            self.lbl_version_status.setText(f"Найдена v{latest}" if latest else "Требуется обновление")
        self.lbl_version_status.setStyleSheet("font-size: 11px; color: #f59e0b; font-weight: bold;")
        self.btn_update.setText("Обновить")

    def clear_update_available(self, version_text: str):
        self._update_release_data = None
        self.lbl_version_status.setText(version_text)
        self.lbl_version_status.setStyleSheet("font-size: 11px; color: #9aa0a6;")
        self.btn_update.setText("Проверить обновления")

    def set_checking_updates(self, checking: bool):
        self.btn_update.setEnabled(not checking)
        if checking:
            self.btn_update.setText("Проверка...")

    def _handle_update_clicked(self):
        if self._on_update_clicked:
            self._on_update_clicked(self._update_release_data)

    def _create_card(self, title, value, color):
        card = QWidget()
        card.setStyleSheet("background-color: #182841; border: 1px solid #2d4465; border-radius: 8px; padding: 8px;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 10px; color: #888;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        
        return card, lbl_val

    def _create_correction_card(self, title, val_mm, turns, direction_text):
        card = QWidget()
        card.setStyleSheet("background-color: #16243a; border: 1px solid #304765; border-radius: 7px; padding: 10px;")
        layout = QVBoxLayout(card)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #aaa;")
        layout.addWidget(lbl_title)

        row = QHBoxLayout()
        
        lbl_mm = QLabel(f"{val_mm:+.3f} мм")
        lbl_mm.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        lbl_turns = QLabel(f"({turns} об. {direction_text})")
        lbl_turns.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {'#4ade80' if 'ВВЕРХ' in direction_text else '#f87171'}")

        row.addWidget(lbl_mm)
        row.addStretch()
        row.addWidget(lbl_turns)
        layout.addLayout(row)

        return card, lbl_mm, lbl_turns

    # max_accel = K * f²  (threshold=0.12, damping=0.1, из shaper_calibrate.py Klipper)
    _SHAPER_K = {
        "zv":        2.60,
        "mzv":       2.15,
        "zvd":       2.00,
        "ei":        1.60,
        "2hump_ei":  1.11,
        "3hump_ei":  0.85,
    }

    def update_shaper(self, shaper: dict | None):
        if not shaper:
            self._lbl_shaper_x.setText("X: —")
            self._lbl_shaper_y.setText("Y: —")
            self._lbl_shaper_rec.setText("Нет данных шейпера")
            self._lbl_shaper_accel.setText("")
            return

        tx = shaper.get("shaper_type_x", "?")
        ty = shaper.get("shaper_type_y", "?")
        fx = shaper.get("shaper_freq_x", 0.0)
        fy = shaper.get("shaper_freq_y", 0.0)

        self._lbl_shaper_x.setText(f"X: {tx.upper()}  {fx:.1f} Гц")
        self._lbl_shaper_y.setText(f"Y: {ty.upper()}  {fy:.1f} Гц")

        kx = self._SHAPER_K.get(tx.lower())
        ky = self._SHAPER_K.get(ty.lower())

        if kx and ky and fx > 0 and fy > 0:
            ax = kx * fx ** 2
            ay = ky * fy ** 2
            rec = int(min(ax, ay) / 500) * 500
            limit_axis = "X" if ax < ay else "Y"
            self._lbl_shaper_rec.setText(f"лимит: ось {limit_axis}")
            self._lbl_shaper_rec.setStyleSheet("font-size: 11px; color: #888;")
            self._lbl_shaper_accel.setText(f"≤ {rec} мм/с²")
            self._lbl_shaper_accel.setStyleSheet("font-size: 18px; font-weight: bold; color: #4ade80;")
        else:
            self._lbl_shaper_rec.setText(f"Тип шейпера не распознан")
            self._lbl_shaper_rec.setStyleSheet("font-size: 11px; color: #f87171;")
            self._lbl_shaper_accel.setText("")

    def update_all(self, stats: dict):
        self.lbl_min.setText(f"{stats['min']:+.3f}")
        self.lbl_max.setText(f"{stats['max']:+.3f}")
        self.lbl_range.setText(f"{stats['range']:.3f}")
        self.lbl_mean.setText(f"{stats['mean']:+.3f}")
        self.lbl_var.setText(f"{stats['var']:.3f}")
        self.lbl_rms.setText(f"{stats['rms']:.3f}")

        self._update_correction(self.lbl_fl_mm, self.lbl_fl_turns, stats['front_left'])
        self._update_correction(self.lbl_fr_mm, self.lbl_fr_turns, stats['front_right'])
        self._update_correction(self.lbl_bc_mm, self.lbl_bc_turns, stats['back_center'])

    def _update_correction(self, lbl_mm, lbl_turns, val_mm):
        turns = abs(val_mm) / 0.7
        direction = "ВВЕРХ" if val_mm < 0 else "ВНИЗ"
        
        lbl_mm.setText(f"{val_mm:+.3f} мм")
        lbl_turns.setText(f"({turns:.2f} об. {direction})")
        
        color = '#4ade80' if direction == "ВВЕРХ" else '#f87171'
        lbl_turns.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color}")
