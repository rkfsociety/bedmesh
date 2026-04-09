import re, json, os, sys, requests, paramiko, numpy as np
import strings_win

VERSION = "0.103-win" 
SETTINGS_FILE = "settings_win.json"

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f: json.dump(data, f, indent=4)

def fetch_ssh(host, port, user, pwd, path):
    if not path or path.strip() == "": return ""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, int(port), user, pwd, timeout=10)
    sftp = client.open_sftp()
    with sftp.open(path, 'r') as f:
        content = f.read().decode('utf-8')
    sftp.close(); client.close()
    return content

def save_ssh(host, port, user, pwd, path, content):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, int(port), user, pwd, timeout=10)
    sftp = client.open_sftp()
    with sftp.open(path, 'w') as f: f.write(content)
    sftp.close(); client.close()

def get_cfg_value(text, section, key):
    """Поиск значения ключа строго внутри границ секции"""
    # Находим начало секции
    sec_start = re.search(rf"^\[{section}\]", text, re.MULTILINE | re.IGNORECASE)
    if not sec_start: return ""
    
    # Находим начало следующей секции, чтобы ограничить область поиска
    next_sec = re.search(r"^\[", text[sec_start.end():], re.MULTILINE)
    end_pos = sec_start.end() + next_sec.start() if next_sec else len(text)
    section_body = text[sec_start.end():end_pos]
    
    # Ищем ключ в теле секции
    match = re.search(rf"^{key}\s*[:=]\s*([^\s#\n]+)", section_body, re.MULTILINE | re.IGNORECASE)
    return match.group(1) if match else ""

def set_cfg_value(text, section, key, new_val):
    """Замена значения ключа строго внутри границ секции без повреждения остального файла"""
    sec_start = re.search(rf"^\[{section}\]", text, re.MULTILINE | re.IGNORECASE)
    if not sec_start: return text # Секция не найдена, возвращаем оригинал
    
    next_sec = re.search(r"^\[", text[sec_start.end():], re.MULTILINE)
    end_pos = sec_start.end() + next_sec.start() if next_sec else len(text)
    
    section_head = text[:sec_start.end()]
    section_body = text[sec_start.end():end_pos]
    file_tail = text[end_pos:]
    
    # Регулярка для замены ключа внутри тела секции
    key_pattern = rf"(^{key}\s*[:=]\s*)([^\s#\n]+)"
    if re.search(key_pattern, section_body, re.MULTILINE | re.IGNORECASE):
        new_body = re.sub(key_pattern, rf"\1{new_val}", section_body, flags=re.MULTILINE | re.IGNORECASE)
        return section_head + new_body + file_tail
    
    return text

def parse_points(raw_text, gx, gy):
    if not raw_text: return None, "Нет данных"
    match = re.search(r'"points":\s*"([\s\S]+?)"', raw_text)
    content = match.group(1) if match else raw_text
    nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", content)]
    if len(nums) < gx * gy: return None, f"Найдено {len(nums)} из {gx*gy} точек"
    matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
    for i in range(len(matrix)):
        if i % 2 != 0: matrix[i] = matrix[i][::-1]
    return matrix, None