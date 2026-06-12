import paramiko
import os
import datetime
from utils.logger import get_logger
from utils.resources import resource_path, gkbridge_binary
from typing import Optional, Callable
import hashlib

TEMP_FILE_NAME = "temp_download.cfg"
BACKUP_TAG = "bedmesh_bak"

# Постоянный автозапуск (SSH + веб-панель) на принтере Anycubic Kobra S1 / GoKlipper.
RUN_SH = "/userdata/app/kenv/run.sh"
BOOT_REMOTE = "/useremain/boot.sh"
SSH_PKG_SRC = "/tmp/ssh"
SSH_PKG_DST = "/useremain/ssh"
GKBRIDGE_REMOTE = "/useremain/gkbridge"
RUN_HOOK_LINE = "[ -f /useremain/boot.sh ] && sh /useremain/boot.sh"

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


# ─────────────────────────────────────────────────────────────────────────────
# Постоянный автозапуск: SSH (dropbear) и веб-панель (gkbridge)
# ─────────────────────────────────────────────────────────────────────────────

def _exec(ssh, cmd: str) -> tuple[int, str, str]:
    """Выполняет команду по SSH, возвращает (exit_status, stdout, stderr)."""
    logger.debug("SSH exec: %s", cmd)
    _, stdout, stderr = ssh.exec_command(cmd)
    status = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="ignore")
    err = stderr.read().decode(errors="ignore")
    if status != 0:
        logger.debug("SSH exec status=%s stderr=%s", status, err.strip())
    return status, out, err


def _upload_boot_sh(sftp) -> None:
    """
    Заливает resources/boot.sh в /useremain/boot.sh с принудительными LF-окончаниями.
    boot.sh универсален: SSH-часть и панель включаются по наличию своих артефактов.
    """
    boot_local = resource_path("resources/boot.sh")
    with open(boot_local, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    with sftp.open(BOOT_REMOTE, "w") as rf:
        rf.write(content)
    logger.info("boot.sh uploaded: %s (LF, %d bytes)", BOOT_REMOTE, len(content))


def _insert_run_hook(ssh, sftp) -> bool:
    """
    Идемпотентно вставляет строку-хук в /userdata/app/kenv/run.sh ПЕРЕД `./start.sh`.
    Делает бэкап перед изменением. Возвращает True, если хук есть/добавлен.
    """
    try:
        with sftp.open(RUN_SH, "r") as f:
            text = f.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error("run.sh read failed: %s (%s)", RUN_SH, e)
        return False

    if "/useremain/boot.sh" in text:
        logger.info("run.sh hook already present, skip")
        return True

    # Бэкап перед правкой.
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{RUN_SH}.{BACKUP_TAG}_{ts}"
    _exec(ssh, f"cp -a {_sh_quote(RUN_SH)} {_sh_quote(backup)}")
    logger.info("run.sh backup created: %s", backup)

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out_lines: list[str] = []
    inserted = False
    # 1-й проход: точное совпадение `./start.sh`.
    for ln in lines:
        if not inserted and ln.strip() == "./start.sh":
            out_lines.append(RUN_HOOK_LINE)
            inserted = True
        out_lines.append(ln)

    # 2-й проход (фолбэк): любая строка, содержащая start.sh.
    if not inserted:
        out_lines = []
        for ln in lines:
            if not inserted and "start.sh" in ln and not ln.strip().startswith("#"):
                out_lines.append(RUN_HOOK_LINE)
                inserted = True
            out_lines.append(ln)

    if not inserted:
        # В конец дописывать нельзя (после ./start.sh идёт exit 0) — отказываемся.
        logger.error("run.sh: anchor './start.sh' not found, hook NOT inserted")
        return False

    new_text = "\n".join(out_lines)
    with sftp.open(RUN_SH, "w") as f:
        f.write(new_text)
    logger.info("run.sh hook inserted before start.sh")
    return True


def _run_boot_now(ssh) -> None:
    """Запускает boot.sh сразу, чтобы артефакты поднялись без ребута."""
    _exec(ssh, f"sh {_sh_quote(BOOT_REMOTE)}")


def _remove_run_hook(ssh, sftp) -> bool:
    """Идемпотентно убирает строку-хук из run.sh (с бэкапом). True, если хука нет/убран."""
    try:
        with sftp.open(RUN_SH, "r") as f:
            text = f.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error("run.sh read failed for hook removal: %s (%s)", RUN_SH, e)
        return False

    if "/useremain/boot.sh" not in text:
        return True

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    _exec(ssh, f"cp -a {_sh_quote(RUN_SH)} {_sh_quote(RUN_SH + '.' + BACKUP_TAG + '_' + ts)}")

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    kept = [ln for ln in lines if "/useremain/boot.sh" not in ln]
    with sftp.open(RUN_SH, "w") as f:
        f.write("\n".join(kept))
    logger.info("run.sh hook removed")
    return True


def check_persistent_status(ip: str, port: int, username: str, password: str) -> Optional[dict]:
    """
    Определяет, что установлено на принтере. Возвращает dict или None при ошибке связи:
      ssh_artifact   — есть /useremain/ssh/dropbear
      panel_artifact — есть /useremain/gkbridge
      boot           — есть /useremain/boot.sh
      hook           — run.sh содержит вызов boot.sh
      ssh_installed  — артефакт SSH + хук (полностью рабочая установка)
      panel_installed— артефакт панели + хук
    """
    try:
        ssh = get_ssh_connection(ip, port, username, password)
    except Exception as e:
        logger.warning("status check connect failed: host=%s port=%s error=%s", ip, port, e)
        return None
    try:
        cmd = (
            "printf '%s%s%s%s' "
            f"$([ -f {SSH_PKG_DST}/dropbear ] && echo 1 || echo 0) "
            f"$([ -x {GKBRIDGE_REMOTE} ] && echo 1 || echo 0) "
            f"$([ -f {BOOT_REMOTE} ] && echo 1 || echo 0) "
            f"$(grep -q /useremain/boot.sh {RUN_SH} 2>/dev/null && echo 1 || echo 0)"
        )
        _, out, err = _exec(ssh, cmd)
        flags = (out or "").strip()
        if len(flags) < 4:
            logger.error("status check bad output: out=%r err=%s", out, err)
            return None
        ssh_art = flags[0] == "1"
        panel_art = flags[1] == "1"
        boot = flags[2] == "1"
        hook = flags[3] == "1"
        status = {
            "ssh_artifact": ssh_art,
            "panel_artifact": panel_art,
            "boot": boot,
            "hook": hook,
            "ssh_installed": ssh_art and hook,
            "panel_installed": panel_art and hook,
        }
        logger.info("persistent status: %s", status)
        return status
    except Exception as e:
        logger.exception("status check failed: host=%s port=%s error=%s", ip, port, e)
        return None
    finally:
        ssh.close()


def uninstall_persistent_ssh(ip: str, port: int, username: str, password: str,
                             progress_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Откатывает постоянный SSH: удаляет /useremain/ssh. Если веб-панель не установлена —
    дополнительно снимает общий хук из run.sh и удаляет boot.sh.
    Запущенный dropbear НЕ убивается (это оборвало бы текущую сессию) — он исчезнет
    после перезагрузки принтера.
    """
    def _p(msg: str):
        logger.info("uninstall_persistent_ssh: %s", msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    ssh = get_ssh_connection(ip, port, username, password)
    try:
        sftp = ssh.open_sftp()
        try:
            _p("Удаление SSH-пакета из /useremain...")
            _exec(ssh, f"rm -rf {_sh_quote(SSH_PKG_DST)}")

            st, _, _ = _exec(ssh, f"test -x {_sh_quote(GKBRIDGE_REMOTE)}")
            if st != 0:
                _p("Снятие автозапуска (веб-панель не установлена)...")
                _remove_run_hook(ssh, sftp)
                _exec(ssh, f"rm -f {_sh_quote(BOOT_REMOTE)}")
            _p("Готово.")
            return True
        finally:
            sftp.close()
    except Exception as e:
        logger.exception("uninstall_persistent_ssh failed: host=%s port=%s error=%s", ip, port, e)
        return False
    finally:
        ssh.close()


def uninstall_web_panel(ip: str, port: int, username: str, password: str,
                        progress_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Откатывает веб-панель: останавливает gkbridge и удаляет бинарник. Если постоянный
    SSH не установлен — дополнительно снимает общий хук из run.sh и удаляет boot.sh.
    """
    def _p(msg: str):
        logger.info("uninstall_web_panel: %s", msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    ssh = get_ssh_connection(ip, port, username, password)
    try:
        sftp = ssh.open_sftp()
        try:
            _p("Остановка веб-панели...")
            _exec(ssh, "killall gkbridge 2>/dev/null")
            _p("Удаление бинарника панели...")
            _exec(ssh, f"rm -f {_sh_quote(GKBRIDGE_REMOTE)}")

            st, _, _ = _exec(ssh, f"test -f {_sh_quote(SSH_PKG_DST + '/dropbear')}")
            if st != 0:
                _p("Снятие автозапуска (постоянный SSH не установлен)...")
                _remove_run_hook(ssh, sftp)
                _exec(ssh, f"rm -f {_sh_quote(BOOT_REMOTE)}")
            _p("Готово.")
            return True
        finally:
            sftp.close()
    except Exception as e:
        logger.exception("uninstall_web_panel failed: host=%s port=%s error=%s", ip, port, e)
        return False
    finally:
        ssh.close()


def install_persistent_ssh(ip: str, port: int, username: str, password: str,
                           progress_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Ставит постоянный SSH (dropbear), переживающий перезагрузку:
      1. копирует живой /tmp/ssh -> /useremain/ssh (если ещё нет);
      2. заливает boot.sh;
      3. вставляет хук в run.sh;
      4. запускает boot.sh сразу.
    Идемпотентно. Требует, чтобы SSH сейчас уже работал (флешка/уже установлено).
    """
    def _p(msg: str):
        logger.info("install_persistent_ssh: %s", msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    ssh = get_ssh_connection(ip, port, username, password)
    try:
        sftp = ssh.open_sftp()
        try:
            _p("Копирование SSH-пакета в постоянное место...")
            st, _, err = _exec(ssh, f"[ -d {_sh_quote(SSH_PKG_DST)} ] || cp -a {_sh_quote(SSH_PKG_SRC)} {_sh_quote(SSH_PKG_DST)}")
            if st != 0:
                logger.error("ssh pkg copy failed: %s", err)
                return False
            st, _, _ = _exec(ssh, f"test -f {_sh_quote(SSH_PKG_DST + '/dropbear')}")
            if st != 0:
                logger.error("dropbear missing after copy: %s/dropbear", SSH_PKG_DST)
                return False

            _p("Загрузка boot.sh...")
            _upload_boot_sh(sftp)
            _exec(ssh, f"chmod +x {_sh_quote(BOOT_REMOTE)}")

            _p("Прописывание автозапуска в run.sh...")
            if not _insert_run_hook(ssh, sftp):
                return False

            _p("Запуск автозапуска...")
            _run_boot_now(ssh)
            _p("Готово.")
            return True
        finally:
            sftp.close()
    except Exception as e:
        logger.exception("install_persistent_ssh failed: host=%s port=%s error=%s", ip, port, e)
        return False
    finally:
        ssh.close()


def install_web_panel(ip: str, port: int, username: str, password: str,
                      gkbridge_local_path: Optional[str] = None,
                      progress_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Ставит постоянную веб-панель (gkbridge), переживающую перезагрузку:
      1. заливает бинарник gkbridge -> /useremain/gkbridge (+chmod);
      2. заливает boot.sh;
      3. вставляет хук в run.sh;
      4. запускает boot.sh сразу (панель поднимется без ребута).
    Идемпотентно.
    """
    def _p(msg: str):
        logger.info("install_web_panel: %s", msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    if gkbridge_local_path is None:
        gkbridge_local_path = gkbridge_binary()
    if not os.path.exists(gkbridge_local_path):
        logger.error("gkbridge binary not found: %s", gkbridge_local_path)
        return False

    ssh = get_ssh_connection(ip, port, username, password)
    try:
        sftp = ssh.open_sftp()
        try:
            _p("Загрузка бинарника веб-панели...")
            sftp.put(gkbridge_local_path, GKBRIDGE_REMOTE)
            _exec(ssh, f"chmod +x {_sh_quote(GKBRIDGE_REMOTE)}")

            _p("Загрузка boot.sh...")
            _upload_boot_sh(sftp)
            _exec(ssh, f"chmod +x {_sh_quote(BOOT_REMOTE)}")

            _p("Прописывание автозапуска в run.sh...")
            if not _insert_run_hook(ssh, sftp):
                return False

            _p("Запуск веб-панели...")
            _run_boot_now(ssh)
            _p("Готово.")
            return True
        finally:
            sftp.close()
    except Exception as e:
        logger.exception("install_web_panel failed: host=%s port=%s error=%s", ip, port, e)
        return False
    finally:
        ssh.close()