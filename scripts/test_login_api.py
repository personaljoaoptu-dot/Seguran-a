import urllib.request
import json
import sys

def test_api():
    url = "http://127.0.0.1:8000/api/login"
    
    # 1. Test correct credentials
    print("Testing API with correct credentials...")
    data_correct = json.dumps({
        "email": "admin@sol.com",
        "password": "123456"
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(
            url, 
            data=data_correct, 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            print(f"Success! Response: {res_json}")
            assert res_json['success'] == True
            assert res_json['user_name'] == 'João Silva'
            assert res_json['tenant_name'] == 'Supermercado Sol'
    except Exception as e:
        print(f"Error testing correct login: {e}")
        sys.exit(1)

    # 2. Test incorrect credentials
    print("\nTesting API with incorrect credentials...")
    data_incorrect = json.dumps({
        "email": "admin@sol.com",
        "password": "wrongpassword"
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(
            url, 
            data=data_incorrect, 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            print(f"Unexpected success response: {res_body}")
            sys.exit(1)
    except urllib.error.HTTPError as e:
        res_body = e.read().decode('utf-8')
        res_json = json.loads(res_body)
        print(f"Correctly caught error response (HTTP {e.code}): {res_json}")
        assert res_json['success'] == False
        assert "E-mail ou senha incorretos" in res_json['message']
    except Exception as e:
        print(f"Error testing incorrect login: {e}")
        sys.exit(1)

    print("\nAll programmatic API authentication checks passed successfully!")

if __name__ == '__main__':
    test_api()
