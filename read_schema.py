import pg8000
import sys

def read_db_schema():
    try:
        # Establish connection to the remote PostgreSQL database
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='aegisyear'
        )
        
        cursor = conn.cursor()
        
        # Query to list tables in public schema
        print("--- Tables in public schema ---")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        tables = cursor.fetchall()
        for t in tables:
            print(f"Table: {t[0]}")
            
        print("\n--- Column descriptions ---")
        for t in tables:
            table_name = t[0]
            print(f"\nTable: {table_name}")
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = '{table_name}' AND table_schema = 'public'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[0]} ({col[1]}), Nullable: {col[2]}, Default: {col[3]}")
                
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error connecting/querying PostgreSQL: {e}")
        sys.exit(1)

if __name__ == '__main__':
    read_db_schema()
