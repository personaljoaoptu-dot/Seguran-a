import paramiko
import sys

def check_cli():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected! Checking n8n CLI help for importing credentials...")
        stdin, stdout, stderr = ssh.exec_command("docker exec -u node n8n_app n8n --help")
        print("n8n CLI Help:\n", stdout.read().decode('utf-8'))
        
        stdin, stdout, stderr = ssh.exec_command("docker exec -u node n8n_app n8n import:credentials --help")
        print("import:credentials Help:\n", stdout.read().decode('utf-8'))
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_cli()
