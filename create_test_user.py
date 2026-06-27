import pg8000
import bcrypt
import sys

def create_test_data():
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
        
        # 1. Clean existing records if any
        cursor.execute("DELETE FROM users;")
        cursor.execute("DELETE FROM tenants;")
        conn.commit()
        
        # 2. Insert Tenant
        print("Creating tenant 'Supermercado Sol'...")
        cursor.execute("INSERT INTO tenants (name) VALUES ('Supermercado Sol') RETURNING id;")
        tenant_id = cursor.fetchone()[0]
        print(f"Tenant created with ID: {tenant_id}")
        
        # 3. Hash password '123456'
        password = '123456'
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 4. Insert User
        print("Creating user 'admin@sol.com'...")
        cursor.execute("""
            INSERT INTO users (tenant_id, name, email, password_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (tenant_id, 'João Silva', 'admin@sol.com', password_hash))
        
        user_id = cursor.fetchone()[0]
        print(f"User created with ID: {user_id}")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Test data created successfully!")
    except Exception as e:
        print(f"Error creating test data: {e}")
        sys.exit(1)

if __name__ == '__main__':
    create_test_data()
