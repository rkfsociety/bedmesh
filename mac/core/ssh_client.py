import datetime
import hashlib
import os
from typing import Optional

import paramiko

from utils.logger import get_logger


TEMP_FILE_NAME = "temp_download.cfg"
BACKUP_TAG = "bedmesh_bak"

logger = get_logger(__name__)


def _sh_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def sha256_local_file(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def sha256_remote_file_via_sftp(ip: str, port: int, username: str, password: str, remote_path: str) -> Optional[str]:
    try:
        ssh = get_ssh_connection(ip, port, username, password)
        sftp = ssh.open_sftp()
        hasher = hashlib.sha256()
        with sftp.open(remote_path, "rb") as file_obj:
            while True:
                chunk = file_obj.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
        sftp.close()
        ssh.close()
        return hasher.hexdigest()
    except Exception as error:
        logger.exception(
            "Remote sha256 failed: host=%s port=%s user=%s remote_path=%s error=%s",
            ip,
            port,
            username,
            remote_path,
            error,
        )
        return None


def list_remote_backups(ip: str, port: int, username: str, password: str, remote_path: str) -> list[str]:
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
                stat_result = sftp.stat(full)
                mtime = int(getattr(stat_result, "st_mtime", 0) or 0)
            except Exception:
                mtime = 0
            files.append((full, mtime))

        sftp.close()
        ssh.close()
        files.sort(key=lambda item: item[1], reverse=True)
        return [path for (path, _) in files]
    except Exception as error:
        logger.exception(
            "SSH list backups failed: host=%s port=%s user=%s remote_path=%s error=%s",
            ip,
            port,
            username,
            remote_path,
            error,
        )
        return []


def restore_remote_backup(ip: str, port: int, username: str, password: str, backup_path: str, remote_path: str) -> bool:
    try:
        ssh = get_ssh_connection(ip, port, username, password)
        command = f"cp {_sh_quote(backup_path)} {_sh_quote(remote_path)}"
        logger.debug("SSH exec: %s", command)
        _, stdout, stderr = ssh.exec_command(command)
        status = stdout.channel.recv_exit_status()
        if status != 0:
            logger.error("SSH restore backup failed: status=%s stderr=%s", status, stderr.read().decode(errors="ignore"))
            ssh.close()
            return False
        ssh.close()
        logger.info("SSH restore backup success: %s -> %s", backup_path, remote_path)
        return True
    except Exception as error:
        logger.exception(
            "SSH restore backup exception: host=%s port=%s user=%s backup=%s remote_path=%s error=%s",
            ip,
            port,
            username,
            backup_path,
            remote_path,
            error,
        )
        return False


def delete_remote_backup(ip: str, port: int, username: str, password: str, backup_path: str) -> bool:
    try:
        ssh = get_ssh_connection(ip, port, username, password)
        command = f"rm -f {_sh_quote(backup_path)}"
        logger.debug("SSH exec: %s", command)
        _, stdout, _ = ssh.exec_command(command)
        _ = stdout.channel.recv_exit_status()
        ssh.close()
        logger.info("SSH delete backup ok: %s", backup_path)
        return True
    except Exception as error:
        logger.exception(
            "SSH delete backup failed: host=%s port=%s user=%s backup=%s error=%s",
            ip,
            port,
            username,
            backup_path,
            error,
        )
        return False


def get_ssh_connection(ip: str, port: int = 2222, username: str = "root", password: str = "rockchip"):
    logger.debug(
        "SSH connect start: host=%s port=%s user=%s password_len=%s",
        ip,
        port,
        username,
        len(password) if password is not None else None,
    )
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=ip, port=port, username=username, password=password, timeout=10)
    logger.info("SSH connected: host=%s port=%s user=%s", ip, port, username)
    return ssh


def download_cfg_via_ssh(
    ip: str,
    port: int = 2222,
    username: str = "root",
    password: str = "rockchip",
    remote_path: str = "/userdata/app/gk/printer.cfg",
    local_path: str | None = None,
) -> Optional[str]:
    try:
        logger.info("SSH download start: host=%s port=%s user=%s remote_path=%s", ip, port, username, remote_path)
        ssh = get_ssh_connection(ip, port, username, password)
        sftp = ssh.open_sftp()
        target = local_path or f"download_{os.path.basename(remote_path) or TEMP_FILE_NAME}"
        logger.debug("SFTP GET: %s -> %s", remote_path, target)
        sftp.get(remote_path, target)
        sftp.close()
        ssh.close()
        logger.info("SSH download success: local_path=%s", target)
        return target
    except Exception as error:
        logger.exception(
            "SSH download failed: host=%s port=%s user=%s remote_path=%s error=%s",
            ip,
            port,
            username,
            remote_path,
            error,
        )
        return None


def upload_cfg_via_ssh(
    local_path: str,
    ip: str,
    port: int = 2222,
    username: str = "root",
    password: str = "rockchip",
    remote_path: str = "/userdata/app/gk/printer.cfg",
) -> bool:
    try:
        logger.info(
            "SSH upload start: host=%s port=%s user=%s remote_path=%s local_path=%s",
            ip,
            port,
            username,
            remote_path,
            local_path,
        )
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
    except Exception as error:
        logger.exception(
            "SSH upload failed: host=%s port=%s user=%s remote_path=%s local_path=%s error=%s",
            ip,
            port,
            username,
            remote_path,
            local_path,
            error,
        )
        return False


def create_remote_backup(
    ip: str,
    port: int,
    username: str,
    password: str,
    remote_path: str = "/userdata/app/gk/printer.cfg",
) -> Optional[str]:
    try:
        logger.info("SSH backup start: host=%s port=%s user=%s remote_path=%s", ip, port, username, remote_path)
        ssh = get_ssh_connection(ip, port, username, password)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{remote_path}.{BACKUP_TAG}_{timestamp}"
        command = f"cp {_sh_quote(remote_path)} {_sh_quote(backup_path)}"
        logger.debug("SSH exec: %s", command)
        _, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()

        if exit_status == 0:
            verify_command = f"test -f {_sh_quote(backup_path)}"
            logger.debug("SSH exec: %s", verify_command)
            _, verify_out, verify_err = ssh.exec_command(verify_command)
            verify_status = verify_out.channel.recv_exit_status()
            if verify_status == 0:
                logger.info("SSH backup success: backup_path=%s", backup_path)
                ssh.close()
                return backup_path
            logger.error("SSH backup verify failed: backup_path=%s stderr=%s", backup_path, verify_err.read().decode(errors="ignore"))
        else:
            error_text = stderr.read().decode(errors="ignore")
            logger.error("SSH backup failed: exit_status=%s stderr=%s", exit_status, error_text)

        ssh.close()
        return None
    except Exception as error:
        logger.exception(
            "SSH backup exception: host=%s port=%s user=%s remote_path=%s error=%s",
            ip,
            port,
            username,
            remote_path,
            error,
        )
        return None


def cleanup_remote_backups(
    ip: str,
    port: int,
    username: str,
    password: str,
    remote_path: str = "/userdata/app/gk/printer.cfg",
    max_backups: int = 5,
):
    try:
        logger.info(
            "SSH cleanup start: host=%s port=%s user=%s remote_path=%s max_backups=%s",
            ip,
            port,
            username,
            remote_path,
            max_backups,
        )
        files = list_remote_backups(ip, port, username, password, remote_path)
        if len(files) > max_backups:
            for file_path in files[max_backups:]:
                delete_remote_backup(ip, port, username, password, file_path)
        logger.info("SSH cleanup done")
    except Exception as error:
        logger.exception(
            "SSH cleanup failed: host=%s port=%s user=%s remote_path=%s error=%s",
            ip,
            port,
            username,
            remote_path,
            error,
        )


def ensure_remote_backup_exists(
    ip: str,
    port: int,
    username: str,
    password: str,
    remote_path: str,
    max_backups: int = 5,
) -> Optional[str]:
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
