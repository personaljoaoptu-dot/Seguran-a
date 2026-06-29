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
    
    # Query all alerts
    cursor.execute("SELECT id, camera_name, severity, title, confidence, created_at FROM public.alertas ORDER BY created_at DESC")
    print("--- ALERTS TABLE ENTRIES ---")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]} | Camera: {row[1]} | Severity: {row[2]} | Title: {row[3]} | Confidence: {row[4]} | Created At: {row[5]}")
        
    cursor.close()
    conn.close()
except Exception as e:
    print("Error:", e)
