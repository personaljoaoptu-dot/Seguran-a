import pg8000
import sys

def check_webhooks():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='n8n_db'
        )
        cursor = conn.cursor()
        
        # Get columns of webhook_entity
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'webhook_entity';")
        cols = [c[0] for c in cursor.fetchall()]
        print("webhook_entity columns:", cols)
        
        # Query all active webhooks
        cursor.execute("SELECT * FROM webhook_entity;")
        rows = cursor.fetchall()
        print("\nAll Webhooks in DB:")
        for r in rows:
            print(dict(zip(cols, r)))
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_webhooks()
