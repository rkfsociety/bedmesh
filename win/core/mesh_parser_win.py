import numpy as np
import re

def parse_points(raw_data, gx, gy):
    """
    Парсит данные Mesh Points, ограничивая поиск только нужной секцией.
    """
    try:
        # 1. Пытаемся найти именно блок points в JSON или CFG
        # Ищем текст между "points": " и ближайшей кавычкой или концом блока
        points_match = re.search(r'"points":\s*"([\s\S]+?)"', raw_data)
        
        # Если не нашли в стиле JSON, ищем в стиле Klipper CFG
        if not points_match:
            points_match = re.search(r'points\s*=\s*([\s\S]+?)(?=\n\s*[a-zA-Z_]+\s*=|\[|\Z)', raw_data)
        
        if points_match:
            search_area = points_match.group(1)
        else:
            # Если структуру найти не удалось, берем весь текст (fallback)
            search_area = raw_data

        # 2. Извлекаем числа только из найденной области
        nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", search_area)]
        
        if len(nums) < gx * gy:
            return None, f"Найдено {len(nums)} точек, ожидалось {gx * gy}"
        
        # 3. Строим матрицу: точки заполняются последовательно слева направо (Linear Scan)
        matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
        
        return matrix, None
        
    except Exception as e:
        return None, f"Ошибка парсера: {str(e)}"