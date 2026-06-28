import paramiko
import sys

def test_paths():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Connected! Testing absolute require paths inside container:")
        
        # Test require('n8n-core') using the node_modules directory under n8n
        cmd = "docker exec -u node n8n_app node -e \"try { const core = require('/usr/local/lib/node_modules/n8n/node_modules/n8n-core'); console.log('Success! Keys:', Object.keys(core)); } catch(e) { console.error('Failed:', e.message); }\""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode('utf-8').strip())
        print(stderr.read().decode('utf-8').strip())
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    test_paths()
