import paramiko
import sys

def inspect_env():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected! Listing files in /root (including hidden ones):")
        stdin, stdout, stderr = ssh.exec_command("ls -la /root")
        print(stdout.read().decode('utf-8', errors='ignore'))
        
        print("\nListing files in /opt/infrastructure:")
        stdin, stdout, stderr = ssh.exec_command("ls -la /opt/infrastructure")
        print(stdout.read().decode('utf-8', errors='ignore'))
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    inspect_env()
