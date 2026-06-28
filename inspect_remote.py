import paramiko
import sys

def inspect():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Connected! Listing running docker containers:")
        stdin, stdout, stderr = ssh.exec_command('docker ps')
        print(stdout.read().decode('utf-8'))
        
        print("\nListing docker networks:")
        stdin, stdout, stderr = ssh.exec_command('docker network ls')
        print(stdout.read().decode('utf-8'))
        
        print("\nChecking if git/docker are installed:")
        stdin, stdout, stderr = ssh.exec_command('docker --version && git --version')
        print(stdout.read().decode('utf-8'))
        
        ssh.close()
    except Exception as e:
        print(f"Error inspecting remote server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    inspect()
