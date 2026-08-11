from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import (Qt, QPropertyAnimation, QEasingCurve,
                          pyqtSignal, pyqtProperty, QRectF)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    _TRACK_W   = 62
    _TRACK_H   = 28
    _KNOB_D    = 22
    _MARGIN    = (_TRACK_H - _KNOB_D) // 2

    _COLOR_ON_TRACK  = QColor("#3b82f6")   # синий
    _COLOR_OFF_TRACK = QColor("#3a3a3a")
    _COLOR_KNOB      = QColor("#ffffff")
    _COLOR_TEXT_ON   = QColor("#ffffff")
    _COLOR_TEXT_OFF  = QColor("#888888")

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._knob_x = float(self._knob_on_x() if checked else self._knob_off_x())

        self.setFixedSize(self._TRACK_W, self._TRACK_H)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"knob_x", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    # ── property для анимации ──────────────────────────────────────────────
    def _get_knob_x(self) -> float:
        return self._knob_x

    def _set_knob_x(self, val: float):
        self._knob_x = val
        self.update()

    knob_x = pyqtProperty(float, _get_knob_x, _set_knob_x)

    # ── вспомогательные позиции ────────────────────────────────────────────
    def _knob_off_x(self) -> float:
        return float(self._MARGIN)

    def _knob_on_x(self) -> float:
        return float(self._TRACK_W - self._MARGIN - self._KNOB_D)

    # ── публичный API ──────────────────────────────────────────────────────
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool):
        if val == self._checked:
            return
        self._checked = val
        self._animate_to(val)

    # ── события ────────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._animate_to(self._checked)
            self.toggled.emit(self._checked)

    def _animate_to(self, on: bool):
        self._anim.stop()
        self._anim.setStartValue(self._knob_x)
        self._anim.setEndValue(self._knob_on_x() if on else self._knob_off_x())
        self._anim.start()

    # ── отрисовка ──────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Интерполируем цвет трека по позиции ручки
        t = (self._knob_x - self._knob_off_x()) / max(
            self._knob_on_x() - self._knob_off_x(), 1
        )
        t = max(0.0, min(1.0, t))
        track_color = _lerp_color(self._COLOR_OFF_TRACK, self._COLOR_ON_TRACK, t)

        # Трек
        track_rect = QRectF(0, 0, self._TRACK_W, self._TRACK_H)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(track_rect, self._TRACK_H / 2, self._TRACK_H / 2)

        # Текст ON / OFF
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        p.setFont(font)
        if self._checked:
            p.setPen(QPen(self._COLOR_TEXT_ON))
            text_rect = QRectF(4, 0, self._TRACK_W - self._KNOB_D - 6, self._TRACK_H)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "ON")
        else:
            p.setPen(QPen(self._COLOR_TEXT_OFF))
            text_rect = QRectF(self._KNOB_D + 2, 0, self._TRACK_W - self._KNOB_D - 6, self._TRACK_H)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "OFF")

        # Ручка
        knob_rect = QRectF(self._knob_x, self._MARGIN, self._KNOB_D, self._KNOB_D)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._COLOR_KNOB)
        p.drawEllipse(knob_rect)

        p.end()


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    return QColor(
        int(c1.red()   + (c2.red()   - c1.red())   * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue()  + (c2.blue()  - c1.blue())  * t),
    )
