import paramiko

TEMP_FILE_NAME = "temp_download.cfg"

def download_cfg_via_ssh(ip: str, port: int = 2222, username: str = 'root',
                         password: str = 'rockchip', remote_path: str = '/userdata/app/gk/printer_mutable.cfg') -> str:
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, port=port, username=username, password=password, timeout=10)
        
        sftp = ssh.open_sftp()
        sftp.get(remote_path, TEMP_FILE_NAME)
        sftp.close()
        ssh.close()
        return TEMP_FILE_NAME
    except Exception as e:
        print(f"SSH Error: {e}")
        return None