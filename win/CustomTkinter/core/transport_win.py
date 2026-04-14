import paramiko
from utils import logger_win

class SSHTransport:
    def __init__(self, host, port, user, pwd):
        self.host = host
        self.port = int(port)
        self.user = user
        self.pwd = pwd

    def read_file(self, path):
        """Читает файл через SFTP"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(self.host, self.port, self.user, self.pwd, timeout=15, look_for_keys=False)
            sftp = client.open_sftp()
            with sftp.open(path, "r") as f:
                content = f.read().decode('utf-8')
            sftp.close()
            client.close()
            return content
        except Exception as e:
            logger_win.error(f"SSH ошибка чтения {path}: {e}")
            try: client.close()
            except: pass
            return None

    def write_file(self, path, content):
        """Записывает файл через SFTP"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(self.host, self.port, self.user, self.pwd, timeout=15, look_for_keys=False)
            sftp = client.open_sftp()
            with sftp.open(path, "w") as f:
                f.write(content)
            sftp.close()
            client.close()
            return True
        except Exception as e:
            logger_win.error(f"SSH ошибка записи {path}: {e}")
            try: client.close()
            except: pass
            return False

    def execute_command(self, command):
        """Выполняет команду в консоли"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(self.host, self.port, self.user, self.pwd, timeout=15, look_for_keys=False)
            client.exec_command(command)
            client.close()
            return True
        except Exception as e:
            logger_win.error(f"SSH ошибка команды {command}: {e}")
            try: client.close()
            except: pass
            return False