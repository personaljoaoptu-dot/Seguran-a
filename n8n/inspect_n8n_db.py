import pg8000
import sys

def inspect_n8n():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='n8n_db'
        )
        cursor = conn.cursor()
        
        # List tables in n8n_db
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [t[0] for t in cursor.fetchall()]
        print("n8n_db tables:", tables)
        
        # Check webhook related tables (like webhook_active_process_key or similar)
        webhook_table = None
        for t in tables:
            if 'webhook' in t:
                webhook_table = t
                print(f"Found webhook table: {webhook_table}")
                
        if webhook_table:
            # Describe column names
            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{webhook_table}';")
            cols = [c[0] for c in cursor.fetchall()]
            print(f"Columns in {webhook_table}: {cols}")
            
            # Select all rows
            cursor.execute(f"SELECT * FROM {webhook_table};")
            rows = cursor.fetchall()
            print(f"Rows in {webhook_table}:")
            for r in rows:
                print("  ", r)
                
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    inspect_n8n()
