import os
import av
import cv2
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import urllib.parse
import sys

# Cache of active video captures to prevent opening multiple streams for the same URL
captures = {}
lock = threading.Lock()

class CameraStreamHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress standard logging to prevent terminal flooding
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == '/':
            try:
                if hasattr(sys, '_MEIPASS'):
                    base_dir = sys._MEIPASS
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                ui_path = os.path.join(base_dir, 'desktop_ui.html')
                with open(ui_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Erro ao carregar UI: {e}".encode())
            return

        if parsed_url.path not in ['/stream', '/stream_ai']:
            self.send_response(404)
            self.end_headers()
            return

        query = urllib.parse.parse_qs(parsed_url.query)
        rtsp_url = query.get('rtsp', [None])[0]

        if not rtsp_url:
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Erro: URL RTSP ausente.")
            return

        print(f"[STREAM] Nova conexao solicitada para: {rtsp_url}")

        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        # Get or create video reader
        with lock:
            if rtsp_url not in captures:
                captures[rtsp_url] = {
                    "last_frame": None,
                    "subscribers": 0,
                    "running": True,
                    "thread": None
                }
                
                # Start frame reader thread using PyAV
                def reader_thread(c_info):
                    print(f"[STREAM] Iniciando thread PyAV para: {rtsp_url}")
                    
                    # Parse host and port from RTSP URL for pre-check
                    # format: rtsp://admin:pass@ip:port/path
                    import socket
                    from urllib.parse import urlparse
                    
                    try:
                        parsed = urlparse(rtsp_url)
                        host = parsed.hostname
                        port = parsed.port or 554
                    except Exception:
                        host = None
                        port = 554
                        
                    while c_info["running"]:
                        if host:
                            # Pre-check if port 554 is open and free
                            try:
                                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                s.settimeout(1.0)
                                s.connect((host, port))
                                s.close()
                            except Exception as socket_err:
                                print(f"[STREAM] Câmera ocupada ou offline (porta {port} bloqueada): {socket_err}. Garanta que o VLC esteja fechado! Retentando em 3s...")
                                time.sleep(3)
                                continue
                                
                        try:
                            # Open container with forced UDP transport and timeout (required for Yoosee cameras)
                            container = av.open(rtsp_url, options={
                                'rtsp_transport': 'udp',
                                'stimeout': '5000000' # 5 seconds
                            })
                            stream = container.streams.video[0]
                            stream.thread_type = 'NONE' # Disable threaded decoding for stability
                            
                            frame_count = 0
                            for frame in container.decode(stream):
                                if not c_info["running"]:
                                    break
                                
                                frame_count += 1
                                if frame_count == 1:
                                    print(f"[STREAM] Conectado e recebendo frames da camera: {rtsp_url}")
                                
                                # Convert PyAV frame to BGR numpy array
                                img = frame.to_ndarray(format='bgr24')
                                resized = cv2.resize(img, (800, 450))
                                _, jpeg = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                                c_info["last_frame"] = jpeg.tobytes()
                                time.sleep(0.01) # throttle to avoid high CPU
                                
                            container.close()
                        except Exception as e:
                            print(f"[STREAM] Conexao RTSP falhou ou caiu: {e}. Tentando novamente em 3s...")
                            time.sleep(3)

                t = threading.Thread(target=reader_thread, args=(captures[rtsp_url],), daemon=True)
                captures[rtsp_url]["thread"] = t
                t.start()
            
            captures[rtsp_url]["subscribers"] += 1
            cap_info = captures[rtsp_url]

        last_served_frame = None
        try:
            while True:
                frame_data = cap_info["last_frame"]
                if frame_data and frame_data != last_served_frame:
                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(frame_data)))
                    self.end_headers()
                    self.wfile.write(frame_data)
                    self.wfile.write(b'\r\n')
                    last_served_frame = frame_data
                else:
                    time.sleep(0.01)
        except Exception as e:
            print(f"[STREAM] Conexao de cliente encerrada para: {rtsp_url}")
        finally:
            with lock:
                cap_info["subscribers"] -= 1
                if cap_info["subscribers"] <= 0:
                    print(f"[STREAM] Parando thread PyAV para: {rtsp_url} (sem assinantes)")
                    cap_info["running"] = False
                    captures.pop(rtsp_url, None)

def run_server(port=8082):
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, CameraStreamHandler)
    print(f"Servidor de Stream AegisEye (Edge Node) rodando em http://localhost:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor parado.")

if __name__ == '__main__':
    port = 8082
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
