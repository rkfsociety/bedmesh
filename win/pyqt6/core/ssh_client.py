import paramiko
import os
from typing import Optional

TEMP_FILE_NAME = "temp_download.cfg"

def download_cfg_via_ssh(ip_address: str) -> Optional[str]:
    """
    Подключается по SSH и скачивает printer_mutable.cfg.
    Возвращает путь к скачанному файлу или None при ошибке.
    """
    try:
        ssh = paramiko.SSHClient()
        # Автоматически принимать новые ключи хоста
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Параметры подключения (твои данные)
        ssh.connect(
            hostname=ip_address,
            port=2222,
            username='root',
            password='rockchip',
            timeout=10 # Ждем не больше 10 секунд
        )
        
        # Используем SFTP для скачивания файлов
        sftp = ssh.open_sftp()
        remote_path = "/userdata/app/gk/printer_mutable.cfg"
        
        # Скачиваем в текущую папку
        sftp.get(remote_path, TEMP_FILE_NAME)
        
        sftp.close()
        ssh.close()
        
        return TEMP_FILE_NAME

    except Exception as e:
        print(f"SSH Error: {e}")
        return None