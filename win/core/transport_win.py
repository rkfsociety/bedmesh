import paramiko
from utils import logger_win

def fetch_ssh(host, port, user, pwd, path):
    """Открывает соединение, качает файл и СРАЗУ закрывает"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        # 1. Устанавливаем соединение
        client.connect(host, int(port), user, pwd, timeout=15, look_for_keys=False)
        sftp = client.open_sftp()
        
        # 2. Читаем данные
        with sftp.open(path, "r") as f:
            content = f.read().decode('utf-8')
            
        # 3. Закрываем SFTP
        sftp.close()
        # 4. Закрываем SSH сессию
        client.close()
        
        return content
    except Exception as e:
        logger_win.error(f"SSH ошибка при чтении {path}: {e}")
        # В случае ошибки всё равно пытаемся закрыть, чтобы не висело
        try: client.close()
        except: pass
        return None

def upload_ssh(host, port, user, pwd, path, content):
    """Открывает соединение, заливает файл и СРАЗУ закрывает"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, int(port), user, pwd, timeout=15, look_for_keys=False)
        sftp = client.open_sftp()
        
        with sftp.open(path, "w") as f:
            f.write(content)
        
        sftp.close()
        client.close()
        return True
    except Exception as e:
        logger_win.error(f"SSH ошибка при записи в {path}: {e}")
        try: client.close()
        except: pass
        return False