import paramiko

def check_login_errors():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        # Look for [AUTH] or [ERROR] logs
        stdin, stdout, stderr = ssh.exec_command("docker logs aegiseye-dashboard 2>&1 | grep -E '\\[AUTH\\]|\\[ERROR\\]'")
        print("--- AUTH & ERROR LOGS ---")
        print(stdout.read().decode('utf-8', errors='ignore'))
        
        # Look at the last 20 lines of the logs
        stdin, stdout, stderr = ssh.exec_command("docker logs aegiseye-dashboard 2>&1 | tail -n 25")
        print("--- LAST 25 LINES ---")
        print(stdout.read().decode('utf-8', errors='ignore'))

        ssh.close()
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    check_login_errors()
