import paramiko

def check_db():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        # Run psql inside postgres_db to query workflows
        cmd = "docker exec -t postgres_db psql -U postgres -d n8n_db -c 'SELECT id, name, active FROM workflow_entity;'"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print("--- Workflows in Postgres ---")
        print(stdout.read().decode('utf-8', errors='ignore'))
        print(stderr.read().decode('utf-8', errors='ignore'))

        ssh.close()
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    check_db()
