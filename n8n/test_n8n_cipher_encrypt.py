import paramiko
import sys

def test_cipher():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=10)
        
        print("Connected! Testing n8n Cipher encrypt/decrypt:")
        
        node_script = """
const { Cipher } = require('/usr/local/lib/node_modules/n8n/node_modules/n8n-core');
const key = process.env.N8N_ENCRYPTION_KEY;
const cipher = new Cipher(key);
const testStr = 'hello world';
try {
    const encrypted = cipher.encrypt(testStr);
    console.log('Encrypted:', encrypted);
    const decrypted = cipher.decrypt(encrypted);
    console.log('Decrypted:', decrypted);
} catch (e) {
    console.error('Error:', e.message);
}
"""
        cmd = f"docker exec -u node -e N8N_ENCRYPTION_KEY='dfb0dbc04a430ae06bcb3a0ffa662e87f2f2dac21901aa3d' n8n_app node -e \"{node_script}\""
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode('utf-8').strip())
        print(stderr.read().decode('utf-8').strip())
        
        ssh.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    test_cipher()
