import pg8000
import sys
import json

def check_exec_data():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='n8n_db'
        )
        cursor = conn.cursor()
        
        # Query columns of execution_data
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'execution_data';")
        cols = [c[0] for c in cursor.fetchall()]
        print("execution_data columns:", cols)
        
        # Query execution data for execution ID 12
        cursor.execute("SELECT * FROM execution_data WHERE \"executionId\" = '12';")
        row = cursor.fetchone()
        if row:
            for c, val in zip(cols, row):
                print(f"\nColumn '{c}':")
                val_str = str(val)
                if len(val_str) > 2000:
                    print(val_str[:2000] + " ... TRUNCATED")
                else:
                    print(val_str)
        else:
            print("No execution data found for executionId = '1'")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_exec_data()
