import pg8000
import sys

def print_tables():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='aegisyear'
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tablename 
            FROM pg_catalog.pg_tables 
            WHERE schemaname = 'public';
        """)
        print("Tables in public schema:")
        tables = [row[0] for row in cursor.fetchall()]
        for t in tables:
            print(f"  {t}")
            
        for t in tables:
            cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{t}';")
            print(f"\nColumns in '{t}':")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]}")
                
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    print_tables()
