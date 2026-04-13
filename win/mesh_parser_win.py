import numpy as np
import re

def parse_points(raw_data, gx, gy):
    """
    Парсит сырые данные Mesh Points. 
    Логика: Линейное построение (строго слева направо для каждого ряда).
    """
    try:
        # Извлекаем все числа из текста (поддерживает форматы Klipper и JSON)
        nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", raw_data)]
        
        if len(nums) < gx * gy:
            return None, f"Найдено {len(nums)} точек, ожидалось {gx * gy}"
        
        # Строим матрицу: точки заполняются последовательно слева направо
        # Это соответствует логике файлов mutable
        matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
        
        return matrix, None
    except Exception as e:
        return None, f"Ошибка парсинга: {str(e)}"