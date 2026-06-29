import pg8000
import paramiko
import sys

def activate_in_db():
    try:
        # 1. Update DB directly
        print("Connecting to PostgreSQL 'n8n_db' to activate workflows...")
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='n8n_db'
        )
        cursor = conn.cursor()
        
        workflow_ids = [
            '8c4ab76c-30c1-419b-a010-91a5e55209f8', # Auth
            'e4f8a6b1-cdbe-4712-a1f9-d892a01f30f5', # Register
            'f1f2f3f4-5678-4c3d-b2a1-098765432109'  # Activate
        ]
        
        for w_id in workflow_ids:
            cursor.execute('UPDATE workflow_entity SET active = true, "activeVersionId" = "versionId" WHERE id = %s;', (w_id,))
        
        conn.commit()
        print("Workflows updated to active=true in PostgreSQL!")
        
        # Verify
        cursor.execute("SELECT id, name, active FROM workflow_entity;")
        rows = cursor.fetchall()
        print("Current workflow status in DB:")
        for r in rows:
            print(f"ID: {r[0]} | Name: {r[1]} | Active: {r[2]}")
            
        cursor.close()
        conn.close()
        
        # 2. Restart n8n container
        print("\nConnecting to VPS via SSH to restart n8n container...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        stdin, stdout, stderr = ssh.exec_command("docker restart n8n_app")
        print("Restart Output:", stdout.read().decode('utf-8').strip(), stderr.read().decode('utf-8').strip())
        
        ssh.close()
        print("Done! Workflows activated and n8n restarted successfully.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    activate_in_db()
