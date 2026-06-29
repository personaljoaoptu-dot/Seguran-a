import paramiko
import sys

def safe_print(prefix, out_bytes, err_bytes):
    out_str = out_bytes.decode('utf-8', errors='replace').strip()
    err_str = err_bytes.decode('utf-8', errors='replace').strip()
    encoding = sys.stdout.encoding or 'utf-8'
    out_safe = out_str.encode(encoding, errors='replace').decode(encoding)
    err_safe = err_str.encode(encoding, errors='replace').decode(encoding)
    print(f"{prefix} | OUT: {out_safe} | ERR: {err_safe}")

def fix_build():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected to VPS! Pruning docker builder cache...")
        
        # 1. Prune builder cache
        stdin, stdout, stderr = ssh.exec_command("docker builder prune -f")
        safe_print("Builder prune", stdout.read(), stderr.read())
        
        # 2. Build without cache
        print("Rebuilding dashboard container without cache...")
        stdin, stdout, stderr = ssh.exec_command("cd /root/aegiseye-dashboard && docker compose build --no-cache")
        exit_status = stdout.channel.recv_exit_status()
        print(f"Build Exit status: {exit_status}")
        safe_print("Build output", stdout.read(), stderr.read())
        
        # 3. Bring compose up
        print("Starting container...")
        stdin, stdout, stderr = ssh.exec_command("cd /root/aegiseye-dashboard && docker compose up -d")
        exit_status = stdout.channel.recv_exit_status()
        print(f"Compose Up Exit status: {exit_status}")
        safe_print("Up output", stdout.read(), stderr.read())
        
        # 4. Check running containers
        stdin, stdout, stderr = ssh.exec_command("docker ps")
        print("\nRunning Containers:\n", stdout.read().decode('utf-8', errors='ignore'))
        
        ssh.close()
        print("Cache fix and rebuild completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    fix_build()
