import paramiko

def test_conn_inside():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('144.91.121.55', username='root', password='2026@Miguel@2026', timeout=15)
        
        # Test connection to public IP
        cmd1 = "docker exec aegiseye-dashboard python -c \"import pg8000; conn=pg8000.connect(host='144.91.121.55', port=5432, user='postgres', password='KtnYcxnVOGjD4thzS6tlBcW9', database='aegisyear'); print('Conn public IP OK')\""
        stdin, stdout, stderr = ssh.exec_command(cmd1)
        print("Test 1 (Public IP):")
        print("stdout:", stdout.read().decode('utf-8'))
        print("stderr:", stderr.read().decode('utf-8'))
        
        # Test connection to postgres_db container service name
        cmd2 = "docker exec aegiseye-dashboard python -c \"import pg8000; conn=pg8000.connect(host='postgres_db', port=5432, user='postgres', password='KtnYcxnVOGjD4thzS6tlBcW9', database='aegisyear'); print('Conn service name OK')\""
        stdin, stdout, stderr = ssh.exec_command(cmd2)
        print("Test 2 (Service Name):")
        print("stdout:", stdout.read().decode('utf-8'))
        print("stderr:", stderr.read().decode('utf-8'))

        ssh.close()
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    test_conn_inside()
