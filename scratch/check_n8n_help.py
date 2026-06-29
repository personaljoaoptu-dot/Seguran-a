import paramiko

def check_help():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        stdin, stdout, stderr = ssh.exec_command("docker exec -u node n8n_app n8n --help")
        print("--- n8n help ---")
        print(stdout.read().decode('utf-8'))
        print(stderr.read().decode('utf-8'))
        
        stdin, stdout, stderr = ssh.exec_command("docker exec -u node n8n_app n8n import:workflow --help")
        print("--- n8n import:workflow help ---")
        print(stdout.read().decode('utf-8'))

        ssh.close()
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    check_help()
