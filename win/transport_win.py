import paramiko

def fetch_ssh(host, port, user, pwd, path):
    if not path or path.strip() == "": return ""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, int(port), user, pwd, timeout=10)
    sftp = client.open_sftp()
    with sftp.open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    sftp.close(); client.close()
    return content

def save_ssh(host, port, user, pwd, path, content):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, int(port), user, pwd, timeout=10)
    sftp = client.open_sftp()
    with sftp.open(path, 'wb') as f: 
        f.write(content.encode('utf-8'))
    sftp.close(); client.close()