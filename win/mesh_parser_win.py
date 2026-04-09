import re
import numpy as np

def parse_points(raw_text, gx, gy):
    """Превращает RAW текст из логов или конфига в матрицу NumPy"""
    if not raw_text: return None, "Нет данных"
    match = re.search(r'"points":\s*"([\s\S]+?)"', raw_text)
    content = match.group(1) if match else raw_text
    nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", content)]
    
    if len(nums) < gx * gy: 
        return None, f"Найдено {len(nums)} из {gx*gy} точек"
        
    matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
    # Зигзаг Anycubic: разворачиваем каждую вторую строку
    for i in range(len(matrix)):
        if i % 2 != 0: matrix[i] = matrix[i][::-1]
    return matrix, None