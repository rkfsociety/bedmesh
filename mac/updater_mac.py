import requests, threading, webbrowser, sys
from tkinter import messagebox

REPO = "rkfsociety/bedmesh"

def check_for_updates(current_version, update_callback):
    def task():
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            if r.status_code == 200:
                data = r.json()
                latest_tag = data.get("tag_name", "").replace("v", "")
                latest_v_num = latest_tag.split('-')[0]
                current_v_num = current_version.split('-')[0]

                if latest_v_num > current_v_num:
                    assets = data.get("assets", [])
                    # Ищем .dmg для Mac
                    has_mac_asset = any(a["name"].endswith(".dmg") for a in assets)
                    if has_mac_asset:
                        update_callback(latest_tag, data)
        except: pass
    threading.Thread(target=task, daemon=True).start()

def install_update(data):
    """На macOS открываем страницу релиза для скачивания .dmg"""
    webbrowser.open(f"https://github.com/{REPO}/releases/latest")