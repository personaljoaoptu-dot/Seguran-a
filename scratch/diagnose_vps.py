import paramiko

def run_diagnostics():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print("Connecting to Contabo remote server...")
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        print("SSH Connected successfully!\n")
        
        commands = {
            "Docker Containers Status": "docker ps -a",
            "Dashboard Container Environment": "docker exec aegiseye-dashboard env",
            "Dashboard Container Logs": "docker logs --tail 25 aegiseye-dashboard",
            "Network Test from Dashboard to n8n": "docker exec aegiseye-dashboard python -c \"import urllib.request; print(urllib.request.urlopen('http://n8n_app:5678/healthz').read().decode())\"",
            "n8n active workflows": "docker exec -u node n8n_app n8n list:workflow"
        }
        
        for desc, cmd in commands.items():
            print("=" * 60)
            print(f" DIAGNOSTIC: {desc}")
            print(f" Command: {cmd}")
            print("=" * 60)
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            print(f"Exit status: {exit_status}")
            stdout_str = stdout.read().decode('utf-8', errors='ignore')
            stderr_str = stderr.read().decode('utf-8', errors='ignore')
            if stdout_str:
                print("--- STDOUT ---")
                print(stdout_str)
            if stderr_str:
                print("--- STDERR ---")
                print(stderr_str)
            print("\n")
            
        ssh.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == '__main__':
    run_diagnostics()
