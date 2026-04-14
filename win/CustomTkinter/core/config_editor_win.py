import os
from utils import logger_win

class ConfigEditor:
    def __init__(self, transport):
        self.transport = transport
        self.config_path = "/userdata/app/gk/printer.cfg" 

    def get_config_parameters(self):
        """Парсинг текущих значений из printer.cfg"""
        try:
            content = self.transport.read_file(self.config_path)
            if not content: return {}

            params = {}
            lines = content.splitlines()
            current_section = None

            for line in lines:
                raw_line = line.strip()
                if not raw_line or raw_line.startswith("#"): continue
                
                if raw_line.startswith("["):
                    current_section = raw_line.split(']')[0][1:].strip().lower()
                    continue

                if (":" in raw_line or "=" in raw_line) and current_section:
                    sep = ":" if ":" in raw_line else "="
                    parts = raw_line.split(sep, 1)
                    key = parts[0].strip().lower()
                    value = parts[1].split("#")[0].strip()

                    if current_section == "bed_mesh":
                        if key in ["mesh_min", "mesh_max", "probe_count"]:
                            params[key] = value
                    elif current_section == "filament_hub":
                        if key == "v2_feed_speed": params["ace_feed"] = value
                        if key == "v2_unwind_speed": params["ace_unwind"] = value
            
            return params
        except Exception as e:
            logger_win.error(f"Ошибка парсинга конфига: {e}")
            return {}

    def _validate_params(self, params):
        try:
            for key in ["mesh_min", "mesh_max", "probe_count"]:
                if "," not in params.get(key, ""): return False, f"Ошибка в {key}"
            for key in ["ace_feed", "ace_unwind"]:
                if not params.get(key, "").replace('.', '', 1).isdigit(): return False, f"Ошибка в {key}"
            return True, ""
        except: return False, "Ошибка валидации"

    def save_config(self, new_params):
        """Сохранение без принудительной перезагрузки"""
        success, err = self._validate_params(new_params)
        if not success: return False

        try:
            content = self.transport.read_file(self.config_path)
            if not content: return False

            lines = content.splitlines()
            new_lines = []
            current_section = None
            modified = 0 

            for line in lines:
                orig = line
                stripped = line.strip()
                if stripped.startswith("["):
                    current_section = stripped.split(']')[0][1:].strip().lower()
                
                updated = False
                if current_section in ["bed_mesh", "filament_hub"] and stripped and not stripped.startswith("#"):
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
                            idx = orig.find(stripped)
                            indent = orig[:idx] if idx != -1 else ""
                            new_lines.append(f"{indent}{key}: {val}")
                            updated = True
                            modified += 1
                if not updated: new_lines.append(line)

            if modified == 0: return False
            self.transport.write_file(self.config_path, "\n".join(new_lines))
            return True
        except Exception as e:
            logger_win.error(f"Ошибка сохранения: {e}")
            return False