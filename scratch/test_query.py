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
    
    tenant_id = '65244ad5-47c7-4905-89c9-0efad0e9d7b6'
    print("Testing type of tenant_id query parameter:")
    
    # 1. As string
    try:
        cursor.execute("SELECT id, name FROM cameras WHERE tenant_id = %s", (tenant_id,))
        print("Query as string succeeded. Results:", cursor.fetchall())
    except Exception as e:
        print("Query as string failed:", e)
        
    conn.rollback()
    
    # 2. Query other tables
    try:
        cursor.execute("SELECT id, name FROM users WHERE tenant_id = %s", (tenant_id,))
        print("Users query as string succeeded. Results:", cursor.fetchall())
    except Exception as e:
        print("Users query failed:", e)

    cursor.close()
    conn.close()
except Exception as e:
    print("General error:", e)
