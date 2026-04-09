import customtkinter as ctk

class RecCard(ctk.CTkFrame):
    def __init__(self, parent, name, val, turns, direction):
        super().__init__(parent, fg_color="#333333", corner_radius=8)
        self.pack(fill="x", pady=2, padx=5)
        
        # Для валов (независимых моторов) выводим только мм
        if turns is None:
            text = f"{name}: {val:+.3f} мм"
        else:
            # Для винтов - мм и обороты
            text = f"{name}: {val:+.3f} мм ({turns:.2f} {direction})"
            
        ctk.CTkLabel(self, text=text, font=("Segoe UI", 12)).pack(pady=5)

def get_recs(matrix, z_sys, pitch, gx):
    gy = matrix.shape[0]
    # Опорная точка всегда центр стола
    ref = matrix[gy//2, gx//2]
    recs = []
    is_shafts = "Валы" in z_sys

    pts_map = {
        "Винты (4шт)": [
            ("Лево-перед", matrix[0, 0]), ("Право-перед", matrix[0, -1]),
            ("Лево-зад", matrix[-1, 0]), ("Право-зад", matrix[-1, -1])
        ],
        "Винты (3шт)": [
            ("Лево-перед", matrix[0, 0]), ("Право-перед", matrix[0, -1]),
            ("Центр-зад", matrix[-1, gx//2])
        ],
        "Валы (2 перед, 1 зад)": [
            ("Вал лево-перед", matrix[0, 0]), ("Вал право-перед", matrix[0, -1]),
            ("Вал центр-зад", matrix[-1, gx//2])
        ],
        "Валы (4 по углам)": [
            ("Вал лево-перед", matrix[0, 0]), ("Вал право-перед", matrix[0, -1]),
            ("Вал лево-зад", matrix[-1, 0]), ("Вал право-зад", matrix[-1, -1])
        ]
    }

    selected_pts = pts_map.get(z_sys, [])
    for name, val in selected_pts:
        diff = ref - val
        if is_shafts:
            # Для валов возвращаем чистую разницу
            recs.append({'name': name, 'val': diff, 'turns': None, 'dir': ""})
        else:
            # Для винтов считаем обороты по шагу резьбы
            turns = abs(diff) / pitch
            direction = "CW (по час.)" if diff > 0 else "CCW (против)"
            recs.append({'name': name, 'val': diff, 'turns': turns, 'dir': direction})
            
    return recs, None