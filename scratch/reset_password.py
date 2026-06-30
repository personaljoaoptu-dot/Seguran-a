import pg8000
import bcrypt
import sys

def reset_pwd(email, new_password):
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='aegisyear'
        )
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, name FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        if not row:
            print(f"User '{email}' not found in database.")
            conn.close()
            return
            
        print(f"Found user: {row[1]} (ID: {row[0]})")
        
        # Generate bcrypt hash
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Update database
        cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s", (hashed, email))
        conn.commit()
        
        print(f"Successfully updated password_hash for user '{email}' to new hash.")
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error resetting password:", e)
        sys.exit(1)

if __name__ == '__main__':
    reset_pwd('personal.joaoptu@gmail.com', '20011998j')
