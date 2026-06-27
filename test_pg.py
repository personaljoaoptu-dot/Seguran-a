import socket
import struct

def test_postgres(port):
    print(f"Testing port {port}...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect(('127.0.0.1', port))
        
        # Send SSLRequest packet: length 8, code 80877103
        ssl_packet = struct.pack('!II', 8, 80877103)
        s.sendall(ssl_packet)
        
        response = s.recv(1)
        print(f"SSLRequest response: {response}")
        if response == b'S' or response == b'N':
            print("Port responded to PostgreSQL SSLRequest! It is likely PostgreSQL.")
            s.close()
            return True
        s.close()
    except Exception as e:
        print(f"Error connecting: {e}")
    return False

test_postgres(8080)
test_postgres(5678)
