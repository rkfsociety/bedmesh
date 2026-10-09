"""Сборка частичной bed mesh из строк журнала GoKlipper."""

from __future__ import annotations

import json
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

    def __init__(
        self,
        total_points: int | None = None,
        *,
        x: np.ndarray | None = None,
        y: np.ndarray | None = None,
    ):
        self.total_points = total_points
        self.x = np.asarray(x, dtype=float) if x is not None else None
        self.y = np.asarray(y, dtype=float) if y is not None else None
        self.points: dict[tuple[float, float], float] = {}
        self.current: tuple[float, float] | None = None

    def feed_line(self, line: str) -> bool:
        match = PROBE_RE.search(line)
        if not match:
            return False
        point = (float(match.group("x")), float(match.group("y")))
        # The printer reports decimal coordinates. Snap them to the grid from
        # printer_mutable.cfg so the live view keeps a fixed 10x10 layout while
        # the firmware probes in its left-to-right/right-to-left snake order.
        if self.x is not None and self.y is not None:
            x_index = int(np.argmin(np.abs(self.x - point[0])))
            y_index = int(np.argmin(np.abs(self.y - point[1])))
            point = (float(self.x[x_index]), float(self.y[y_index]))
        self.points[point] = float(match.group("z"))
        self.current = point
        return True

    def snapshot(self) -> LiveMeshSnapshot | None:
        if not self.points:
            return None
        xs = self.x if self.x is not None else np.array(sorted({point[0] for point in self.points}), dtype=float)
        ys = self.y if self.y is not None else np.array(sorted({point[1] for point in self.points}), dtype=float)
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


def update_bed_mesh_json(config_text: str, data: BedMeshData) -> str:
    """Replace the saved bed mesh in a mutable Klipper JSON config."""
    try:
        config = json.loads(config_text)
    except json.JSONDecodeError as error:
        raise ValueError("printer_mutable.cfg содержит некорректный JSON") from error

    if not isinstance(config, dict) or not isinstance(config.get("bed_mesh default"), dict):
        raise ValueError("В printer_mutable.cfg не найден объект bed_mesh default")

    z = np.asarray(data.z, dtype=float)
    expected_shape = (data.y_count, data.x_count)
    if z.shape != expected_shape or not np.isfinite(z).all():
        raise ValueError("Live-карта имеет некорректный размер или значения")

    mesh = config["bed_mesh default"]
    mesh.update(
        {
            "min_x": f"{data.min_x:g}",
            "max_x": f"{data.max_x:g}",
            "min_y": f"{data.min_y:g}",
            "max_y": f"{data.max_y:g}",
            "x_count": str(data.x_count),
            "y_count": str(data.y_count),
            "points": "\n".join(
                ", ".join(f"{value:.6f}" for value in row) for row in z
            ),
        }
    )
    return json.dumps(config, ensure_ascii=False, indent=2) + "\n"
