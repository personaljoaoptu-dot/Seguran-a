import urllib.request
import json

url = "http://localhost:8000/api/get-cameras?tenant_id=65244ad5-47c7-4905-89c9-0efad0e9d7b6"

print("Fetching:", url)
try:
    with urllib.request.urlopen(url, timeout=10) as response:
        code = response.getcode()
        body = response.read().decode('utf-8')
        print(f"Response code: {code}")
        print(f"Response body: {body}")
except urllib.error.HTTPError as he:
    code = he.code
    body = he.read().decode('utf-8')
    print(f"HTTPError code: {code}")
    print(f"HTTPError body: {body}")
except Exception as e:
    print(f"General error: {e}")
