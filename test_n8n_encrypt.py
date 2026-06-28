import paramiko
import sys

def test():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Connected! Testing n8n internal modules:")
        
        # Test 1: Check n8n-core exports
        cmd1 = "docker exec -u node n8n_app node -e \"try { const core = require('n8n-core'); console.log('n8n-core keys:', Object.keys(core)); } catch(e) { console.error(e.message); }\""
        stdin, stdout, stderr = ssh.exec_command(cmd1)
        print("Test 1:", stdout.read().decode('utf-8').strip(), stderr.read().decode('utf-8').strip())
        
        # Test 2: Check n8n-workflow exports
        cmd2 = "docker exec -u node n8n_app node -e \"try { const wf = require('n8n-workflow'); console.log('n8n-workflow keys:', Object.keys(wf)); } catch(e) { console.error(e.message); }\""
        stdin, stdout, stderr = ssh.exec_command(cmd2)
        print("Test 2:", stdout.read().decode('utf-8').strip(), stderr.read().decode('utf-8').strip())
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    test()
