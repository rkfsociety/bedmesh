import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import re
import paramiko
import json
import os

# Имя файла для хранения настроек
SETTINGS_FILE = "settings.json"

class TableVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Bed Mesh Visualizer Pro v4.0 (SSH Port Support)")
        self.root.geometry("800x920")

        # Загружаем настройки из файла
        self.settings = self.load_settings()

        # --- БЛОК SSH ПОДКЛЮЧЕНИЯ ---
        ssh_frame = tk.LabelFrame(root, text=" Подключение к принтеру (SSH) ", padx=10, pady=10)
        ssh_frame.pack(fill="x", padx=20, pady=5)

        # Первая строка: Хост, Порт, Юзер, Пароль
        tk.Label(ssh_frame, text="IP:").grid(row=0, column=0)
        self.ssh_host = tk.Entry(ssh_frame, width=15)
        self.ssh_host.insert(0, self.settings.get("host", "192.168.1.100"))
        self.ssh_host.grid(row=0, column=1, padx=5)

        tk.Label(ssh_frame, text="Порт:").grid(row=0, column=2)
        self.ssh_port = tk.Entry(ssh_frame, width=6)
        self.ssh_port.insert(0, self.settings.get("port", "22"))
        self.ssh_port.grid(row=0, column=3, padx=5)

        tk.Label(ssh_frame, text="User:").grid(row=0, column=4)
        self.ssh_user = tk.Entry(ssh_frame, width=10)
        self.ssh_user.insert(0, self.settings.get("user", "pi"))
        self.ssh_user.grid(row=0, column=5, padx=5)

        tk.Label(ssh_frame, text="Pass:").grid(row=0, column=6)
        self.ssh_pass = tk.Entry(ssh_frame, width=10, show="*")
        self.ssh_pass.insert(0, self.settings.get("password", "raspberry"))
        self.ssh_pass.grid(row=0, column=7, padx=5)

        # Вторая строка: Путь и кнопка
        tk.Label(ssh_frame, text="Путь к файлу:").grid(row=1, column=0, pady=10)
        self.cfg_path = tk.Entry(ssh_frame, width=50)
        self.cfg_path.insert(0, self.settings.get("path", "/home/pi/printer_data/config/printer_mutable.cfg"))
        self.cfg_path.grid(row=1, column=1, columnspan=5, sticky="w", padx=5)

        self.btn_ssh = tk.Button(ssh_frame, text="ВЫТЯНУТЬ CFG", command=self.fetch_ssh, bg="#2196F3", fg="white", font=("Arial", 9, "bold"))
        self.btn_ssh.grid(row=1, column=6, columnspan=2, padx=10)

        # --- НАСТРОЙКИ СЕТКИ ---
        settings_frame = tk.LabelFrame(root, text=" Параметры сетки ", padx=10, pady=10)
        settings_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(settings_frame, text="Точек X:").grid(row=0, column=0)
        self.entry_x = tk.Entry(settings_frame, width=7)
        self.entry_x.insert(0, self.settings.get("grid_x", "5"))
        self.entry_x.grid(row=0, column=1)
        
        tk.Label(settings_frame, text="Точек Y:").grid(row=0, column=2, padx=10)
        self.entry_y = tk.Entry(settings_frame, width=7)
        self.entry_y.insert(0, self.settings.get("grid_y", "5"))
        self.entry_y.grid(row=0, column=3)

        self.btn_save = tk.Button(settings_frame, text="СОХРАНИТЬ НАСТРОЙКИ", command=self.save_settings, bg="#FF9800", fg="white")
        self.btn_save.grid(row=0, column=4, padx=20)

        # --- ПОЛЕ ВВОДА ---
        tk.Label(root, text="Данные калибровки:", font=("Arial", 9, "bold")).pack(pady=5)
        self.text_area = scrolledtext.ScrolledText(root, width=90, height=20, font=("Consolas", 10))
        self.text_area.pack(padx=20, pady=5)

        self.btn_plot = tk.Button(root, text="ВИЗУАЛИЗИРОВАТЬ 3D", command=self.plot_3d, 
                                 bg="#4CAF50", fg="white", height=2, font=("Arial", 11, "bold"))
        self.btn_plot.pack(pady=15, fill="x", padx=200)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_settings(self, silent=False):
        data = {
            "host": self.ssh_host.get(),
            "port": self.ssh_port.get(),
            "user": self.ssh_user.get(),
            "password": self.ssh_pass.get(),
            "path": self.cfg_path.get(),
            "grid_x": self.entry_x.get(),
            "grid_y": self.entry_y.get()
        }
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
            if not silent:
                messagebox.showinfo("Успех", "Настройки сохранены!")
        except Exception as e:
            if not silent:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

    def fetch_ssh(self):
        host = self.ssh_host.get()
        user = self.ssh_user.get()
        password = self.ssh_pass.get()
        remote_path = self.cfg_path.get()
        
        # Получаем порт и проверяем, что это число
        try:
            port = int(self.ssh_port.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Порт должен быть числом!")
            return

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # Подключаемся с учетом порта
            client.connect(hostname=host, port=port, username=user, password=password, timeout=10)

            sftp = client.open_sftp()
            with sftp.open(remote_path, 'r') as f:
                content = f.read().decode('utf-8')
            sftp.close()
            client.close()

            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, content)
            
            self.save_settings(silent=True)

            try:
                data = json.loads(content)
                mesh_default = data.get("bed_mesh default", {})
                if mesh_default:
                    x_count = mesh_default.get("x_count", "5")
                    y_count = mesh_default.get("y_count", "5")
                    self.entry_x.delete(0, tk.END); self.entry_x.insert(0, str(x_count))
                    self.entry_y.delete(0, tk.END); self.entry_y.insert(0, str(y_count))
                    self.save_settings(silent=True)
            except:
                pass

            messagebox.showinfo("Успех", "Файл загружен!")
        except Exception as e:
            messagebox.showerror("Ошибка SSH", f"Ошибка подключения (Порт {port}):\n{str(e)}")

    def parse_input(self):
        text = self.text_area.get("1.0", tk.END).strip()
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
        nums = [float(n) for n in raw_nums]
        if not nums: return None
        try:
            gx, gy = int(self.entry_x.get()), int(self.entry_y.get())
            total = gx * gy
            if len(nums) < total:
                messagebox.showerror("Ошибка", f"Нужно {total} точек, найдено {len(nums)}")
                return None
            return np.array(nums[-total:]).reshape((gy, gx))
        except:
            return None

    def plot_3d(self):
        matrix = self.parse_input()
        if matrix is None: return
        self.save_settings(silent=True)
        
        plt.close('all')
        fig = plt.figure("Bed Mesh 3D", figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        rows, cols = matrix.shape
        y, x = np.indices((rows, cols))
        surf = ax.plot_surface(x, y, matrix, cmap='RdYlBu_r', edgecolor='black', alpha=0.8)
        fig.colorbar(surf, shrink=0.5, aspect=10)
        plt.show()

if __name__ == "__main__":
    root = tk.Tk()
    app = TableVisualizer(root)
    root.mainloop()