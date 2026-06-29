import urllib.request
import sys

def test_connectivity():
    print("Testing connectivity to n8n on public VPS IP (144.91.121.55:5678)...")
    try:
        urllib.request.urlopen("http://144.91.121.55:5678/", timeout=5)
        print("  Public IP is REACHABLE!")
    except Exception as e:
        print(f"  Public IP failed: {e}")

    print("\nTesting connectivity to n8n on local tunnel (127.0.0.1:5678)...")
    try:
        urllib.request.urlopen("http://127.0.0.1:5678/", timeout=5)
        print("  Local tunnel (127.0.0.1) is REACHABLE!")
    except Exception as e:
        print(f"  Local tunnel failed: {e}")

if __name__ == '__main__':
    test_connectivity()
