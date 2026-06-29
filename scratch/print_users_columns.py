import pg8000
import sys

def print_columns():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='postgres'
        )
        cursor = conn.cursor()
        
        # Check users columns
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users';")
        print("Columns in 'users':")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    print_columns()
