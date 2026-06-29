import pg8000
import av
import socket
from urllib.parse import urlparse

DB_HOST = "144.91.121.55"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASS = "KtnYcxnVOGjD4thzS6tlBcW9"
DB_NAME = "aegisyear"

def check_socket(rtsp_url):
    try:
        parsed = urlparse(rtsp_url)
        host = parsed.hostname
        port = parsed.port or 554
        if not host:
            return False
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        res = s.connect_ex((host, port))
        s.close()
        return res == 0
    except Exception:
        return False

try:
    conn = pg8000.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    cursor = conn.cursor()
    
    # Query the cameras for Tenant 65244ad5-47c7-4905-89c9-0efad0e9d7b6
    cursor.execute("SELECT name, rtsp FROM cameras WHERE tenant_id = '65244ad5-47c7-4905-89c9-0efad0e9d7b6'")
    rows = cursor.fetchall()
    
    print("--- TESTING TENANT CAMERAS WITH RESILIENCE ---")
    for name, rtsp in rows:
        print(f"\nCamera: {name}")
        print(f"RTSP: {rtsp}")
        
        # Pre-check port 554
        online = check_socket(rtsp)
        print(f"  TCP Port 554 open: {online}")
        
        if online:
            # Test connection using PyAV
            try:
                container = av.open(rtsp, options={
                    'rtsp_transport': 'udp',
                    'stimeout': '3000000' # 3s timeout
                })
                print("  [SUCCESS] Connected to camera successfully!")
                container.close()
            except Exception as e:
                print(f"  [FAILED] Connection failed: {e}")
        else:
            print("  [SKIPPED] skipping RTSP connection test (port closed / offline)")
            
    cursor.close()
    conn.close()
except Exception as e:
    print("Error:", e)
