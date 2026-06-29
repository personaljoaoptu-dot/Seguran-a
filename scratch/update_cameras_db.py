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
    
    # Let's find cameras with 'eagiseye' in the RTSP URL
    cursor.execute("SELECT id, name, rtsp FROM cameras WHERE rtsp LIKE '%eagiseye%'")
    rows = cursor.fetchall()
    
    if not rows:
        print("No cameras with 'eagiseye' found in the database.")
    else:
        print("Found cameras with 'eagiseye':")
        for row in rows:
            cam_id, name, rtsp = row
            new_rtsp = rtsp.replace("eagiseye", "aegiseye")
            print(f"Updating ID: {cam_id} | Name: {name}")
            print(f"  Old RTSP: {rtsp}")
            print(f"  New RTSP: {new_rtsp}")
            
            cursor.execute("UPDATE cameras SET rtsp = %s WHERE id = %s", (new_rtsp, cam_id))
        
        conn.commit()
        print("\nUpdate completed and committed successfully!")
        
    cursor.close()
    conn.close()
except Exception as e:
    print("Error:", e)
