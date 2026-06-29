import pg8000
import sys
import os

def execute_ddl():
    try:
        # Read the DDL script
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'registration_schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            ddl_sql = f.read()

        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='aegisyear'
        )
        cursor = conn.cursor()
        
        print("Executing DDL script on 'aegisyear' database...")
        cursor.execute(ddl_sql)
        conn.commit()
        print("DDL script executed successfully! Tables 'usuarios', 'empresas', and 'dispositivos' have been created.")
        
        # Verify tables list
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [t[0] for t in cursor.fetchall()]
        print("Existing tables in public schema:", tables)
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error executing DDL: {e}")
        sys.exit(1)

if __name__ == '__main__':
    execute_ddl()
