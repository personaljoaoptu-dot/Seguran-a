import subprocess
import sys

url = "rtsp://admin:20011998j@192.168.1.14:554/onvif1"

# Script content to execute in a clean sub-process
script_template = """
import os
import sys
import time

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "{options}"
import cv2

url = "{url}"
cap = cv2.VideoCapture(url)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

success = False
for i in range(15):
    ret, frame = cap.read()
    if ret:
        print(f"[SUCESSO] Conectado no modo {sys.argv[1]}! Resolucao: {{frame.shape[1]}}x{{frame.shape[0]}}")
        success = True
        break
    time.sleep(0.1)

cap.release()
if not success:
    print(f"[FALHA] Sem conexao no modo {sys.argv[1]}")
    sys.exit(1)
sys.exit(0)
"""

def run_isolated_test(label, options):
    print(f"\nIniciando teste isolado: {label}...")
    code = script_template.replace("{options}", options).replace("{url}", url)
    
    # Run python subprocess passing the code via stdin
    p = subprocess.Popen([sys.executable, "-", label], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(input=code)
    
    print(stdout.strip())
    if stderr.strip():
         print("Stderr:", stderr.strip())
    return p.returncode == 0

# Test TCP
tcp_ok = run_isolated_test("FORÇAR TCP", "rtsp_transport;tcp")

# Test UDP
udp_ok = run_isolated_test("FORÇAR UDP", "rtsp_transport;udp")

if not tcp_ok and not udp_ok:
    print("\nAmbos os modos falharam nos processos limpos. Tentando o fluxo alternativo /onvif2...")
    url = "rtsp://admin:20011998j@192.168.1.14:554/onvif2"
    run_isolated_test("FORÇAR TCP (/onvif2)", "rtsp_transport;tcp")
    run_isolated_test("FORÇAR UDP (/onvif2)", "rtsp_transport;udp")
