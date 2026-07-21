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
import collections
import subprocess
import shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import cv2
import numpy as np
from ultralytics import YOLO
import pg8000

# Global dictionary buffers for serving frames (camera_id -> bytes/data)
latest_clean_frames = {}
latest_ai_frames = {}
frames_to_process = {}
running = True

frame_lock = threading.Lock()
buffer_lock = threading.Lock()
recorders_lock = threading.Lock()

# Multi-camera thread registry and state
active_cameras = {}
cameras_watchdog_lock = threading.Lock()

# Multi-camera state tracking lists (camera_id -> lists)
circular_frame_buffers = {}
active_recorders = {}
tracked_persons = {} # camera_id -> dict of track_id -> state

RTSP_URL = ""
CAMERA_ID = ""
CAMERA_NAME = ""
TENANT_ID = "a7974ee4-329c-4c06-a57a-0377bcae242e" # João Pedro
N8N_WEBHOOK_URL = "http://144.91.121.55:5678/webhook/e5f6a7b8-cdbe-4712-a1f9-d892a01f30f6/webhook/aegiseye-alerts"
AI_SENSITIVITY = 75
AI_FPS = 10

ROI_ENABLED = True
LAST_ROI_MTIME = 0.0
CAMERA_CONFIGS = {}

def load_roi_config(camera_id=None):
    global ROI_POLYGON, ROI_ENABLED, LAST_ROI_MTIME, CAMERA_CONFIGS
    config_path = "config_roi.json"
    
    # Default fallback polygon
    default_poly = [
        [0.02, 0.02],
        [0.98, 0.02],
        [0.98, 0.98],
        [0.02, 0.98]
    ]
    
    if not os.path.exists(config_path):
        initial_config = {
            "camera_rois": {
                "default": {
                    "enabled": True,
                    "camera_type": "internal",
                    "polygon": default_poly
                }
            }
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(initial_config, f, indent=4)
            print("[CONFIG-ROI] Arquivo config_roi.json criado com os polígonos padrões.")
        except Exception as e:
            print(f"[CONFIG-ROI] Erro ao criar config_roi.json padrão: {e}")
            
    try:
        LAST_ROI_MTIME = os.path.getmtime(config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        rois = config.get("camera_rois", {})
        
        new_configs = {}
        for key, val in rois.items():
            if isinstance(val, dict):
                enabled = val.get("enabled", True)
                poly = val.get("polygon", [])
                cam_type = val.get("camera_type")
                if not cam_type:
                    cam_type = "external"
                    print(f"[CONFIG-ROI] [WARNING] Câmera '{key}' não possui 'camera_type' definido. Aplicando 'external' por segurança.")
                else:
                    cam_type = cam_type.lower()
                    if cam_type not in ["internal", "external"]:
                        cam_type = "external"
                        print(f"[CONFIG-ROI] [WARNING] Câmera '{key}' possui 'camera_type' inválido ({val.get('camera_type')}). Forçando 'external' por segurança.")
                
                new_configs[key] = {
                    "enabled": enabled,
                    "polygon": poly,
                    "camera_type": cam_type
                }
            else:
                # Format legacy lists of points
                print(f"[CONFIG-ROI] [WARNING] Câmera '{key}' está em formato legado de polígono simples. Aplicando 'external' por segurança.")
                new_configs[key] = {
                    "enabled": True,
                    "polygon": val,
                    "camera_type": "external"
                }
        
        # Safe default fallback key validation
        if "default" not in new_configs:
            new_configs["default"] = {
                "enabled": True,
                "polygon": default_poly,
                "camera_type": "external"
            }
            
        CAMERA_CONFIGS = new_configs
        
        # Update legacy globals for default compatibility
        target_key = "default"
        if camera_id and camera_id in CAMERA_CONFIGS:
            target_key = camera_id
        
        cfg = CAMERA_CONFIGS.get(target_key) or CAMERA_CONFIGS.get("default")
        if cfg:
            ROI_ENABLED = cfg["enabled"]
            ROI_POLYGON = cfg["polygon"]
            
        print(f"[CONFIG-ROI] Configurações de ROI e tipos de câmera carregadas para {len(CAMERA_CONFIGS)} canais.")
    except Exception as e:
        CAMERA_CONFIGS = {
            "default": {
                "enabled": True,
                "polygon": default_poly,
                "camera_type": "external"
            }
        }
        ROI_ENABLED = True
        ROI_POLYGON = default_poly
        print(f"[CONFIG-ROI] Falha ao carregar config_roi.json: {e}. Usando fallback seguro.")

def check_and_reload_roi_config(camera_id=None):
    global CAMERA_CONFIGS, LAST_ROI_MTIME
    config_path = "config_roi.json"
    if not os.path.exists(config_path):
        return
    try:
        mtime = os.path.getmtime(config_path)
        if mtime != LAST_ROI_MTIME:
            LAST_ROI_MTIME = mtime
            print("[CONFIG-ROI] Alteração física detectada em config_roi.json. Recarregando configurações...")
            load_roi_config(camera_id)
    except Exception as e:
        print(f"[CONFIG-ROI] Erro ao recarregar config_roi.json pelo watchdog: {e}")

def get_camera_config(camera_id):
    # Retrieve configuration dynamically
    check_and_reload_roi_config(camera_id)
    
    cfg = CAMERA_CONFIGS.get(camera_id)
    if not cfg:
        cfg = CAMERA_CONFIGS.get("default")
    if not cfg:
        cfg = {
            "enabled": True,
            "polygon": [[0.02, 0.02], [0.98, 0.02], [0.98, 0.98], [0.02, 0.98]],
            "camera_type": "external"
        }
    return cfg

def roi_watchdog_loop(camera_id):
    while running:
        check_and_reload_roi_config(camera_id)
        time.sleep(2.0)

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

def is_point_in_polygon(point, polygon):
    """Ray-casting algorithm in Python for geometry check (Point in Polygon)"""
    x, y = point
    poly = polygon
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

last_cleanup_time = 0.0

def cleanup_old_evidence_clips():
    global last_cleanup_time
    now = time.time()
    if now - last_cleanup_time < 300.0: # Run every 5 minutes for quick response
        return
    last_cleanup_time = now
    
    evidence_dir = "evidencias"
    if not os.path.exists(evidence_dir):
        return
        
    print("[EVIDENCE-CLEANUP] Iniciando limpeza e monitoramento de espaço de evidências...")
    try:
        # 1. Clear files older than 2 days
        count = 0
        limit_sec = 2 * 24 * 3600 # 2 days
        files = []
        for filename in os.listdir(evidence_dir):
            filepath = os.path.join(evidence_dir, filename)
            if os.path.isfile(filepath):
                mtime = os.path.getmtime(filepath)
                size = os.path.getsize(filepath)
                if now - mtime > limit_sec:
                    os.remove(filepath)
                    count += 1
                else:
                    files.append((filepath, mtime, size))
                    
        if count > 0:
            print(f"[EVIDENCE-CLEANUP] Removidos {count} clipes de evidência antigos expirados (mais de 2 dias).")
            
        # 2. Strict storage size limit check (Max 300 MB)
        total_size = sum(f[2] for f in files)
        MAX_STORAGE_BYTES = 300 * 1024 * 1024 # 300 MB
        if total_size > MAX_STORAGE_BYTES:
            # Sort files by modification time (oldest first)
            files.sort(key=lambda x: x[1])
            freed = 0
            removed_count = 0
            for filepath, mtime, size in files:
                os.remove(filepath)
                freed += size
                removed_count += 1
                if total_size - freed <= 150 * 1024 * 1024: # Target size: 150 MB
                    break
            print(f"[EVIDENCE-CLEANUP] Armazenamento excedeu limite! Removidos {removed_count} arquivos mais antigos para liberar {freed / (1024*1024):.1f} MB.")
            
    except Exception as e:
        print(f"[EVIDENCE-CLEANUP] Erro durante a limpeza: {e}")

def write_video_ffmpeg(frames, filepath, fps=15):
    if not frames:
        return
    h, w, _ = frames[0].shape
    
    # Try using FFmpeg first
    cmd = [
        'ffmpeg',
        '-y', # Overwrite file
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-s', f'{w}x{h}',
        '-pix_fmt', 'bgr24',
        '-r', str(fps),
        '-i', '-', # Pipe input
        '-an', # No audio
        '-vcodec', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', 'veryfast',
        '-crf', '28', # Small file size
        filepath
    ]
    
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for f in frames:
            proc.stdin.write(f.tobytes())
        proc.stdin.close()
        proc.wait()
        if proc.returncode == 0 and os.path.exists(filepath):
            print(f"[EVIDENCE] Clipe de evidência salvo via FFmpeg em {filepath} ({len(frames)} frames)")
            return
    except Exception as e:
        print(f"[EVIDENCE] FFmpeg falhou ou não está instalado: {e}. Tentando OpenCV VideoWriter fallback...")

    # Fallback: encode via OpenCV VideoWriter
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Universal fallback for MP4 container
        out = cv2.VideoWriter(filepath, fourcc, fps, (w, h))
        for f in frames:
            out.write(f)
        out.release()
        if os.path.exists(filepath):
            print(f"[EVIDENCE] Clipe de evidência salvo via OpenCV em {filepath} ({len(frames)} frames)")
        else:
            print(f"[EVIDENCE] Falha ao criar arquivo de vídeo com OpenCV em {filepath}")
    except Exception as ex:
        print(f"[EVIDENCE] Erro ao gravar vídeo com OpenCV fallback: {ex}")

def upload_file_tmpfiles(file_path):
    """Uploads local file to tmpfiles.org via anonymous POST and returns the direct download URL"""
    import urllib.request
    import uuid
    
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    filename = os.path.basename(file_path)
    
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
            
        part_header = (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            f"Content-Type: video/mp4\r\n\r\n"
        ).encode('utf-8')
        
        part_footer = f"\r\n--{boundary}--\r\n".encode('utf-8')
        body = part_header + file_content + part_footer
        
        req = urllib.request.Request(
            "https://tmpfiles.org/api/v1/upload",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        
        with urllib.request.urlopen(req, timeout=30) as res:
            response_data = res.read().decode('utf-8')
            
        response_json = json.loads(response_data)
        if response_json.get("status") == "success":
            raw_url = response_json["data"]["url"]
            dl_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            print(f"[EVIDENCE] Upload concluído com sucesso: {dl_url}")
            return dl_url
        else:
            print(f"[EVIDENCE] Erro no upload (API tmpfiles): {response_json}")
    except Exception as e:
        print(f"[EVIDENCE] Falha ao fazer upload da evidência: {e}")
        
    return f"http://127.0.0.1:8082/evidencias/{filename}"

def finalize_evidence_clip(camera_id, frames, track_id, trigger_type, event_time, n8n_context):
    evidence_dir = "evidencias"
    os.makedirs(evidence_dir, exist_ok=True)
    cleanup_old_evidence_clips()
    
    filename = f"evidence_{camera_id}_{track_id}_{int(event_time)}.mp4"
    filepath = os.path.join(evidence_dir, filename)
    
    # Save optimized H.264 video
    write_video_ffmpeg(frames, filepath, fps=15)
    
    # Upload and obtain cloud URL
    video_url = upload_file_tmpfiles(filepath)
    
    # Send the final webhook with the uploaded video URL
    send_webhook_alert(
        title=n8n_context["title"],
        details=n8n_context["details"],
        severity=n8n_context["severity"],
        trigger_type=trigger_type,
        confidence=n8n_context["confidence"],
        tenant_id=n8n_context["tenant_id"],
        camera_id=n8n_context["camera_id"],
        camera_name=n8n_context["camera_name"],
        user_id=n8n_context["user_id"],
        track_id=track_id,
        video_url=video_url,
        frame_base64=n8n_context.get("frame_base64")
    )

def trigger_evidence_and_alert(title, details, severity, trigger_type, confidence, tenant_id, camera_id, camera_name, user_id, track_id, frame=None):
    global circular_frame_buffers, active_recorders
    print(f"[TRIGGER] Alerta enviado ao webhook para a câmera '{camera_name}' (ID: {camera_id})")
    
    if camera_id not in circular_frame_buffers:
        circular_frame_buffers[camera_id] = collections.deque()
    if camera_id not in active_recorders:
        active_recorders[camera_id] = []
        
    # Take snapshot of the last 10 seconds of frames from circular buffer
    with buffer_lock:
        pre_frames = [f[1] for f in circular_frame_buffers[camera_id]]
        
    print(f"[EVIDENCE] Iniciada gravação de clipe de evidência para a Pessoa #{track_id} na câmera {camera_name} (10s antes + 5s depois)...")
    
    frame_b64 = None
    if frame is not None:
        try:
            _, jpeg_img = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            import base64
            frame_b64 = base64.b64encode(jpeg_img).decode('utf-8')
        except Exception as e:
            print(f"[EVIDENCE ERROR] Erro ao codificar frame para base64: {e}")
            
    with recorders_lock:
        active_recorders[camera_id].append({
            "track_id": track_id,
            "trigger_type": trigger_type,
            "event_time": time.time(),
            "frames": list(pre_frames),
            "n8n_context": {
                "title": title,
                "details": details,
                "severity": severity,
                "confidence": confidence,
                "tenant_id": tenant_id,
                "camera_id": camera_id,
                "camera_name": camera_name,
                "user_id": user_id,
                "frame_base64": frame_b64
            }
        })

def add_frame_to_buffers(camera_id, resized_frame):
    global circular_frame_buffers, active_recorders
    now = time.time()
    
    if camera_id not in circular_frame_buffers:
        circular_frame_buffers[camera_id] = collections.deque()
    if camera_id not in active_recorders:
        active_recorders[camera_id] = []
        
    # 1. Update circular buffer (keep last 10 seconds)
    with buffer_lock:
        buf = circular_frame_buffers[camera_id]
        buf.append((now, resized_frame))
        while buf and (now - buf[0][0] > 10.0):
            buf.popleft()
            
    # 2. Feed active recorders (post-event frames for next 5 seconds)
    with recorders_lock:
        still_active = []
        for rec in active_recorders[camera_id]:
            rec["frames"].append(resized_frame)
            if now - rec["event_time"] >= 5.0:
                # Trigger evidence video encoding & upload
                threading.Thread(
                    target=finalize_evidence_clip,
                    args=(camera_id, rec["frames"], rec["track_id"], rec["trigger_type"], rec["event_time"], rec["n8n_context"]),
                    daemon=True
                ).start()
            else:
                still_active.append(rec)
        active_recorders[camera_id] = still_active

def send_webhook_alert(title, details, severity="critical", trigger_type="CONCEALMENT_ROI", confidence=90.0, tenant_id=None, camera_id=None, camera_name=None, user_id=None, track_id=None, video_url=None, frame_base64=None):
    """Sends the alert metadata payload to n8n backend webhook asynchronously"""
    # Strict validation of confidence and trigger_type/risk_type
    if (confidence is None or trigger_type is None or 
        str(confidence).lower() in ['none', 'undefined', 'nan', ''] or 
        str(trigger_type).lower() in ['none', 'undefined', '']):
        print(f"[API] [ALERT SKIPPED] Alerta descartado devido a campos confidence ou risk_type invalidos (confidence={confidence}, trigger_type={trigger_type})")
        return

    import datetime
    current_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    t_id = tenant_id or TENANT_ID
    c_id = camera_id or CAMERA_ID
    c_name = camera_name or CAMERA_NAME

    # Fallback DB query if camera_id is empty/null
    if not c_id or str(c_id).lower() in ['none', 'undefined', 'null', '']:
        print(f"[API] [FALLBACK] camera_id vazio no envio de alerta. Buscando camera de fallback para o tenant {t_id} no banco...")
        try:
            import pg8000
            conn = pg8000.connect(
                host="144.91.121.55",
                port=5432,
                user="postgres",
                password="KtnYcxnVOGjD4thzS6tlBcW9",
                database="aegisyear",
                timeout=5
            )
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM public.cameras WHERE tenant_id = %s LIMIT 1", (str(t_id),))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                c_id = str(row[0])
                if not c_name or c_name == "":
                    c_name = str(row[1])
                print(f"[API] [FALLBACK SUCCESS] Usando camera de fallback: {c_name} (ID: {c_id})")
            else:
                print(f"[API] [FALLBACK WARNING] Nenhuma camera cadastrada para o tenant {t_id}. Usando UUID padrao.")
                c_id = "00000000-0000-0000-0000-000000000000"
        except Exception as e:
            print(f"[API] [FALLBACK ERROR] Falha ao consultar camera de fallback: {e}. Usando UUID padrao.")
            c_id = "00000000-0000-0000-0000-000000000000"

    payload = {
        "tenant_id": t_id,
        "user_id": user_id,
        "camera_id": c_id,
        "camera_name": c_name,
        "severity": severity,
        "risk_level": severity,
        "title": title,
        "details": details,
        "confidence": float(confidence),
        "confidence_score": float(confidence),
        "trigger_type": trigger_type,
        "risk_type": trigger_type,
        "track_id": track_id,
        "url_video": video_url, # cloud url of evidence
        "evento": trigger_type,   # furto_detectado/CONCEALMENT_ROI
        "timestamp": current_timestamp,
        "frame_base64": frame_base64
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
                print(f"[WEBHOOK DISPATCHED] ID: {track_id} | Confidence: {confidence} | Event: {trigger_type}")
        except Exception as ex:
            print(f"[API] Erro ao enviar alerta para o n8n: {ex}. Iniciando fallback de inserção direta no Banco de Dados...")
            try:
                import pg8000
                import uuid
                conn = pg8000.connect(
                    host="144.91.121.55",
                    port=5432,
                    user="postgres",
                    password="KtnYcxnVOGjD4thzS6tlBcW9",
                    database="aegisyear",
                    timeout=5
                )
                cursor = conn.cursor()
                
                u_id = user_id
                if u_id and str(u_id).lower() in ['none', 'undefined', 'null', '']:
                    u_id = None
                
                alert_uuid = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO public.alertas (
                        id, tenant_id, user_id, camera_id, camera_name, severity, title, details, confidence_score, risk_type, track_id, video_url, timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    alert_uuid, str(t_id), str(u_id) if u_id else None, str(c_id) if c_id else None, str(c_name), 
                    str(severity), str(title), str(details), float(confidence), str(trigger_type), 
                    int(track_id) if track_id is not None else None, str(video_url) if video_url else None,
                    current_timestamp
                ))
                conn.commit()
                cursor.close()
                conn.close()
                print(f"[DB FALLBACK] Alerta inserido diretamente via conexão direta do Banco de Dados com sucesso! ID: {alert_uuid}")
            except Exception as dbe:
                print(f"[DB FALLBACK ERROR] Falha grave ao tentar inserir alerta diretamente no banco de dados: {dbe}")

    threading.Thread(target=post_req, daemon=True).start()

def load_db_config(tenant_id):
    global N8N_WEBHOOK_URL, AI_SENSITIVITY, AI_FPS
    try:
        conn = pg8000.connect(
            host="144.91.121.55",
            port=5432,
            user="postgres",
            password="KtnYcxnVOGjD4thzS6tlBcW9",
            database="aegisyear",
            timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ai_sensitivity, ai_fps, n8n_webhook_url 
            FROM public.configuracoes 
            WHERE tenant_id = %s;
        """, (str(tenant_id),))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            AI_SENSITIVITY = int(row[0]) if row[0] is not None else 75
            AI_FPS = int(row[1]) if row[1] is not None else 10
            if row[2]:
                webhook_url = row[2]
                if "127.0.0.1" in webhook_url or "localhost" in webhook_url:
                    webhook_url = webhook_url.replace("127.0.0.1", "144.91.121.55").replace("localhost", "144.91.121.55")
                N8N_WEBHOOK_URL = webhook_url
            print(f"[CONFIG] Configurações da IA carregadas do banco: Sensibilidade={AI_SENSITIVITY}%, FPS={AI_FPS}, Webhook={N8N_WEBHOOK_URL}")
    except Exception as e:
        print(f"[CONFIG WARNING] Erro ao carregar configurações do banco, utilizando padrões: {e}")

def heartbeat_loop():
    """Periodically sends an online heartbeat signal to the central dashboard VPS"""
    print("[HEARTBEAT] Iniciando loop de sinal de presença (heartbeat)...")
    url = "http://144.91.121.55:8000/api/edge-ping"
    while running:
        cleanup_old_evidence_clips()
        payload = {
            "tenant_id": TENANT_ID,
            "camera_name": CAMERA_NAME,
            "status": "online"
        }
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
                        active_streams[rtsp_url]["raw_frame"] = frame.copy()
                        active_streams[rtsp_url]["new_frame"] = True
                    else:
                        break
                time.sleep(0.033)
            else:
                # Open container and decode frames using PyAV
                try:
                    container = av.open(rtsp_url, options={
                        'rtsp_transport': 'tcp',
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
                                active_streams[rtsp_url]["raw_frame"] = img.copy()
                                active_streams[rtsp_url]["new_frame"] = True
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
        
        # Serve local evidence video files static fallback
        if parsed_url.path.startswith('/evidencias/'):
            filename = os.path.basename(parsed_url.path)
            filepath = os.path.join("evidencias", filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'video/mp4')
                    self.send_header('Content-Length', str(len(content)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Private-Network', 'true')
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(f"Erro ao ler evidência: {e}".encode())
                    return
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Arquivo de evidencia nao encontrado.")
                return

        # Serve Desktop UI
        if parsed_url.path == '/':
            try:
                if hasattr(sys, '_MEIPASS'):
                    base_dir = sys._MEIPASS
                    actual_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    actual_dir = base_dir
                
                ui_path = os.path.join(base_dir, 'desktop_ui.html')
                if not os.path.exists(ui_path):
                    ui_path = os.path.join(actual_dir, 'desktop_ui.html')
                if not os.path.exists(ui_path):
                    ui_path = os.path.join(actual_dir, '..', 'desktop_ui.html')
                    
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

        if parsed_url.path == '/style.css':
            try:
                if hasattr(sys, '_MEIPASS'):
                    base_dir = sys._MEIPASS
                    actual_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    actual_dir = base_dir
                
                css_path = os.path.join(base_dir, 'frontend', 'style.css')
                if not os.path.exists(css_path):
                    css_path = os.path.join(base_dir, 'style.css')
                if not os.path.exists(css_path):
                    css_path = os.path.join(actual_dir, 'frontend', 'style.css')
                if not os.path.exists(css_path):
                    css_path = os.path.join(actual_dir, '..', 'frontend', 'style.css')
                if not os.path.exists(css_path):
                    css_path = os.path.join(actual_dir, 'style.css')
                if not os.path.exists(css_path):
                    css_path = os.path.join(actual_dir, '..', 'style.css')
                    
                with open(css_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/css; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Private-Network', 'true')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Erro ao carregar CSS: {e}".encode())
            return

        # Serve Live Clean Stream (Used by both Web and Desktop clients, smooth 30 FPS)
        if parsed_url.path in ['/stream', '/stream_ai']:
            query_params = urllib.parse.parse_qs(parsed_url.query)
            camera_id = query_params.get('camera_id', [''])[0].strip() or 'default'
            
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Private-Network', 'true')
            self.end_headers()
            
            last_served_frame = None
            try:
                while True:
                    frame_data = None
                    with frame_lock:
                        if parsed_url.path == '/stream_ai':
                            frame_data = latest_ai_frames.get(camera_id) or latest_clean_frames.get(camera_id)
                            if not frame_data and latest_ai_frames:
                                frame_data = next(iter(latest_ai_frames.values()), None)
                            if not frame_data and latest_clean_frames:
                                frame_data = next(iter(latest_clean_frames.values()), None)
                        else:
                            frame_data = latest_clean_frames.get(camera_id)
                            if not frame_data and latest_clean_frames:
                                frame_data = next(iter(latest_clean_frames.values()), None)
                            
                    if frame_data is None:
                        frame = np.zeros((360, 640, 3), dtype=np.uint8)
                        cv2.putText(frame, "CONECTANDO AO FLUXO DA IA...", (170, 180),
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

def process_skeleton_keypoints(person_keypoints, objects):
    """
    [FUTURE YOLOv8-POSE INTEGRATION STUB]
    Esta função processará os pontos do esqueleto (keypoints) da pessoa e comparará
    as coordenadas dos membros superiores (como pulsos e mãos) com as bounding boxes dos produtos.
    
    COCO Keypoints de Interesse:
    - 9: Left Wrist (Pulso Esquerdo)
    - 10: Right Wrist (Pulso Direito)
    - 7: Left Elbow (Cotovelo Esquerdo)
    - 8: Right Elbow (Cotovelo Direito)
    """
    if person_keypoints is not None:
        for kp in person_keypoints:
            # Exemplo de extração de pontos:
            # left_wrist = kp[9]   # (x, y, conf)
            # right_wrist = kp[10] # (x, y, conf)
            # 
            # for obj in objects:
            #     ox1, oy1, ow, oh = obj["bbox"]
            #     ox2, oy2 = ox1 + ow, oy1 + oh
            #     
            #     # Interseção do esqueleto da mão com bounding box do produto
            #     if (ox1 <= left_wrist[0] <= ox2 and oy1 <= left_wrist[1] <= oy2) or \
            #        (ox1 <= right_wrist[0] <= ox2 and oy1 <= right_wrist[1] <= oy2):
            #         print(f"[POSE-INFO] Mão/pulso intersectando objeto {obj['class']}!")
            pass

def process_detections_and_infractions(detections, W, H, frame=None, simulate=False, camera_name=None, camera_id=None, tenant_id=None, user_id=None, rtsp_url=None, weapon_detections=None, pose_model=None):
    """Processes detections and updates infraction timers with advanced behavior tracking & log throttling"""
    global tracked_persons
    current_time = time.time()
    
    if camera_id not in tracked_persons:
        tracked_persons[camera_id] = {}
    cam_tracked = tracked_persons[camera_id]
    
    # Load configuration dynamically based on camera_id
    cam_cfg = get_camera_config(camera_id)
    roi_enabled = cam_cfg["enabled"]
    roi_polygon = cam_cfg["polygon"]
    camera_type = cam_cfg["camera_type"] # 'internal' or 'external'
    
    # Map ROI coords to pixels
    roi_pixels = [[int(pt[0] * W), int(pt[1] * H)] for pt in roi_polygon]
    
    # Target product classes in COCO
    PRODUCT_CLASSES = ["bottle", "wine glass", "cup", "book", "cell phone", "scissors", "toothbrush", "can", "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake"]
    
    # Helper to calculate box overlap
    def boxes_overlap(boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
        yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        return interArea > 0

    # Extract bboxes by target class
    persons = []
    objects = []
    products = []
    
    # Early ROI polygon filter before any behavior analysis
    for det in detections:
        bbox = det["bbox"]
        cls = det["class"]
        
        # Center of the bbox
        cx = int(bbox[0] + bbox[2] / 2)
        cy = int(bbox[1] + bbox[3] / 2)
        
        # Check ROI intersection using centroid (centroide)
        in_roi = is_point_in_polygon((cx, cy), roi_pixels)
        
        # Decide if the detection is accepted:
        # If ROI is not enabled, we accept all detections.
        # If ROI is enabled, we only accept detections inside the ROI polygon.
        is_accepted = (not roi_enabled) or in_roi
        
        if cls == "person":
            if is_accepted:
                persons.append({
                    "track_id": det.get("track_id", 0),
                    "center": (cx, cy),
                    "conf": det["conf"],
                    "in_roi": in_roi,
                    "bbox": bbox
                })
        elif cls in ["handbag", "backpack", "bag", "suitcase", "briefcase"]:
            if is_accepted:
                objects.append({
                    "center": (cx, cy),
                    "conf": det["conf"],
                    "in_roi": in_roi,
                    "class": cls,
                    "bbox": bbox
                })
        elif cls in PRODUCT_CLASSES:
            if is_accepted:
                products.append({
                    "center": (cx, cy),
                    "conf": det["conf"],
                    "in_roi": in_roi,
                    "class": cls,
                    "bbox": bbox
                })

    # Association & Update State
    with tracked_lock:
        detected_track_ids = set()
        
        # Process weapon threats immediately
        associated_weapons = {} # track_key -> weapon conf
        if weapon_detections and persons:
            for w_det in weapon_detections:
                w_bbox = w_det["bbox"]
                wcx = w_bbox[0] + w_bbox[2]/2
                wcy = w_bbox[1] + w_bbox[3]/2
                
                # Find the closest person
                closest_p = None
                min_d = float('inf')
                for p in persons:
                    pcx, pcy = p["center"]
                    d = math.sqrt((pcx - wcx)**2 + (pcy - wcy)**2)
                    if d < min_d:
                        min_d = d
                        closest_p = p
                
                if closest_p:
                    p_tid = closest_p["track_id"]
                    p_key = f"{camera_name or CAMERA_NAME}_{p_tid}"
                    associated_weapons[p_key] = w_det["conf"]

        for p in persons:
            track_id = p["track_id"]
            track_key = f"{camera_name or CAMERA_NAME}_{track_id}"
            detected_track_ids.add(track_key)
            pcx, pcy = p["center"]
            px1, py1, pw, ph = p["bbox"]
            in_roi = p["in_roi"]
            
            # Initialize track if new
            if track_key not in cam_tracked:
                cam_tracked[track_key] = {
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
                    "highest_risk_percentage": 0,
                    "detection_conf": p["conf"],
                    "missing_frames": 0,
                    "conf_history": [p["conf"]],
                    "last_alert_time": 0.0,
                    "product_overlap_timers": {},
                    "proximity_product_detected": False,
                    "last_proximity_product_time": 0.0
                }
                print(f"[AI-INFO] Rastreando nova pessoa #{track_id} em ({pcx}, {pcy}). ROI={in_roi}")
                
            p_state = cam_tracked[track_key]
            p_state["last_seen"] = current_time
            p_state["detection_conf"] = p["conf"]
            if "conf_history" not in p_state:
                p_state["conf_history"] = []
            p_state["conf_history"].append(p["conf"])
            if len(p_state["conf_history"]) > 3:
                p_state["conf_history"].pop(0)
            
            # Update ROI lingering timer
            if in_roi:
                if p_state["first_in_roi_time"] is None:
                    p_state["first_in_roi_time"] = current_time
            else:
                p_state["first_in_roi_time"] = None
                
            # Log monitored track details for validation
            duration_in_roi = 0.0
            if p_state.get("first_in_roi_time") is not None:
                duration_in_roi = current_time - p_state["first_in_roi_time"]
            print(f"[SCANNING] Analisando frame... Pessoa detectada: {track_id} | Dentro da ROI: {in_roi}")
            print(f"[DEBUG-TRACK] Monitorando track_id: {track_id} em ({pcx}, {pcy}) | ROI={in_roi} | Duracao na ROI={duration_in_roi:.1f}s")
                
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
            
            # -------------------------------------------------------------
            # RULE: Object Proximity (Permanência sobre produto > 3 segundos)
            # -------------------------------------------------------------
            overlapping_products = []
            if camera_type == 'internal':
                for prod in products:
                    if boxes_overlap(p["bbox"], prod["bbox"]):
                        overlapping_products.append(prod)
                        
                if "product_overlap_timers" not in p_state:
                    p_state["product_overlap_timers"] = {}
                    
                current_overlap_keys = set()
                for prod in overlapping_products:
                    prod_cls = prod["class"]
                    pr_cx, pr_cy = prod["center"]
                    prod_key = f"{prod_cls}_{int(pr_cx/30)}_{int(pr_cy/30)}"
                    current_overlap_keys.add(prod_key)
                    
                    if prod_key not in p_state["product_overlap_timers"]:
                        p_state["product_overlap_timers"][prod_key] = current_time
                    else:
                        overlap_time = current_time - p_state["product_overlap_timers"][prod_key]
                        if overlap_time >= 3.0:
                            p_state["proximity_product_detected"] = True
                            p_state["last_proximity_product_time"] = current_time
                            print(f"[AI-POSE] Pessoa #{track_id} em proximidade prolongada com produto '{prod_cls}' por {overlap_time:.1f}s.")
                            
                # Cleanup timers for products no longer overlapping
                for pk in list(p_state["product_overlap_timers"].keys()):
                    if pk not in current_overlap_keys:
                        p_state["product_overlap_timers"].pop(pk, None)
            
            # Check active bag / object association and concealment
            process_skeleton_keypoints(None, objects)
            
            obj_associated_in_frame = False
            if camera_type == 'internal':
                if "nearby_objects" not in p_state:
                    p_state["nearby_objects"] = {} # class_name -> {"last_seen": t, "pos": (x,y)}
                    
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
                
                # Temporal concealment heuristic: small object disappears near person
                for old_cls, obj_info in list(p_state["nearby_objects"].items()):
                    if old_cls not in current_nearby_classes:
                        time_since_seen = current_time - obj_info["last_seen"]
                        if time_since_seen < 1.8:
                            ox, oy = obj_info["pos"]
                            # Verify if disappearance happened near the person's torso region
                            if (py1 + 0.25*ph <= oy <= py1 + 0.85*ph) and (px1 - 20 <= ox <= px1 + pw + 20):
                                # Duration filter: only flag if loitered in ROI for >= 5s
                                duration_in_roi = 0.0
                                if p_state.get("first_in_roi_time") is not None:
                                    duration_in_roi = current_time - p_state["first_in_roi_time"]
                                    
                                if duration_in_roi >= 5.0:
                                    if current_time - p_state["last_concealment_event_time"] > 5.0:
                                        p_state["concealment_events"] += 1
                                        p_state["last_concealment_event_time"] = current_time
                                        print(f"[AI-ALERT] Ocultamento Temporal: Objeto '{old_cls}' sumiu na área corporal da Pessoa #{track_id}!")
                                else:
                                    print(f"[AI-INFO] Ocultamento temporal ignorado (trânsito rápido): Pessoa #{track_id} está na ROI há apenas {duration_in_roi:.1f}s (mínimo 5s).")
                        if time_since_seen > 3.0:
                            p_state["nearby_objects"].pop(old_cls, None)
                
                # Handle bag persistence if no bag detected in this frame
                if not obj_associated_in_frame:
                    if p_state["bag_persistence_start"] is not None:
                        if current_time - p_state["bag_persistence_start"] > BAG_PERSISTENCE_DURATION:
                            p_state["has_bag"] = False
                            
            # Handle Face Detection (Gaze at camera)
            looking_at_camera = False
            if camera_type == 'internal':
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

            # -------------------------------------------------------------
            # RULE: YOLOv8-pose based concealment verification
            # -------------------------------------------------------------
            hand_movement_to_hide = False
            if camera_type == 'internal' and p_state.get("proximity_product_detected", False) and frame is not None:
                # Run pose estimation on cropped person bounding box
                try:
                    x1_c = max(0, px1)
                    y1_c = max(0, py1)
                    x2_c = min(W, px1 + pw)
                    y2_c = min(H, py1 + ph)
                    person_crop = frame[y1_c:y2_c, x1_c:x2_c]
                    
                    if person_crop.size > 0 and pose_model is not None:
                        pose_results = pose_model(person_crop, verbose=False)
                        if len(pose_results) > 0 and pose_results[0].keypoints is not None:
                            keypoints = pose_results[0].keypoints.xy.cpu().numpy()[0] # shape (17, 2)
                            
                            # Wrist, Hip and Shoulder coordinates inside the cropped frame
                            left_wrist = keypoints[9] if len(keypoints) > 9 else [0, 0]
                            right_wrist = keypoints[10] if len(keypoints) > 10 else [0, 0]
                            left_hip = keypoints[11] if len(keypoints) > 11 else [0, 0]
                            right_hip = keypoints[12] if len(keypoints) > 12 else [0, 0]
                            left_shoulder = keypoints[5] if len(keypoints) > 5 else [0, 0]
                            right_shoulder = keypoints[6] if len(keypoints) > 6 else [0, 0]
                            
                            crop_h = y2_c - y1_c
                            pocket_dist_thresh = 0.20 * crop_h
                            
                            # Check 1: Wrist close to hips (pockets)
                            if left_wrist[0] > 0 and left_wrist[1] > 0:
                                for hip in [left_hip, right_hip]:
                                    if hip[0] > 0 and hip[1] > 0:
                                        d = math.sqrt((left_wrist[0] - hip[0])**2 + (left_wrist[1] - hip[1])**2)
                                        if d < pocket_dist_thresh:
                                            hand_movement_to_hide = True
                                            print(f"[AI-POSE] Mao esquerda proxima ao bolso/quadril detectada para Pessoa #{track_id}!")
                                            
                            if right_wrist[0] > 0 and right_wrist[1] > 0:
                                for hip in [left_hip, right_hip]:
                                    if hip[0] > 0 and hip[1] > 0:
                                        d = math.sqrt((right_wrist[0] - hip[0])**2 + (right_wrist[1] - hip[1])**2)
                                        if d < pocket_dist_thresh:
                                            hand_movement_to_hide = True
                                            print(f"[AI-POSE] Mao direita proxima ao bolso/quadril detectada para Pessoa #{track_id}!")
                                            
                            # Check 2: Wrist inside central torso box (pocket/jacket concealment)
                            if not hand_movement_to_hide:
                                for wrist in [left_wrist, right_wrist]:
                                    if wrist[0] > 0 and wrist[1] > 0:
                                        min_y = min(left_shoulder[1], right_shoulder[1]) if (left_shoulder[1] > 0 and right_shoulder[1] > 0) else 0.1 * crop_h
                                        max_y = max(left_hip[1], right_hip[1]) if (left_hip[1] > 0 and right_hip[1] > 0) else 0.8 * crop_h
                                        if min_y < wrist[1] < max_y:
                                            # wrist x within central 60% of crop width
                                            if 0.2 * pw < wrist[0] < 0.8 * pw:
                                                hand_movement_to_hide = True
                                                print(f"[AI-POSE] Mao detectada na area do torso (jaqueta) para Pessoa #{track_id}!")
                                                
                            # Check 3: Wrist near a handbag/backpack
                            if not hand_movement_to_hide:
                                for wrist in [left_wrist, right_wrist]:
                                    if wrist[0] > 0 and wrist[1] > 0:
                                        abs_wx = wrist[0] + x1_c
                                        abs_wy = wrist[1] + y1_c
                                        for obj in objects:
                                            ox1, oy1, ow, oh = obj["bbox"]
                                            if (ox1 - 20 <= abs_wx <= ox1 + ow + 20) and (oy1 - 20 <= abs_wy <= oy1 + oh + 20):
                                                hand_movement_to_hide = True
                                                print(f"[AI-POSE] Mao detectada em direcao a bolsa/mochila '{obj['class']}' para Pessoa #{track_id}!")
                except Exception as pose_err:
                    print(f"[AI-POSE ERROR] Falha no processamento pose_model: {pose_err}")
                    
            if hand_movement_to_hide:
                p_state["concealment_events"] += 1
                p_state["last_concealment_event_time"] = current_time
                print(f"[AI-ALERT] FURTO EM ANDAMENTO: Suspeita critica de ocultação pos proximidade de produto para Pessoa #{track_id}!")

            # Calculate Dynamic Risk Percentage (0% to 100%)
            risk_percentage = 20
            reasons = ["Pessoa identificada em área de monitoramento (+20%)"]
            
            # 1. Standing still (Loitering) in ROI
            still_s = p_state["accumulated_standing_still"]
            if still_s > 4.0:
                still_risk = min(35, int((still_s / 15.0) * 35))
                risk_percentage += still_risk
                reasons.append(f"Parado na ROI por {int(still_s)}s (+{still_risk}%)")
                
            # 2. Carrying bag (only internal)
            if camera_type == 'internal' and p_state.get("has_bag"):
                risk_percentage += 15
                reasons.append("Portando sacola/mochila (+15%)")
                
            # 3. Gaze/Facing camera duration (only internal)
            cam_s = p_state.get("look_at_camera_duration", 0.0)
            if camera_type == 'internal' and cam_s > 3.0:
                cam_risk = min(15, int((cam_s / 8.0) * 15))
                risk_percentage += cam_risk
                reasons.append(f"Olhando p/ câmera por {int(cam_s)}s (+{cam_risk}%)")
                
            # 4. Concealment action (only internal)
            if camera_type == 'internal' and p_state.get("concealment_events", 0) > 0:
                conceal_risk = min(40, p_state["concealment_events"] * 40)
                risk_percentage += conceal_risk
                reasons.append(f"Movimento de ocultação detectado (+{conceal_risk}%)")
                
            # Scale risk based on database global sensitivity setting
            # Default sensitivity is 75. If sensitivity is 75, scaling factor is 1.0.
            global AI_SENSITIVITY
            sensitivity_factor = AI_SENSITIVITY / 75.0
            risk_percentage = int(risk_percentage * sensitivity_factor)
            risk_percentage = min(risk_percentage, 100)
            p_state["current_risk"] = risk_percentage
            
            # Verbose diagnostics for suspicious movement logic activation
            print(f"[DIAGNOSTICO-MOVIMENTO] Avaliando comportamento da Pessoa #{track_id} no canal '{camera_name or CAMERA_NAME}':")
            print(f"  - ROI Ativa: {roi_enabled} | Dentro da ROI: {in_roi} (Tempo na ROI: {duration_in_roi:.1f}s)")
            print(f"  - Tipo da Câmera: {camera_type.upper()}")
            print(f"  - Tempo parado (lingering): {still_s:.1f}s (Limite: {LINGERING_THRESHOLD}s)")
            if camera_type == 'internal':
                print(f"  - Carrega bolsa/mochila: {p_state.get('has_bag')} | Olhar p/ camera: {cam_s:.1f}s")
                print(f"  - Ocultamentos detectados: {p_state.get('concealment_events')}")
            print(f"  - Risco Calculado: {risk_percentage}% | Sensibilidade: {AI_SENSITIVITY}%")
            print(f"  - Fatores de Risco Ativos: {reasons}")
            
            # Logging Throttling to prevent console flooding (Log once every 2s per person, or on state/risk spike)
            last_logged = p_state["last_logged"]
            risk_diff = abs(risk_percentage - p_state["highest_risk_percentage"])
            
            if (current_time - last_logged > 2.0) or (risk_diff >= 15) or (risk_percentage >= 80 and "critical" not in p_state["alerts_fired"]):
                p_state["last_logged"] = current_time
                p_state["highest_risk_percentage"] = max(p_state["highest_risk_percentage"], risk_percentage)
                reasons_str = "; ".join(reasons) if reasons else "Nenhuma ação suspeita"
                log_tag = "[AI-ALERT]" if risk_percentage >= 80 else ("[AI-WARNING]" if risk_percentage >= 40 else "[AI-MONITOR]")
                print(f"{log_tag} Pessoa #{track_id}: Risco={risk_percentage}% | Confiança={p_state.get('detection_conf', 0.0):.2f} | ROI={in_roi} | Parado={still_s:.1f}s | Bolsa={p_state.get('has_bag', False)} | Olhar Câmera={cam_s:.1f}s | Motivos: {reasons_str}")

            # Calculate dynamic confidence threshold based on AI_SENSITIVITY (slider)
            conf_threshold = 1.25 - (AI_SENSITIVITY / 100.0)
            conf_threshold = max(0.15, min(0.85, conf_threshold))

            # -------------------------------------------------------------
            # RULE: Weapon Detection Bypass Cooldown and immediate alert
            # -------------------------------------------------------------
            is_armed_threat = track_key in associated_weapons
            weapon_conf = associated_weapons.get(track_key, 0.0)
            
            # Intention-based alerts (threshold >= 80% or armed threat)
            if risk_percentage >= 80 or is_armed_threat:
                details = f"Detecção de Intenção de Risco Crítico para a Pessoa #{track_id}. Motivos analisados pela IA: " + ", ".join(reasons)
                severity_val = "critical"
                trigger_type_val = "CONCEALMENT_ROI"
                
                if is_armed_threat:
                    title = f"Ameaça Armada - URGENTE"
                    details = f"Arma de fogo identificada em posse da Pessoa #{track_id} no canal '{camera_name or CAMERA_NAME}'!"
                    severity_val = "critical"
                    trigger_type_val = "ARMED_THREAT"
                    risk_percentage = int(weapon_conf * 100)
                elif camera_type == 'internal' and p_state.get("concealment_events", 0) > 0:
                    title = f"Furto em Andamento (Pessoa #{track_id})"
                    trigger_type_val = "CONCEALMENT_ROI"
                elif p_state["accumulated_standing_still"] > LINGERING_THRESHOLD:
                    title = f"Tempo de Permanência Alto (Adega)" if camera_type == 'internal' else f"Permanência Elevada em Perímetro Crítico"
                    trigger_type_val = "LINGER_ROI"
                else:
                    title = f"Alerta de Segurança - Risco Crítico ({risk_percentage}%)"
                    trigger_type_val = "SUSPICIOUS_BEHAVIOR"
                
                # Check confidence limit, cooldown remaining, and ROI lingering duration
                avg_conf = sum(p_state["conf_history"]) / 3.0 if len(p_state["conf_history"]) >= 3 else 0.0
                cooldown_remaining = 60.0 - (current_time - p_state.get("last_alert_time", 0.0))
                
                # Weapon ignores cooldown and confidence threshold
                if duration_in_roi >= 2.5 or is_armed_threat:
                    if cooldown_remaining <= 0.0 or is_armed_threat:
                        if avg_conf >= conf_threshold or is_armed_threat:
                            p_state["last_alert_time"] = current_time
                            
                            # Encode visual frame to base64
                            frame_b64 = None
                            if frame is not None:
                                try:
                                    _, jpeg_img = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                                    import base64
                                    frame_b64 = base64.b64encode(jpeg_img).decode('utf-8')
                                except Exception:
                                    pass
                                    
                            # Send webhook IMMEDIATELY
                            send_webhook_alert(
                                title=title,
                                details=details,
                                severity=severity_val,
                                trigger_type=trigger_type_val,
                                confidence=risk_percentage,
                                tenant_id=tenant_id,
                                camera_id=camera_id,
                                camera_name=camera_name,
                                user_id=user_id,
                                track_id=track_id,
                                frame_base64=frame_b64
                            )
                            
                            # Also trigger evidence video clip recording
                            trigger_evidence_and_alert(
                                title=title,
                                details=details,
                                severity=severity_val,
                                trigger_type=trigger_type_val,
                                confidence=risk_percentage,
                                tenant_id=tenant_id,
                                camera_id=camera_id,
                                camera_name=camera_name,
                                user_id=user_id,
                                track_id=track_id,
                                frame=frame
                            )
                        else:
                            if current_time - p_state.get("last_conf_log_time_crit", 0.0) >= 5.0:
                                p_state["last_conf_log_time_crit"] = current_time
                                print(f"[AI-INFO-INTERNAL] Alerta crítico suprimido para n8n: Média de confiança de 3 frames ({avg_conf:.2f}) < threshold ({conf_threshold:.2f}). Logado apenas internamente.")
                    else:
                        if current_time - p_state.get("last_cooldown_log_time_crit", 0.0) >= 10.0:
                            p_state["last_cooldown_log_time_crit"] = current_time
                            print(f"[AI-INFO-INTERNAL] Alerta crítico suprimido para n8n: Cooldown ativo para Pessoa #{track_id} (tempo restante: {cooldown_remaining:.1f}s).")
                else:
                    if current_time - p_state.get("last_roi_log_time_crit", 0.0) >= 10.0:
                        p_state["last_roi_log_time_crit"] = current_time
                        print(f"[AI-INFO-INTERNAL] Alerta crítico suprimido para n8n: Pessoa #{track_id} permaneceu na ROI por apenas {duration_in_roi:.1f}s (mínimo 2.5s).")
            else:
                # Log internally if risk calculated is between 15% and 80% (Estabilização de Confiança)
                if 15 <= risk_percentage < 80:
                    if current_time - p_state.get("last_internal_log_time", 0.0) >= 5.0:
                        p_state["last_internal_log_time"] = current_time
                        print(f"[AI-INFO-INTERNAL] Evento monitorado (Risco={risk_percentage}% < 80%): Pessoa #{track_id} em atividade na ROI. Apenas logado.")

        # Cleanup expired tracks (not seen for 10 frames or more)
        expired_ids = []
        for tid, p_state in list(cam_tracked.items()):
            if tid not in detected_track_ids:
                p_state["missing_frames"] = p_state.get("missing_frames", 0) + 1
            else:
                p_state["missing_frames"] = 0
                
            # Keep history if missing for less than 10 frames (occlusao rapida)
            if p_state["missing_frames"] >= 10:
                expired_ids.append(tid)
                
        for tid in expired_ids:
            print(f"[AI-INFO] Pessoa #{tid} saiu de cena por 10 frames. Finalizando rastreamento.")
            cam_tracked.pop(tid, None)

        # Draw ROI polygon and centroids/boxes on frame_ai if frame is provided
        if frame is not None and rtsp_url is not None:
            debug_frame = frame.copy()
            # Draw green ROI polygon boundaries
            pts = np.array(roi_pixels, np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(debug_frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
            
            # Draw bounding boxes and centroids for persons
            for p in persons:
                cx, cy = p["center"]
                tid = p["track_id"]
                x1, y1, w, h = p["bbox"]
                
                track_key = f"{camera_name or CAMERA_NAME}_{tid}"
                risk_val = 0
                if track_key in cam_tracked:
                    risk_val = cam_tracked[track_key].get("current_risk", 0)
                
                # Box color: Red if risk >= 70, Yellow if risk >= 40, Cyan if low risk
                box_color = (0, 0, 255) if risk_val >= 70 else ((0, 255, 255) if risk_val >= 40 else (255, 255, 0))
                cv2.rectangle(debug_frame, (x1, y1), (x1 + w, y1 + h), box_color, 2)
                cv2.circle(debug_frame, (cx, cy), 6, box_color, -1)
                
                label = f"PESSOA #{tid} | RISCO: {risk_val}%"
                cv2.putText(debug_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
                
            # Draw bounding boxes for other objects (bags, backpacks, etc.)
            for obj in objects:
                x1, y1, w, h = obj["bbox"]
                cls_name = obj["class"]
                cv2.rectangle(debug_frame, (x1, y1), (x1 + w, y1 + h), (255, 100, 0), 2)
                cv2.putText(debug_frame, cls_name.upper(), (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 100, 0), 1)

            # Draw bounding boxes for products
            for prod in products:
                x1, y1, w, h = prod["bbox"]
                cls_name = prod["class"]
                cv2.rectangle(debug_frame, (x1, y1), (x1 + w, y1 + h), (100, 255, 100), 1)
                cv2.putText(debug_frame, f"PROD: {cls_name.upper()}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 255, 100), 1)

            # Draw bounding boxes for active weapons
            if weapon_detections:
                for w_det in weapon_detections:
                    x1, y1, w, h = w_det["bbox"]
                    cv2.rectangle(debug_frame, (x1, y1), (x1 + w, y1 + h), (0, 0, 255), 3)
                    cv2.putText(debug_frame, "ARMA DE FOGO!", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # Encode drawn frame and save to latest_ai_frames
            try:
                _, jpeg_data = cv2.imencode('.jpg', debug_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                frame_bytes = jpeg_data.tobytes()
                with frame_lock:
                    latest_ai_frames[camera_id] = frame_bytes
            except Exception as draw_err:
                print(f"[ENGINE] Erro ao codificar frame_ai: {draw_err}")

def fetch_registered_cameras(tenant_id):
    try:
        conn = pg8000.connect(
            host="144.91.121.55",
            port=5432,
            user="postgres",
            password="KtnYcxnVOGjD4thzS6tlBcW9",
            database="aegisyear",
            timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, rtsp FROM public.cameras WHERE tenant_id = %s", (str(tenant_id),))
        rows = cursor.fetchall()
        cameras = []
        for r in rows:
            cameras.append({
                "id": str(r[0]),
                "name": str(r[1]),
                "rtsp": str(r[2])
            })
        cursor.close()
        conn.close()
        return cameras
    except Exception as e:
        print(f"[CAMERAS-LOAD ERROR] Falha ao carregar câmeras do banco: {e}")
        return []

def camera_capture_worker(camera_id, camera_name, rtsp_url, simulate=False):
    global running, latest_clean_frames, frames_to_process
    print(f"[CAPTURE] Iniciando captura para a câmera '{camera_name}' (ID: {camera_id})")
    
    import av
    frame_id = 0
    is_mock = simulate or "192.168.1.100" in rtsp_url or "localhost" in rtsp_url or "127.0.0.1" in rtsp_url or not rtsp_url
    
    while running and camera_id in active_cameras:
        try:
            if is_mock:
                while running and camera_id in active_cameras:
                    frame_id += 1
                    time.sleep(0.033) # 30 FPS
                    
                    frame = np.zeros((1080, 1920, 3), dtype=np.uint8) + 18
                    cv2.putText(frame, f"FEED DE VIDEO: {camera_name.upper()}", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    cv2.putText(frame, f"Frame: {frame_id} | FPS: 30 | Headless Edge-Node", (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)
                    
                    # Add simple simulation motion so that AI has someone to track if simulate is active
                    if simulate:
                        # Draw a moving box to simulate a person tracking box
                        pos_x = int(400 + 300 * math.sin(frame_id * 0.05))
                        cv2.rectangle(frame, (pos_x, 300), (pos_x + 150, 700), (100, 100, 100), -1)
                        cv2.putText(frame, "Pessoa Simulada", (pos_x, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    resized_clean = cv2.resize(frame, (800, 450))
                    _, jpeg_clean = cv2.imencode('.jpg', resized_clean, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    
                    with frame_lock:
                        latest_clean_frames[camera_id] = jpeg_clean.tobytes()
                        if frames_to_process.get(camera_id) is None:
                            frames_to_process[camera_id] = frame.copy()
                            
                    add_frame_to_buffers(camera_id, resized_clean)
            else:
                container = av.open(rtsp_url, options={
                    'rtsp_transport': 'tcp',
                    'stimeout': '5000000',
                    'timeout': '5000000'
                })
                stream = container.streams.video[0]
                stream.thread_type = 'NONE'
                
                for frame_obj in container.decode(stream):
                    if not running or camera_id not in active_cameras:
                        break
                        
                    frame_id += 1
                    img = frame_obj.to_ndarray(format='bgr24')
                    resized_clean = cv2.resize(img, (800, 450))
                    _, jpeg_clean = cv2.imencode('.jpg', resized_clean, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    
                    with frame_lock:
                        latest_clean_frames[camera_id] = jpeg_clean.tobytes()
                        if frames_to_process.get(camera_id) is None:
                            frames_to_process[camera_id] = img.copy()
                            
                    add_frame_to_buffers(camera_id, resized_clean)
                    
                container.close()
        except Exception as e:
            print(f"[CAPTURE ERROR] Câmera '{camera_name}' (ID: {camera_id}) falhou: {e}. Reconectando em 5s...")
            time.sleep(5)

def camera_inference_worker(camera_id, camera_name, simulate=False):
    global running, frames_to_process, N8N_WEBHOOK_URL, AI_SENSITIVITY, AI_FPS
    print(f"[INFERENCE] Thread de inferência YOLOv8 ativa para a câmera '{camera_name}' (ID: {camera_id})")
    
    # Load YOLOv8 models
    model = None
    pose_model = None
    weapon_model = None
    
    if not simulate:
        try:
            model = YOLO("yolov8n.pt")
            import torch
            if torch.cuda.is_available() and hasattr(model, 'to'):
                model.to("cuda")
        except Exception as e:
            print(f"[ENGINE ERROR] Falha ao carregar model: {e}")
        try:
            pose_model = YOLO("yolov8n-pose.pt")
            if torch.cuda.is_available() and hasattr(pose_model, 'to'):
                pose_model.to("cuda")
        except Exception as e:
            print(f"[ENGINE ERROR] Falha ao carregar pose_model: {e}")
        weapon_model_path = "weapon_detector.pt"
        if os.path.exists(weapon_model_path):
            try:
                weapon_model = YOLO(weapon_model_path)
                if torch.cuda.is_available() and hasattr(weapon_model, 'to'):
                    weapon_model.to("cuda")
            except Exception as e:
                print(f"[ENGINE ERROR] Falha ao carregar weapon_model: {e}")
                
    frame_count = 0
    while running and camera_id in active_cameras:
        img_to_check = None
        with frame_lock:
            if frames_to_process.get(camera_id) is not None:
                img_to_check = frames_to_process[camera_id]
                frames_to_process[camera_id] = None
                
        if img_to_check is None:
            time.sleep(0.01)
            continue
            
        start_processing_time = time.time()
        frame_count += 1
        H, W, _ = img_to_check.shape
        
        # Standard detections
        detections = []
        if model and not simulate:
            try:
                results = model.track(img_to_check, persist=True, tracker="bytetrack.yaml", verbose=False)[0]
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = results.names[cls_id]
                    conf = float(box.conf[0])
                    PRODUCT_CLASSES = ["bottle", "wine glass", "cup", "book", "cell phone", "scissors", "toothbrush", "can", "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake"]
                    if (cls_name in ["person", "backpack", "handbag", "bag", "suitcase", "briefcase"] or cls_name in PRODUCT_CLASSES) and conf > 0.22:
                        xyxy = box.xyxy[0].cpu().numpy()
                        w = xyxy[2] - xyxy[0]
                        h = xyxy[3] - xyxy[1]
                        detections.append({
                            "track_id": int(box.id[0]) if box.id is not None else 100,
                            "bbox": [int(xyxy[0]), int(xyxy[1]), int(w), int(h)],
                            "class": cls_name,
                            "conf": conf
                        })
            except Exception as e:
                pass
        elif simulate:
            # Generate simulated track person
            pos_x = int(400 + 300 * math.sin(frame_count * 0.05))
            detections.append({
                "track_id": 1,
                "bbox": [pos_x, 300, 150, 400],
                "class": "person",
                "conf": 0.88
            })
            
        # Weapon detections
        weapon_detections = []
        if weapon_model and not simulate:
            try:
                w_results = weapon_model(img_to_check, verbose=False)[0]
                for box in w_results.boxes:
                    conf = float(box.conf[0])
                    if conf > 0.30:
                        xyxy = box.xyxy[0].cpu().numpy()
                        w = xyxy[2] - xyxy[0]
                        h = xyxy[3] - xyxy[1]
                        weapon_detections.append({
                            "bbox": [int(xyxy[0]), int(xyxy[1]), int(w), int(h)],
                            "class": "arma",
                            "conf": conf
                        })
            except:
                pass
                
        if os.path.exists("trigger_weapon.txt"):
            weapon_detections.append({
                "bbox": [150, 150, 60, 60],
                "class": "arma",
                "conf": 0.96
            })
            
        process_detections_and_infractions(
            detections, W, H, img_to_check, simulate,
            camera_name=camera_name, camera_id=camera_id, tenant_id=TENANT_ID,
            weapon_detections=weapon_detections, pose_model=pose_model
        )
        
        # DIAGNOSTICO-FPS
        processing_latency_ms = (time.time() - start_processing_time) * 1000.0
        if frame_count % 150 == 0:
            print(f"[DIAGNOSTICO-FPS] Câmera '{camera_name}': Latência={processing_latency_ms:.1f}ms | FPS IA={1000.0 / max(1.0, processing_latency_ms):.1f}")
            
        sleep_sec = 1.0 / AI_FPS if AI_FPS > 0 else 0.1
        time.sleep(sleep_sec)

def camera_manager_loop(simulate=False):
    global running, active_cameras, TENANT_ID
    print("[CAMERAS-WATCHDOG] Iniciando monitor de câmeras cadastradas...")
    
    while running:
        db_cams = fetch_registered_cameras(TENANT_ID)
        
        if not db_cams:
            db_cams = [
                {"id": "default", "name": "Câmera Principal (Caixas)", "rtsp": RTSP_URL or "rtsp://127.0.0.1/ch1"},
                {"id": "79f0f0a6-d388-49aa-8ad6-b7645da973ce", "name": "Câmera Externa (Rua)", "rtsp": "rtsp://127.0.0.1/ch2"}
            ]
            
        db_cam_ids = {c["id"] for c in db_cams}
        
        with cameras_watchdog_lock:
            # Start new cameras
            for cam in db_cams:
                cid = cam["id"]
                cname = cam["name"]
                crtsp = cam["rtsp"]
                
                if cid not in active_cameras:
                    print(f"[CAMERAS-WATCHDOG] Nova câmera cadastrada: '{cname}' (ID: {cid})")
                    active_cameras[cid] = {
                        "name": cname,
                        "rtsp": crtsp,
                        "capture_thread": None,
                        "inference_thread": None
                    }
                    
                    load_roi_config(cid)
                    
                    t_cap = threading.Thread(target=camera_capture_worker, args=(cid, cname, crtsp, simulate), daemon=True)
                    t_inf = threading.Thread(target=camera_inference_worker, args=(cid, cname, simulate), daemon=True)
                    
                    active_cameras[cid]["capture_thread"] = t_cap
                    active_cameras[cid]["inference_thread"] = t_inf
                    
                    t_cap.start()
                    t_inf.start()
                    
            # Stop removed cameras
            for cid in list(active_cameras.keys()):
                if cid not in db_cam_ids:
                    print(f"[CAMERAS-WATCHDOG] Câmera removida: ID {cid}.")
                    active_cameras.pop(cid, None)
                    
        time.sleep(10.0)

if __name__ == '__main__':
    print("=" * 60)
    print(" AegisEye AI Edge Node - Pipeline de Visão Computacional")
    print("=" * 60)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--rtsp', type=str, default="")
    parser.add_argument('--camera-id', type=str, default="")
    parser.add_argument('--name', type=str, default="")
    parser.add_argument('--tenant-id', type=str, default="")
    parser.add_argument('--simulate', action='store_true')
    args = parser.parse_known_args()[0]
    
    if args.rtsp:
        RTSP_URL = args.rtsp
    if args.camera_id:
        CAMERA_ID = args.camera_id
    if args.name:
        CAMERA_NAME = args.name
    if args.tenant_id:
        TENANT_ID = args.tenant_id
        
    load_db_config(TENANT_ID)
    cleanup_old_evidence_clips()
        
    simulate_mode = args.simulate or not RTSP_URL
    
    # Start HTTP Server thread on port 8082
    def start_http():
        server_address = ('', 8082)
        httpd = ThreadingHTTPServer(server_address, CameraStreamHandler)
        print("Servidor HTTP do Edge Node rodando em http://localhost:8082/")
        httpd.serve_forever()
        
    threading.Thread(target=start_http, daemon=True).start()
    
    # Start Heartbeat Thread
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    
    # Start dynamic camera manager watchdog (starts inference and capture threads per camera)
    threading.Thread(target=camera_manager_loop, args=(simulate_mode,), daemon=True).start()


def camera_manager_loop(simulate=False):
    global running, active_cameras, TENANT_ID
    print("[CAMERAS-WATCHDOG] Iniciando monitor de câmeras cadastradas...")
    
    while running:
        db_cams = fetch_registered_cameras(TENANT_ID)
        
        if not db_cams:
            db_cams = [
                {"id": "default", "name": "Câmera Principal (Caixas)", "rtsp": RTSP_URL or "rtsp://127.0.0.1/ch1"},
                {"id": "79f0f0a6-d388-49aa-8ad6-b7645da973ce", "name": "Câmera Externa (Rua)", "rtsp": "rtsp://127.0.0.1/ch2"}
            ]
            
        db_cam_ids = {c["id"] for c in db_cams}
        
        with cameras_watchdog_lock:
            # Start new cameras
            for cam in db_cams:
                cid = cam["id"]
                cname = cam["name"]
                crtsp = cam["rtsp"]
                
                if cid not in active_cameras:
                    print(f"[CAMERAS-WATCHDOG] Nova câmera cadastrada: '{cname}' (ID: {cid})")
                    active_cameras[cid] = {
                        "name": cname,
                        "rtsp": crtsp,
                        "capture_thread": None,
                        "inference_thread": None
                    }
                    
                    load_roi_config(cid)
                    
                    t_cap = threading.Thread(target=camera_capture_worker, args=(cid, cname, crtsp, simulate), daemon=True)
                    t_inf = threading.Thread(target=camera_inference_worker, args=(cid, cname, simulate), daemon=True)
                    
                    active_cameras[cid]["capture_thread"] = t_cap
                    active_cameras[cid]["inference_thread"] = t_inf
                    
                    t_cap.start()
                    t_inf.start()
                    
            # Stop removed cameras
            for cid in list(active_cameras.keys()):
                if cid not in db_cam_ids:
                    print(f"[CAMERAS-WATCHDOG] Câmera removida: ID {cid}.")
                    active_cameras.pop(cid, None)
                    
        time.sleep(10.0)

if __name__ == '__main__':
    print("=" * 60)
    print(" AegisEye AI Edge Node - Pipeline de Visão Computacional")
    print("=" * 60)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--rtsp', type=str, default="")
    parser.add_argument('--camera-id', type=str, default="")
    parser.add_argument('--name', type=str, default="")
    parser.add_argument('--tenant-id', type=str, default="")
    parser.add_argument('--simulate', action='store_true')
    args = parser.parse_known_args()[0]
    
    if args.rtsp:
        RTSP_URL = args.rtsp
    if args.camera_id:
        CAMERA_ID = args.camera_id
    if args.name:
        CAMERA_NAME = args.name
    if args.tenant_id:
        TENANT_ID = args.tenant_id
        
    load_db_config(TENANT_ID)
    cleanup_old_evidence_clips()
        
    simulate_mode = args.simulate or not RTSP_URL
    
    # Start HTTP Server thread on port 8082
    def start_http():
        server_address = ('', 8082)
        httpd = ThreadingHTTPServer(server_address, CameraStreamHandler)
        print("Servidor HTTP do Edge Node rodando em http://localhost:8082/")
        httpd.serve_forever()
        
    threading.Thread(target=start_http, daemon=True).start()
    
    # Start Heartbeat Thread
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    
    # Start dynamic camera manager watchdog (starts inference and capture threads per camera)
    threading.Thread(target=camera_manager_loop, args=(simulate_mode,), daemon=True).start()
    
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Encerrando pipeline...")
        running = False
        sys.exit(0)
