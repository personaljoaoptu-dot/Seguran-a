import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import webview
import pg8000
import json
import subprocess
import threading
import scripts.aegiseye_vision_pipeline as pipeline_module

# Database connection credentials
DB_HOST = "144.91.121.55"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASS = "KtnYcxnVOGjD4thzS6tlBcW9"
DB_NAME = "aegisyear"

class AegisEyeApi:
    def login(self, email):
        email = email.strip()
        print(f"[DESKTOP API] Tentativa de login: {email}")
        try:
            conn = pg8000.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME
            )
            cursor = conn.cursor()
            
            # Find User & Tenant ID
            cursor.execute("SELECT tenant_id, name FROM users WHERE email = %s", (email,))
            user_data = cursor.fetchone()
            
            if not user_data:
                # Fallback to check usuarios table
                cursor.execute("SELECT id, nome FROM usuarios WHERE email = %s", (email,))
                user_data = cursor.fetchone()
                if not user_data:
                    conn.close()
                    return json.dumps({"success": False, "error": f"Nenhum perfil encontrado para o e-mail: {email}"})
                tenant_id = user_data[0]
                tenant_name = user_data[1]
            else:
                tenant_id = user_data[0]
                # Fetch tenant name
                cursor.execute("SELECT name FROM tenants WHERE id = %s", (tenant_id,))
                t_data = cursor.fetchone()
                tenant_name = t_data[0] if t_data else "Empresa Conectada"

            # Fetch active cameras
            cursor.execute("SELECT id, name, rtsp, device, status FROM cameras WHERE tenant_id = %s", (tenant_id,))
            cameras = []
            for row in cursor.fetchall():
                cameras.append({
                    "id": str(row[0]),
                    "name": row[1],
                    "rtsp": row[2],
                    "device": row[3] or "Câmera IP",
                    "status": row[4] or "online"
                })
                
            cursor.close()
            conn.close()
            
            # Sync tenant ID with background AI Vision pipeline
            pipeline_module.TENANT_ID = str(tenant_id)
            print(f"[DESKTOP API] Cameras carregadas para o tenant {tenant_id}: {cameras}")

            # Trigger welcome notification in a separate thread
            self.trigger_notification(
                "AegisEye Conectado!",
                f"Sincronizado com sucesso na conta {tenant_name}."
            )

            return json.dumps({
                "success": True,
                "tenant_id": str(tenant_id),
                "tenant_name": tenant_name,
                "cameras": cameras
            })
        except Exception as e:
            print(f"[DESKTOP API] Erro no login: {e}")
            return json.dumps({"success": False, "error": f"Erro de banco de dados: {str(e)}"})

    def get_cameras(self, tenant_id):
        print(f"[DESKTOP API] Buscando cameras para o tenant: {tenant_id}")
        try:
            conn = pg8000.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME
            )
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, rtsp, device, status FROM cameras WHERE tenant_id = %s", (tenant_id,))
            cameras = []
            for row in cursor.fetchall():
                cameras.append({
                    "id": str(row[0]),
                    "name": row[1],
                    "rtsp": row[2],
                    "device": row[3] or "Câmera IP",
                    "status": row[4] or "online"
                })
            cursor.close()
            conn.close()
            
            # Sync tenant ID with background AI Vision pipeline
            pipeline_module.TENANT_ID = str(tenant_id)
            
            return json.dumps({"success": True, "cameras": cameras})
        except Exception as e:
            print(f"[DESKTOP API] Erro ao carregar cameras: {e}")
            return json.dumps({"success": False, "error": str(e)})

    def get_alerts(self, tenant_id):
        print(f"[DESKTOP API] Buscando alertas para o tenant: {tenant_id}")
        try:
            conn = pg8000.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME
            )
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, severity, title, camera_name, confidence_score, id, video_url, details 
                FROM public.alertas 
                WHERE tenant_id = %s AND status = 'active'
                ORDER BY timestamp DESC 
                LIMIT 50
            """, (tenant_id,))
            
            alerts = []
            for row in cursor.fetchall():
                timestamp_val = row[0]
                time_str = timestamp_val.strftime("%H:%M")
                severity = row[1]
                label = "CRÍTICO" if severity == "critical" else ("ATENÇÃO" if severity == "warning" else "MÉDIO")
                
                alerts.append({
                    "id": str(row[5]),
                    "time": time_str,
                    "timestamp": timestamp_val.isoformat() if timestamp_val else None,
                    "severity": severity,
                    "label": label,
                    "title": row[2],
                    "camera": row[3] or "Câmera Geral",
                    "confidence": int(row[4]) if row[4] is not None else 90,
                    "video_url": row[6] if len(row) > 6 else None,
                    "details": row[7] if len(row) > 7 else "Alerta de segurança em tempo real."
                })
                
            # Count today's total alerts
            cursor.execute("""
                SELECT COUNT(*) FROM public.alertas 
                WHERE tenant_id = %s AND timestamp >= CURRENT_DATE
            """, (tenant_id,))
            today_count = cursor.fetchone()[0]
                
            cursor.close()
            conn.close()
            return json.dumps({"success": True, "alerts": alerts, "today_count": today_count})
        except Exception as e:
            print(f"[DESKTOP API] Erro ao carregar alertas: {e}")
            return json.dumps({"success": False, "error": str(e)})

    def check_edge_status(self, tenant_id):
        print(f"[DESKTOP API] Verificando status do Edge Node para o tenant: {tenant_id}")
        import urllib.request
        try:
            url = f"http://144.91.121.55:8000/api/edge-status?tenant_id={tenant_id}"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                res_body = response.read().decode('utf-8')
                return res_body
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def resolve_alert(self, alert_id, feedback_type="correct"):
        print(f"[DESKTOP API] Resolvendo alerta {alert_id} com feedback: {feedback_type}")
        try:
            conn = pg8000.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME
            )
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE public.alertas 
                SET status = 'resolved'
                WHERE id = %s
            """, (alert_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return json.dumps({"success": True})
        except Exception as e:
            print(f"[DESKTOP API] Erro ao resolver alerta {alert_id}: {e}")
            return json.dumps({"success": False, "error": str(e)})


    def trigger_notification(self, title, message):
        """Sends a native Windows balloon notification using PowerShell in a background thread."""
        print(f"[DESKTOP API] Disparando notificacao: {title} | {message}")
        ps_script = f"""
        [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")
        $objNotification = New-Object System.Windows.Forms.NotifyIcon
        $objNotification.Icon = [System.Drawing.SystemIcons]::Warning
        $objNotification.BalloonTipIcon = "Warning"
        $objNotification.BalloonTipText = "{message}"
        $objNotification.BalloonTipTitle = "{title}"
        $objNotification.Visible = $True
        $objNotification.ShowBalloonTip(5000)
        """
        threading.Thread(target=lambda: subprocess.run(["powershell", "-Command", ps_script], capture_output=True), daemon=True).start()

if __name__ == '__main__':
    import threading
    import socket
    import http.server
    import time


    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    # Start the integrated AI pipeline inside the same process
    try:
        # Load configs
        pipeline_module.load_db_config("")
        pipeline_module.load_roi_config("")
        pipeline_module.cleanup_old_evidence_clips()
        
        # Start integrated HTTP Server thread on port 8082 if not in use
        if not is_port_in_use(8082):
            def start_http():
                server_address = ('', 8082)
                httpd = http.server.ThreadingHTTPServer(server_address, pipeline_module.CameraStreamHandler)
                print("[DESKTOP] Integrated AI HTTP Server running on http://localhost:8082/")
                httpd.serve_forever()
                
            threading.Thread(target=start_http, daemon=True).start()
            
            # Start AI Inference Thread (YOLO detection)
            threading.Thread(target=pipeline_module.ai_inference_loop, args=(False,), daemon=True).start()
            
            # Start Heartbeat Thread
            threading.Thread(target=pipeline_module.heartbeat_loop, daemon=True).start()
            
            # Wait up to 3 seconds for port 8082 to be ready
            print("[DESKTOP] Waiting for integrated AI server to bind port 8082...")
            for _ in range(30):
                time.sleep(0.1)
                if is_port_in_use(8082):
                    print("[DESKTOP] Integrated AI server is ready on port 8082.")
                    break
        else:
            print("[DESKTOP] Port 8082 in use. Integrated AI pipeline server skipped (already active).")
            
    except Exception as pipeline_err:
        print(f"[DESKTOP] Failed to initialize integrated AI pipeline: {pipeline_err}")

    api = AegisEyeApi()
    
    # Create webview window loading from the local HTTP streamer server
    window = webview.create_window(
        title='AegisEye AI - Loss Prevention Monitor Extension', 
        url='http://localhost:8082/', 
        js_api=api,
        width=1280, 
        height=800, 
        resizable=True
    )
    
    # Run application loop
    webview.start(debug=False)
