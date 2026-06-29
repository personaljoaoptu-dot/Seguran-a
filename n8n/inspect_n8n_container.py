import paramiko
import sys
import json

def inspect():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Connected! Inspecting n8n_app container:")
        stdin, stdout, stderr = ssh.exec_command("docker inspect n8n_app")
        data = json.loads(stdout.read().decode('utf-8'))
        
        env = data[0]['Config']['Env']
        print("n8n_app Env Vars:")
        for item in env:
            print(f"  {item}")
                
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    inspect()
