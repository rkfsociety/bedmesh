import paramiko
import os
import datetime
from utils.logger import get_logger
from typing import Optional
import hashlib

TEMP_FILE_NAME = "temp_download.cfg"
BACKUP_TAG = "bedmesh_bak"

logger = get_logger(__name__)

def _sh_quote(s: str) -> str:
    # Safe-ish single-quote for POSIX shells (busybox/ash).
    return "'" + str(s).replace("'", "'\"'\"'") + "'"

def sha256_local_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_remote_file_via_sftp(ip: str, port: int, username: str, password: str, remote_path: str) -> Optional[str]:
    try:
        ssh = get_ssh_connection(ip, port, username, password)
        sftp = ssh.open_sftp()
        h = hashlib.sha256()
        with sftp.open(remote_path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        sftp.close()
        ssh.close()
        return h.hexdigest()
    except Exception as e:
        logger.exception("Remote sha256 failed: host=%s port=%s user=%s remote_path=%s error=%s", ip, port, username, remote_path, e)
        return None

def _backup_glob(remote_path: str) -> str:
    # Pattern used to detect backups created by this app.
    return f"{remote_path}.{BACKUP_TAG}_*"

def list_remote_backups(ip: str, port: int, username: str, password: str, remote_path: str) -> list[str]:
    """
    Returns backup file paths, newest first.
    Only returns backups that match this app's mask: `<remote_path>.bedmesh_bak_*`
    """
    try:
        ssh = get_ssh_connection(ip, port, username, password)
        sftp = ssh.open_sftp()
        dir_name = os.path.dirname(remote_path)
        base_name = os.path.basename(remote_path)
        prefix = f"{base_name}.{BACKUP_TAG}_"

        files: list[tuple[str, int]] = []
        for name in sftp.listdir(dir_name):
            if not name.startswith(prefix):
                continue
            full = f"{dir_name.rstrip('/')}/{name}"
            try:
                st = sftp.stat(full)
                mtime = int(getattr(st, "st_mtime", 0) or 0)
            except Exception:
                mtime = 0
            files.append((full, mtime))

        sftp.close()
        ssh.close()

        # Sort newest first.
        files.sort(key=lambda x: x[1], reverse=True)
        return [p for (p, _) in files]
    except Exception as e:
        logger.exception("SSH list backups failed: host=%s port=%s user=%s remote_path=%s error=%s", ip, port, username, remote_path, e)
        return []

def restore_remote_backup(ip: str, port: int, username: str, password: str, backup_path: str, remote_path: str) -> bool:
    """Restores backup_path -> remote_path."""
    try:
        ssh = get_ssh_connection(ip, port, username, password)
        cmd = f"cp {_sh_quote(backup_path)} {_sh_quote(remote_path)}"
        logger.debug("SSH exec: %s", cmd)
        _, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            logger.error("SSH restore backup failed: status=%s stderr=%s", status, stderr.read().decode(errors="ignore"))
            ssh.close()
            return False
        ssh.close()
        logger.info("SSH restore backup success: %s -> %s", backup_path, remote_path)
        return True
    except Exception as e:
        logger.exception("SSH restore backup exception: host=%s port=%s user=%s backup=%s remote_path=%s error=%s", ip, port, username, backup_path, remote_path, e)
        return False

def delete_remote_backup(ip: str, port: int, username: str, password: str, backup_path: str) -> bool:
    try:
        ssh = get_ssh_connection(ip, port, username, password)
        cmd = f"rm -f {_sh_quote(backup_path)}"
        logger.debug("SSH exec: %s", cmd)
        _, stdout, _ = ssh.exec_command(cmd)
        _ = stdout.channel.recv_exit_status()
        ssh.close()
        logger.info("SSH delete backup ok: %s", backup_path)
        return True
    except Exception as e:
        logger.exception("SSH delete backup failed: host=%s port=%s user=%s backup=%s error=%s", ip, port, username, backup_path, e)
        return False

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
) -> Optional[str]:
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
                         remote_path: str = '/userdata/app/gk/printer.cfg') -> Optional[str]:
    """
    Создает бекап файла НА ПРИНТЕРЕ.
    Команда: cp /path/to/file /path/to/file.bak_YYYYMMDD_HHMMSS
    """
    try:
        logger.info("SSH backup start: host=%s port=%s user=%s remote_path=%s", ip, port, username, remote_path)
        ssh = get_ssh_connection(ip, port, username, password)
        
        # Формируем имя бэкапа на удаленной машине (с нашей маской)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{remote_path}.{BACKUP_TAG}_{timestamp}"
        
        # Выполняем команду копирования
        cmd = f"cp {_sh_quote(remote_path)} {_sh_quote(backup_path)}"
        logger.debug("SSH exec: %s", cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()

        if exit_status == 0:
            # Verify file exists (best-effort).
            v_cmd = f"test -f {_sh_quote(backup_path)}"
            logger.debug("SSH exec: %s", v_cmd)
            _, v_out, v_err = ssh.exec_command(v_cmd)
            v_status = v_out.channel.recv_exit_status()
            if v_status == 0:
                logger.info("SSH backup success: backup_path=%s", backup_path)
                ssh.close()
                return backup_path
            logger.error("SSH backup verify failed: backup_path=%s stderr=%s", backup_path, v_err.read().decode(errors='ignore'))
        else:
            error = stderr.read().decode(errors='ignore')
            logger.error("SSH backup failed: exit_status=%s stderr=%s", exit_status, error)

        ssh.close()
        return None
            
    except Exception as e:
        logger.exception("SSH backup exception: host=%s port=%s user=%s remote_path=%s error=%s", ip, port, username, remote_path, e)
        return None

def cleanup_remote_backups(ip: str, port: int, username: str, password: str,
                           remote_path: str = '/userdata/app/gk/printer.cfg', max_backups: int = 5):
    """
    Удаляет старые бекапы на принтере, оставляя только max_backups последних.
    Ищет файлы по маске `<remote_path>.bedmesh_bak_*`
    """
    try:
        logger.info("SSH cleanup start: host=%s port=%s user=%s remote_path=%s max_backups=%s", ip, port, username, remote_path, max_backups)
        files = list_remote_backups(ip, port, username, password, remote_path)
        if len(files) > max_backups:
            for f in files[max_backups:]:
                delete_remote_backup(ip, port, username, password, f)
        logger.info("SSH cleanup done")
    except Exception as e:
        logger.exception("SSH cleanup failed: host=%s port=%s user=%s remote_path=%s error=%s", ip, port, username, remote_path, e)

def ensure_remote_backup_exists(ip: str, port: int, username: str, password: str, remote_path: str, max_backups: int = 5) -> Optional[str]:
    """
    If there are no backups with our mask, create one.
    Always enforces cleanup(max_backups). Returns created backup path or None if nothing created/failed.
    """
    backups = list_remote_backups(ip, port, username, password, remote_path)
    if backups:
        try:
            cleanup_remote_backups(ip, port, username, password, remote_path, max_backups=max_backups)
        except Exception:
            pass
        return None
    created = create_remote_backup(ip, port, username, password, remote_path)
    try:
        cleanup_remote_backups(ip, port, username, password, remote_path, max_backups=max_backups)
    except Exception:
        pass
    return created