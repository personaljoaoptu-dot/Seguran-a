import pg8000
import sys

def clear_alerts():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='aegisyear'
        )
        cursor = conn.cursor()
        
        print("Deleting all historical alerts from public.alertas table...")
        cursor.execute("DELETE FROM public.alertas;")
        conn.commit()
        
        print("Success! Database alerts cleared.")
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error clearing alerts:", e)
        sys.exit(1)

if __name__ == '__main__':
    clear_alerts()
