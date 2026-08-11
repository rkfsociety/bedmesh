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
    z: np.ndarray
    x_count: int
    y_count: int
    min_x: float
    max_x: float
    min_y: float
    max_y: float

class MeshParser:
    def parse_file(self, filepath: str) -> Optional[BedMeshData]:
        text = Path(filepath).read_text(encoding='utf-8')
        return self.parse_text(text)

    def parse_text(self, text: str) -> Optional[BedMeshData]:
        """Разбирает содержимое конфигурации без повторного чтения файла."""
        try:
            data = json.loads(text)
            return self._parse_json(data)
        except json.JSONDecodeError:
            pass
        return self.parse_config(text)

    def _parse_json(self, data: dict) -> Optional[BedMeshData]:
        mesh = data.get("bed_mesh default")
        if not mesh: return None

        try:
            x_c = int(mesh.get("x_count", 0))
            y_c = int(mesh.get("y_count", 0))
            x_min = float(mesh.get("min_x", 0))
            x_max = float(mesh.get("max_x", 0))
            y_min = float(mesh.get("min_y", 0))
            y_max = float(mesh.get("max_y", 0))
        except (TypeError, ValueError):
            return None

        # min_x/min_y часто равны 0 — это валидно, поэтому не проверяем "truthy".
        if x_c <= 0 or y_c <= 0:
            return None

        points_str = mesh.get("points", "")
        z_flat = [float(v) for v in points_str.replace(',', ' ').split()]
        if len(z_flat) != x_c * y_c: return None

        return BedMeshData(
            x=np.linspace(x_min, x_max, x_c),
            y=np.linspace(y_min, y_max, y_c),
            z=np.array(z_flat).reshape((y_c, x_c)),
            x_count=x_c, y_count=y_c,
            min_x=x_min, max_x=x_max, min_y=y_min, max_y=y_max
        )

    def parse_config(self, config_text: str) -> Optional[BedMeshData]:
        lines = config_text.splitlines()
        section_lines, in_section = [], False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('[') and 'bed_mesh' in stripped:
                in_section, section_lines = True, []
                continue
            if in_section:
                if stripped.startswith('['): break
                section_lines.append(line)
        if not section_lines: return None

        def get(key, fallback):
            for l in section_lines:
                l = l.split('#')[0].strip()
                # Klipper часто использует "key:"; иногда встречается "key=".
                if l.startswith(f"{key}:") or l.startswith(f"{key} :"):
                    return l.split(':', 1)[1].strip()
                if l.startswith(f"{key} =") or l.startswith(f"{key}="):
                    return l.split('=', 1)[1].strip()
            return fallback

        def _parse_pair(raw: str) -> Optional[tuple[float, float]]:
            if raw is None:
                return None
            parts = [p.strip() for p in str(raw).replace(" ", "").split(",") if p.strip() != ""]
            if len(parts) != 2:
                return None
            try:
                return float(parts[0]), float(parts[1])
            except ValueError:
                return None

        def _parse_int_pair(raw: str) -> Optional[tuple[int, int]]:
            p = _parse_pair(raw)
            if not p:
                return None
            return int(round(p[0])), int(round(p[1]))

        # Формат A (старый/нестандартный): x_count/y_count + min_x/max_x + min_y/max_y + points
        # Формат B (типичный Klipper): probe_count + mesh_min/mesh_max + points
        try:
            x_c = int(get('x_count', 0))
            y_c = int(get('y_count', 0))
        except (TypeError, ValueError):
            x_c, y_c = 0, 0

        mesh_min_pair = _parse_pair(get("mesh_min", None))
        mesh_max_pair = _parse_pair(get("mesh_max", None))
        probe_count_pair = _parse_int_pair(get("probe_count", None))

        if (x_c <= 0 or y_c <= 0) and probe_count_pair:
            x_c, y_c = probe_count_pair[0], probe_count_pair[1]

        if x_c <= 0 or y_c <= 0:
            return None

        if mesh_min_pair and mesh_max_pair:
            x_min, y_min = mesh_min_pair[0], mesh_min_pair[1]
            x_max, y_max = mesh_max_pair[0], mesh_max_pair[1]
        else:
            try:
                x_min = float(get('min_x', 0))
                x_max = float(get('max_x', 0))
                y_min = float(get('min_y', 0))
                y_max = float(get('max_y', 0))
            except (TypeError, ValueError):
                return None

        pts, capture = [], False
        for raw_line in section_lines:
            # points обычно многострочные и с отступами; сохраняем сырой вариант, но убираем комментарии
            no_comment = raw_line.split('#')[0].rstrip("\r\n")
            stripped = no_comment.strip()
            if stripped.startswith("points") and (":" in stripped or "=" in stripped):
                capture = True
                if ":" in stripped:
                    after = stripped.split(':', 1)[1].strip()
                else:
                    after = stripped.split('=', 1)[1].strip()
                if after: pts.append(after)
                continue
            if capture:
                # Остановимся на следующем ключе (например, "fade_start:"), но позволим строкам с числами/запятыми.
                if stripped.startswith('['):
                    break
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*[:=]", stripped):
                    break
                if stripped != "":
                    pts.append(stripped)

        if not pts:
            return None

        # Попробуем распарсить как матрицу строк (y строк по x значений).
        rows: list[list[float]] = []
        for line in pts:
            # допускаем форматы: "0.1,0.2,0.3" или "[0.1, 0.2]" или "0.1 0.2 0.3"
            cleaned = line.strip().strip("[]()")
            parts = [p for p in re.split(r"[,\s]+", cleaned) if p]
            try:
                row = [float(p) for p in parts]
            except ValueError:
                continue
            if row:
                rows.append(row)

        z: Optional[np.ndarray] = None
        if len(rows) == y_c and all(len(r) == x_c for r in rows):
            z = np.array(rows, dtype=float)
        else:
            # fallback: плоский список
            flat: list[float] = []
            for r in rows:
                flat.extend(r)
            if len(flat) != x_c * y_c:
                return None
            z = np.array(flat, dtype=float).reshape((y_c, x_c))

        return BedMeshData(
            x=np.linspace(x_min, x_max, x_c),
            y=np.linspace(y_min, y_max, y_c),
            z=z,
            x_count=x_c, y_count=y_c,
            min_x=x_min, max_x=x_max, min_y=y_min, max_y=y_max
        )

    def parse_input_shaper(self, filepath: str) -> Optional[dict]:
        """Возвращает dict с ключами shaper_type_x/y, shaper_freq_x/y или None."""
        text = Path(filepath).read_text(encoding='utf-8')
        return self.parse_input_shaper_text(text)

    def parse_input_shaper_text(self, text: str) -> Optional[dict]:
        """Разбирает input shaper из уже загруженного текста."""
        try:
            data = json.loads(text)
            sec = data.get("input_shaper") or data.get("[input_shaper]")
            if isinstance(sec, dict):
                return self._extract_shaper_fields(sec)
        except json.JSONDecodeError:
            pass
        return self._parse_shaper_cfg(text)

    def _extract_shaper_fields(self, sec: dict) -> Optional[dict]:
        try:
            result = {
                "shaper_type_x": str(sec.get("shaper_type_x", "")).strip().lower(),
                "shaper_type_y": str(sec.get("shaper_type_y", "")).strip().lower(),
                "shaper_freq_x": float(sec.get("shaper_freq_x", 0)),
                "shaper_freq_y": float(sec.get("shaper_freq_y", 0)),
            }
            if result["shaper_freq_x"] > 0 and result["shaper_freq_y"] > 0:
                return result
        except (TypeError, ValueError):
            pass
        return None

    def _parse_shaper_cfg(self, text: str) -> Optional[dict]:
        lines = text.splitlines()
        sec_lines, in_sec = [], False
        for line in lines:
            s = line.strip()
            if s.lower() in ("[input_shaper]", "input_shaper"):
                in_sec, sec_lines = True, []
                continue
            if in_sec:
                if s.startswith("["):
                    break
                sec_lines.append(s)
        if not sec_lines:
            return None

        def get(key):
            for l in sec_lines:
                l = l.split("#")[0].strip()
                for sep in (":", "="):
                    if l.lower().startswith(key + sep) or l.lower().startswith(key + " " + sep):
                        return l.split(sep, 1)[1].strip()
            return None

        try:
            fx = float(get("shaper_freq_x") or 0)
            fy = float(get("shaper_freq_y") or 0)
            tx = (get("shaper_type_x") or "").strip().lower()
            ty = (get("shaper_type_y") or "").strip().lower()
            if fx > 0 and fy > 0:
                return {"shaper_type_x": tx, "shaper_type_y": ty,
                        "shaper_freq_x": fx, "shaper_freq_y": fy}
        except (TypeError, ValueError):
            pass
        return None
