import cv2
import time

usernames = ["admin", "", "root"]
passwords = ["20011998j", "123", "123456", "admin", ""]
paths = ["/onvif1", "/onvif2"]

ip = "192.168.1.14"

print("--- INICIANDO VERIFICAÇÃO DE CREDENCIAIS ---")

found = False
for path in paths:
    if found:
        break
    for user in usernames:
        if found:
            break
        for pwd in passwords:
            if user == "" and pwd == "":
                url = f"rtsp://{ip}:554{path}"
            elif user == "":
                url = f"rtsp://:{pwd}@{ip}:554{path}"
            else:
                url = f"rtsp://{user}:{pwd}@{ip}:554{path}"
                
            print(f"Testando: {url}")
            cap = cv2.VideoCapture(url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Wait a few frames
            ret = False
            for _ in range(5):
                ret, frame = cap.read()
                if ret:
                    break
                time.sleep(0.1)
                
            cap.release()
            
            if ret:
                print(f"\n[SUCESSO COMPLETO!] Câmera conectada com a URL:\n👉 {url}\n")
                found = True
                break
            else:
                time.sleep(0.1)

if not found:
    print("\n[FALHA] Nenhuma combinação de credenciais padrão ou a senha informada conectou. Verifique se o NVR/ONVIF está realmente ativo com a senha informada.")
