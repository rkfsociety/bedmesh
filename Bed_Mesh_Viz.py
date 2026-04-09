import tkinter as tk
from tkinter import scrolledtext, messagebox, Menu
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import re
import paramiko
import json
import os

class TableVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Bed Mesh Visualizer Pro (SSH + Auto-Parse)")
        self.root.geometry("750x900")

        # --- БЛОК SSH ПОДКЛЮЧЕНИЯ ---
        ssh_frame = tk.LabelFrame(root, text=" Подключение к принтеру (SSH) ", padx=10, pady=10)
        ssh_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(ssh_frame, text="IP:").grid(row=0, column=0)
        self.ssh_host = tk.Entry(ssh_frame, width=15)
        self.ssh_host.insert(0, "192.168.1.100")
        self.ssh_host.grid(row=0, column=1, padx=5)

        tk.Label(ssh_frame, text="User:").grid(row=0, column=2)
        self.ssh_user = tk.Entry(ssh_frame, width=10)
        self.ssh_user.insert(0, "pi")
        self.ssh_user.grid(row=0, column=3, padx=5)

        tk.Label(ssh_frame, text="Pass:").grid(row=0, column=4)
        self.ssh_pass = tk.Entry(ssh_frame, width=10, show="*")
        self.ssh_pass.insert(0, "raspberry")
        self.ssh_pass.grid(row=0, column=5, padx=5)

        # ПОЛЕ ДЛЯ ДИРЕКТОРИИ / ПУТИ
        tk.Label(ssh_frame, text="Путь к файлу:").grid(row=1, column=0, pady=10)
        self.cfg_path = tk.Entry(ssh_frame, width=45)
        self.cfg_path.insert(0, "/home/pi/printer_data/config/printer_mutable.cfg")
        self.cfg_path.grid(row=1, column=1, columnspan=4, sticky="w", padx=5)

        self.btn_ssh = tk.Button(ssh_frame, text="ВЫТЯНУТЬ CFG", command=self.fetch_ssh, bg="#2196F3", fg="white", font=("Arial", 9, "bold"))
        self.btn_ssh.grid(row=1, column=5, columnspan=2, padx=10)

        # --- НАСТРОЙКИ СЕТКИ (АВТОЗАПОЛНЯЮТСЯ) ---
        settings_frame = tk.LabelFrame(root, text=" Параметры сетки ", padx=10, pady=10)
        settings_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(settings_frame, text="Точек X:").grid(row=0, column=0)
        self.entry_x = tk.Entry(settings_frame, width=7); self.entry_x.insert(0, "5"); self.entry_x.grid(row=0, column=1)
        
        tk.Label(settings_frame, text="Точек Y:").grid(row=0, column=2, padx=10)
        self.entry_y = tk.Entry(settings_frame, width=7); self.entry_y.insert(0, "5"); self.entry_y.grid(row=0, column=3)

        # --- ПОЛЕ ВВОДА ---
        tk.Label(root, text="Данные калибровки (текст или JSON):", font=("Arial", 9, "bold")).pack(pady=5)
        self.text_area = scrolledtext.ScrolledText(root, width=85, height=20, font=("Consolas", 10))
        self.text_area.pack(padx=20, pady=5)

        # КНОПКА ПОСТРОЕНИЯ
        self.btn_plot = tk.Button(root, text="ВИЗУАЛИЗИРОВАТЬ 3D", command=self.plot_3d, 
                                 bg="#4CAF50", fg="white", height=2, font=("Arial", 11, "bold"))
        self.btn_plot.pack(pady=15, fill="x", padx=200)

    def fetch_ssh(self):
        host = self.ssh_host.get()
        user = self.ssh_user.get()
        password = self.ssh_pass.get()
        remote_path = self.cfg_path.get()

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, username=user, password=password, timeout=10)

            sftp = client.open_sftp()
            with sftp.open(remote_path, 'r') as f:
                content = f.read().decode('utf-8')
            sftp.close()
            client.close()

            # Вставляем текст в поле
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, content)
            
            # АВТО-ПАРСИНГ ПАРАМЕТРОВ ИЗ JSON (для твоего файла)
            try:
                data = json.loads(content)
                mesh_default = data.get("bed_mesh default", {})
                if mesh_default:
                    x_count = mesh_default.get("x_count", "5")
                    y_count = mesh_default.get("y_count", "5")
                    
                    self.entry_x.delete(0, tk.END); self.entry_x.insert(0, str(x_count))
                    self.entry_y.delete(0, tk.END); self.entry_y.insert(0, str(y_count))
                    
                    messagebox.showinfo("Успех", f"Файл загружен! Обнаружена сетка {x_count}x{y_count}")
                else:
                    messagebox.showinfo("Успех", "Файл загружен, но секция 'bed_mesh default' не найдена.")
            except:
                messagebox.showinfo("Успех", "Файл загружен (текстовый формат). Проверьте X и Y вручную.")

        except Exception as e:
            messagebox.showerror("Ошибка SSH", f"Не удалось получить файл:\n{str(e)}")

    def parse_input(self):
        text = self.text_area.get("1.0", tk.END).strip()
        # Извлекаем все числа (дробные и целые)
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
        nums = [float(n) for n in raw_nums]
        
        if not nums:
            messagebox.showwarning("Ошибка", "Данные не найдены!")
            return None

        try:
            gx, gy = int(self.entry_x.get()), int(self.entry_y.get())
            total = gx * gy
            if len(nums) < total:
                messagebox.showerror("Ошибка", f"Нужно {total} точек, найдено {len(nums)}")
                return None
            
            # Берем последние total чисел (актуальные точки)
            data_array = np.array(nums[-total:])
            return data_array.reshape((gy, gx))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка парсинга: {e}")
            return None

    def plot_3d(self):
        matrix = self.parse_input()
        if matrix is None: return
        
        plt.close('all')
        fig = plt.figure("Bed Mesh 3D Visualizer", figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        rows, cols = matrix.shape
        y, x = np.indices((rows, cols))
        
        surf = ax.plot_surface(x, y, matrix, cmap='RdYlBu_r', edgecolor='black', alpha=0.8)
        fig.colorbar(surf, shrink=0.5, aspect=10, label='Z отклонение (мм)')
        
        ax.set_xlabel('X (точки)')
        ax.set_ylabel('Y (точки)')
        ax.set_zlabel('Высота Z')
        ax.set_title(f"Сетка {cols}x{rows}")
        
        plt.show()

if __name__ == "__main__":
    root = tk.Tk()
    app = TableVisualizer(root)
    root.mainloop()