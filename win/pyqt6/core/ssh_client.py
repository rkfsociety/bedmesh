import paramiko
import os
import datetime
from utils.logger import get_logger

TEMP_FILE_NAME = "temp_download.cfg"

logger = get_logger(__name__)

def get_ssh_connection(ip: str, port: int = 2222, username: str = 'root', password: str = 'rockchip'):
    """Вспомогательная функция для создания подключения"""
    logger.debug(
        "SSH connect start: host=%s port=%s user=%s password_len=%s",
        ip, port, username, len(password) if password is not None else None
    )
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=ip, port=port, username=username, password=password, timeout=10)
    logger.info("SSH connected: host=%s port=%s user=%s", ip, port, username)
    return ssh

def download_cfg_via_ssh(
    ip: str,
    port: int = 2222,
    username: str = 'root',
    password: str = 'rockchip',
    remote_path: str = '/userdata/app/gk/printer.cfg',
    local_path: str | None = None,
) -> str:
    try:
        logger.info("SSH download start: host=%s port=%s user=%s remote_path=%s", ip, port, username, remote_path)
        ssh = get_ssh_connection(ip, port, username, password)
        sftp = ssh.open_sftp()
        # По умолчанию сохраняем под уникальным именем (чтобы printer.cfg и printer_mutable.cfg не перетирали друг друга).
        target = local_path or f"download_{os.path.basename(remote_path) or TEMP_FILE_NAME}"
        logger.debug("SFTP GET: %s -> %s", remote_path, target)
        sftp.get(remote_path, target)
        sftp.close()
        ssh.close()
        logger.info("SSH download success: local_path=%s", target)
        return target
    except Exception as e:
        logger.exception("SSH download failed: host=%s port=%s user=%s remote_path=%s error=%s", ip, port, username, remote_path, e)
        return None

def upload_cfg_via_ssh(local_path: str, ip: str, port: int = 2222, username: str = 'root',
                       password: str = 'rockchip', remote_path: str = '/userdata/app/gk/printer.cfg') -> bool:
    try:
        logger.info("SSH upload start: host=%s port=%s user=%s remote_path=%s local_path=%s", ip, port, username, remote_path, local_path)
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
            
        ssh = get_ssh_connection(ip, port, username, password)
        sftp = ssh.open_sftp()
        logger.debug("SFTP PUT: %s -> %s", local_path, remote_path)
        sftp.put(local_path, remote_path)
        sftp.close()
        ssh.close()
        logger.info("SSH upload success: remote_path=%s", remote_path)
        return True
    except Exception as e:
        logger.exception("SSH upload failed: host=%s port=%s user=%s remote_path=%s local_path=%s error=%s", ip, port, username, remote_path, local_path, e)
        return False

def create_remote_backup(ip: str, port: int, username: str, password: str, 
                         remote_path: str = '/userdata/app/gk/printer.cfg') -> bool:
    """
    Создает бекап файла НА ПРИНТЕРЕ.
    Команда: cp /path/to/file /path/to/file.bak_YYYYMMDD_HHMMSS
    """
    try:
        logger.info("SSH backup start: host=%s port=%s user=%s remote_path=%s", ip, port, username, remote_path)
        ssh = get_ssh_connection(ip, port, username, password)
        
        # Формируем имя бекапа на удаленной машине
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{remote_path}.bak_{timestamp}"
        
        # Выполняем команду копирования
        cmd = f"cp {remote_path} {backup_path}"
        logger.debug("SSH exec: %s", cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        
        ssh.close()
        
        if exit_status == 0:
            logger.info("SSH backup success: backup_path=%s", backup_path)
            return True
        else:
            error = stderr.read().decode()
            logger.error("SSH backup failed: exit_status=%s stderr=%s", exit_status, error)
            return False
            
    except Exception as e:
        logger.exception("SSH backup exception: host=%s port=%s user=%s remote_path=%s error=%s", ip, port, username, remote_path, e)
        return False

def cleanup_remote_backups(ip: str, port: int, username: str, password: str,
                           remote_path: str = '/userdata/app/gk/printer.cfg', max_backups: int = 3):
    """
    Удаляет старые бекапы на принтере, оставляя только max_backups последних.
    Ищет файлы по маске printer_mutable.cfg.bak_*
    """
    try:
        logger.info("SSH cleanup start: host=%s port=%s user=%s remote_path=%s max_backups=%s", ip, port, username, remote_path, max_backups)
        ssh = get_ssh_connection(ip, port, username, password)
        
        dir_name = os.path.dirname(remote_path)
        base_name = os.path.basename(remote_path)
        # Команда: ls -t /path/printer_mutable.cfg.bak_* (сортировка по времени, новые первые)
        cmd = f"ls -t {dir_name}/{base_name}.bak_*"
        logger.debug("SSH exec: %s", cmd)
        
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode().strip()
        
        if output:
            files = output.split('\n')
            # Оставляем первые max_backups, остальные удаляем
            if len(files) > max_backups:
                to_delete = files[max_backups:]
                for f in to_delete:
                    logger.debug("SSH exec: rm %s", f)
                    ssh.exec_command(f"rm {f}")
                    logger.info("SSH cleanup removed backup: %s", f)
        
        ssh.close()
        logger.info("SSH cleanup done")
    except Exception as e:
        logger.exception("SSH cleanup failed: host=%s port=%s user=%s remote_path=%s error=%s", ip, port, username, remote_path, e)