import json
import numpy as np
from utils import logger_win

def parse_points(raw_text, gx, gy):
    """
    Парсит точки из JSON формата файла printer_mutable.cfg
    """
    try:
        # Загружаем текст как JSON объект
        data = json.loads(raw_text)
        
        # Ищем ключ, который начинается на "bed_mesh"
        # Обычно это "bed_mesh default", но может меняться
        mesh_key = None
        for key in data.keys():
            if key.startswith("bed_mesh"):
                mesh_key = key
                break
        
        if not mesh_key or "points" not in data[mesh_key]:
            return None, "Секция bed_mesh или ключ points не найдены в JSON"

        # Извлекаем строку с точками
        points_str = data[mesh_key]["points"]
        
        # Очищаем строку и превращаем в список чисел
        # Заменяем переносы строк на пробелы, убираем запятые
        clean_str = points_str.replace('\n', ' ').replace(',', ' ')
        points = [float(p) for p in clean_str.split() if p.strip()]

        if not points:
            return None, "Список точек пуст"

        # Проверка количества точек
        expected = gx * gy
        if len(points) < expected:
            return None, f"Мало точек: в файле {len(points)}, нужно {expected}"
        
        # Если точек больше (например, сетка в файле не совпадает с настройкой в GUI), 
        # берем первые gx*gy
        points = points[:expected]
        
        # Превращаем в матрицу
        matrix = np.array(points).reshape((gy, gx))
        logger_win.info(f"Матрица {gx}x{gy} успешно распарсена из JSON")
        
        return matrix, None

    except json.JSONDecodeError:
        logger_win.error("Файл не является валидным JSON")
        return None, "Ошибка: Файл должен быть в формате JSON"
    except Exception as e:
        logger_win.error(f"Ошибка парсинга JSON: {e}")
        return None, str(e)