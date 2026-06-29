import socket
import sys

ip = "192.168.1.14"
ports = {
    554: "RTSP (Real-Time Streaming Protocol)",
    8899: "ONVIF (Camera Discovery & Control)",
    5000: "ONVIF Alternate / Yoosee",
    8000: "ONVIF Alternate / Hikvision/Intelbras",
    80: "HTTP (Web Administration)",
    8554: "RTSP Alternate",
    5544: "RTSP Alternate"
}

print(f"--- ESCANEANDO CÂMERA IP: {ip} ---")
open_ports = []

for port, desc in ports.items():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.5)
    result = s.connect_ex((ip, port))
    if result == 0:
        print(f"[ON] Porta {port} está ABERTA - {desc}")
        open_ports.append(port)
    else:
        print(f"[OFF] Porta {port} está fechada")
    s.close()

print("\n--- RESULTADO DA ANÁLISE ---")
if not open_ports:
    print("Nenhuma porta de vídeo padrão foi encontrada aberta. Verifique se a câmera está ligada, conectada na mesma rede/Wi-Fi e se o IP está correto.")
else:
    print("Portas detectadas com sucesso!")
    if 554 in open_ports or 8554 in open_ports:
        r_port = 554 if 554 in open_ports else 8554
        print(f"\n=> A câmera suporta transmissão direta RTSP (Porta {r_port})!")
        print("Tente as seguintes URLs no AegisEye:")
        print(f"  rtsp://admin:SUA_SENHA_ONVIF@{ip}:{r_port}/onvif1")
        print(f"  rtsp://admin:SUA_SENHA_ONVIF@{ip}:{r_port}/onvif2")
        print(f"  rtsp://{ip}:{r_port}/live/ch0")
        print("\n*Nota: Substitua SUA_SENHA_ONVIF pela senha configurada no aplicativo Yoosee (Configurações -> Conexão NVR/ONVIF).")
    
    if 8899 in open_ports or 5000 in open_ports:
        o_port = 8899 if 8899 in open_ports else 5000
        print(f"\n=> ONVIF detectado na porta {o_port}!")
        print("Esta câmera é compatível com descoberta automática de vídeo. Você pode usar aplicativos como ONVIF Device Manager para encontrar a URL RTSP exata de forma visual.")
