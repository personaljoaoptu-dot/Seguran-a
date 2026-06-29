import socket
import cv2
import av
import time

cameras = [
    {"name": "teste", "rtsp": "rtsp://admin:20011998j@192.168.1.14:554/onvif1", "ip": "192.168.1.14", "port": 554},
    {"name": "teste 2", "rtsp": "rtsp://admin:20011998Jpl@192.168.1.15:554/onvif1", "ip": "192.168.1.15", "port": 554},
    {"name": "teste 3", "rtsp": "rtsp://eagiseye:911%40Miguel@192.168.1.88:554/cam/realmonitor?channel=1&subtype=1", "ip": "192.168.1.88", "port": 554}
]

def check_socket(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        res = s.connect_ex((ip, port))
        s.close()
        return res == 0
    except Exception as e:
        print(f"Error socket check on {ip}:{port}: {e}")
        return False

def test_opencv(rtsp_url):
    try:
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        success = False
        for i in range(15):
            ret, frame = cap.read()
            if ret:
                success = True
                break
            time.sleep(0.1)
        cap.release()
        return success
    except Exception as e:
        print(f"OpenCV error: {e}")
        return False

def test_pyav(rtsp_url):
    try:
        container = av.open(rtsp_url, options={
            'rtsp_transport': 'udp',
            'stimeout': '3000000' # 3 seconds
        })
        stream = container.streams.video[0]
        stream.thread_type = 'NONE'
        
        success = False
        for frame in container.decode(stream):
            success = True
            break
        container.close()
        return success
    except Exception as e:
        print(f"PyAV error: {e}")
        return False

print("--- PROBING CAMERAS ---")
for cam in cameras:
    print(f"\nCamera: {cam['name']} ({cam['ip']}:{cam['port']})")
    
    # 1. Socket ping
    online = check_socket(cam['ip'], cam['port'])
    print(f"  TCP Port {cam['port']} open: {online}")
    
    if online:
        # 2. Try OpenCV
        cv2_ok = test_opencv(cam['rtsp'])
        print(f"  OpenCV connection: {cv2_ok}")
        
        # 3. Try PyAV
        pyav_ok = test_pyav(cam['rtsp'])
        print(f"  PyAV connection: {pyav_ok}")
    else:
        print("  Skipping RTSP tests since port is closed.")
