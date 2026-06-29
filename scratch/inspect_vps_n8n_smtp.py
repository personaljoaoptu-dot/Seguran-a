import paramiko
import sys

def inspect_smtp():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected to VPS! Finding SMTP credential source files inside n8n_app...")
        cmd = "docker exec -u root n8n_app find /usr/local/lib/node_modules/n8n -name \"*Smtp*\""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        files = stdout.read().decode('utf-8').strip().split('\n')
        print("SMTP Files found:")
        for f in files:
            print(f"  {f}")
            
        # Cat the credential file
        cred_file = [f for f in files if "credentials" in f.lower() and f.endswith(".js")]
        if cred_file:
            print(f"\nCating {cred_file[0]}...")
            stdin, stdout, stderr = ssh.exec_command(f"docker exec -u root n8n_app cat {cred_file[0]}")
            print(stdout.read().decode('utf-8'))
            
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    inspect_smtp()
