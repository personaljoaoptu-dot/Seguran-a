import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import webview
import pg8000
import json
import subprocess
import threading

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
            cursor.execute("SELECT name, rtsp, device, status FROM cameras WHERE tenant_id = %s", (tenant_id,))
            cameras = []
            for row in cursor.fetchall():
                cameras.append({
                    "name": row[0],
                    "rtsp": row[1],
                    "device": row[2] or "Câmera IP",
                    "status": row[3] or "online"
                })
                
            cursor.close()
            conn.close()
            
            print(f"[DESKTOP API] Cameras carregadas: {cameras}")

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
            cursor.execute("SELECT name, rtsp, device, status FROM cameras WHERE tenant_id = %s", (tenant_id,))
            cameras = []
            for row in cursor.fetchall():
                cameras.append({
                    "name": row[0],
                    "rtsp": row[1],
                    "device": row[2] or "Câmera IP",
                    "status": row[3] or "online"
                })
            cursor.close()
            conn.close()
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
                SELECT created_at, severity, title, camera_name, confidence, id 
                FROM public.alertas 
                WHERE tenant_id = %s 
                ORDER BY created_at DESC 
                LIMIT 20
            """, (tenant_id,))
            
            alerts = []
            for row in cursor.fetchall():
                created_at = row[0]
                time_str = created_at.strftime("%H:%M")
                severity = row[1]
                label = "CRÍTICO" if severity == "critical" else ("ATENÇÃO" if severity == "warning" else "MÉDIO")
                
                alerts.append({
                    "id": str(row[5]),
                    "time": time_str,
                    "severity": severity,
                    "label": label,
                    "title": row[2],
                    "camera": row[3],
                    "conf": f"{int(row[4])}%" if row[4] is not None else "90%"
                })
                
            cursor.close()
            conn.close()
            return json.dumps({"success": True, "alerts": alerts})
        except Exception as e:
            print(f"[DESKTOP API] Erro ao carregar alertas: {e}")
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
    # Start the local camera streamer in a background thread to ensure port 8082 is open
    import threading
    try:
        import local_camera_streamer
        streamer_thread = threading.Thread(
            target=lambda: local_camera_streamer.run_server(8082),
            daemon=True
        )
        streamer_thread.start()
        print("[DESKTOP] Local camera streamer started automatically on port 8082.")
    except Exception as streamer_err:
        print(f"[DESKTOP] Failed to start local camera streamer: {streamer_err}")

    api = AegisEyeApi()
    
    # Create webview window loading from the local HTTP streamer server
    window = webview.create_window(
        title='AegisEye AI - Loss Prevention Monitor Extension', 
        url='http://127.0.0.1:8082/', 
        js_api=api,
        width=900, 
        height=550, 
        resizable=False
    )
    
    # Run application loop with debug mode enabled (Press F12 to inspect)
    webview.start(debug=True)
