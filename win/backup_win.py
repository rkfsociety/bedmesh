import paramiko

def create_backup_ssh(host, port, user, pwd, path):
    if not path: return False
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, int(port), user, pwd, timeout=10)
        client.exec_command(f"cp '{path}' '{path}.bak'")
        client.close()
        return True
    except: return False

def auto_backup_if_missing(host, port, user, pwd, path):
    if not path: return False
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, int(port), user, pwd, timeout=10)
        sftp = client.open_sftp()
        try:
            sftp.stat(f"{path}.bak")
        except FileNotFoundError:
            client.exec_command(f"cp '{path}' '{path}.bak'")
        sftp.close(); client.close()
        return True
    except: return False

def restore_backup_ssh(host, port, user, pwd, path):
    if not path: return False
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, int(port), user, pwd, timeout=10)
        sftp = client.open_sftp()
        try:
            sftp.stat(f"{path}.bak")
            client.exec_command(f"cp '{path}.bak' '{path}'")
            res = True
        except FileNotFoundError: res = False
        sftp.close(); client.close()
        return res
    except: return False