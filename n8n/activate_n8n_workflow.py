import paramiko
import sys

def activate():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Activating AegisEye Auth Webhook workflow...")
        stdin1, stdout1, stderr1 = ssh.exec_command(
            "docker exec -u node n8n_app n8n update:workflow --active=true --id=8c4ab76c-30c1-419b-a010-91a5e55209f8"
        )
        stdout_str1 = stdout1.read().decode('utf-8', errors='ignore')
        stderr_str1 = stderr1.read().decode('utf-8', errors='ignore')
        if stdout_str1:
            sys.stdout.buffer.write(stdout_str1.encode('utf-8', errors='ignore'))
            sys.stdout.write("\n")
        if stderr_str1:
            sys.stdout.buffer.write(stderr_str1.encode('utf-8', errors='ignore'))
            sys.stdout.write("\n")

        print("Activating AegisEye Registration Webhook workflow...")
        stdin2, stdout2, stderr2 = ssh.exec_command(
            "docker exec -u node n8n_app n8n update:workflow --active=true --id=e4f8a6b1-cdbe-4712-a1f9-d892a01f30f5"
        )
        stdout_str2 = stdout2.read().decode('utf-8', errors='ignore')
        stderr_str2 = stderr2.read().decode('utf-8', errors='ignore')
        if stdout_str2:
            sys.stdout.buffer.write(stdout_str2.encode('utf-8', errors='ignore'))
            sys.stdout.write("\n")
        if stderr_str2:
            sys.stdout.buffer.write(stderr_str2.encode('utf-8', errors='ignore'))
            sys.stdout.write("\n")
            
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    activate()
