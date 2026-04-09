import re
import numpy as np

def parse_points(raw_text, gx, gy):
    """
    Парсинг zigzag-сканирования:
    Row 0 (Y=0): X0 -> Xmax
    Row 1 (Y=1): Xmax -> X0 (реверс)
    Row 2 (Y=2): X0 -> Xmax
    """
    if not raw_text: return None, "Нет данных"
    
    match = re.search(r'"points":\s*"([\s\S]+?)"', raw_text)
    content = match.group(1) if match else raw_text
    nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", content)]
    
    if len(nums) < gx * gy: 
        return None, f"Найдено {len(nums)} из {gx*gy} точек"
        
    matrix = np.zeros((gy, gx))
    
    for y in range(gy):
        row_data = nums[y*gx : (y+1)*gx]
        if y % 2 != 0:
            # Разворачиваем нечетные строки (индексы 1, 3, 5...)
            matrix[y] = row_data[::-1]
        else:
            # Четные строки оставляем как есть
            matrix[y] = row_data
            
    return matrix, None