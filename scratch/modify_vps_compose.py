import paramiko
import sys

def modify_compose():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected! Reading /opt/infrastructure/docker-compose.yml...")
        sftp = ssh.open_sftp()
        filepath = "/opt/infrastructure/docker-compose.yml"
        
        with sftp.open(filepath, 'r') as file:
            content = file.read().decode('utf-8')
            
        target = "      - N8N_ENCRYPTION_KEY='dfb0dbc04a430ae06bcb3a0ffa662e87f2f2dac21901aa3d'"
        replacement = target + "\n      - N8N_SECURE_COOKIE=false"
        
        if target not in content:
            print("ERROR: Encryption key block not found in compose file.")
            sys.exit(1)
            
        if "N8N_SECURE_COOKIE=false" in content:
            print("N8N_SECURE_COOKIE is already set to false in compose file.")
        else:
            new_content = content.replace(target, replacement)
            with sftp.open(filepath, 'w') as file:
                file.write(new_content.encode('utf-8'))
            print("Compose file successfully updated with N8N_SECURE_COOKIE=false!")
            
        sftp.close()
        
        # Restart the docker compose services
        print("\nRestarting infrastructure compose services on VPS...")
        stdin, stdout, stderr = ssh.exec_command("cd /opt/infrastructure && docker compose down && docker compose up -d")
        print("Stdout:\n", stdout.read().decode('utf-8'))
        print("Stderr:\n", stderr.read().decode('utf-8'))
        
        ssh.close()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    modify_compose()
