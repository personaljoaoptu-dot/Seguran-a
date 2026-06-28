import urllib.request
import urllib.error
import json
import sys
import random

def generate_random_cpf():
    return "".join(str(random.randint(0, 9)) for _ in range(11))

def test_registration():
    url = "http://144.91.121.55:5678/webhook/e4f8a6b1-cdbe-4712-a1f9-d892a01f30f5/webhook/cadastro-seguranca"
    
    # Test 1: Valid registration (Dynamic data)
    print("Testing valid registration payload...")
    cpf = generate_random_cpf()
    email = f"carvalho.silva+{random.randint(10000, 99999)}@seguranca.com.br"
    
    valid_payload = {
        "nome": "Carvalho Silva",
        "email": email,
        "whatsapp": "+5511988887777",
        "nome_empresa": "Carvalho Monitoramento SA",
        "cpf": cpf
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(valid_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            print("Raw Response:", res_body)
            res_json = json.loads(res_body)
            print(f"Success Response: {res_json}")
            assert res_json['success'] == True
            assert 'usuario_id' in res_json['data']
            assert 'empresa_id' in res_json['data']
            print("Valid registration test PASSED!")
    except Exception as e:
        print(f"Error testing valid registration: {e}")
        if hasattr(e, 'read'):
            print("Error body:", e.read().decode('utf-8'))
        sys.exit(1)

    # Test 2: Invalid registration (validation failure)
    print("\nTesting invalid registration payload (empty name and wrong CPF format)...")
    invalid_payload = {
        "nome": "",
        "email": "invalid-email",
        "whatsapp": "123",
        "nome_empresa": "",
        "cpf": "123"
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(invalid_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            print(f"Unexpected success response: {res_body}")
            sys.exit(1)
    except urllib.error.HTTPError as e:
        res_body = e.read().decode('utf-8')
        res_json = json.loads(res_body)
        print(f"Correctly caught validation error (HTTP {e.code}): {res_json}")
        assert e.code == 400
        assert res_json['success'] == False
        assert len(res_json['errors']) > 0
        print("Invalid registration validation test PASSED!")
    except Exception as e:
        print(f"Error testing invalid registration: {e}")
        sys.exit(1)

    print("\nAll client registration tests passed successfully!")

if __name__ == '__main__':
    test_registration()

