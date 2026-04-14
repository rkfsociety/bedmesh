import re
import json
import numpy as np
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class BedMeshData:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray  # shape: (y_count, x_count)
    x_count: int
    y_count: int
    min_x: float
    max_x: float
    min_y: float
    max_y: float

class MeshParser:
    def parse_file(self, filepath: str) -> Optional[BedMeshData]:
        text = Path(filepath).read_text(encoding='utf-8')
        
        # Пробуем JSON
        try:
            data = json.loads(text)
            return self._parse_json(data)
        except json.JSONDecodeError:
            pass
        
        # Текстовый формат
        return self.parse_config(text)

    def _parse_json(self, data: dict) -> Optional[BedMeshData]:
        mesh = data.get("bed_mesh default")
        if not mesh:
            return None

        x_c = int(mesh.get("x_count", 0))
        y_c = int(mesh.get("y_count", 0))
        x_min = float(mesh.get("min_x", 0))
        x_max = float(mesh.get("max_x", 0))
        y_min = float(mesh.get("min_y", 0))
        y_max = float(mesh.get("max_y", 0))

        if not all([x_c, y_c, x_min, x_max, y_min, y_max]):
            return None

        points_str = mesh.get("points", "")
        z_flat = [float(v) for v in points_str.replace(',', ' ').split()]

        if len(z_flat) != x_c * y_c:
            return None

        return BedMeshData(
            x=np.linspace(x_min, x_max, x_c),
            y=np.linspace(y_min, y_max, y_c),
            z=np.array(z_flat).reshape((y_c, x_c)),
            x_count=x_c, y_count=y_c,
            min_x=x_min, max_x=x_max, min_y=y_min, max_y=y_max
        )

    def parse_config(self, config_text: str) -> Optional[BedMeshData]:
        lines = config_text.splitlines()
        section_lines = []
        in_section = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('[') and 'bed_mesh' in stripped:
                in_section, section_lines = True, []
                continue
            if in_section:
                if stripped.startswith('['): break
                section_lines.append(line)

        if not section_lines:
            return None

        def get(key: str, fallback):
            for l in section_lines:
                l = l.split('#')[0].strip()
                if l.startswith(f"{key} =") or l.startswith(f"{key}="):
                    return l.split('=', 1)[1].strip()
            return fallback

        x_c = int(get('x_count', 0))
        y_c = int(get('y_count', 0))
        x_min = float(get('min_x', 0))
        x_max = float(get('max_x', 0))
        y_min = float(get('min_y', 0))
        y_max = float(get('max_y', 0))

        if not all([x_c, y_c, x_min, x_max, y_min, y_max]):
            return None

        pts, capture = [], False
        for l in section_lines:
            l = l.split('#')[0].strip()
            if 'points' in l and '=' in l:
                capture = True
                after = l.split('=', 1)[1].strip()
                if after: pts.append(after)
                continue
            if capture:
                if l.startswith('[') or '=' in l: break
                pts.append(l)

        raw = ' '.join(pts).replace(',', ' ')
        z_flat = [float(v) for v in raw.split() if v]

        if len(z_flat) != x_c * y_c:
            return None

        return BedMeshData(
            x=np.linspace(x_min, x_max, x_c),
            y=np.linspace(y_min, y_max, y_c),
            z=np.array(z_flat).reshape((y_c, x_c)),
            x_count=x_c, y_count=y_c,
            min_x=x_min, max_x=x_max, min_y=y_min, max_y=y_max
        )