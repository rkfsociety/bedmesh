import re, json, os, sys, requests, paramiko, numpy as np
import strings_win

VERSION = "0.088-win" 
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
    with sftp.open(path, 'w') as f:
        f.write(content)
    sftp.close(); client.close()

def get_cfg_value(text, section, key):
    pattern = rf"\[{section}\][^\[]*?{key}\s*[:=]\s*([^\s#\n]+)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ""

def set_cfg_value(text, section, key, new_val):
    section_pattern = rf"(\[{section}\][^\[]*?{key}\s*[:=]\s*)([^\s#\n]+)"
    return re.sub(section_pattern, rf"\1{new_val}", text, flags=re.IGNORECASE | re.DOTALL)

def parse_points(raw_text, gx, gy):
    if not raw_text: return None, "Нет данных"
    match = re.search(r'"points":\s*"([\s\S]+?)"', raw_text)
    content = match.group(1) if match else raw_text
    nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", content)]
    if len(nums) < gx * gy:
        return None, f"Найдено {len(nums)} из {gx*gy} точек"
    matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
    for i in range(len(matrix)):
        if i % 2 != 0: matrix[i] = matrix[i][::-1]
    return matrix, None

def get_recs(matrix, z_type, pitch, gx):
    is_screws = "Винты" in z_type
    if is_screws or "4 вала" in z_type:
        pts = {"ПЛ (0,0)": matrix[0,0], "ПП (X,0)": matrix[0,-1], "ЗЛ (0,Y)": matrix[-1,0], "ЗП (X,Y)": matrix[-1,-1]}
    elif "2 вала" in z_type:
        pts = {"Левый вал": np.mean(matrix[:, 0]), "Правый вал": np.mean(matrix[:, -1])}
    elif "3 вала" in z_type:
        pts = {"Перед Лево": matrix[0,0], "Перед Право": matrix[0,-1], "Зад Центр": matrix[-1, gx//2]}
    else: pts = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
    
    vals = list(pts.values())
    avg_val = sum(vals) / len(vals)
    best_ref_key = min(pts, key=lambda k: abs(pts[k] - avg_val))
    ref_val = pts[best_ref_key]
    res_data = []
    for name, val in pts.items():
        diff = val - ref_val
        direction = strings_win.DIR_OK if name == best_ref_key else (strings_win.DIR_DOWN if diff > 0 else strings_win.DIR_UP)
        t_info = f"{abs(diff/pitch):.2f} об." if is_screws else ""
        res_data.append({"name": name, "val": diff, "turns": t_info, "dir": direction})
    return res_data, is_screws