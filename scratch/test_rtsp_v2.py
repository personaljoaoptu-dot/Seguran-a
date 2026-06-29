import os
import time

urls = [
    "rtsp://admin:20011998j@192.168.1.14:554/onvif2",
    "rtsp://admin:20011998j@192.168.1.14:554/live/ch0",
    "rtsp://admin:20011998j@192.168.1.14:554/ch0.h264",
    "rtsp://192.168.1.14:554/onvif1",
    "rtsp://192.168.1.14:554/onvif2"
]

import cv2

for rtsp_url in urls:
    print(f"\n--- TESTANDO URL: {rtsp_url} ---")
    
    # Test with default first
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    success = False
    for i in range(15):
        ret, frame = cap.read()
        if ret:
            print(f"[SUCESSO] Conectado! Resolução: {frame.shape[1]}x{frame.shape[0]}")
            success = True
            break
        time.sleep(0.1)
    cap.release()
    
    if success:
        print(f"URL FUNCIONAL ENCONTRADA: {rtsp_url}")
        break
else:
    print("\n[FALHA] Nenhuma das URLs adicionais conectou.")
