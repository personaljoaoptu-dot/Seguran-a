import urllib.request
import urllib.error
import json
import sys
import random
import time

def generate_random_cpf():
    return "".join(str(random.randint(0, 9)) for _ in range(11))

def test_activation_flow():
    base_url = "http://144.91.121.55:8000"
    
    # 1. Register a new user
    print("Step 1: Registering a new customer/company...")
    email = f"parceiro+{random.randint(10000, 99999)}@aegiseye.com.br"
    nome_empresa = f"Mercado Alpha {random.randint(100, 999)}"
    cpf = generate_random_cpf()
    
    reg_payload = {
        "nome": "Inacio Carvalho",
        "email": email,
        "whatsapp": "+5511977776666",
        "nome_empresa": nome_empresa,
        "cpf": cpf
    }
    
    try:
        req = urllib.request.Request(
            f"{base_url}/api/register",
            data=json.dumps(reg_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            print("Register Response:", res_json)
            assert res_json['success'] == True
            token = res_json['data']['token']
            print(f"Registration successful! Token generated: {token}")
    except Exception as e:
        print(f"Error during registration: {e}")
        if hasattr(e, 'read'):
            print("Response body:", e.read().decode('utf-8'))
        sys.exit(1)
        
    # Wait briefly for n8n/DB sync
    time.sleep(1)

    # 2. Verify token
    print(f"\nStep 2: Verifying token {token}...")
    try:
        req = urllib.request.Request(
            f"{base_url}/api/verify-token?token={token}",
            method='GET'
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            print("Verify Token Response:", res_json)
            assert res_json['success'] == True
            assert res_json['email'] == email
            assert res_json['nome_empresa'] == nome_empresa
            print("Token verification successful!")
    except Exception as e:
        print(f"Error during token verification: {e}")
        sys.exit(1)

    # 3. Activate account and set password
    print("\nStep 3: Activating account and setting password...")
    activate_payload = {
        "token": token,
        "password": "senha_segura_123"
    }
    try:
        req = urllib.request.Request(
            f"{base_url}/api/activate",
            data=json.dumps(activate_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            print("Activation Response:", res_json)
            assert res_json['success'] == True
            print("Account activation successful!")
    except Exception as e:
        print(f"Error during activation: {e}")
        if hasattr(e, 'read'):
            print("Response body:", e.read().decode('utf-8'))
        sys.exit(1)

    # Wait briefly for n8n/DB update
    time.sleep(1)

    # 4. Attempt login with new credentials
    print("\nStep 4: Attempting login with newly registered and activated account...")
    login_payload = {
        "email": email,
        "password": "senha_segura_123"
    }
    try:
        req = urllib.request.Request(
            f"{base_url}/api/login",
            data=json.dumps(login_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            print("Login Response:", res_json)
            assert res_json['success'] == True
            assert res_json['user_name'] == "Inacio Carvalho"
            assert res_json['tenant_name'] == nome_empresa
            print(f"Login successful! Session token generated: {res_json['session_token']}")
    except Exception as e:
        print(f"Error during login: {e}")
        if hasattr(e, 'read'):
            print("Response body:", e.read().decode('utf-8'))
        sys.exit(1)

    print("\n[SUCCESS] End-to-end Activation Magic Link Flow verified and working perfectly!")

if __name__ == '__main__':
    test_activation_flow()
