import paramiko
import sys

def find_compose():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected! Searching for docker-compose.yml files on VPS...")
        
        # Search under /root and other common folders
        cmd = 'find /root -name "docker-compose.yml"'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print("Found in /root:\n", stdout.read().decode('utf-8').strip())
        
        cmd_global = 'find / -maxdepth 3 -name "docker-compose.yml" 2>/dev/null'
        stdin, stdout, stderr = ssh.exec_command(cmd_global)
        print("\nFound globally (up to depth 3):\n", stdout.read().decode('utf-8').strip())
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    find_compose()
