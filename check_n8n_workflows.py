import paramiko
import sys

def check():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Connected! Exporting existing workflows from n8n:")
        stdin, stdout, stderr = ssh.exec_command("docker exec -u node n8n_app n8n export:workflow --all")
        print(stdout.read().decode('utf-8'))
        print(stderr.read().decode('utf-8'))
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check()
