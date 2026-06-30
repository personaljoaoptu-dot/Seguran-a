import paramiko
import sys

def check_errors():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected! Fetching docker logs:")
        stdin, stdout, stderr = ssh.exec_command("docker logs aegiseye-dashboard 2>&1")
        logs = stdout.read().decode('utf-8', errors='ignore')
        
        lines = logs.splitlines()
        error_lines = [line for line in lines if any(w in line.upper() for w in ["ERROR", "EXCEPTION", "FAIL", "400", "500"])]
        
        print(f"Found {len(error_lines)} matching log lines:")
        for line in error_lines[-40:]: # show last 40 lines
            print(line)
            
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_errors()
