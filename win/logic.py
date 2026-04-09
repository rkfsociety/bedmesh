import re, json, os, sys, requests, paramiko, numpy as np

VERSION = "6.2"
SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try: return json.load(open(SETTINGS_FILE, "r"))
        except: return {}
    return {}

def save_settings(data):
    json.dump(data, open(SETTINGS_FILE, "w"), indent=4)

def parse_points(raw_text, gx, gy):
    match = re.search(r'"points":\s*"([\s\S]+?)"', raw_text)
    content = match.group(1) if match else raw_text
    nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", content)]
    if len(nums) < gx * gy: return None, f"Найдено {len(nums)}/{gx*gy} точек"
    matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
    for i in range(len(matrix)):
        if i % 2 != 0: matrix[i] = matrix[i][::-1]
    return matrix, None

def get_recs(matrix, z_type, pitch, gx):
    is_screws = "Винты" in z_type
    if is_screws:
        pts = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
    elif "2 вала" in z_type:
        pts = {"Левый вал": np.mean(matrix[:, 0]), "Правый вал": np.mean(matrix[:, -1])}
    elif "3 вала" in z_type:
        pts = {"Пер. Лево": matrix[0,0], "Пер. Право": matrix[0,-1], "Зад Центр": matrix[-1, gx//2]}
    else: # 4 вала
        pts = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
    
    low = min(pts.values())
    res = []
    for name, val in pts.items():
        diff = val - low
        t_info = f" | {abs(diff/pitch):.2f} об." if is_screws else ""
        res.append(f"● {name}:\n  {diff:+.3f}mm{t_info}\n  [{'🔽 ВНИЗ' if diff > 0 else '✅ OK' if diff == 0 else '🔼 ВВЕРХ'}]")
    return "\n\n".join(res), is_screws