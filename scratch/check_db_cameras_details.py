import pg8000

DB_HOST = "144.91.121.55"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASS = "KtnYcxnVOGjD4thzS6tlBcW9"
DB_NAME = "aegisyear"

try:
    conn = pg8000.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    cursor = conn.cursor()
    
    # Query all cameras
    cursor.execute("SELECT id, name, rtsp, tenant_id FROM cameras")
    print("--- ALL CAMERAS IN DB ---")
    for row in cursor.fetchall():
        print(f"ID: {row[0]} | Name: {row[1]} | RTSP: {row[2]} | Tenant: {row[3]}")
        
    cursor.close()
    conn.close()
except Exception as e:
    print("Error:", e)
