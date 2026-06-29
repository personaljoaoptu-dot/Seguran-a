import paramiko
import sys

def test_ssh(username, password):
    print(f"Testing SSH with username '{username}' and password '{password}'...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username=username, password=password, timeout=5)
        print(f"SUCCESS! Logged in as {username}!")
        
        # Run test command
        stdin, stdout, stderr = ssh.exec_command('docker ps')
        print(f"Docker containers on server:\n{stdout.read().decode('utf-8')}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

passwords = [
    "ShE67XnR4vFysNUFYfjoXaqd", # pgAdmin password
    "911@Miguel",               # n8n password
    "KtnYcxnVOGjD4thzS6tlBcW9"  # Database password
]

usernames = ["root", "ubuntu"]

success = False
for u in usernames:
    for p in passwords:
        if test_ssh(u, p):
            success = True
            break
    if success:
        break

if not success:
    print("Could not connect with standard credentials.")
    sys.exit(1)
