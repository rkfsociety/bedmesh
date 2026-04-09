import re

def get_cfg_value(text, section, key):
    """Построчный поиск значения внутри секции"""
    lines = text.splitlines()
    target_sec = f"[{section.lower()}]"
    current_sec = ""
    for line in lines:
        clean = line.strip().lower()
        if clean.startswith("[") and clean.endswith("]"):
            current_sec = clean
            continue
        if current_sec == target_sec:
            if clean.startswith(f"{key.lower()}:") or clean.startswith(f"{key.lower()}="):
                val_part = line.split(':', 1)[1] if ':' in line else line.split('=', 1)[1]
                return val_part.split('#', 1)[0].strip()
    return ""

def set_cfg_value(text, section, key, new_val):
    """Безопасная замена значения ключа внутри секции"""
    lines = text.splitlines()
    output = []
    target_sec = f"[{section.lower()}]"
    current_sec = ""
    replaced = False

    for line in lines:
        clean = line.strip().lower()
        if clean.startswith("[") and clean.endswith("]"):
            current_sec = clean
            output.append(line)
            continue
        
        if current_sec == target_sec and not replaced:
            match = re.match(rf"^(\s*{key}\s*[:=]\s*)([^\s#]+)", line, re.IGNORECASE)
            if match:
                prefix = match.group(1)
                comment = ""
                if "#" in line:
                    comment = "  " + line[line.find("#"):]
                output.append(f"{prefix}{new_val}{comment}")
                replaced = True
                continue
        output.append(line)
    
    return "\n".join(output)