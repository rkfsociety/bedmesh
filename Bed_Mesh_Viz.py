import tkinter as tk
from tkinter import scrolledtext, messagebox, Menu
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import re

class TableVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Bed Mesh Visualizer v3.1")
        self.root.geometry("600x750")

        # --- НАСТРОЙКИ СЕТКИ ---
        settings_frame = tk.LabelFrame(root, text=" Настройки сетки (Mesh) ", padx=10, pady=10)
        settings_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(settings_frame, text="Точек по X:").grid(row=0, column=0, sticky="w")
        self.entry_x = tk.Entry(settings_frame, width=7)
        self.entry_x.insert(0, "5")
        self.entry_x.grid(row=0, column=1, padx=5)

        tk.Label(settings_frame, text="Точек по Y:").grid(row=0, column=2, sticky="w", padx=10)
        self.entry_y = tk.Entry(settings_frame, width=7)
        self.entry_y.insert(0, "5")
        self.entry_y.grid(row=0, column=3, padx=5)

        tk.Label(root, text="Вставьте данные (Ctrl+V работает в любой раскладке):", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Поле ввода
        self.text_area = scrolledtext.ScrolledText(root, width=70, height=18, font=("Consolas", 10))
        self.text_area.pack(padx=20, pady=5)

        # --- УНИВЕРСАЛЬНАЯ ВСТАВКА (ENG/RUS) ---
        # Привязываем событие ко всему окну, чтобы ловить нажатие клавиш по коду
        self.root.bind("<Control-KeyPress>", self.universal_paste)
        
        # Меню правой кнопки
        self.menu = Menu(self.root, tearoff=0)
        self.menu.add_command(label="Вставить", command=self.paste_text)
        self.menu.add_command(label="Копировать", command=lambda: self.root.focus_get().event_generate('<<Copy>>'))
        self.menu.add_separator()
        self.menu.add_command(label="Очистить всё", command=self.clear_text)
        self.text_area.bind("<Button-3>", lambda e: self.menu.post(e.x_root, e.y_root))

        # Кнопка построения
        self.btn_plot = tk.Button(root, text="ВИЗУАЛИЗИРОВАТЬ 3D", command=self.plot_3d, 
                                 bg="#4CAF50", fg="white", height=2, font=("Arial", 11, "bold"))
        self.btn_plot.pack(pady=20, fill="x", padx=100)

    def universal_paste(self, event):
        # 86 - это код клавиши V/М в Windows
        # event.state & 4 проверяет, зажат ли Ctrl
        if event.keycode == 86 and (event.state & 4):
            self.paste_text()
            return "break"

    def paste_text(self):
        try:
            clipboard = self.root.clipboard_get()
            try:
                self.text_area.delete("sel.first", "sel.last")
            except:
                pass
            self.text_area.insert(tk.INSERT, clipboard)
        except:
            pass
        return "break"

    def clear_text(self):
        self.text_area.delete("1.0", tk.END)

    def parse_input(self):
        text = self.text_area.get("1.0", tk.END).strip()
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
        nums = [float(n) for n in raw_nums]
        
        if not nums:
            messagebox.showwarning("Ошибка", "Данные не найдены!")
            return None

        try:
            grid_x = int(self.entry_x.get())
            grid_y = int(self.entry_y.get())
        except:
            messagebox.showerror("Ошибка", "Введите числа в поля X и Y")
            return None

        total = grid_x * grid_y
        if len(nums) < total:
            messagebox.showerror("Ошибка", f"Нужно {total} точек, а найдено {len(nums)}")
            return None
        
        return np.array(nums[:total]).reshape((grid_y, grid_x))

    def plot_3d(self):
        matrix = self.parse_input()
        if matrix is None: return
        plt.close('all')
        fig = plt.figure("Bed Mesh 3D", figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        rows, cols = matrix.shape
        y, x = np.indices((rows, cols))
        surf = ax.plot_surface(x, y, matrix, cmap='RdYlBu_r', edgecolor='black', 
                               linewidth=0.4, antialiased=True, alpha=0.8)
        fig.colorbar(surf, shrink=0.5, aspect=10, label='Z (мм)')
        ax.set_title(f"Сетка: {cols} x {rows}")
        plt.show()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap("icon.ico")
    except:
        pass
    app = TableVisualizer(root)
    root.mainloop()