import numpy as np

def get_recs(matrix, z_sys, pitch, gx):
    """
    Расчет коррекции для 3-х точек (2 спереди, 1 сзади по центру)
    Относительно СРЕДНЕЙ плоскости меша.
    """
    if matrix is None: return []
    
    # Вычисляем среднее значение всей поверхности
    mean_val = np.mean(matrix)
    
    # Координаты точек (индексы в матрице)
    # Передний левый (FL): индекс [0, 0]
    # Передний правый (FR): индекс [0, gx-1]
    # Задний центр (BC): индекс [gx-1, gx//2]
    
    points = [
        {"name": "Передний Левый", "val": matrix[0, 0] - mean_val},
        {"name": "Передний Правый", "val": matrix[0, gx-1] - mean_val},
        {"name": "Задний Центр", "val": matrix[gx-1, gx//2] - mean_val}
    ]
    
    recs = []
    for p in points:
        diff = p["val"]
        # Если значение > 0, значит точка выше средней -> надо ОПУСТИТЬ
        # Если значение < 0, значит точка ниже средней -> надо ПОДНЯТЬ
        direction = "ВНИЗ" if diff > 0 else "ВВЕРХ"
        
        # Переводим в обороты (для валов шаг pitch обычно справочный)
        # Если используем винты на валах, шаг важен. Если просто микроны - оставляем val.
        turns = abs(diff) / pitch if pitch > 0 else 0
        
        recs.append({
            "name": p["name"],
            "val": abs(diff),
            "turns": turns,
            "dir": direction
        })
        
    return recs