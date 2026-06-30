import urllib.request
import urllib.error
import json
import sys
import pg8000

def test():
    url = 'http://144.91.121.55:8000/api/configurar'
    payload = {
        "action": "add_camera",
        "tenant_id": "65244ad5-47c7-4905-89c9-0efad0e9d7b6",
        "name": "Camera Test GPT",
        "device": "Dispositivo Genérico",
        "rtsp": "rtsp://127.0.0.1/ch_test",
        "profile": "Ocultamento / Suspeita",
        "type": "aisle",
        "status": "online"
    }
    
    print("Testing add_camera configuration API...")
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        res = urllib.request.urlopen(req)
        res_body = res.read().decode('utf-8')
        print("API Response:", res_body)
        res_json = json.loads(res_body)
        
        # Verify in database directly
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='aegisyear'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM cameras WHERE tenant_id = '65244ad5-47c7-4905-89c9-0efad0e9d7b6' AND name = 'Camera Test GPT'")
        row = cursor.fetchone()
        if row:
            print(f"Success! Camera found in DB: {row[1]} (ID: {row[0]})")
            
            # Clean up the test camera
            cursor.execute("DELETE FROM cameras WHERE id = %s", (row[0],))
            conn.commit()
            print("Cleanup completed.")
        else:
            print("Failure: Camera not found in database!")
            sys.exit(1)
            
        cursor.close()
        conn.close()
        
    except urllib.error.HTTPError as e:
        print("HTTP Error", e.code, e.read().decode('utf-8'))
        sys.exit(1)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

if __name__ == '__main__':
    test()
