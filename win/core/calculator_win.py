import numpy as np

def get_recs(matrix, z_sys, pitch, gx):
    """
    Рассчитывает отклонения и обороты. 
    Возвращает список словарей с данными.
    """
    if matrix is None or matrix.size == 0:
        return []
        
    gy = matrix.shape[0]
    # Опорная точка всегда центр стола
    ref = matrix[gy//2, gx//2]
    recs = []
    
    # Флаг: является ли выбранная система валами
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
            recs.append({
                'name': name, 
                'val': diff, 
                'turns': None, 
                'dir': ""
            })
        else:
            current_pitch = pitch if pitch > 0 else 1.0
            turns = abs(diff) / current_pitch
            direction = "CW (по час.)" if diff > 0 else "CCW (против)"
            recs.append({
                'name': name, 
                'val': diff, 
                'turns': turns, 
                'dir': direction
            })
            
    return recs