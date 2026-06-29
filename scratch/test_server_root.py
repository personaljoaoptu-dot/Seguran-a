import urllib.request

try:
    response = urllib.request.urlopen("http://127.0.0.1:8082/", timeout=3)
    print("Status:", response.status)
    print("Headers:", dict(response.headers))
    content = response.read(200)
    print("Content preview (first 200 chars):")
    print(content.decode('utf-8', errors='ignore'))
except Exception as e:
    print("Error connecting to server:", e)
