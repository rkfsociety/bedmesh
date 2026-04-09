import re, json, os, sys, requests, paramiko, subprocess, numpy as np

VERSION = "6.0"
REPO = "rkfsociety/bedmesh"
SETTINGS_FILE = "settings.json"

def cleanup_old_files():
    for f in ["updater.bat", "Bed_Mesh_Viz_new.exe"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f: return json.load(f)
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

def check_updates():
    try:
        r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
        latest = r.json().get("tag_name", "").replace("v", "")
        return latest if latest > VERSION else None
    except: return None

def parse_data(raw_text, gx, gy):
    match = re.search(r'"points":\s*"([\s\S]+?)"', raw_text)
    pts_content = match.group(1) if match else raw_text
    nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", pts_content)]
    
    if len(nums) < gx * gy:
        return None, f"Найдено {len(nums)} точек, нужно {gx*gy}"
    
    matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
    for i in range(len(matrix)):
        if i % 2 != 0: matrix[i] = matrix[i][::-1]
    return matrix, None

def get_recommendations(matrix, z_type, pitch, gx):
    pts = {}
    if "Винты" in z_type:
        pts = {"ПЛ (0,0)": matrix[0,0], "ПП (X,0)": matrix[0,-1], "ЗЛ (0,Y)": matrix[-1,0], "ЗП (X,Y)": matrix[-1,-1]}
    elif "2 вала" in z_type:
        pts = {"Левый вал": np.mean(matrix[:, 0]), "Правый вал": np.mean(matrix[:, -1])}
    elif "3 вала" in z_type:
        pts = {"Пер. Лево": matrix[0,0], "Пер. Право": matrix[0,-1], "Зад Центр": matrix[-1, gx//2]}
    elif "4 вала" in z_type:
        pts = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}

    low = min(pts.values())
    res = []
    for name, val in pts.items():
        diff = val - low
        res.append({"name": name, "mm": diff, "turns": abs(diff/pitch), 
                    "dir": "🔽 ВНИЗ" if diff > 0 else "✅ OK" if diff == 0 else "🔼 ВВЕРХ"})
    return res