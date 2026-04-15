import paramiko
import os
import datetime

TEMP_FILE_NAME = "temp_download.cfg"

def get_ssh_connection(ip: str, port: int = 2222, username: str = 'root', password: str = 'rockchip'):
    """Вспомогательная функция для создания подключения"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=ip, port=port, username=username, password=password, timeout=10)
    return ssh

def download_cfg_via_ssh(ip: str, port: int = 2222, username: str = 'root',
                         password: str = 'rockchip', remote_path: str = '/userdata/app/gk/printer_mutable.cfg') -> str:
    try:
        ssh = get_ssh_connection(ip, port, username, password)
        sftp = ssh.open_sftp()
        sftp.get(remote_path, TEMP_FILE_NAME)
        sftp.close()
        ssh.close()
        return TEMP_FILE_NAME
    except Exception as e:
        print(f"SSH Download Error: {e}")
        return None

def upload_cfg_via_ssh(local_path: str, ip: str, port: int = 2222, username: str = 'root',
                       password: str = 'rockchip', remote_path: str = '/userdata/app/gk/printer_mutable.cfg') -> bool:
    try:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
            
        ssh = get_ssh_connection(ip, port, username, password)
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        ssh.close()
        return True
    except Exception as e:
        print(f"SSH Upload Error: {e}")
        return False

def create_remote_backup(ip: str, port: int, username: str, password: str, 
                         remote_path: str = '/userdata/app/gk/printer_mutable.cfg') -> bool:
    """
    Создает бекап файла НА ПРИНТЕРЕ.
    Команда: cp /path/to/file /path/to/file.bak_YYYYMMDD_HHMMSS
    """
    try:
        ssh = get_ssh_connection(ip, port, username, password)
        
        # Формируем имя бекапа на удаленной машине
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{remote_path}.bak_{timestamp}"
        
        # Выполняем команду копирования
        stdin, stdout, stderr = ssh.exec_command(f"cp {remote_path} {backup_path}")
        exit_status = stdout.channel.recv_exit_status()
        
        ssh.close()
        
        if exit_status == 0:
            print(f"Remote backup created: {backup_path}")
            return True
        else:
            error = stderr.read().decode()
            print(f"Remote backup failed: {error}")
            return False
            
    except Exception as e:
        print(f"SSH Backup Command Error: {e}")
        return False

def cleanup_remote_backups(ip: str, port: int, username: str, password: str,
                           remote_path: str = '/userdata/app/gk/printer_mutable.cfg', max_backups: int = 3):
    """
    Удаляет старые бекапы на принтере, оставляя только max_backups последних.
    Ищет файлы по маске printer_mutable.cfg.bak_*
    """
    try:
        ssh = get_ssh_connection(ip, port, username, password)
        
        dir_name = os.path.dirname(remote_path)
        base_name = os.path.basename(remote_path)
        # Команда: ls -t /path/printer_mutable.cfg.bak_* (сортировка по времени, новые первые)
        cmd = f"ls -t {dir_name}/{base_name}.bak_*"
        
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode().strip()
        
        if output:
            files = output.split('\n')
            # Оставляем первые max_backups, остальные удаляем
            if len(files) > max_backups:
                to_delete = files[max_backups:]
                for f in to_delete:
                    ssh.exec_command(f"rm {f}")
                    print(f"Removed old remote backup: {f}")
        
        ssh.close()
    except Exception as e:
        print(f"SSH Cleanup Error: {e}")