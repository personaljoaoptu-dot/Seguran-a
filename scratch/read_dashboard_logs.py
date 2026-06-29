import paramiko
import sys

def read_logs():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected! Fetching docker logs for aegiseye-dashboard (last 30 lines):")
        stdin, stdout, stderr = ssh.exec_command("docker logs --tail 30 aegiseye-dashboard")
        print("Dashboard Logs:\n", stdout.read().decode('utf-8', errors='ignore'))
        print("Dashboard Errors:\n", stderr.read().decode('utf-8', errors='ignore'))
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    read_logs()
