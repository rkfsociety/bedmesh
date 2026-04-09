import re, json, os, sys, requests, paramiko, numpy as np
import strings # Импортируем строки

VERSION = "6.3"
SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def fetch_ssh(host, port, user, pwd, path):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, int(port), user, pwd, timeout=10)
    sftp = client.open_sftp()
    with sftp.open(path, 'r') as f:
        content = f.read().decode('utf-8')
    sftp.close()
    client.close()
    return content

def parse_points(raw_text, gx, gy):
    match = re.search(r'"points":\s*"([\s\S]+?)"', raw_text)
    content = match.group(1) if match else raw_text
    nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", content)]
    
    if len(nums) < gx * gy:
        return None, f"Найдено {len(nums)} из {gx*gy} точек"
    
    matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
    for i in range(len(matrix)):
        if i % 2 != 0:
            matrix[i] = matrix[i][::-1]
    return matrix, None

def get_recs(matrix, z_type, pitch, gx):
    is_screws = "Винты" in z_type
    if is_screws:
        pts = {"ПЛ (0,0)": matrix[0,0], "ПП (X,0)": matrix[0,-1], "ЗЛ (0,Y)": matrix[-1,0], "ЗП (X,Y)": matrix[-1,-1]}
    elif "2 вала" in z_type:
        pts = {"Левый вал (среднее)": np.mean(matrix[:, 0]), "Правый вал (среднее)": np.mean(matrix[:, -1])}
    elif "3 вала" in z_type:
        pts = {"Пер. Лево": matrix[0,0], "Пер. Право": matrix[0,-1], "Зад Центр": matrix[-1, gx//2]}
    else:
        pts = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
    
    low = min(pts.values())
    res_list = []
    for name, val in pts.items():
        diff = val - low
        t_info = f" | {abs(diff/pitch):.2f} об." if is_screws else ""
        
        # Используем направления из strings.py
        direction = strings.DIR_OK
        if diff > 0: direction = strings.DIR_DOWN
        elif diff < 0: direction = strings.DIR_UP
        
        res_list.append(f"● {name}:\n  {diff:+.3f}мм{t_info}\n  [{direction}]")
    
    return "\n\n".join(res_list), is_screws