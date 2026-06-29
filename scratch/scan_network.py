import socket
import concurrent.futures

def scan_ip(ip):
    results = []
    # Ports to check: 554 (RTSP), 8899 (ONVIF), 5000 (Yoosee ONVIF)
    for port in [554, 8899, 5000]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            res = s.connect_ex((ip, port))
            s.close()
            if res == 0:
                results.append(port)
        except Exception:
            pass
    return ip, results

print("Scanning subnet 192.168.1.1 to 192.168.1.254 for camera ports (554, 8899, 5000)...")

found_devices = []
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    ips = [f"192.168.1.{i}" for i in range(1, 255)]
    future_to_ip = {executor.submit(scan_ip, ip): ip for ip in ips}
    for future in concurrent.futures.as_completed(future_to_ip):
        ip, open_ports = future.result()
        if open_ports:
            print(f"[FOUND] {ip} has open ports: {open_ports}")
            found_devices.append((ip, open_ports))

print("\nScan completed.")
print(f"Total camera devices found: {len(found_devices)}")
