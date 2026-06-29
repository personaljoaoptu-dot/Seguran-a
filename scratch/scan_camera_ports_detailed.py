import socket
import concurrent.futures

ports = [80, 554, 1935, 5000, 8000, 8080, 8554, 8899, 9000, 37777]

def scan_ip(ip):
    results = []
    for port in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            res = s.connect_ex((ip, port))
            s.close()
            if res == 0:
                results.append(port)
        except Exception:
            pass
    return ip, results

print("Detailed scan of subnet 192.168.1.1 to 192.168.1.254...")

found = []
with concurrent.futures.ThreadPoolExecutor(max_workers=80) as executor:
    ips = [f"192.168.1.{i}" for i in range(1, 255)]
    future_to_ip = {executor.submit(scan_ip, ip): ip for ip in ips}
    for future in concurrent.futures.as_completed(future_to_ip):
        ip, open_ports = future.result()
        if open_ports:
            print(f"[FOUND] {ip} has open ports: {open_ports}")
            found.append((ip, open_ports))

print("\nDetailed scan completed.")
print(f"Total active hosts with camera ports: {len(found)}")
