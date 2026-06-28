import paramiko
import sys

def inspect_source():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Connected! Inspecting n8n Cipher source:")
        cmd = "docker exec -u node n8n_app node -e \"const { Cipher } = require('/usr/local/lib/node_modules/n8n/node_modules/n8n-core'); console.log(Cipher.toString());\""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode('utf-8').strip())
        print(stderr.read().decode('utf-8').strip())
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    inspect_source()
