import av
import time
import sys

rtsp_url = "rtsp://admin:20011998j@192.168.1.14:554/onvif1"
print("--- TESTANDO CONEXÃO RTSP COM PYAV (FORÇANDO TCP) ---")

try:
    # Open the container with forced TCP transport and a shorter timeout (3 seconds)
    container = av.open(rtsp_url, options={
        'rtsp_transport': 'tcp',
        'stimeout': '3000000' # 3 seconds timeout
    })
    print("Container aberto com sucesso!")
    
    stream = container.streams.video[0]
    print(f"Fluxo de vídeo detectado: {stream.name} | Codec: {stream.codec_context.name}")
    
    # Decode the first frame
    for frame in container.decode(stream):
        img = frame.to_image()
        print(f"[SUCESSO] Frame capturado via PyAV! Resolução: {img.width}x{img.height}")
        break
        
    container.close()
    sys.exit(0)
except Exception as e:
    print(f"[FALHA] Erro ao conectar via PyAV: {e}")
    sys.exit(1)
