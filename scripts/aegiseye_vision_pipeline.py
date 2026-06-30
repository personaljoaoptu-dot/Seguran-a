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

# Load Haar Cascades for face detection (Looking at camera heuristic)
face_cascade = None
profile_cascade = None
try:
    frontal_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    profile_path = cv2.data.haarcascades + 'haarcascade_profileface.xml'
    face_cascade = cv2.CascadeClassifier(frontal_path)
    profile_cascade = cv2.CascadeClassifier(profile_path)
    if face_cascade.empty() or profile_cascade.empty():
        print("[ENGINE] Classificadores de faces/perfil vazios. Usando o que for válido.")
        if face_cascade.empty(): face_cascade = None
        if profile_cascade.empty(): profile_cascade = None
    else:
        print("[ENGINE] Classificadores frontal e perfil de faces carregados com sucesso.")
except Exception as e:
    print(f"[ENGINE] Erro ao carregar Cascades de faces: {e}. Detecção de olhar será reduzida.")
    face_cascade = None
    profile_cascade = None

# Persistent state tracking: track_id -> dict
tracked_persons = {}
tracked_lock = threading.Lock()

BAG_PERSISTENCE_DURATION = 12.0 # Keep "carrying bag" state active for 12 seconds
LINGERING_THRESHOLD = 15.0 # Segundos de permanência no ROI para loitering
CONCEALMENT_DISTANCE_THRESHOLD = 120.0 # Pixels (Euclidean distance) between person center and bag/object to assume interaction

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

def heartbeat_loop():
    """Periodically sends an online heartbeat signal to the central dashboard VPS"""
    print("[HEARTBEAT] Iniciando loop de sinal de presença (heartbeat)...")
    url = "http://144.91.121.55:8000/api/edge-ping"
    payload = {
        "tenant_id": TENANT_ID,
        "camera_name": CAMERA_NAME,
        "status": "online"
    }
    while running:
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.getcode() == 200:
                    pass
        except Exception as e:
            pass
        time.sleep(10.0)

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

def process_detections_and_infractions(detections, W, H, frame=None, simulate=False):
    """Processes detections and updates infraction timers with advanced behavior tracking & log throttling"""
    global tracked_persons
    current_time = time.time()
    
    # Map ROI coords to pixels
    roi_pixels = [[int(pt[0] * W), int(pt[1] * H)] for pt in ROI_POLYGON]
    
    # Extract bboxes by target class
    persons = []
    objects = []
    
    for det in detections:
        bbox = det["bbox"]
        cls = det["class"]
        
        # Center of the bbox
        cx = int(bbox[0] + bbox[2] / 2)
        cy = int(bbox[1] + bbox[3] / 2)
        
        # Bottom-center of the bbox (for ROI check)
        bcx = cx
        bcy = int(bbox[1] + bbox[3])
        
        # Check ROI intersection using bottom-center
        in_roi = is_point_in_polygon(bcx, bcy, roi_pixels)
        
        if cls == "person":
            persons.append({
                "track_id": det.get("track_id", 0),
                "center": (cx, cy),
                "conf": det["conf"],
                "in_roi": in_roi,
                "bbox": bbox
            })
        elif cls in ["handbag", "backpack", "bag", "suitcase", "briefcase", "cell phone", "snowboard", "skateboard", "umbrella", "elephant", "surfboard"]:
            objects.append({
                "center": (cx, cy),
                "conf": det["conf"],
                "in_roi": in_roi,
                "class": cls,
                "bbox": bbox
            })

    # Association & Update State
    with tracked_lock:
        detected_track_ids = set()
        
        for p in persons:
            track_id = p["track_id"]
            detected_track_ids.add(track_id)
            pcx, pcy = p["center"]
            px1, py1, pw, ph = p["bbox"]
            in_roi = p["in_roi"]
            
            # Initialize track if new
            if track_id not in tracked_persons:
                tracked_persons[track_id] = {
                    "start_time": current_time,
                    "last_seen": current_time,
                    "last_logged": 0.0,
                    "first_in_roi_time": current_time if in_roi else None,
                    "standing_still_start": None,
                    "accumulated_standing_still": 0.0,
                    "last_position": (pcx, pcy),
                    "position_history": [(pcx, pcy, current_time)],
                    "has_bag": False,
                    "bag_conf": 0.0,
                    "bag_type": "bag",
                    "bag_persistence_start": None,
                    "look_at_camera_duration": 0.0,
                    "last_look_at_camera_time": None,
                    "concealment_events": 0,
                    "last_concealment_event_time": 0.0,
                    "alerts_fired": set(),
                    "highest_risk_percentage": 0
                }
                print(f"[AI-INFO] Rastreando nova pessoa #{track_id} em ({pcx}, {pcy}). ROI={in_roi}")
                
            p_state = tracked_persons[track_id]
            p_state["last_seen"] = current_time
            
            # Update ROI lingering timer
            if in_roi:
                if p_state["first_in_roi_time"] is None:
                    p_state["first_in_roi_time"] = current_time
            else:
                p_state["first_in_roi_time"] = None
                
            # Update standing still / lingering heuristic
            p_state["position_history"].append((pcx, pcy, current_time))
            # prune history older than 5 seconds
            p_state["position_history"] = [pt for pt in p_state["position_history"] if current_time - pt[2] <= 5.0]
            
            # Find position ~3 seconds ago to check speed
            three_sec_ago_pos = None
            for pt in p_state["position_history"]:
                if 2.5 <= (current_time - pt[2]) <= 4.0:
                    three_sec_ago_pos = pt
                    break
                    
            if three_sec_ago_pos:
                old_x, old_y, _ = three_sec_ago_pos
                dist = math.sqrt((pcx - old_x) ** 2 + (pcy - old_y) ** 2)
                
                # Scale-invariant movement threshold: 18% of the person's bounding box maximum dimension
                movement_threshold = max(20.0, min(80.0, 0.18 * max(pw, ph)))
                
                if dist < movement_threshold:
                    if p_state["standing_still_start"] is None:
                        p_state["standing_still_start"] = current_time
                    else:
                        p_state["accumulated_standing_still"] = current_time - p_state["standing_still_start"]
                else:
                    # Decay standing still time slowly or reset it
                    p_state["standing_still_start"] = current_time # reset start timer to current time
                    p_state["accumulated_standing_still"] = max(0.0, p_state["accumulated_standing_still"] - 1.0)
            else:
                p_state["standing_still_start"] = current_time
            
            p_state["last_position"] = (pcx, pcy)
            
            # Check active bag / object association and concealment
            if "nearby_objects" not in p_state:
                p_state["nearby_objects"] = {} # class_name -> {"last_seen": t, "pos": (x,y)}
                
            obj_associated_in_frame = False
            current_nearby_classes = set()
            
            for obj in objects:
                ocx, ocy = obj["center"]
                ox1, oy1, ow, oh = obj["bbox"]
                obj_cls = obj["class"]
                
                # Distance between centers
                dist = math.sqrt((pcx - ocx) ** 2 + (pcy - ocy) ** 2)
                
                # Proximity check
                if dist < CONCEALMENT_DISTANCE_THRESHOLD:
                    p_state["has_bag"] = True
                    p_state["bag_conf"] = obj["conf"]
                    p_state["bag_type"] = obj_cls
                    p_state["bag_persistence_start"] = current_time
                    obj_associated_in_frame = True
                    
                    p_state["nearby_objects"][obj_cls] = {
                        "last_seen": current_time,
                        "pos": (ocx, ocy)
                    }
                    current_nearby_classes.add(obj_cls)
                    
                    # Real-time concealment heuristic: small object overlapping person's torso region
                    is_small_object = obj_cls in ["cell phone", "umbrella"]
                    if is_small_object:
                        if (py1 + 0.3*ph <= ocy <= py1 + 0.85*ph) and (px1 <= ocx <= px1 + pw):
                            if current_time - p_state["last_concealment_event_time"] > 5.0:
                                p_state["concealment_events"] += 1
                                p_state["last_concealment_event_time"] = current_time
                                print(f"[AI-ALERT] Ação de ocultamento detectada: Pessoa #{track_id} com objeto '{obj_cls}' na região corporal.")
            
            # Temporal concealment heuristic: small object disappears near person
            for old_cls, obj_info in list(p_state["nearby_objects"].items()):
                if old_cls not in current_nearby_classes:
                    time_since_seen = current_time - obj_info["last_seen"]
                    if time_since_seen < 1.8:
                        ox, oy = obj_info["pos"]
                        # Verify if disappearance happened near the person's torso region
                        if (py1 + 0.25*ph <= oy <= py1 + 0.85*ph) and (px1 - 20 <= ox <= px1 + pw + 20):
                            if current_time - p_state["last_concealment_event_time"] > 5.0:
                                p_state["concealment_events"] += 1
                                p_state["last_concealment_event_time"] = current_time
                                print(f"[AI-ALERT] Ocultamento Temporal: Objeto '{old_cls}' sumiu na área corporal da Pessoa #{track_id}!")
                    if time_since_seen > 3.0:
                        p_state["nearby_objects"].pop(old_cls, None)
            
            # Handle bag persistence if no bag detected in this frame
            if not obj_associated_in_frame:
                if p_state["bag_persistence_start"] is not None:
                    if current_time - p_state["bag_persistence_start"] > BAG_PERSISTENCE_DURATION:
                        p_state["has_bag"] = False
                        
            # Handle Face Detection (Gaze at camera)
            looking_at_camera = False
            if frame is not None:
                try:
                    # Crop upper 35% of person bbox
                    head_y2 = py1 + int(ph * 0.35)
                    if head_y2 > py1 and pw > 0 and head_y2 < H and px1 >= 0 and px1 + pw < W:
                        head_crop = frame[py1:head_y2, px1:px1+pw]
                        if head_crop.size > 0:
                            gray = cv2.cvtColor(head_crop, cv2.COLOR_BGR2GRAY)
                            # Frontal face cascade
                            if face_cascade is not None:
                                faces_front = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(15, 15))
                                if len(faces_front) > 0:
                                    looking_at_camera = True
                            # Profile face cascade
                            if not looking_at_camera and profile_cascade is not None:
                                faces_profile = profile_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(15, 15))
                                if len(faces_profile) > 0:
                                    looking_at_camera = True
                except Exception as ex:
                    pass
            elif simulate and frame is None:
                # Fallback to simulate look at camera in simulation mode
                if track_id % 2 == 0 and p_state["accumulated_standing_still"] > 3.0:
                    looking_at_camera = (int(current_time) % 3 == 0) # look every 3 seconds
                    
            if looking_at_camera:
                if p_state["last_look_at_camera_time"] is None:
                    p_state["last_look_at_camera_time"] = current_time
                else:
                    p_state["look_at_camera_duration"] += (current_time - p_state["last_look_at_camera_time"])
                    p_state["last_look_at_camera_time"] = current_time
            else:
                p_state["last_look_at_camera_time"] = None

            # Calculate Dynamic Risk Percentage (0% to 100%)
            risk_percentage = 0
            reasons = []
            
            # 1. Standing still (Loitering) in ROI
            still_s = p_state["accumulated_standing_still"]
            if still_s > 4.0:
                still_risk = min(35, int((still_s / 15.0) * 35))
                risk_percentage += still_risk
                reasons.append(f"Parado na ROI por {int(still_s)}s (+{still_risk}%)")
                
            # 2. Carrying bag
            if p_state["has_bag"]:
                risk_percentage += 15
                reasons.append("Portando sacola/mochila (+15%)")
                
            # 3. Gaze/Facing camera duration
            cam_s = p_state["look_at_camera_duration"]
            if cam_s > 3.0:
                cam_risk = min(15, int((cam_s / 8.0) * 15))
                risk_percentage += cam_risk
                reasons.append(f"Olhando p/ câmera por {int(cam_s)}s (+{cam_risk}%)")
                
            # 4. Concealment action
            if p_state["concealment_events"] > 0:
                conceal_risk = min(35, p_state["concealment_events"] * 35)
                risk_percentage += conceal_risk
                reasons.append(f"Movimento de ocultação detectado (+{conceal_risk}%)")
                
            risk_percentage = min(risk_percentage, 100)
            
            # Logging Throttling to prevent console flooding (Log once every 2s per person, or on state/risk spike)
            last_logged = p_state["last_logged"]
            risk_diff = abs(risk_percentage - p_state["highest_risk_percentage"])
            
            if (current_time - last_logged > 2.0) or (risk_diff >= 15) or (risk_percentage >= 70 and "critical" not in p_state["alerts_fired"]):
                p_state["last_logged"] = current_time
                p_state["highest_risk_percentage"] = max(p_state["highest_risk_percentage"], risk_percentage)
                
                reasons_str = "; ".join(reasons) if reasons else "Nenhuma ação suspeita"
                log_tag = "[AI-ALERT]" if risk_percentage >= 70 else ("[AI-WARNING]" if risk_percentage >= 40 else "[AI-MONITOR]")
                print(f"{log_tag} Pessoa #{track_id}: Risco={risk_percentage}% | ROI={in_roi} | Parado={still_s:.1f}s | Bolsa={p_state['has_bag']} | Olhar Câmera={cam_s:.1f}s | Motivos: {reasons_str}")

            # Send Alerts based on Risk thresholds
            # Critical Alert: Risk >= 70%
            if risk_percentage >= 70 and "critical" not in p_state["alerts_fired"]:
                p_state["alerts_fired"].add("critical")
                details = f"Detecção de Alto Risco de furto para a Pessoa #{track_id}. Motivos analisados pela IA: " + ", ".join(reasons)
                send_webhook_alert(
                    title=f"Alerta de Segurança - Risco Crítico ({risk_percentage}%)",
                    details=details,
                    severity="critical",
                    trigger_type="CONCEALMENT_ROI",
                    confidence=risk_percentage
                )
                
            # Warning Alert: 40% <= Risk < 70%
            elif 40 <= risk_percentage < 70 and "warning" not in p_state["alerts_fired"]:
                p_state["alerts_fired"].add("warning")
                details = f"Comportamento atípico detectado para a Pessoa #{track_id}. Fatores de risco: " + ", ".join(reasons)
                send_webhook_alert(
                    title=f"Aviso de Atenção - Risco Médio ({risk_percentage}%)",
                    details=details,
                    severity="warning",
                    trigger_type="SUSPICIOUS_BEHAVIOR",
                    confidence=risk_percentage
                )

        # Cleanup expired tracks (not seen for more than 4 seconds)
        expired_ids = []
        for tid, p_state in list(tracked_persons.items()):
            if current_time - p_state["last_seen"] > 4.0:
                expired_ids.append(tid)
                
        for tid in expired_ids:
            print(f"[AI-INFO] Pessoa #{tid} saiu de cena. Finalizando rastreamento.")
            tracked_persons.pop(tid, None)

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
                # Simulate cell phone in hand (near torso) from frame 12 to 180, then disappear
                if 12 <= frame_count <= 180:
                    detections.append({
                        "bbox": [870, 550, 30, 50],
                        "class": "cell phone",
                        "conf": 0.85
                    })

        # Process detections and infractions
        process_detections_and_infractions(detections, W, H, img_to_check, simulate)
        
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
    
    # Start Heartbeat Thread
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    
    try:
        pipeline.run_pipeline()
    except KeyboardInterrupt:
        print("\n[INFO] Encerrando pipeline...")
        running = False
        pipeline.stop()
        sys.exit(0)
