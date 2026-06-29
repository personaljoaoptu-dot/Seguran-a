import paramiko
import sys

def inspect_schema():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected! Exporting existing credentials to inspect schema...")
        ssh.exec_command("docker exec -u node n8n_app n8n export:credentials --output=/tmp/credentials_export.json")
        
        stdin, stdout, stderr = ssh.exec_command("docker exec -u root n8n_app cat /tmp/credentials_export.json")
        export_content = stdout.read().decode('utf-8')
        print("Exported JSON:\n", export_content)
        
        ssh.exec_command("docker exec -u root n8n_app rm -f /tmp/credentials_export.json")
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    inspect_schema()
