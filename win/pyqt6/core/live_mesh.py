"""Сборка частичной bed mesh из строк журнала GoKlipper."""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

try:
    from core.mesh_parser import BedMeshData
except ModuleNotFoundError:  # запуск теста непосредственно из каталога core
    from mesh_parser import BedMeshData


PROBE_RE = re.compile(
    r"probe\s+at\s+(?P<x>[+-]?\d+(?:\.\d+)?),"
    r"(?P<y>[+-]?\d+(?:\.\d+)?)\s+is\s+z="
    r"(?P<z>[+-]?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LiveMeshSnapshot:
    data: BedMeshData
    measured_points: int
    total_points: int
    current: tuple[float, float] | None


class LiveMeshAccumulator:
    """Хранит последнее значение для каждой координаты, убирая повторы проб."""

    def __init__(self, total_points: int | None = None):
        self.total_points = total_points
        self.points: dict[tuple[float, float], float] = {}
        self.current: tuple[float, float] | None = None

    def feed_line(self, line: str) -> bool:
        match = PROBE_RE.search(line)
        if not match:
            return False
        point = (float(match.group("x")), float(match.group("y")))
        self.points[point] = float(match.group("z"))
        self.current = point
        return True

    def snapshot(self) -> LiveMeshSnapshot | None:
        if not self.points:
            return None
        xs = np.array(sorted({point[0] for point in self.points}), dtype=float)
        ys = np.array(sorted({point[1] for point in self.points}), dtype=float)
        z = np.full((len(ys), len(xs)), np.nan, dtype=float)
        x_index = {value: index for index, value in enumerate(xs)}
        y_index = {value: index for index, value in enumerate(ys)}
        for (x, y), value in self.points.items():
            z[y_index[y], x_index[x]] = value
        known = z[np.isfinite(z)]
        z[~np.isfinite(z)] = float(np.mean(known)) if known.size else 0.0
        data = BedMeshData(
            x=xs,
            y=ys,
            z=z,
            x_count=len(xs),
            y_count=len(ys),
            min_x=float(xs[0]),
            max_x=float(xs[-1]),
            min_y=float(ys[0]),
            max_y=float(ys[-1]),
        )
        total = self.total_points or len(xs) * len(ys)
        return LiveMeshSnapshot(data, len(self.points), total, self.current)
