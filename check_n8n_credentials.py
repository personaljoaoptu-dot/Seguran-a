import pg8000
import sys

def check_creds():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='n8n_db'
        )
        cursor = conn.cursor()
        
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'credentials_entity';")
        cols = [c[0] for c in cursor.fetchall()]
        print("credentials_entity columns:", cols)
        
        cursor.execute("SELECT id, name, type FROM credentials_entity;")
        rows = cursor.fetchall()
        print("\nStored Credentials:")
        for r in rows:
            print(f"ID: {r[0]}, Name: {r[1]}, Type: {r[2]}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_creds()
