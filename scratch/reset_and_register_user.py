import pg8000
import urllib.request
import json
import sys

def reset_and_register():
    try:
        conn = pg8000.connect(
            host='144.91.121.55',
            port=5432,
            user='postgres',
            password='KtnYcxnVOGjD4thzS6tlBcW9',
            database='aegisyear'
        )
        cursor = conn.cursor()
        
        print("Deleting existing registration records for email 'skalidor02@gmail.com' and CPF '02301368696'...")
        cursor.execute("DELETE FROM activation_tokens WHERE usuario_id IN (SELECT id FROM usuarios WHERE email = 'skalidor02@gmail.com');")
        cursor.execute("DELETE FROM empresas WHERE usuario_id IN (SELECT id FROM usuarios WHERE email = 'skalidor02@gmail.com');")
        cursor.execute("DELETE FROM usuarios WHERE email = 'skalidor02@gmail.com' OR cpf = '02301368696';")
        conn.commit()
        cursor.close()
        conn.close()
        print("Database cleaned for fresh registration test!")
        
        # Trigger register request
        base_url = "http://144.91.121.55:8000"
        payload = {
            "nome": "João Pedro de Oliveira Silva",
            "email": "skalidor02@gmail.com",
            "whatsapp": "+5511999998888",
            "nome_empresa": "AegisEye Security System",
            "cpf": "02301368696"
        }
        
        print("\nSubmitting fresh registration request...")
        req = urllib.request.Request(
            f"{base_url}/api/register",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            print("\nResponse from server:", json.dumps(res_json, indent=2))
            if res_json.get('success'):
                print("\n[SUCCESS] Fresh registration submitted and activation email sent to your inbox!")
            else:
                print("\n[FAILED] Server returned error:", res_json.get('message'))
    except urllib.error.HTTPError as he:
        res_body = he.read().decode('utf-8')
        print(f"HTTP Error {he.code}: {he.reason}")
        print("Response Body:", res_body)
        sys.exit(1)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

if __name__ == '__main__':
    reset_and_register()
