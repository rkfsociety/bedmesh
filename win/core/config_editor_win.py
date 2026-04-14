import os
from utils import logger_win

class ConfigEditor:
    def __init__(self, transport):
        self.transport = transport
        self.config_path = "/home/pi/printer_data/config/printer.cfg" 

    def get_config_parameters(self):
        """Подтягивает текущие значения из printer.cfg"""
        try:
            content = self.transport.read_file(self.config_path)
            if not content: return {}

            params = {}
            lines = content.splitlines()
            current_section = None

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1].lower()
                    continue

                if (":" in line or "=" in line) and current_section:
                    sep = ":" if ":" in line else "="
                    key, value = line.split(sep, 1)
                    key = key.strip().lower()
                    value = value.split("#")[0].strip()

                    if current_section == "bed_mesh" and key in ["mesh_min", "mesh_max", "probe_count"]:
                        params[key] = value
                    elif current_section == "filament_hub":
                        if key == "v2_feed_speed": params["ace_feed"] = value
                        if key == "v2_unwind_speed": params["ace_unwind"] = value
            
            return params
        except Exception as e:
            logger_win.error(f"Ошибка при чтении текущих значений: {e}")
            return {}

    def _validate_params(self, params):
        """Проверка корректности введенных данных перед сборкой конфига"""
        try:
            # Проверка координат (должно быть X,Y)
            for key in ["mesh_min", "mesh_max", "probe_count"]:
                val = params.get(key, "")
                if "," not in val or len(val.split(",")) != 2:
                    raise ValueError(f"Неверный формат {key}: ожидается 'X,Y'")
            
            # Проверка скоростей (должны быть числами)
            for key in ["ace_feed", "ace_unwind"]:
                val = params.get(key, "")
                float(val) # Вызовет ошибку, если не число
                
            return True
        except ValueError as e:
            logger_win.error(f"Валидация не пройдена: {e}")
            return False

    def save_config(self, new_params):
        """Безопасная замена параметров с проверкой структуры"""
        if not self._validate_params(new_params):
            return False # Прерываем, если данные неверны

        try:
            content = self.transport.read_file(self.config_path)
            if not content: return False

            lines = content.splitlines()
            new_lines = []
            current_section = None
            modified_count = 0 # Счетчик внесенных изменений

            for line in lines:
                original_line = line
                stripped = line.strip()
                
                if stripped.startswith("[") and stripped.endswith("]"):
                    current_section = stripped[1:-1].lower()
                
                updated = False
                if current_section in ["bed_mesh", "filament_hub"] and not stripped.startswith("#"):
                    sep = ":" if ":" in stripped else "=" if "=" in stripped else None
                    if sep:
                        key = stripped.split(sep, 1)[0].strip().lower()
                        val = None
                        
                        if current_section == "bed_mesh":
                            val = new_params.get(key)
                        elif current_section == "filament_hub":
                            if key == "v2_feed_speed": val = new_params.get("ace_feed")
                            if key == "v2_unwind_speed": val = new_params.get("ace_unwind")

                        if val is not None and val != "":
                            # Сохраняем отступ (табуляцию), если он был в оригинале
                            indent = original_line[:original_line.find(stripped)]
                            new_lines.append(f"{indent}{key}: {val}")
                            updated = True
                            modified_count += 1

                if not updated:
                    new_lines.append(line)

            # ФИНАЛЬНАЯ ПРОВЕРКА: Если количество строк изменилось критически 
            # или мы не нашли ни одного параметра — не сохраняем.
            if modified_count == 0:
                logger_win.error("Изменения не применены: параметры не найдены в файле")
                return False

            final_content = "\n".join(new_lines)
            
            # Записываем и перезагружаем
            self.transport.write_file(self.config_path, final_content)
            self.transport.execute_command("RESTART")
            return True
        except Exception as e:
            logger_win.error(f"Критическая ошибка при записи конфига: {e}")
            return False