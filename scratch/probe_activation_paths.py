import urllib.request
import urllib.error

urls = [
    "http://144.91.121.55:5678/webhook/f1f2f3f4-5678-4c3d-b2a1-098765432109/webhook-verify/verify-token",
    "http://144.91.121.55:5678/webhook/f1f2f3f4-5678-4c3d-b2a1-098765432109/webhook_verify/verify-token",
    "http://144.91.121.55:5678/webhook/f1f2f3f4-5678-4c3d-b2a1-098765432109/WebhookVerify/verify-token",
    "http://144.91.121.55:5678/webhook/f1f2f3f4-5678-4c3d-b2a1-098765432109/verify-token",
    "http://144.91.121.55:5678/webhook/f1f2f3f4-5678-4c3d-b2a1-098765432109/Webhook%20Verify/verify-token",
    "http://144.91.121.55:5678/webhook/verify-token"
]

for url in urls:
    print(f"Probing {url} ...")
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=3) as resp:
            print(f"  SUCCESS! Status: {resp.getcode()}")
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code}: {e.reason}")
    except Exception as e:
        print(f"  Error: {e}")
