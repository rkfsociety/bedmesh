import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class BedMeshData:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    x_count: int
    y_count: int
    min_x: float
    max_x: float
    min_y: float
    max_y: float


class MeshParser:
    def parse_file(self, filepath: str) -> Optional[BedMeshData]:
        text = Path(filepath).read_text(encoding="utf-8")
        try:
            data = json.loads(text)
            return self._parse_json(data)
        except json.JSONDecodeError:
            pass
        return self.parse_config(text)

    def _parse_json(self, data: dict) -> Optional[BedMeshData]:
        mesh = data.get("bed_mesh default")
        if not mesh:
            return None

        try:
            x_count = int(mesh.get("x_count", 0))
            y_count = int(mesh.get("y_count", 0))
            x_min = float(mesh.get("min_x", 0))
            x_max = float(mesh.get("max_x", 0))
            y_min = float(mesh.get("min_y", 0))
            y_max = float(mesh.get("max_y", 0))
        except (TypeError, ValueError):
            return None

        if x_count <= 0 or y_count <= 0:
            return None

        points_str = mesh.get("points", "")
        z_flat = [float(value) for value in points_str.replace(",", " ").split()]
        if len(z_flat) != x_count * y_count:
            return None

        return BedMeshData(
            x=np.linspace(x_min, x_max, x_count),
            y=np.linspace(y_min, y_max, y_count),
            z=np.array(z_flat).reshape((y_count, x_count)),
            x_count=x_count,
            y_count=y_count,
            min_x=x_min,
            max_x=x_max,
            min_y=y_min,
            max_y=y_max,
        )

    def parse_config(self, config_text: str) -> Optional[BedMeshData]:
        lines = config_text.splitlines()
        section_lines, in_section = [], False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and "bed_mesh" in stripped:
                in_section, section_lines = True, []
                continue
            if in_section:
                if stripped.startswith("["):
                    break
                section_lines.append(line)
        if not section_lines:
            return None

        def get(key, fallback):
            for line in section_lines:
                line = line.split("#")[0].strip()
                if line.startswith(f"{key}:") or line.startswith(f"{key} :"):
                    return line.split(":", 1)[1].strip()
                if line.startswith(f"{key} =") or line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
            return fallback

        def _parse_pair(raw: str) -> Optional[tuple[float, float]]:
            if raw is None:
                return None
            parts = [part.strip() for part in str(raw).replace(" ", "").split(",") if part.strip() != ""]
            if len(parts) != 2:
                return None
            try:
                return float(parts[0]), float(parts[1])
            except ValueError:
                return None

        def _parse_int_pair(raw: str) -> Optional[tuple[int, int]]:
            pair = _parse_pair(raw)
            if not pair:
                return None
            return int(round(pair[0])), int(round(pair[1]))

        try:
            x_count = int(get("x_count", 0))
            y_count = int(get("y_count", 0))
        except (TypeError, ValueError):
            x_count, y_count = 0, 0

        mesh_min_pair = _parse_pair(get("mesh_min", None))
        mesh_max_pair = _parse_pair(get("mesh_max", None))
        probe_count_pair = _parse_int_pair(get("probe_count", None))

        if (x_count <= 0 or y_count <= 0) and probe_count_pair:
            x_count, y_count = probe_count_pair[0], probe_count_pair[1]

        if x_count <= 0 or y_count <= 0:
            return None

        if mesh_min_pair and mesh_max_pair:
            x_min, y_min = mesh_min_pair[0], mesh_min_pair[1]
            x_max, y_max = mesh_max_pair[0], mesh_max_pair[1]
        else:
            try:
                x_min = float(get("min_x", 0))
                x_max = float(get("max_x", 0))
                y_min = float(get("min_y", 0))
                y_max = float(get("max_y", 0))
            except (TypeError, ValueError):
                return None

        points, capture = [], False
        for raw_line in section_lines:
            no_comment = raw_line.split("#")[0].rstrip("\r\n")
            stripped = no_comment.strip()
            if stripped.startswith("points") and (":" in stripped or "=" in stripped):
                capture = True
                if ":" in stripped:
                    after = stripped.split(":", 1)[1].strip()
                else:
                    after = stripped.split("=", 1)[1].strip()
                if after:
                    points.append(after)
                continue
            if capture:
                if stripped.startswith("["):
                    break
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*[:=]", stripped):
                    break
                if stripped != "":
                    points.append(stripped)

        if not points:
            return None

        rows: list[list[float]] = []
        for line in points:
            cleaned = line.strip().strip("[]()")
            parts = [part for part in re.split(r"[,\s]+", cleaned) if part]
            try:
                row = [float(part) for part in parts]
            except ValueError:
                continue
            if row:
                rows.append(row)

        z: Optional[np.ndarray] = None
        if len(rows) == y_count and all(len(row) == x_count for row in rows):
            z = np.array(rows, dtype=float)
        else:
            flat: list[float] = []
            for row in rows:
                flat.extend(row)
            if len(flat) != x_count * y_count:
                return None
            z = np.array(flat, dtype=float).reshape((y_count, x_count))

        return BedMeshData(
            x=np.linspace(x_min, x_max, x_count),
            y=np.linspace(y_min, y_max, y_count),
            z=z,
            x_count=x_count,
            y_count=y_count,
            min_x=x_min,
            max_x=x_max,
            min_y=y_min,
            max_y=y_max,
        )
