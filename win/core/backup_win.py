import paramiko
from utils import logger_win
from datetime import datetime
import os

# Префикс, чтобы программа знала, что это её бэкапы
BACKUP_PREFIX = "bmesh_backup"
MAX_BACKUPS = 5

def get_backup_list(host, port, user, pwd, path):
    """Получает список именно наших бэкапов (.bak) на принтере"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    backups = []
    try:
        client.connect(host, int(port), user, pwd, timeout=10)
        sftp = client.open_sftp()
        
        dir_path = os.path.dirname(path).replace("\\", "/")
        file_name = os.path.basename(path)
        
        files = sftp.listdir(dir_path)
        # Ищем файлы, которые начинаются на имя конфига и содержат наш префикс
        for f in files:
            if f.startswith(file_name) and BACKUP_PREFIX in f and f.endswith(".bak"):
                backups.append(f)
        
        sftp.close()
        client.close()
        # Сортируем: новые сверху
        return sorted(backups, reverse=True)
    except Exception as e:
        logger_win.error(f"Ошибка получения списка бэкапов: {e}")
        return []

def auto_backup_if_missing(host, port, user, pwd, path):
    """Создает помеченный бэкап и удаляет лишние (ротация)"""
    if not path: return False
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, int(port), user, pwd, timeout=10)
        
        # 1. Получаем список только наших текущих бэкапов
        existing = get_backup_list(host, port, user, pwd, path)
        
        # 2. Создаем новый бэкап с уникальной меткой времени
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{path}.{BACKUP_PREFIX}.{timestamp}.bak"
        
        # Выполняем копирование на стороне принтера
        client.exec_command(f"cp '{path}' '{new_name}'")
        logger_win.info(f"Создан системный бэкап: {os.path.basename(new_name)}")

        # 3. Ротация: если бэкапов стало больше лимита, удаляем старые
        # Мы проверяем список ДО создания + 1 новый
        if len(existing) >= MAX_BACKUPS:
            dir_path = os.path.dirname(path).replace("\\", "/")
            # Удаляем все, что выходит за лимит (самые старые в конце списка)
            for old_file in existing[(MAX_BACKUPS-1):]:
                full_old_path = f"{dir_path}/{old_file}"
                client.exec_command(f"rm '{full_old_path}'")
                logger_win.info(f"Удален лишний бэкап: {old_file}")

        client.close()
        return True
    except Exception as e:
        logger_win.error(f"Ошибка в системе бэкапов: {e}")
        return False

def restore_backup_ssh(host, port, user, pwd, path, backup_filename):
    """Восстанавливает выбранный файл"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, int(port), user, pwd, timeout=10)
        dir_path = os.path.dirname(path).replace("\\", "/")
        full_backup_path = f"{dir_path}/{backup_filename}"
        
        client.exec_command(f"cp '{full_backup_path}' '{path}'")
        logger_win.info(f"Конфиг восстановлен из: {backup_filename}")
        client.close()
        return True
    except Exception as e:
        logger_win.error(f"Ошибка восстановления: {e}")
        return False