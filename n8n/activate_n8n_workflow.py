import paramiko
import sys

def activate():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        workflow_ids = [
            "8c4ab76c-30c1-419b-a010-91a5e55209f8", # Auth
            "e4f8a6b1-cdbe-4712-a1f9-d892a01f30f5", # Registration
            "f1f2f3f4-5678-4c3d-b2a1-098765432109", # Activation
            "9c8d7e6f-5a4b-3c2d-1e0f-9876543210fe", # Camera Config
            "e5f6a7b8-cdbe-4712-a1f9-d892a01f30f6"  # Alerts
        ]
        
        for w_id in workflow_ids:
            print(f"Activating workflow {w_id}...")
            stdin, stdout, stderr = ssh.exec_command(
                f"docker exec -u node n8n_app n8n update:workflow --active=true --id={w_id}"
            )
            stdout_str = stdout.read().decode('utf-8', errors='ignore')
            stderr_str = stderr.read().decode('utf-8', errors='ignore')
            if stdout_str:
                sys.stdout.buffer.write(stdout_str.encode('utf-8'))
                sys.stdout.write("\n")
            if stderr_str:
                sys.stdout.buffer.write(stderr_str.encode('utf-8'))
                sys.stdout.write("\n")
            
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    activate()
