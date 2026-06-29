import paramiko
import sys

def curl_directly():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected! Curling n8n directly...")
        
        cmd1 = 'curl -i "http://127.0.0.1:5678/webhook/f1f2f3f4-5678-4c3d-b2a1-098765432109/webhook%20verify/verify-token?token=8a118c95-5bcf-4959-87c4-e39a29fe86c8"'
        stdin, stdout, stderr = ssh.exec_command(cmd1)
        print("Curl %20:\n", stdout.read().decode('utf-8', errors='ignore'))
        
        cmd2 = 'curl -i "http://127.0.0.1:5678/webhook/f1f2f3f4-5678-4c3d-b2a1-098765432109/webhook%2520verify/verify-token?token=8a118c95-5bcf-4959-87c4-e39a29fe86c8"'
        stdin, stdout, stderr = ssh.exec_command(cmd2)
        print("\nCurl %2520:\n", stdout.read().decode('utf-8', errors='ignore'))
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    curl_directly()
