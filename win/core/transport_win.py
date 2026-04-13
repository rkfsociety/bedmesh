import paramiko
from utils import logger_win

def fetch_ssh(host, port, user, pwd, path):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    logger_win.info(f"--- SSH START: {host}:{port} ---")
    
    try:
        # timeout=5 не даст программе висеть дольше 5 секунд при плохом соединении
        logger_win.info("Подключение к серверу...")
        client.connect(
            hostname=host, 
            port=int(port), 
            username=user, 
            password=pwd, 
            timeout=5, 
            auth_timeout=5
        )
        
        logger_win.info(f"Запрос файла по пути: {path}")
        sftp = client.open_sftp()
        
        with sftp.open(path, "r") as f:
            content = f.read().decode('utf-8', errors='ignore')
        
        sftp.close()
        logger_win.info(f"Данные получены успешно ({len(content)} байт)")
        return content

    except paramiko.AuthenticationException:
        logger_win.error("Ошибка: Неверный логин или пароль")
    except paramiko.SSHException as e:
        logger_win.error(f"Ошибка протокола SSH: {e}")
    except Exception as e:
        logger_win.error(f"Ошибка соединения: {str(e)}")
    finally:
        client.close()
        logger_win.info("--- SSH END ---")
            
    return ""