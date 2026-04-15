import numpy as np


# Ключ -> (отображаемое имя, якорные цвета RGB)
PALETTES: dict[str, tuple[str, list[tuple[int, int, int]]]] = {
    "classic": (
        "Классическая (яркая)",
        [(0, 0, 255), (128, 128, 255), (255, 255, 255), (255, 128, 128), (255, 0, 0)],
    ),
    "soft": (
        "Мягкая (приятная)",
        [(45, 85, 160), (140, 180, 220), (245, 245, 245), (235, 170, 155), (185, 70, 60)],
    ),
    "icefire": (
        "Ice/Fire (контрастная)",
        [(0, 20, 80), (0, 120, 255), (245, 245, 245), (255, 140, 120), (120, 0, 0)],
    ),
}


def build_lut(palette_key: str) -> np.ndarray:
    """
    Возвращает LUT (256x4 uint8) для палитры.
    """
    if palette_key not in PALETTES:
        palette_key = "classic"

    _, colors = PALETTES[palette_key]
    pos = np.linspace(0, 255, num=len(colors)).astype(int)

    lut = np.zeros((256, 4), dtype=np.uint8)
    for c in range(3):
        lut[:, c] = np.interp(np.arange(256), pos, [x[c] for x in colors])
    lut[:, 3] = 255
    return lut

