import av

users = ["aegiseye", "eagiseye", "admin", "user"]
passwords = ["911@Miguel", "911%40Miguel", "20011998j", "20011998Jpl"]

ip = "192.168.1.88"
port = 554

print(f"Testing typo combinations on {ip}:{port}...")

found = False
for u in users:
    for p in passwords:
        # We try constructing the URL. 
        # If the password already contains %40, we don't encode it again.
        # Otherwise, we try both as-is.
        for url_pattern in [
            f"rtsp://{u}:{p}@{ip}:{port}/cam/realmonitor?channel=1&subtype=1",
            f"rtsp://{u}:{p}@{ip}:{port}/onvif1",
            f"rtsp://{u}:{p}@{ip}:{port}/live/ch0"
        ]:
            try:
                # print(f"Trying: {url_pattern}")
                container = av.open(url_pattern, options={
                    'rtsp_transport': 'tcp',
                    'stimeout': '1000000' # 1 second
                })
                print(f"\n[SUCCESS] Connected using: {url_pattern}")
                container.close()
                found = True
                break
            except Exception as e:
                # If it's a connection refused or timeout, the IP is wrong or port closed,
                # but we know port is open, so it's likely 401.
                # Let's print only non-401 errors, or just pass to keep it clean.
                if "401 Unauthorized" not in str(e):
                    print(f"Error for {u} / {p}: {e}")
                pass
        if found:
            break
    if found:
        break

if not found:
    print("No credentials succeeded with 192.168.1.88.")
