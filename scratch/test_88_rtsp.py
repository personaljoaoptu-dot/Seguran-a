import av
import cv2
import time

urls = [
    # 1. URL encoded password with %40
    "rtsp://eagiseye:911%40Miguel@192.168.1.88:554/cam/realmonitor?channel=1&subtype=1",
    # 2. Decoded password with @
    "rtsp://eagiseye:911@Miguel@192.168.1.88:554/cam/realmonitor?channel=1&subtype=1",
    # 3. Just admin and password? Let's try different user/pass combos if we know any
    "rtsp://admin:911%40Miguel@192.168.1.88:554/cam/realmonitor?channel=1&subtype=1",
    "rtsp://admin:911@Miguel@192.168.1.88:554/cam/realmonitor?channel=1&subtype=1",
    # 4. Without channel and subtype parameters
    "rtsp://eagiseye:911%40Miguel@192.168.1.88:554/onvif1",
    "rtsp://eagiseye:911@Miguel@192.168.1.88:554/onvif1",
]

def test_url_pyav(url):
    print(f"\nTesting PyAV on: {url}")
    try:
        container = av.open(url, options={
            'rtsp_transport': 'tcp', # Try TCP first
            'stimeout': '3000000'
        })
        print("  [SUCCESS] PyAV connected with TCP!")
        container.close()
        return True
    except Exception as e_tcp:
        print(f"  TCP failed: {e_tcp}")
        try:
            container = av.open(url, options={
                'rtsp_transport': 'udp',
                'stimeout': '3000000'
            })
            print("  [SUCCESS] PyAV connected with UDP!")
            container.close()
            return True
        except Exception as e_udp:
            print(f"  UDP failed: {e_udp}")
            return False

def test_url_cv2(url):
    print(f"Testing OpenCV on: {url}")
    try:
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        ret, frame = cap.read()
        cap.release()
        if ret:
            print("  [SUCCESS] OpenCV read frame!")
            return True
        else:
            print("  [FAILED] OpenCV could not read frame")
            return False
    except Exception as e:
        print(f"  OpenCV exception: {e}")
        return False

for url in urls:
    if test_url_pyav(url):
        test_url_cv2(url)
