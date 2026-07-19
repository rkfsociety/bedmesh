import numpy as np

from ui.components.palettes import build_lut

Z_VISUAL_SCALE = 40.0


def scaled_z(z: np.ndarray, scale: float = Z_VISUAL_SCALE) -> np.ndarray:
    return np.asarray(z, dtype=float) * float(scale)


def colors_from_z(z: np.ndarray, palette_key: str) -> np.ndarray:
    """RGBA float colors in [0, 1], shape (ny, nx, 4), for GLSurfacePlotItem."""
    z = np.asarray(z, dtype=float)
    z_min = float(np.min(z))
    z_max = float(np.max(z))
    norm = (z - z_min) / (z_max - z_min + 1e-9)
    idx = (norm * 255).astype(np.uint8)
    lut = build_lut(palette_key)  # (256, 4) uint8
    rgba_u8 = lut[idx]
    return rgba_u8.astype(np.float64) / 255.0
