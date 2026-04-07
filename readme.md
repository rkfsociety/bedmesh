# Bed Mesh Visualizer

[RU] Простая утилита для 3D-визуализации данных калибровки стола 3D-принтера (Klipper/Marlin).
[EN] A simple utility for 3D visualization of 3D printer bed mesh calibration data (Klipper/Marlin).

---

## Описание / Description (RU)

Эта программа позволяет быстро превратить текстовые данные о высоте точек стола в наглядную 3D-карту. Это помогает понять, где на столе есть провалы или горбы, которые мешают идеальному первому слою.

### Основные возможности:
* **Универсальная вставка:** Работает через Ctrl+V в любой раскладке (RU/EN).
* **Настройка сетки:** Можно указать количество точек по X и Y (например, 5x5, 7x7).
* **Klipper Style:** Визуализация в знакомой цветовой схеме (синий — низко, красный — высоко).
* **Автономность:** Работает как один `.exe` файл, не требует установки Python пользователем.

---

## Description (EN)

This program allows you to quickly transform text data of bed mesh points into a clear 3D map. It helps to identify where the bed has dips or bumps that prevent a perfect first layer.

### Key Features:
* **Universal Paste:** Works via Ctrl+V in any keyboard layout (RU/EN).
* **Grid Setup:** Custom X and Y point counts (e.g., 5x5, 7x7).
* **Klipper Style:** Visualization in a familiar color scheme (blue for low, red for high).
* **Standalone:** Runs as a single `.exe` file, no Python installation required for the end user.

---

## Как использовать / How to use

1. **Запустите** `Bed_Mesh_Viz.exe`.
2. **Введите размер сетки** (например, 5 и 5), который настроен в вашем принтере.
3. **Скопируйте данные** калибровки из консоли принтера.
4. **Вставьте данные** в текстовое поле программы (Ctrl+V или Правая кнопка мыши).
5. **Нажмите "ВИЗУАЛИЗИРОВАТЬ 3D"**.

---

## Разработка / Development

Если вы хотите запустить проект из исходного кода / To run from source:

1. Install requirements:
   `pip install matplotlib numpy`
2. Run:
   `python Bed_Mesh_Viz.py`
3. Build EXE:
   `python -m PyInstaller --onefile --noconsole --icon=icon.ico Bed_Mesh_Viz.py`