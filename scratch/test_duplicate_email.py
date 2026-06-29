import urllib.request
import urllib.error
import json
import sys

def test_duplicate():
    base_url = "http://144.91.121.55:8000"
    payload = {
        "nome": "João Pedro de Oliveira Silva",
        "email": "skalidor02@gmail.com",
        "whatsapp": "+5511999998888",
        "nome_empresa": "Minha Empresa Teste",
        "cpf": "02301368696"
    }
    
    print("Testing duplicate email registration with skalidor02@gmail.com...")
    try:
        req = urllib.request.Request(
            f"{base_url}/api/register",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            print("Response:", res_body)
            print("FAILED: Expected HTTP 400 Bad Request, but got HTTP 200 OK.")
            sys.exit(1)
    except urllib.error.HTTPError as he:
        res_body = he.read().decode('utf-8')
        print(f"HTTP Error {he.code}: {he.reason}")
        print("Response Body:", res_body)
        try:
            res_json = json.loads(res_body)
            assert res_json['success'] == False
            assert "cadastrado" in res_json['message'].lower()
            print("\n[SUCCESS] Duplicate email handled gracefully by n8n and returned as HTTP 400 with message:", res_json['message'])
        except Exception as e:
            print("Failed to parse or assert duplicate response:", e)
            sys.exit(1)
    except Exception as e:
        print("Connection or parsing error:", e)
        sys.exit(1)

if __name__ == '__main__':
    test_duplicate()
