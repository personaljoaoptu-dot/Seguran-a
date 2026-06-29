import smtplib
import sys

def test_auth():
    print("Testing SMTP authentication to smtp.gmail.com:465...")
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10)
        server.ehlo()
        print("Connected to Gmail SMTP! Attempting login...")
        server.login('segurancasaas@gmail.com', 'gxysvutjjekdgcrz')
        print("[SUCCESS] Successfully authenticated with Gmail SMTP!")
        server.quit()
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    test_auth()
