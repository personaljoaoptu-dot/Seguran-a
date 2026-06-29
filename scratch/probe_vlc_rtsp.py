import os
import time

# Force FFMPEG parameters for Yoosee Digest authentication and TCP transport
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|rtsp_flags;prefer_tcp"

import cv2

url = "rtsp://admin:20011998j@192.168.1.14:554/onvif1"
print(f"--- TESTANDO CONEXÃO DIRETA COM PARÂMETROS OTIMIZADOS ---")
print("Certifique-se de que o VLC esteja COMPLETAMENTE FECHADO!")

cap = cv2.VideoCapture(url)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

success = False
for i in range(1, 21):
    print(f"Tentando ler frame (Tentativa {i}/20)...")
    ret, frame = cap.read()
    if ret:
        print(f"\n[SUCESSO] Frame capturado com sucesso! Resolução: {frame.shape[1]}x{frame.shape[0]}")
        success = True
        break
    time.sleep(0.5)

cap.release()

if not success:
    print("\n[FALHA] Não foi possível obter o frame. Se o VLC estava fechado, pode ser necessário ajustar o transporte para UDP.")
