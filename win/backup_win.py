import paramiko
import os

def create_backup_ssh(host, port, user, pwd, path):
    """Создает копию файла .cfg -> .cfg.bak на принтере через SSH"""
    if not path: return
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, int(port), user, pwd, timeout=10)
        # Команда cp перезапишет старый .bak новым актуальным состоянием
        client.exec_command(f"cp '{path}' '{path}.bak'")
        client.close()
        return True
    except:
        return False

def restore_backup_ssh(host, port, user, pwd, path):
    """Восстанавливает основной файл из .bak на принтере"""
    if not path: return False
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, int(port), user, pwd, timeout=10)
        # Проверяем, существует ли файл бэкапа
        sftp = client.open_sftp()
        try:
            sftp.stat(f"{path}.bak")
            client.exec_command(f"cp '{path}.bak' '{path}'")
            res = True
        except FileNotFoundError:
            res = False
        sftp.close()
        client.close()
        return res
    except:
        return False