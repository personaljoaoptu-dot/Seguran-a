import urllib.request
import json
import sys

def register_user():
    base_url = "http://144.91.121.55:8000"
    payload = {
        "nome": "João Pedro de Oliveira Silva",
        "email": "skalidor02@gmail.com",
        "whatsapp": "+5511999998888",
        "nome_empresa": "AegisEye Security System",
        "cpf": "02301368696"
    }
    
    print("Submitting registration for skalidor02@gmail.com...")
    try:
        req = urllib.request.Request(
            f"{base_url}/api/register",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            print("\nResponse from server:", json.dumps(res_json, indent=2))
            if res_json.get('success'):
                print("\n[SUCCESS] User registered and activation email triggered successfully!")
            else:
                print("\n[FAILED] Server returned unsuccessful:", res_json.get('message'))
    except urllib.error.HTTPError as he:
        res_body = he.read().decode('utf-8')
        print(f"HTTP Error {he.code}: {he.reason}")
        print("Response Body:", res_body)
        sys.exit(1)
    except Exception as e:
        print("Error connecting to registration API:", e)
        sys.exit(1)

if __name__ == '__main__':
    register_user()
