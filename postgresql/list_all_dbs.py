import pg8000
import sys

def list_dbs():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='postgres'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        dbs = cursor.fetchall()
        print("Databases on server:")
        for db in dbs:
            print(f"  - {db[0]}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    list_dbs()
