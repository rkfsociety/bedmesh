import paramiko

def fetch_ssh(host, port, user, pwd, path):
    if not path or path.strip() == "": 
        return ""
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(host, int(port), user, pwd, timeout=10)
        sftp = client.open_sftp()
        try:
            with sftp.open(path, 'rb') as f:
                content = f.read().decode('utf-8', errors='ignore')
            return content
        finally:
            sftp.close() # Закрываем SFTP в любом случае
    except Exception as e:
        print(f"SSH Fetch Error: {e}")
        return ""
    finally:
        client.close() # Закрываем сессию SSH, чтобы процесс не висел

def save_ssh(host, port, user, pwd, path, content):
    if not path or path.strip() == "":
        return
        
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(host, int(port), user, pwd, timeout=10)
        sftp = client.open_sftp()
        try:
            with sftp.open(path, 'wb') as f: 
                f.write(content.encode('utf-8'))
        finally:
            sftp.close()
    except Exception as e:
        print(f"SSH Save Error: {e}")
    finally:
        client.close()