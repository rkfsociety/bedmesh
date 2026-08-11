import numpy as np
from dataclasses import dataclass

from ui.components.palettes import build_lut

Z_VISUAL_SCALE = 40.0


@dataclass(frozen=True)
class SurfacePayload:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    colors: np.ndarray
    span_x: float
    span_y: float
    center_z: float
    spacing_x: float
    spacing_y: float


@dataclass(frozen=True)
class CameraFit:
    center: tuple[float, float, float]
    distance: float
    minimum_distance: float
    maximum_distance: float


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


def prepare_surface(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    palette_key: str,
    bed_bounds: tuple[float, float, float, float] | None = None,
) -> SurfacePayload:
    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    z_values = np.asarray(z, dtype=float)
    if x_values.ndim != 1 or y_values.ndim != 1:
        raise ValueError("x and y must be one-dimensional")
    expected_shape = (len(y_values), len(x_values))
    if z_values.shape != expected_shape:
        raise ValueError(f"z shape {z_values.shape} does not match {expected_shape}")
    if len(x_values) < 2 or len(y_values) < 2:
        raise ValueError("3D mesh requires at least 2 x 2 points")
    if not (
        np.all(np.isfinite(x_values))
        and np.all(np.isfinite(y_values))
        and np.all(np.isfinite(z_values))
    ):
        raise ValueError("3D mesh contains non-finite values")

    if bed_bounds is None:
        bed_min_x, bed_max_x = float(np.min(x_values)), float(np.max(x_values))
        bed_min_y, bed_max_y = float(np.min(y_values)), float(np.max(y_values))
    else:
        bed_min_x, bed_max_x, bed_min_y, bed_max_y = map(float, bed_bounds)
        if not (bed_max_x > bed_min_x and bed_max_y > bed_min_y):
            raise ValueError("bed bounds must have positive size")

    bed_center_x = (bed_min_x + bed_max_x) / 2.0
    bed_center_y = (bed_min_y + bed_max_y) / 2.0
    x_centered = x_values - bed_center_x
    y_centered = y_values - bed_center_y
    z_visual = scaled_z(z_values).T
    colors = np.transpose(colors_from_z(z_values, palette_key), (1, 0, 2))
    colors_flat = np.ascontiguousarray(colors.reshape(-1, 4))
    span_x = max(float(bed_max_x - bed_min_x), 1.0)
    span_y = max(float(bed_max_y - bed_min_y), 1.0)
    return SurfacePayload(
        x=x_centered,
        y=y_centered,
        z=z_visual,
        colors=colors_flat,
        span_x=span_x,
        span_y=span_y,
        center_z=float(np.mean(z_visual)),
        spacing_x=span_x / (len(x_values) - 1),
        spacing_y=span_y / (len(y_values) - 1),
    )


def fit_camera(payload: SurfacePayload) -> CameraFit:
    distance = max(payload.span_x, payload.span_y, 1.0) * 1.8
    return CameraFit(
        center=(0.0, 0.0, payload.center_z),
        distance=distance,
        minimum_distance=distance * 0.08,
        maximum_distance=distance * 8.0,
    )


def clamp_zoom_distance(
    current: float,
    wheel_delta: int,
    minimum: float,
    maximum: float,
) -> float:
    proposed = float(current) * (0.999 ** int(wheel_delta))
    return min(max(proposed, float(minimum)), float(maximum))
