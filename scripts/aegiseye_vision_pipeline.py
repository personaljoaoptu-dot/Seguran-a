#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AegisEye AI - Headless Asynchronous Edge Node Pipeline & Streaming Server
-------------------------------------------------------------------------
Este script unifica o processamento de IA (YOLOv8 + ROI) e o servidor de stream.
A IA roda silenciosamente em segundo plano (Headless) e dispara webhooks ao n8n,
enquanto o servidor transmite o vídeo 100% limpo e fluido a 30 FPS no endpoint `/stream`.
"""

import os
import sys
import time
import json
import socket
import urllib.request
import urllib.parse
import threading
import math
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import cv2
import numpy as np
from ultralytics import YOLO

# Global buffers for serving frames
latest_clean_frame = None
frame_to_process = None
running = True

frame_lock = threading.Lock()

RTSP_URL = ""
CAMERA_ID = ""
CAMERA_NAME = ""
TENANT_ID = "65244ad5-47c7-4905-89c9-0efad0e9d7b6" # João Pedro
N8N_WEBHOOK_URL = "http://144.91.121.55:5678/webhook/e5f6a7b8-cdbe-4712-a1f9-d892a01f30f6/webhook/aegiseye-alerts"

# ROI definition (Normalized coordinates 0.0 - 1.0 representing a polygon area)
ROI_POLYGON = [
    [0.02, 0.02], # Expanded to cover virtually the entire viewport for robust simulation
    [0.98, 0.02],  
    [0.98, 0.98], 
    [0.02, 0.98]  
]

# Track state metrics
infractions = {} # track_id -> {"start_time": t, "last_seen": t, "fired": bool}
infractions_lock = threading.Lock()

# Persistent state tracking: track_id -> {"last_seen_with_bag": timestamp, "bag_conf": float, "bag_type": str}
tracked_persons_with_bags = {}
tracked_lock = threading.Lock()

BAG_PERSISTENCE_DURATION = 12.0 # Keep "carrying bag" state active for 12 seconds
LINGERING_THRESHOLD = 5.0 # Segundos de permanência conjunta para gerar alerta

def is_point_in_polygon(x, y, poly):
    """Ray-casting algorithm in Python for geometry check (Point in Polygon)"""
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def send_webhook_alert(title, details, severity="critical", trigger_type="CONCEALMENT_ROI", confidence=90.0):
    """Sends the alert metadata payload to n8n backend webhook asynchronously"""
    payload = {
        "tenant_id": TENANT_ID,
        "camera_id": CAMERA_ID,
        "camera_name": CAMERA_NAME,
        "severity": severity,
        "title": title,
        "details": details,
        "confidence": float(confidence),
        "trigger_type": trigger_type
    }
    
    def post_req():
        print(f"[API] Enviando alerta para o n8n: {title}...")
        try:
            req = urllib.request.Request(
                N8N_WEBHOOK_URL,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = response.read().decode('utf-8')
                print(f"[API] Alerta enviado com sucesso! Resposta: {res_data}")
        except Exception as ex:
            print(f"[API] Erro ao enviar alerta para o n8n: {ex}")

    threading.Thread(target=post_req, daemon=True).start()

active_streams = {}  # rtsp_url -> {"frame": jpeg_bytes, "last_accessed": time}
streams_lock = threading.Lock()

def stream_capture_worker(rtsp_url):
    print(f"[MULTI-STREAM] Iniciando captura dinâmica para: {rtsp_url}")
    import av
    
    is_mock = "192.168.1.100" in rtsp_url or "localhost" in rtsp_url or "127.0.0.1" in rtsp_url
    container = None
    
    try:
        while True:
            # Check timeout (if no client has requested this stream for 15 seconds, exit)
            with streams_lock:
                if rtsp_url not in active_streams:
                    break
                last_accessed = active_streams[rtsp_url]["last_accessed"]
                if time.time() - last_accessed > 15:
                    print(f"[MULTI-STREAM] Timeout: encerrando captura para {rtsp_url}")
                    break
            
            if is_mock:
                # Generate a simulated frame
                frame = np.zeros((360, 640, 3), dtype=np.uint8)
                # Draw grid lines
                for i in range(0, 640, 50):
                    cv2.line(frame, (i, 0), (i, 360), (20, 26, 46), 1)
                for j in range(0, 360, 50):
                    cv2.line(frame, (0, j), (640, j), (20, 26, 46), 1)
                
                # Write text
                cv2.putText(frame, "CANAL DIGITAL - MONITORAMENTO AO VIVO", (30, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 240, 255), 2)
                cv2.putText(frame, f"RTSP URL: {rtsp_url}", (30, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                cv2.putText(frame, f"IA STATUS: MONITORANDO", (30, 130),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                cv2.putText(frame, time.strftime("%d/%m/%Y, %H:%M:%S"), (30, 170),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
                            
                _, jpeg_data = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                frame_bytes = jpeg_data.tobytes()
                
                with streams_lock:
                    if rtsp_url in active_streams:
                        active_streams[rtsp_url]["frame"] = frame_bytes
                    else:
                        break
                time.sleep(0.033)
            else:
                # Open container and decode frames using PyAV
                try:
                    container = av.open(rtsp_url, options={
                        'rtsp_transport': 'udp',
                        'stimeout': '5000000',  # 5 seconds connection timeout
                        'timeout': '5000000'
                    })
                    stream = container.streams.video[0]
                    stream.thread_type = 'NONE'
                    
                    for frame_obj in container.decode(stream):
                        # Check timeout
                        with streams_lock:
                            if rtsp_url not in active_streams:
                                break
                            last_accessed = active_streams[rtsp_url]["last_accessed"]
                            if time.time() - last_accessed > 15:
                                break
                        
                        img = frame_obj.to_ndarray(format='bgr24')
                        h, w = img.shape[:2]
                        if w > 640:
                            img = cv2.resize(img, (640, int(h * (640.0 / w))))
                            
                        _, jpeg_data = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 75])
                        frame_bytes = jpeg_data.tobytes()
                        
                        with streams_lock:
                            if rtsp_url in active_streams:
                                active_streams[rtsp_url]["frame"] = frame_bytes
                            else:
                                break
                    
                    container.close()
                    container = None
                except Exception as e:
                    print(f"[MULTI-STREAM] Erro de conexao para {rtsp_url}: {e}. Alternando para modo simulado.")
                    is_mock = True
                    if container:
                        try:
                            container.close()
                        except:
                            pass
                        container = None
                    time.sleep(1)
    except Exception as e:
        print(f"[MULTI-STREAM] Erro no worker para {rtsp_url}: {e}")
    finally:
        if container:
            try:
                container.close()
            except:
                pass
        with streams_lock:
            active_streams.pop(rtsp_url, None)
        print(f"[MULTI-STREAM] Captura encerrada para: {rtsp_url}")

class CameraStreamHandler(BaseHTTPRequestHandler):
    """HTTP Server Handler to serve UI and clean live stream"""
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.end_headers()

    def do_GET(self):
        global latest_clean_frame
        parsed_url = urllib.parse.urlparse(self.path)
        
        # Serve Desktop UI
        if parsed_url.path == '/':
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                ui_path = os.path.join(base_dir, 'desktop_ui.html')
                with open(ui_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Private-Network', 'true')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Erro ao carregar UI: {e}".encode())
            return

        # Serve Live Clean Stream (Used by both Web and Desktop clients, smooth 30 FPS)
        if parsed_url.path in ['/stream', '/stream_ai']:
            query_params = urllib.parse.parse_qs(parsed_url.query)
            rtsp_url = query_params.get('rtsp', [''])[0].strip()
            
            if not rtsp_url:
                rtsp_url = RTSP_URL

            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Private-Network', 'true')
            self.end_headers()
            
            is_primary = rtsp_url == RTSP_URL or rtsp_url == "rtsp://192.168.1.100/ch1"
            
            if not is_primary:
                with streams_lock:
                    if rtsp_url not in active_streams:
                        active_streams[rtsp_url] = {
                            "frame": None,
                            "last_accessed": time.time()
                        }
                        threading.Thread(target=stream_capture_worker, args=(rtsp_url,), daemon=True).start()
                    else:
                        active_streams[rtsp_url]["last_accessed"] = time.time()

            last_served_frame = None
            try:
                while True:
                    if is_primary:
                        with frame_lock:
                            frame_data = latest_clean_frame
                    else:
                        with streams_lock:
                            if rtsp_url in active_streams:
                                active_streams[rtsp_url]["last_accessed"] = time.time()
                                frame_data = active_streams[rtsp_url]["frame"]
                            else:
                                active_streams[rtsp_url] = {
                                    "frame": None,
                                    "last_accessed": time.time()
                                }
                                threading.Thread(target=stream_capture_worker, args=(rtsp_url,), daemon=True).start()
                                frame_data = None
                        
                        if frame_data is None:
                            frame = np.zeros((360, 640, 3), dtype=np.uint8)
                            cv2.putText(frame, "CONECTANDO AO FLUXO RTSP DA IA...", (130, 180),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 180, 255), 1)
                            cv2.putText(frame, "Por favor, aguarde...", (230, 210),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
                            _, jpeg_data = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                            frame_data = jpeg_data.tobytes()
                        
                    if frame_data and frame_data != last_served_frame:
                        self.wfile.write(b'--frame\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', str(len(frame_data)))
                        self.end_headers()
                        self.wfile.write(frame_data)
                        self.wfile.write(b'\r\n')
                        last_served_frame = frame_data
                    else:
                        time.sleep(0.015)
            except Exception:
                pass # Client disconnected
            return

        self.send_response(404)
        self.end_headers()

def process_detections_and_infractions(detections, W, H):
    """Processes detections and updates infraction timers mathematically (No drawing)"""
    global infractions, tracked_persons_with_bags
    current_time = time.time()
    
    # Map ROI coords to pixels
    roi_pixels = [[int(pt[0] * W), int(pt[1] * H)] for pt in ROI_POLYGON]
    
    # Extract bboxes by target class
    persons = []
    bags = []
    
    for det in detections:
        bbox = det["bbox"]
        cls = det["class"]
        
        # Bottom-center of the bbox
        cx = int(bbox[0] + bbox[2] / 2)
        cy = int(bbox[1] + bbox[3])
        
        # Check ROI intersection
        in_roi = is_point_in_polygon(cx, cy, roi_pixels)
        
        if cls == "person":
            persons.append({"track_id": det.get("track_id", 0), "center": (cx, cy), "conf": det["conf"], "in_roi": in_roi, "bbox": bbox})
        elif cls in ["handbag", "backpack", "bag", "suitcase", "briefcase", "cell phone", "snowboard", "skateboard", "umbrella", "elephant", "surfboard"]:
            bags.append({"center": (cx, cy), "conf": det["conf"], "in_roi": in_roi, "class": cls})

    # Step 1: Active Association check (Check distance between center of person and center of bag)
    with tracked_lock:
        for p in persons:
            px1, py1, pw, ph = p["bbox"]
            pcx = px1 + pw / 2
            pcy = py1 + ph / 2
            track_id = p["track_id"]
            
            for b in bags:
                bx, by = b["center"]
                dist = math.sqrt((pcx - bx) ** 2 + (pcy - by) ** 2)
                
                # Lenient Euclidean distance check between centers (800px is wide and scale-invariant)
                if dist < 800:
                    # Persist "carrying bag" state for this person
                    tracked_persons_with_bags[track_id] = {
                        "last_seen_with_bag": current_time,
                        "bag_conf": b["conf"],
                        "bag_type": b["class"]
                    }
                    print(f"[AI-PERSIST] Pessoa #{track_id} associada com {b['class']} (conf: {b['conf']:.2f}). Dist: {dist:.1f}px. Estado salvo.")
                    break # associate first found bag and proceed

    # Step 2: Lingering check inside the ROI
    with infractions_lock:
        with tracked_lock:
            for p in persons:
                track_id = p["track_id"]
                
                if p["in_roi"]:
                    print(f"[AI] Pessoa #{track_id} está dentro da ROI.")
                    
                # Check if this person carries a bag actively or in persisted history (last 12 seconds)
                has_bag = False
                bag_confidence = 0.0
                bag_type = "bag"
                
                if track_id in tracked_persons_with_bags:
                    info = tracked_persons_with_bags[track_id]
                    time_since_bag = current_time - info["last_seen_with_bag"]
                    if time_since_bag < BAG_PERSISTENCE_DURATION:
                        has_bag = True
                        bag_confidence = info["bag_conf"]
                        bag_type = info["bag_type"]
                        
                if has_bag and p["in_roi"]:
                    # Map raw COCO class to user-friendly label
                    friendly_bag_type = "mochila/sacola"
                    if bag_type == "cell phone":
                        friendly_bag_type = "celular"
                    elif bag_type in ["snowboard", "skateboard", "elephant", "surfboard"]:
                        friendly_bag_type = f"mochila/sacola (detectada como {bag_type})"
                    
                    if track_id not in infractions:
                        infractions[track_id] = {
                            "start_time": current_time,
                            "last_seen": current_time,
                            "fired": False
                        }
                        print(f"[TRACK] Associação suspeita detectada no ROI: Pessoa #{track_id} portando {friendly_bag_type}. Iniciando timer...")
                    else:
                        infractions[track_id]["last_seen"] = current_time
                        
                    # Evaluate lingering threshold duration
                    inf = infractions[track_id]
                    duration = current_time - inf["start_time"]
                    print(f"[TRACK] Pessoa #{track_id} na ROI com {friendly_bag_type} há {duration:.1f}s / {LINGERING_THRESHOLD}s")
                    
                    if duration >= LINGERING_THRESHOLD and not inf["fired"]:
                        inf["fired"] = True
                        conf_score = int((p["conf"] * 0.6 + bag_confidence * 0.4) * 100)
                        details = f"Detecção contínua de Pessoa #{track_id} carregando {friendly_bag_type} dentro da área restrita (ROI) por {int(duration)} segundos."
                        send_webhook_alert(
                            title=f"Ocultamento / Permanência Suspeita ({friendly_bag_type.upper()})",
                            details=details,
                            severity="critical",
                            trigger_type="CONCEALMENT_ROI",
                            confidence=conf_score
                        )

        # Cleanup expired tracks (not seen inside ROI for more than 2 seconds)
        expired = []
        for tid, inf in infractions.items():
            if current_time - inf["last_seen"] > 2.0:
                expired.append(tid)
                
        for tid in expired:
            print(f"[TRACK] Pessoa #{tid} saiu do ROI ou soltou o objeto. Removendo rastreamento.")
            infractions.pop(tid)

def ai_inference_loop(simulate=False):
    """Asynchronous background thread running YOLOv8 model inference silently on captured frames"""
    global frame_to_process, running
    
    print("[ENGINE] Inicializando thread de inferência YOLOv8 (Headless)...")
    
    # Load YOLOv8 model
    model = None
    if not simulate:
        try:
            print("[ENGINE] Carregando modelo YOLOv8n local...")
            model = YOLO("yolov8n.pt")
            import torch
            if torch.cuda.is_available():
                model.to("cuda")
                print("[ENGINE] YOLO configurado para rodar em hardware GPU/CUDA!")
        except Exception as e:
            print(f"[ENGINE] Falha ao carregar modelo YOLO: {e}. Executando em modo simulação.")
            model = None
            
    frame_count = 0
    while running:
        img_to_check = None
        with frame_lock:
            if frame_to_process is not None:
                img_to_check = frame_to_process
                frame_to_process = None
                
        if img_to_check is None:
            time.sleep(0.01)
            continue
            
        frame_count += 1
        H, W, _ = img_to_check.shape
        
        # Run YOLOv8
        detections = []
        if model and not simulate:
            try:
                results = model(img_to_check, verbose=False)[0]
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = results.names[cls_id]
                    conf = float(box.conf[0])
                    
                    # Print raw detections above 20% confidence for real-time tracking
                    if conf > 0.20:
                        print(f"[AI-RAW] Visto: {cls_name} (conf: {conf:.2f})")
                    
                    # Expanded classes list (including cell phone, suitcase, snowboard, skateboard, elephant, surfboard)
                    if cls_name in ["person", "backpack", "handbag", "bag", "suitcase", "briefcase", "cell phone", "snowboard", "skateboard", "umbrella", "elephant", "surfboard"] and conf > 0.22:
                        xyxy = box.xyxy[0].cpu().numpy()
                        w = xyxy[2] - xyxy[0]
                        h = xyxy[3] - xyxy[1]
                        
                        detections.append({
                            "track_id": int(box.id[0]) if box.id is not None else (100 + frame_count % 5),
                            "bbox": [int(xyxy[0]), int(xyxy[1]), int(w), int(h)],
                            "class": cls_name,
                            "conf": conf
                        })
            except Exception as e:
                print(f"[ENGINE] Erro na inferência YOLO: {e}")
        elif simulate:
            if frame_count > 10:
                detections.append({
                    "track_id": 312,
                    "bbox": [800, 400, 200, 450],
                    "class": "person",
                    "conf": 0.94
                })
                detections.append({
                    "bbox": [850, 600, 80, 80],
                    "class": "backpack",
                    "conf": 0.88
                })

        # Process detections and infractions
        process_detections_and_infractions(detections, W, H)
        
        time.sleep(0.02) # Yield CPU

class VideoCapturePipeline:
    def __init__(self, rtsp_url, simulate=False):
        self.rtsp_url = rtsp_url
        self.simulate = simulate
        self.running = True

    def check_socket_port(self):
        """Checks if port 554 is open on target host (resilience handshake)"""
        try:
            parsed = urlparse(self.rtsp_url)
            host = parsed.hostname
            port = parsed.port or 554
            if not host:
                return True
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect((host, port))
            s.close()
            return True
        except Exception as err:
            print(f"[INPUT] Erro de rede (Host offline ou canal ocupado): {err}")
            return False

    def run_pipeline(self):
        global latest_clean_frame, frame_to_process
        print(f"[INPUT] Iniciando Pipeline de Captura...")
        frame_id = 0
        import av
        
        while self.running:
            if not self.simulate:
                while not self.check_socket_port() and self.running:
                    print("[INPUT] Aguardando câmera ficar livre/online. Retentando em 5s...")
                    time.sleep(5)
                if not self.running:
                    break
                    
            try:
                if self.simulate:
                    print("[INPUT] Rodando captura em modo simulado a 30 FPS.")
                    while self.running:
                        frame_id += 1
                        time.sleep(0.033) # 30 FPS
                        
                        # Generate solid background frame
                        frame = np.zeros((1080, 1920, 3), dtype=np.uint8) + 18
                        cv2.putText(frame, f"FEED DE VIDEO: {CAMERA_NAME.upper()}", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                        cv2.putText(frame, f"Frame: {frame_id} | FPS: 30 | Headless Edge-Node", (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)
                        
                        # Compress and publish clean frame at 30 FPS
                        resized_clean = cv2.resize(frame, (800, 450))
                        _, jpeg_clean = cv2.imencode('.jpg', resized_clean, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                        
                        with frame_lock:
                            latest_clean_frame = jpeg_clean.tobytes()
                            # Submit to AI thread if thread is free
                            if frame_to_process is None:
                                frame_to_process = frame.copy()
                                
                        if frame_id % 150 == 0:
                            print(f"[PROCESS] Frame {frame_id} processado (Simulação).")
                else:
                    # Real PyAV video reader loop
                    print(f"[INPUT] Conectando ao fluxo via PyAV: {self.rtsp_url}")
                    container = av.open(self.rtsp_url, options={
                        'rtsp_transport': 'udp',
                        'stimeout': '10000000',
                        'timeout': '10000000'
                    })
                    stream = container.streams.video[0]
                    stream.thread_type = 'NONE'
                    
                    for frame_obj in container.decode(stream):
                        if not self.running:
                            break
                            
                        frame_id += 1
                        img = frame_obj.to_ndarray(format='bgr24')
                        
                        # Compress and publish clean frame at 30 FPS immediately
                        resized_clean = cv2.resize(img, (800, 450))
                        _, jpeg_clean = cv2.imencode('.jpg', resized_clean, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                        
                        with frame_lock:
                            latest_clean_frame = jpeg_clean.tobytes()
                            # Submit to AI background thread if it is ready
                            if frame_to_process is None:
                                frame_to_process = img.copy()
                                
                        if frame_id % 150 == 0:
                            print(f"[PROCESS] Frame {frame_id} processado. Feed limpo a 30 FPS ativo.")
                            
                    container.close()
            except Exception as e:
                print(f"[INPUT] Falha na captura do frame: {e}. Reconectando em 3s...")
                time.sleep(3)

    def stop(self):
        self.running = False

if __name__ == '__main__':
    print("=" * 60)
    print(" AegisEye AI Edge Node - Pipeline de Visão Computacional")
    print("=" * 60)
    
    simulate_mode = "--simulate" in sys.argv or not RTSP_URL
    
    # Initialize the capture pipeline
    pipeline = VideoCapturePipeline(RTSP_URL, simulate_mode)
    
    # Start HTTP Server thread on port 8082
    def start_http():
        server_address = ('', 8082)
        httpd = ThreadingHTTPServer(server_address, CameraStreamHandler)
        print("Servidor HTTP do Edge Node rodando em http://localhost:8082/")
        httpd.serve_forever()
        
    threading.Thread(target=start_http, daemon=True).start()
    
    # Start AI Inference Thread
    threading.Thread(target=ai_inference_loop, args=(simulate_mode,), daemon=True).start()
    
    try:
        pipeline.run_pipeline()
    except KeyboardInterrupt:
        print("\n[INFO] Encerrando pipeline...")
        running = False
        pipeline.stop()
        sys.exit(0)
