import math


def choose_label_font_px(
    cell_width: float,
    cell_height: float,
    text_width_at_px: float,
    text_height_at_px: float,
    preferred_px: int = 15,
    minimum_px: int = 7,
    padding_px: int = 4,
) -> int | None:
    available_width = max(0.0, cell_width - padding_px)
    available_height = max(0.0, cell_height - padding_px)
    scale = min(
        1.0,
        available_width / max(text_width_at_px, 1.0),
        available_height / max(text_height_at_px, 1.0),
    )
    font_px = min(preferred_px, math.floor(preferred_px * scale))
    return font_px if font_px >= minimum_px else None


def detail_canvas_size(
    x_count: int,
    y_count: int,
    minimum_cell_px: int = 96,
    base_size: int = 700,
    maximum_size: int = 4096,
) -> tuple[int, int]:
    width = min(maximum_size, max(base_size, x_count * minimum_cell_px))
    height = min(maximum_size, max(base_size, y_count * minimum_cell_px))
    return width, height


def detail_zoom_threshold(
    x_count: int,
    y_count: int,
    scene_size: int = 700,
    minimum_cell_screen_px: int = 48,
    maximum_zoom: float = 12.0,
) -> float:
    cell_at_fit = min(scene_size / x_count, scene_size / y_count)
    required = minimum_cell_screen_px / max(cell_at_fit, 1e-9)
    return min(maximum_zoom, max(1.0, required))


def mesh_index_at_position(
    mouse_x: float,
    mouse_y: float,
    viewport_width: float,
    viewport_height: float,
    pixmap_width: float,
    pixmap_height: float,
    x_count: int,
    y_count: int,
) -> tuple[int, int] | None:
    left = (viewport_width - pixmap_width) / 2
    top = (viewport_height - pixmap_height) / 2
    local_x = mouse_x - left
    local_y = mouse_y - top
    if not (0 <= local_x < pixmap_width and 0 <= local_y < pixmap_height):
        return None

    column = min(x_count - 1, int(local_x * x_count / pixmap_width))
    drawn_row = min(y_count - 1, int(local_y * y_count / pixmap_height))
    return y_count - 1 - drawn_row, column
