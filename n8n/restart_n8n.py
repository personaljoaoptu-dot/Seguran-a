import paramiko
import sys

def restart():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Connected! Restarting n8n container...")
        stdin, stdout, stderr = ssh.exec_command("docker restart n8n_app")
        print(stdout.read().decode('utf-8'))
        print(stderr.read().decode('utf-8'))
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    restart()
