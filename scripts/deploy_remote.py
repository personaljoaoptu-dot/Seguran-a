import paramiko
import os
import sys

def deploy():
    files_to_upload = [
        "frontend/index.html",
        "frontend/login.html",
        "frontend/activate.html",
        "frontend/style.css",
        "frontend/app.js",
        "server.py",
        "Dockerfile",
        "docker-compose.yml",
        "n8n/aegiseye_auth_workflow.json",
        "n8n/n8n_registration_workflow.json",
        "n8n/n8n_activation_workflow.json",
        "n8n/n8n_camera_config_workflow.json",
        "n8n/n8n_alerts_workflow.json",
        "import_cameras.py",
        "cameras.json"
    ]
    
    remote_dir = "/root/aegiseye-dashboard"
    
    try:
        # 1. Establish SSH connection
        print("Connecting to Contabo remote server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        print("SSH Connected successfully!")
        
        # Create remote directories
        print("Creating remote directories...")
        ssh.exec_command(f"mkdir -p {remote_dir}/frontend {remote_dir}/n8n")
        
        # 2. Establish SFTP connection
        print("Starting SFTP upload...")
        sftp = ssh.open_sftp()
        
        local_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(local_dir)
        
        for f in files_to_upload:
            local_path = os.path.join(project_root, f)
            remote_path = os.path.join(remote_dir, f).replace("\\", "/")
            print(f"Uploading {f} -> {remote_path}...")
            sftp.put(local_path, remote_path)
            
        sftp.close()
        print("SFTP Upload completed successfully!")
        
        # 3. Docker Compose build & deploy
        print("\nBuilding and deploying AegisEye Dashboard Docker container...")
        commands = [
            f"cd {remote_dir} && docker compose down --remove-orphans",
            f"cd {remote_dir} && docker compose build",
            f"cd {remote_dir} && docker compose up -d"
        ]
        
        for cmd in commands:
            print(f"Executing: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            print(f"Exit status: {exit_status}")
            stdout_str = stdout.read().decode('utf-8', errors='ignore')
            stderr_str = stderr.read().decode('utf-8', errors='ignore')
            if stdout_str:
                sys.stdout.buffer.write(stdout_str.encode('utf-8', errors='ignore'))
                sys.stdout.write("\n")
            if stderr_str:
                sys.stdout.buffer.write(stderr_str.encode('utf-8', errors='ignore'))
                sys.stdout.write("\n")
                
        # 4. Integrate n8n workflows
        print("\nIntegrating DDL/Authentication/Registration workflows in n8n container...")
        n8n_cmds = [
            f"docker cp {remote_dir}/n8n/aegiseye_auth_workflow.json n8n_app:/tmp/aegiseye_auth_workflow.json",
            "docker exec -u node n8n_app n8n import:workflow --input=/tmp/aegiseye_auth_workflow.json",
            "docker exec -u root n8n_app rm -f /tmp/aegiseye_auth_workflow.json",
            f"docker cp {remote_dir}/n8n/n8n_registration_workflow.json n8n_app:/tmp/n8n_registration_workflow.json",
            "docker exec -u node n8n_app n8n import:workflow --input=/tmp/n8n_registration_workflow.json",
            "docker exec -u root n8n_app rm -f /tmp/n8n_registration_workflow.json",
            f"docker cp {remote_dir}/n8n/n8n_activation_workflow.json n8n_app:/tmp/n8n_activation_workflow.json",
            "docker exec -u node n8n_app n8n import:workflow --input=/tmp/n8n_activation_workflow.json",
            "docker exec -u root n8n_app rm -f /tmp/n8n_activation_workflow.json",
            f"docker cp {remote_dir}/n8n/n8n_camera_config_workflow.json n8n_app:/tmp/n8n_camera_config_workflow.json",
            "docker exec -u node n8n_app n8n import:workflow --input=/tmp/n8n_camera_config_workflow.json",
            "docker exec -u root n8n_app rm -f /tmp/n8n_camera_config_workflow.json",
            f"docker cp {remote_dir}/n8n/n8n_alerts_workflow.json n8n_app:/tmp/n8n_alerts_workflow.json",
            "docker exec -u node n8n_app n8n import:workflow --input=/tmp/n8n_alerts_workflow.json",
            "docker exec -u root n8n_app rm -f /tmp/n8n_alerts_workflow.json",
            "docker exec -u node n8n_app n8n publish:workflow --id=8c4ab76c-30c1-419b-a010-91a5e55209f8",
            "docker exec -u node n8n_app n8n publish:workflow --id=e4f8a6b1-cdbe-4712-a1f9-d892a01f30f5",
            "docker exec -u node n8n_app n8n publish:workflow --id=f1f2f3f4-5678-4c3d-b2a1-098765432109",
            "docker exec -u node n8n_app n8n publish:workflow --id=9c8d7e6f-5a4b-3c2d-1e0f-9876543210fe",
            "docker exec -u node n8n_app n8n publish:workflow --id=e5f6a7b8-cdbe-4712-a1f9-d892a01f30f6",
            "docker exec -u root postgres_db psql -U postgres -d n8n_db -c \"UPDATE workflow_entity SET active = true WHERE id IN ('8c4ab76c-30c1-419b-a010-91a5e55209f8', 'e4f8a6b1-cdbe-4712-a1f9-d892a01f30f5', 'f1f2f3f4-5678-4c3d-b2a1-098765432109', '9c8d7e6f-5a4b-3c2d-1e0f-9876543210fe', 'e5f6a7b8-cdbe-4712-a1f9-d892a01f30f6');\"",
            "docker restart n8n_app"
        ]
        
        for cmd in n8n_cmds:
            print(f"Executing: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            print(f"Exit status: {exit_status}")
            stdout_str = stdout.read().decode('utf-8', errors='ignore')
            stderr_str = stderr.read().decode('utf-8', errors='ignore')
            if stdout_str:
                sys.stdout.buffer.write(stdout_str.encode('utf-8', errors='ignore'))
                sys.stdout.write("\n")
            if stderr_str:
                sys.stdout.buffer.write(stderr_str.encode('utf-8', errors='ignore'))
                sys.stdout.write("\n")
                
        # Check running containers
        print("\nVerifying running containers:")
        stdin, stdout, stderr = ssh.exec_command("docker ps")
        stdout_str = stdout.read().decode('utf-8', errors='ignore')
        sys.stdout.buffer.write(stdout_str.encode('utf-8', errors='ignore'))
        sys.stdout.write("\n")
        
        ssh.close()
        print("Deployment completed successfully!")
    except Exception as e:
        print(f"Error during deployment: {e}")
        sys.exit(1)

if __name__ == '__main__':
    deploy()
