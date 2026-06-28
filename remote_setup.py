import paramiko
import sys

def safe_print(prefix, out_bytes, err_bytes):
    out_str = out_bytes.decode('utf-8', errors='replace').strip()
    err_str = err_bytes.decode('utf-8', errors='replace').strip()
    encoding = sys.stdout.encoding or 'utf-8'
    out_safe = out_str.encode(encoding, errors='replace').decode(encoding)
    err_safe = err_str.encode(encoding, errors='replace').decode(encoding)
    print(f"{prefix} | OUT: {out_safe} | ERR: {err_safe}")

def setup():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected to VPS! Activating workflows...")
        
        # 1. Activate Auth Workflow
        stdin, stdout, stderr = ssh.exec_command(
            "docker exec -u node n8n_app n8n update:workflow --active=true --id=8c4ab76c-30c1-419b-a010-91a5e55209f8"
        )
        safe_print("Auth activation", stdout.read(), stderr.read())
        
        # 2. Activate Registration Workflow
        stdin, stdout, stderr = ssh.exec_command(
            "docker exec -u node n8n_app n8n update:workflow --active=true --id=e4f8a6b1-cdbe-4712-a1f9-d892a01f30f5"
        )
        safe_print("Registration activation", stdout.read(), stderr.read())
        
        # 3. Restart n8n
        print("Restarting n8n container...")
        stdin, stdout, stderr = ssh.exec_command("docker restart n8n_app")
        safe_print("Restart output", stdout.read(), stderr.read())
        
        ssh.close()
        print("Setup completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    setup()

