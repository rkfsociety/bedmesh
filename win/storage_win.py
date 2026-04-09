import json
import os

SETTINGS_FILE = "settings_win.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f: json.dump(data, f, indent=4)