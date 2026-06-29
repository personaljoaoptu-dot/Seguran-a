import paramiko
import sys

def check_logs():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Connected! Fetching docker logs for aegiseye-dashboard:")
        stdin, stdout, stderr = ssh.exec_command("docker logs aegiseye-dashboard")
        print(stdout.read().decode('utf-8'))
        print(stderr.read().decode('utf-8'))
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_logs()
