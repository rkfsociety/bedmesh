import paramiko
import os
from utils import logger_win

class ConfigEditor:
    def __init__(self, transport):
        self.transport = transport
        # Путь к конфигу на твоем принтере
        self.config_path = "/home/pi/printer_data/config/printer.cfg" 

    def get_config_parameters(self):
        """Парсинг параметров Bed Mesh и скоростей Ace Pro"""
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

                    # Параметры сетки стола
                    if current_section == "bed_mesh":
                        if key in ["mesh_min", "mesh_max", "probe_count"]:
                            params[key] = value
                    
                    # Параметры скоростей Ace Pro
                    elif current_section == "filament_hub":
                        if key == "v2_feed_speed": params["ace_feed"] = value
                        if key == "v2_unwind_speed": params["ace_unwind"] = value
            
            return params
        except Exception as e:
            logger_win.error(f"Ошибка чтения конфигурации: {e}")
            return {}

    def save_config(self, new_params):
        """Сохранение параметров в printer.cfg и RESTART"""
        try:
            content = self.transport.read_file(self.config_path)
            if not content: return False

            lines = content.splitlines()
            new_lines = []
            current_section = None

            for line in lines:
                stripped = line.strip()
                if stripped.startswith("[") and stripped.endswith("]"):
                    current_section = stripped[1:-1].lower()
                
                updated = False
                if current_section in ["bed_mesh", "filament_hub"] and not stripped.startswith("#"):
                    # Определяем разделитель, который уже используется в этой строке
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
                            # Сохраняем формат (ключ: значение)
                            new_lines.append(f"{key}: {val}")
                            updated = True

                if not updated:
                    new_lines.append(line)

            final_content = "\n".join(new_lines)
            self.transport.write_file(self.config_path, final_content)
            self.transport.execute_command("RESTART")
            logger_win.info("Конфигурация успешно обновлена, Klipper перезагружен.")
            return True
        except Exception as e:
            logger_win.error(f"Ошибка сохранения конфигурации: {e}")
            return False