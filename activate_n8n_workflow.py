import paramiko
import sys

def activate():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Connected! Activating AegisEye Auth Webhook workflow in n8n:")
        stdin, stdout, stderr = ssh.exec_command(
            "docker exec -u node n8n_app n8n update:workflow --active=true --id=8c4ab76c-30c1-419b-a010-91a5e55209f8"
        )
        
        stdout_str = stdout.read().decode('utf-8', errors='ignore')
        stderr_str = stderr.read().decode('utf-8', errors='ignore')
        
        if stdout_str:
            sys.stdout.buffer.write(stdout_str.encode('utf-8', errors='ignore'))
            sys.stdout.write("\n")
        if stderr_str:
            sys.stdout.buffer.write(stderr_str.encode('utf-8', errors='ignore'))
            sys.stdout.write("\n")
            
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    activate()
