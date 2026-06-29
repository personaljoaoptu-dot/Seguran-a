import paramiko
import json
import sys

def deploy_smtp():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected to VPS!")
        
        # Define the credential JSON payload
        cred_payload = [
            {
                "id": "LXgw91EssOGeetUz",
                "name": "SMTP account",
                "type": "smtp",
                "data": {
                    "host": "smtp.gmail.com",
                    "port": 465,
                    "secure": True,
                    "user": "segurancasaas@gmail.com",
                    "password": "gxysvutjjekdgcrz"
                }
            }
        ]
        
        # Write payload locally to /tmp/smtp_credential.json on VPS via SFTP
        print("Writing credential JSON to VPS...")
        sftp = ssh.open_sftp()
        with sftp.open("/tmp/smtp_credential.json", "w") as f:
            f.write(json.dumps(cred_payload, indent=2))
        sftp.close()
        
        # Copy file into n8n container
        print("Copying credentials file to n8n container...")
        stdin, stdout, stderr = ssh.exec_command("docker cp /tmp/smtp_credential.json n8n_app:/tmp/smtp_credential.json")
        print("cp stdout:", stdout.read().decode('utf-8'))
        print("cp stderr:", stderr.read().decode('utf-8'))
        
        # Execute import:credentials inside n8n
        print("Importing credentials into n8n via CLI...")
        stdin, stdout, stderr = ssh.exec_command("docker exec -u node n8n_app n8n import:credentials --input=/tmp/smtp_credential.json")
        import_stdout = stdout.read().decode('utf-8')
        import_stderr = stderr.read().decode('utf-8')
        print("Import stdout:\n", import_stdout)
        print("Import stderr:\n", import_stderr)
        
        # Clean up temporary files
        ssh.exec_command("rm -f /tmp/smtp_credential.json")
        ssh.exec_command("docker exec -u root n8n_app rm -f /tmp/smtp_credential.json")
        
        ssh.close()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    deploy_smtp()
