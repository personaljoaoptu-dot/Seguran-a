import pg8000
import sys

def check_constraints():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='aegisyear'
        )
        cursor = conn.cursor()
        
        # Check constraints for usuarios
        print("Checking constraints on table 'usuarios':")
        cursor.execute("""
            SELECT conname, pg_get_constraintdef(c.oid) 
            FROM pg_constraint c 
            JOIN pg_namespace n ON n.oid = c.connamespace 
            WHERE conrelid = 'usuarios'::regclass;
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
            
        # Check current rows in usuarios
        cursor.execute("SELECT id, nome, email, cpf FROM usuarios;")
        rows = cursor.fetchall()
        print(f"\nCurrent rows in 'usuarios' ({len(rows)} total):")
        for r in rows:
            print(r)
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    check_constraints()
