import paramiko
import sys

def check_webhooks():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected! Listing active webhooks from n8n:")
        
        stdin, stdout, stderr = ssh.exec_command("docker exec -u node n8n_app n8n webhook:list")
        webhook_list = stdout.read().decode('utf-8', errors='ignore')
        webhook_err = stderr.read().decode('utf-8', errors='ignore')
        
        print("Webhook list output:\n", webhook_list)
        print("Webhook list error:\n", webhook_err)
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_webhooks()
