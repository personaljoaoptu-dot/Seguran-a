import pg8000
import bcrypt
import sys

def clear_and_reset():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='aegisyear'
        )
        cursor = conn.cursor()
        
        print("Clearing all registrations and active records...")
        
        # 1. Truncate/delete all transient registration data
        cursor.execute("TRUNCATE TABLE activation_tokens CASCADE;")
        cursor.execute("TRUNCATE TABLE empresas CASCADE;")
        cursor.execute("TRUNCATE TABLE usuarios CASCADE;")
        
        # 2. Truncate/delete active tenants and users
        cursor.execute("TRUNCATE TABLE users CASCADE;")
        cursor.execute("TRUNCATE TABLE tenants CASCADE;")
        conn.commit()
        print("All records successfully deleted!")
        
        # 3. Recreate clean default administrator account for test purposes
        print("\nRecreating default test user 'admin@sol.com'...")
        cursor.execute("INSERT INTO tenants (name) VALUES ('Supermercado Sol') RETURNING id;")
        tenant_id = cursor.fetchone()[0]
        
        password = '123456'
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute("""
            INSERT INTO users (tenant_id, name, email, password_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (tenant_id, 'João Silva', 'admin@sol.com', password_hash))
        
        user_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Default tenant and user successfully recreated! Tenant ID: {tenant_id} | User ID: {user_id}")
        
        cursor.close()
        conn.close()
        print("Database reset completed successfully!")
    except Exception as e:
        print(f"Error resetting database: {e}")
        sys.exit(1)

if __name__ == '__main__':
    clear_and_reset()
