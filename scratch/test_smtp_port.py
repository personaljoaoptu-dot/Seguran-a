import paramiko
import sys

def test_ports():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        print("Connected to VPS! Testing connection to smtp.gmail.com...")
        
        # Test port 465
        cmd_465 = "nc -zv -w5 smtp.gmail.com 465"
        stdin, stdout, stderr = ssh.exec_command(cmd_465)
        print("Port 465 connection:")
        print("Stdout:", stdout.read().decode('utf-8'))
        print("Stderr:", stderr.read().decode('utf-8'))
        
        # Test port 587
        cmd_587 = "nc -zv -w5 smtp.gmail.com 587"
        stdin, stdout, stderr = ssh.exec_command(cmd_587)
        print("Port 587 connection:")
        print("Stdout:", stdout.read().decode('utf-8'))
        print("Stderr:", stderr.read().decode('utf-8'))
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    test_ports()
