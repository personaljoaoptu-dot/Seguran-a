import urllib.request
import urllib.error
import json

def test():
    url = 'http://144.91.121.55:8000/api/login'
    data = json.dumps({'email': 'personal.joaoptu@gmail.com', 'password': '20011998j'}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        res = urllib.request.urlopen(req)
        print("Success:", res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print("HTTP Error", e.code, e.read().decode('utf-8'))
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    test()
