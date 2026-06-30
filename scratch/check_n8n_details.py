import paramiko
import sys
import json

def check():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected! Listing active n8n workflows and webhooks...")
        
        # We can query postgres_db inside the n8n_db database!
        # n8n stores workflows in the workflow_entity table.
        # Let's inspect the active workflows.
        cmd = "docker exec -u root postgres_db psql -U postgres -d n8n_db -c \"SELECT id, name, active FROM workflow_entity;\""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print("Active workflows:")
        print(stdout.read().decode('utf-8'))
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check()
