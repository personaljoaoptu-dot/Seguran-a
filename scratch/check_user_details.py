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
    
    # Check users table
    cursor.execute("SELECT id, tenant_id, name, email FROM users")
    print("--- USERS TABLE ---")
    for row in cursor.fetchall():
        print(f"ID: {row[0]} | TenantID: {row[1]} | Name: {row[2]} | Email: {row[3]}")
        
    # Check usuarios table
    cursor.execute("SELECT id, nome, email FROM usuarios WHERE email = 'personal.joaoptu@gmail.com'")
    print("\n--- USUARIOS TABLE ---")
    row = cursor.fetchone()
    if row:
        print(f"ID: {row[0]} | Name: {row[1]} | Email: {row[2]}")
    else:
        print("Not found in 'usuarios'")
        
    cursor.close()
    conn.close()
except Exception as e:
    print("Error:", e)
