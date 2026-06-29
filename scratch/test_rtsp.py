import os
import time

rtsp_url = "rtsp://admin:20011998j@192.168.1.14:554/onvif1"

def test_mode(label, env_value):
    print(f"\n--- TESTANDO MODO: {label} ({env_value}) ---")
    if env_value:
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = env_value
    else:
        if "OPENCV_FFMPEG_CAPTURE_OPTIONS" in os.environ:
            del os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"]
            
    import cv2
    
    start_time = time.time()
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # Wait a bit to see if it connects
    success = False
    for i in range(30):
        ret, frame = cap.read()
        if ret:
            print(f"[SUCESSO] Conectado com sucesso no modo {label}! Resolução: {frame.shape[1]}x{frame.shape[0]}")
            success = True
            break
        time.sleep(0.1)
        
    cap.release()
    print(f"Tempo de teste: {time.time() - start_time:.2f}s")
    return success

# We test default first, then TCP, then UDP
if not test_mode("PADRÃO", None):
    if not test_mode("FORÇAR TCP", "rtsp_transport;tcp"):
        if not test_mode("FORÇAR UDP", "rtsp_transport;udp"):
            print("\n[FALHA] Nenhum dos modos padrão de transporte funcionou. Verifique se o IP/senha estão corretos ou tente /onvif2.")
