import paramiko
import sys

def check_smtp():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected! Checking port 25 (SMTP) status on VPS...")
        
        # Check active listening ports
        stdin, stdout, stderr = ssh.exec_command("ss -tlnp | grep -E ':25 '")
        ss_out = stdout.read().decode('utf-8').strip()
        print("SS output:", ss_out)
        
        # Check if postfix is active
        stdin, stdout, stderr = ssh.exec_command("systemctl status postfix 2>/dev/null || systemctl status sendmail 2>/dev/null")
        status_out = stdout.read().decode('utf-8').strip()
        print("SMTP service status:", status_out)
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_smtp()
