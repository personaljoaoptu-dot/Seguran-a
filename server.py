import http.server
import socketserver
import os
import urllib.parse
import urllib.request
import json
import bcrypt
import uuid
import traceback
import time
import threading

# In-memory registry for Edge Node heartbeats (tenant_id -> timestamp)
active_edge_nodes = {}

# Active SSE client subscribers for real-time alert push
sse_subscribers = set()
sse_lock = threading.Lock()

def send_telegram_alert(alert):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        return
    
    severity = alert.get("severity", "critical")
    emoji = "🚨" if severity == "critical" else "⚠️"
    msg_text = (
        f"{emoji} *AEGISEYE AI — NOVO ALERTA*\n\n"
        f"*Evento:* {alert.get('title', 'Alerta de Risco')}\n"
        f"*Severidade:* {severity.upper()}\n"
        f"*Câmera:* {alert.get('camera', 'Câmera Geral')}\n"
        f"*Confiança:* {alert.get('confidence', 90)}%\n"
        f"*Detalhes:* {alert.get('details', 'Detecção comportamental')}\n"
    )
    if alert.get("video_url"):
        msg_text += f"\n🎥 [Assistir Evidência em Vídeo]({alert['video_url']})"
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": msg_text,
        "parse_mode": "Markdown"
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=5):
            print(f"[TELEGRAM] Notificação de alerta enviada para o chat {chat_id}")
    except Exception as e:
        print(f"[TELEGRAM] Notificação Telegram não enviada (token/chat_id ausente ou offline): {e}")

def broadcast_alert_event(alert_data):
    # Asynchronously dispatch Telegram push notification
    threading.Thread(target=send_telegram_alert, args=(alert_data,), daemon=True).start()

    with sse_lock:
        dead = set()
        payload = f"data: {json.dumps(alert_data)}\n\n".encode('utf-8')
        for wfile in list(sse_subscribers):
            try:
                wfile.write(payload)
                wfile.flush()
            except Exception:
                dead.add(wfile)
        for w in dead:
            sse_subscribers.discard(w)

PORT = 8000

def get_db_connection():
    import os
    import pg8000
    
    hosts = ["postgres_db", "144.91.121.55"]
    if not os.path.exists('/.dockerenv'):
        hosts = ["144.91.121.55", "postgres_db"]
        
    for host in hosts:
        try:
            print(f"[DB] Tentando conectar ao host do banco: {host}...")
            conn = pg8000.connect(
                host=host,
                port=5432,
                user="postgres",
                password="KtnYcxnVOGjD4thzS6tlBcW9",
                database="aegisyear",
                timeout=5
            )
            print(f"[DB] Conectado com sucesso ao host: {host}")
            return conn
        except Exception as e:
            print(f"[DB] Falha de conexão ao host {host}: {e}")
    raise Exception("Não foi possível conectar ao banco de dados PostgreSQL.")

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="frontend", **kwargs)

    def end_headers(self):
        # Disable browser cache
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        clean_path = parsed_url.path
        
        if clean_path == '/api/verify-token':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            token = query_params.get('token', [''])[0].strip()
            
            if not token:
                self.send_error_response("Token é obrigatório.")
                return
            
            n8n_base = os.environ.get('N8N_URL', 'http://127.0.0.1:5678')
            n8n_webhook_url = f"{n8n_base}/webhook/f1f2f3f4-5678-4c3d-b2a1-098765432109/webhook_verify/verify-token?token={urllib.parse.quote(token)}"
            
            print(f"[VERIFY] Encaminhando verificação de token para o n8n: {n8n_webhook_url}")
            
            try:
                req = urllib.request.Request(n8n_webhook_url, method='GET')
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_body = response.read().decode('utf-8')
                    n8n_response = json.loads(res_body)
                    status_code = response.getcode()
            except urllib.error.HTTPError as he:
                res_body = he.read().decode('utf-8')
                try:
                    n8n_response = json.loads(res_body)
                except Exception:
                    n8n_response = {"success": False, "message": "Link inválido ou expirado."}
                status_code = he.code
            except Exception as e:
                print(f"[ERROR] Falha na comunicação com o n8n para verificação: {e}")
                self.send_error_response("Serviço de verificação offline.")
                return
                
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(n8n_response).encode('utf-8'))
            return

        elif clean_path == '/api/get-cameras':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            tenant_id = query_params.get('tenant_id', [''])[0].strip()
            if not tenant_id:
                self.send_error_response("tenant_id é obrigatório.")
                return
            conn = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT name, rtsp, device, status, id FROM cameras WHERE tenant_id = %s", (tenant_id,))
                cameras = []
                for row in cursor.fetchall():
                    cameras.append({
                        "id": str(row[4]),
                        "name": row[0],
                        "rtsp": row[1],
                        "device": row[2] or "Câmera IP",
                        "status": row[3] or "online"
                    })
                cursor.close()
                self.send_success_response({"success": True, "cameras": cameras})
            except Exception as e:
                print(f"[ERROR] Falha ao carregar câmeras para o tenant {tenant_id}: {e}")
                traceback.print_exc()
                self.send_error_response(f"Erro ao carregar câmeras: {e}")
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
            return

        elif clean_path == '/api/get-alerts':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            tenant_id = query_params.get('tenant_id', [''])[0].strip()
            user_id = query_params.get('user_id', [''])[0].strip()
            if user_id.lower() in ['none', 'undefined', 'null', '']:
                user_id = ''
            if not tenant_id and not user_id:
                self.send_error_response("tenant_id ou user_id é obrigatório.")
                return
            conn = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                if tenant_id:
                    cursor.execute("""
                        SELECT timestamp, severity, title, camera_name, confidence_score, id, details, risk_type, video_url 
                        FROM public.alertas 
                        WHERE tenant_id = %s AND status = 'active'
                        ORDER BY timestamp DESC 
                        LIMIT 50
                    """, (tenant_id,))
                else:
                    cursor.execute("""
                        SELECT timestamp, severity, title, camera_name, confidence_score, id, details, risk_type, video_url 
                        FROM public.alertas 
                        WHERE user_id = %s AND status = 'active'
                        ORDER BY timestamp DESC 
                        LIMIT 50
                    """, (user_id,))
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
                        "details": row[6] or "Alerta detectado por processador IA local.",
                        "trigger": row[7] or "Detecção automática.",
                        "video_url": row[8] if len(row) > 8 else None
                    })
                # Count today's total alerts
                if tenant_id:
                    cursor.execute("""
                        SELECT COUNT(*) FROM public.alertas 
                        WHERE tenant_id = %s AND timestamp >= CURRENT_DATE
                    """, (tenant_id,))
                else:
                    cursor.execute("""
                        SELECT COUNT(*) FROM public.alertas 
                        WHERE user_id = %s AND timestamp >= CURRENT_DATE
                    """, (user_id,))
                today_count = cursor.fetchone()[0]
                
                cursor.close()
                self.send_success_response({"success": True, "alerts": alerts, "today_count": today_count})
            except Exception as e:
                print(f"[ERROR] Falha ao carregar alertas para o tenant {tenant_id}: {e}")
                traceback.print_exc()
                self.send_error_response(f"Erro ao carregar alertas: {e}")
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
            return
        elif clean_path == '/api/get-analytics':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            tenant_id = query_params.get('tenant_id', [''])[0].strip()
            camera_name = query_params.get('camera_name', [''])[0].strip()
            if not tenant_id:
                self.send_error_response("tenant_id é obrigatório.")
                return
            conn = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Fetch counts of alerts in last 24h grouped by camera_name
                if camera_name and camera_name.lower() != 'all':
                    cursor.execute("""
                        SELECT camera_name, COUNT(*) 
                        FROM public.alertas 
                        WHERE tenant_id = %s AND camera_name = %s AND timestamp >= NOW() - INTERVAL '24 HOURS'
                        GROUP BY camera_name
                    """, (tenant_id, camera_name))
                else:
                    cursor.execute("""
                        SELECT camera_name, COUNT(*) 
                        FROM public.alertas 
                        WHERE tenant_id = %s AND timestamp >= NOW() - INTERVAL '24 HOURS'
                        GROUP BY camera_name
                    """, (tenant_id,))
                
                camera_stats = {}
                for row in cursor.fetchall():
                    cam_name = row[0] or "Geral"
                    camera_stats[cam_name] = row[1]
                    
                # If no last 24 hours exists, fallback to all active alerts
                if not camera_stats:
                    if camera_name and camera_name.lower() != 'all':
                        cursor.execute("""
                            SELECT camera_name, COUNT(*) 
                            FROM public.alertas 
                            WHERE tenant_id = %s AND camera_name = %s
                            GROUP BY camera_name
                        """, (tenant_id, camera_name))
                    else:
                        cursor.execute("""
                            SELECT camera_name, COUNT(*) 
                            FROM public.alertas 
                            WHERE tenant_id = %s
                            GROUP BY camera_name
                        """, (tenant_id,))
                    for row in cursor.fetchall():
                        cam_name = row[0] or "Geral"
                        camera_stats[cam_name] = row[1]
                
                # Hourly distribution (08h, 12h, 16h, 20h, 22h buckets)
                if camera_name and camera_name.lower() != 'all':
                    cursor.execute("""
                        SELECT EXTRACT(HOUR FROM timestamp) as hr, COUNT(*)
                        FROM public.alertas
                        WHERE tenant_id = %s AND camera_name = %s AND timestamp >= CURRENT_DATE
                        GROUP BY hr
                    """, (tenant_id, camera_name))
                else:
                    cursor.execute("""
                        SELECT EXTRACT(HOUR FROM timestamp) as hr, COUNT(*)
                        FROM public.alertas
                        WHERE tenant_id = %s AND timestamp >= CURRENT_DATE
                        GROUP BY hr
                    """, (tenant_id,))
                
                hourly_raw = {}
                for row in cursor.fetchall():
                    hr = int(row[0])
                    hourly_raw[hr] = row[1]
                    
                cursor.close()
                
                # Buckets mapping
                hourly_buckets = {
                    "08h": sum(v for k, v in hourly_raw.items() if k < 10),
                    "12h": sum(v for k, v in hourly_raw.items() if 10 <= k < 14),
                    "16h": sum(v for k, v in hourly_raw.items() if 14 <= k < 18),
                    "20h": sum(v for k, v in hourly_raw.items() if 18 <= k < 21),
                    "22h": sum(v for k, v in hourly_raw.items() if k >= 21)
                }
                
                self.send_success_response({
                    "success": True,
                    "camera_stats": camera_stats,
                    "hourly_buckets": hourly_buckets
                })
            except Exception as e:
                print(f"[ERROR] Falha ao carregar analytics para o tenant {tenant_id}: {e}")
                traceback.print_exc()
                self.send_error_response(f"Erro ao carregar analytics: {e}")
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
            return
        elif clean_path == '/api/edge-status':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            tenant_id = query_params.get('tenant_id', [''])[0].strip()
            if not tenant_id:
                self.send_error_response("tenant_id é obrigatório.")
                return
            
            last_seen = active_edge_nodes.get(tenant_id, 0)
            is_online = (time.time() - last_seen) < 25.0
            self.send_success_response({"success": True, "online": is_online})
            return
            
        elif clean_path == '/api/get-settings':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            tenant_id = query_params.get('tenant_id', [''])[0].strip()
            if not tenant_id:
                self.send_error_response("tenant_id é obrigatório.")
                return
            conn = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ai_sensitivity, ai_fps, n8n_webhook_url, recovery_master_key 
                    FROM public.configuracoes 
                    WHERE tenant_id = %s;
                """, (tenant_id,))
                row = cursor.fetchone()
                if not row:
                    # Insert default settings if not exists
                    cursor.execute("""
                        INSERT INTO public.configuracoes (tenant_id)
                        VALUES (%s)
                        ON CONFLICT DO NOTHING;
                    """, (tenant_id,))
                    conn.commit()
                    cursor.execute("""
                        SELECT ai_sensitivity, ai_fps, n8n_webhook_url, recovery_master_key 
                        FROM public.configuracoes 
                        WHERE tenant_id = %s;
                    """, (tenant_id,))
                    row = cursor.fetchone()
                
                cursor.close()
                self.send_success_response({
                    "success": True,
                    "ai_sensitivity": row[0],
                    "ai_fps": row[1],
                    "n8n_webhook_url": row[2],
                    "recovery_master_key": row[3]
                })
            except Exception as e:
                print(f"[ERROR] Falha ao carregar configuracoes: {e}")
                self.send_error_response(f"Erro ao carregar configurações: {e}")
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
            return
            
        elif clean_path == '/api/stream-alerts':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with sse_lock:
                sse_subscribers.add(self.wfile)
            print(f"[SSE] Cliente conectado para alertas ao vivo. Inscritos: {len(sse_subscribers)}")
            
            try:
                while True:
                    time.sleep(15)
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
            except Exception:
                pass
            finally:
                with sse_lock:
                    sse_subscribers.discard(self.wfile)
                print(f"[SSE] Cliente desconectado. Restantes: {len(sse_subscribers)}")
            return

        elif clean_path == '/api/cameras/roi':
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, 'config_roi.json')
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        roi_data = json.load(f)
                    self.send_success_response({"success": True, "rois": roi_data})
                except Exception as e:
                    self.send_error_response(f"Erro ao ler ROI: {e}")
            else:
                self.send_success_response({"success": True, "rois": {}})
            return

        elif clean_path.startswith('/evidencias/'):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            filename = os.path.basename(clean_path)
            file_path = os.path.join(script_dir, 'evidencias', filename)
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Length', str(os.path.getsize(file_path)))
                self.send_header('Cache-Control', 'public, max-age=86400')
                self.end_headers()
                try:
                    with open(file_path, 'rb') as f:
                        self.wfile.write(f.read())
                except Exception:
                    pass
                return
            else:
                self.send_error(404, "Vídeo de evidência não encontrado.")
                return

        # Default index resolution
        if clean_path == '/' or clean_path == '':
            self.path = '/index.html'
        else:
            self.path = clean_path
            
        return super().do_GET()

    def do_POST(self):
        # API Routes
        if self.path == '/api/login':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                email = payload.get('email', '').strip()
                password = payload.get('password', '')
                
                if not email or not password:
                    self.send_error_response("E-mail e senha são obrigatórios.")
                    return
                
                # Fetch N8N webhook URL from environment or default to local tunnel
                n8n_base = os.environ.get('N8N_URL', 'http://127.0.0.1:5678')
                n8n_webhook_url = f"{n8n_base}/webhook/8c4ab76c-30c1-419b-a010-91a5e55209f8/webhook/aegiseye-auth"
                
                print(f"[AUTH] Encaminhando consulta para o n8n: {n8n_webhook_url}")
                
                # Call n8n Webhook for DB query (Secure isolation)
                req_data = json.dumps({"email": email}).encode('utf-8')
                req = urllib.request.Request(
                    n8n_webhook_url,
                    data=req_data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                n8n_response = None
                try:
                    with urllib.request.urlopen(req, timeout=5) as response:
                        res_body = response.read().decode('utf-8')
                        n8n_response = json.loads(res_body)
                except Exception as e:
                    print(f"[WARN] n8n offline ou erro no webhook ({e}). Executando consulta direta ao banco de dados...")
                
                user_row = None
                if n8n_response:
                    if isinstance(n8n_response, list) and len(n8n_response) > 0:
                        user_row = n8n_response[0]
                    elif isinstance(n8n_response, dict):
                        user_row = n8n_response

                # Direct PostgreSQL Fallback Query if n8n returned no user or was unreachable
                if not user_row or 'password_hash' not in user_row:
                    conn_fb = None
                    try:
                        conn_fb = get_db_connection()
                        cur_fb = conn_fb.cursor()
                        cur_fb.execute("""
                            SELECT u.id, u.name, u.email, u.password_hash, u.tenant_id, t.name as tenant_name
                            FROM public.users u
                            LEFT JOIN public.tenants t ON u.tenant_id = t.id
                            WHERE LOWER(u.email) = LOWER(%s);
                        """, (email,))
                        row_fb = cur_fb.fetchone()
                        cur_fb.close()
                        if row_fb:
                            user_row = {
                                "id": row_fb[0],
                                "name": row_fb[1],
                                "email": row_fb[2],
                                "password_hash": row_fb[3],
                                "tenant_id": row_fb[4],
                                "tenant_name": row_fb[5] or "Tenant"
                            }
                    except Exception as fb_err:
                        print(f"[ERROR] Falha na consulta de fallback no PostgreSQL: {fb_err}")
                    finally:
                        if conn_fb:
                            try: conn_fb.close()
                            except Exception: pass

                if user_row and 'password_hash' in user_row:
                    password_hash = user_row['password_hash']
                    tenant_id = user_row.get('tenant_id')
                    user_name = user_row.get('name', 'Usuário')
                    tenant_name = user_row.get('tenant_name', 'Tenant')
                    
                    # Verify bcrypt hash locally in Python
                    if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                        session_token = str(uuid.uuid4())
                        
                        response_data = {
                            "success": True,
                            "session_token": session_token,
                            "user_name": user_name,
                            "user_id": str(user_row.get('id')),
                            "tenant_id": str(tenant_id),
                            "tenant_name": tenant_name
                        }
                        self.send_success_response(response_data)
                        print(f"[AUTH] Login bem-sucedido via n8n para {email} no Tenant {tenant_name}")
                    else:
                        print(f"[AUTH] Senha inválida para o e-mail: {email}")
                        self.send_error_response("E-mail ou senha incorretos.")
                else:
                    print(f"[AUTH] Usuário não encontrado no n8n: {email}")
                    self.send_error_response("E-mail ou senha incorretos.")
                
            except Exception as e:
                print(f"[ERROR] Erro interno durante autenticação: {e}")
                self.send_error_response("Erro interno de comunicação.")
        
        elif self.path == '/api/register':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                nome = payload.get('nome', '').strip()
                email = payload.get('email', '').strip()
                whatsapp = payload.get('whatsapp', '').strip()
                nome_empresa = payload.get('nome_empresa', '').strip()
                cpf = payload.get('cpf', '').strip()
                
                if not all([nome, email, whatsapp, nome_empresa, cpf]):
                    self.send_error_response("Todos os campos são obrigatórios.")
                    return
                
                # Fetch N8N webhook URL from environment or default to local tunnel
                n8n_base = os.environ.get('N8N_URL', 'http://127.0.0.1:5678')
                n8n_webhook_url = f"{n8n_base}/webhook/e4f8a6b1-cdbe-4712-a1f9-d892a01f30f5/webhook/cadastro-seguranca"
                
                print(f"[REGISTER] Encaminhando cadastro para o n8n: {n8n_webhook_url}")
                
                # Call n8n Webhook for registration
                req_data = json.dumps({
                    "nome": nome,
                    "email": email,
                    "whatsapp": whatsapp,
                    "nome_empresa": nome_empresa,
                    "cpf": cpf
                }).encode('utf-8')
                
                req = urllib.request.Request(
                    n8n_webhook_url,
                    data=req_data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                try:
                    with urllib.request.urlopen(req, timeout=12) as response:
                        res_body = response.read().decode('utf-8')
                        n8n_response = json.loads(res_body)
                        status_code = response.getcode()
                except urllib.error.HTTPError as he:
                    res_body = he.read().decode('utf-8')
                    try:
                        n8n_response = json.loads(res_body)
                    except Exception:
                        n8n_response = {"success": False, "message": "Erro de comunicação com o n8n."}
                    status_code = he.code
                except Exception as e:
                    print(f"[ERROR] Falha na comunicação com o n8n para cadastro: {e}")
                    self.send_error_response("Serviço de cadastro offline.")
                    return
                
                # Forward response to frontend
                self.send_response(status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(n8n_response).encode('utf-8'))
                
            except Exception as e:
                print(f"[ERROR] Erro interno durante o cadastro: {e}")
                self.send_error_response("Erro interno ao processar o cadastro.")
        
        elif self.path == '/api/activate':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                token = payload.get('token', '').strip()
                password = payload.get('password', '')
                
                if not token or not password:
                    self.send_error_response("Token e senha são obrigatórios.")
                    return
                
                if len(password) < 6:
                    self.send_error_response("A senha deve ter no mínimo 6 caracteres.")
                    return
                
                # Criptografar a senha com bcrypt localmente
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                n8n_base = os.environ.get('N8N_URL', 'http://127.0.0.1:5678')
                n8n_webhook_url = f"{n8n_base}/webhook/f1f2f3f4-5678-4c3d-b2a1-098765432109/webhook_activate/activate-user"
                
                print(f"[ACTIVATE] Encaminhando ativação de usuário para o n8n: {n8n_webhook_url}")
                
                req_data = json.dumps({
                    "token": token,
                    "password_hash": password_hash
                }).encode('utf-8')
                
                req = urllib.request.Request(
                    n8n_webhook_url,
                    data=req_data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                try:
                    with urllib.request.urlopen(req, timeout=15) as response:
                        res_body = response.read().decode('utf-8')
                        n8n_response = json.loads(res_body)
                        status_code = response.getcode()
                except urllib.error.HTTPError as he:
                    res_body = he.read().decode('utf-8')
                    try:
                        n8n_response = json.loads(res_body)
                    except Exception:
                        n8n_response = {"success": False, "message": "Erro de comunicação com o n8n."}
                    status_code = he.code
                except Exception as e:
                    print(f"[ERROR] Falha na comunicação com o n8n para ativação: {e}")
                    self.send_error_response("Serviço de ativação offline.")
                    return
                
                # Forward response to frontend
                self.send_response(status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(n8n_response).encode('utf-8'))
                
            except Exception as e:
                print(f"[ERROR] Erro interno durante ativação: {e}")
                self.send_error_response("Erro interno ao processar ativação.")
        elif self.path == '/api/configurar':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                n8n_base = os.environ.get('N8N_URL', 'http://127.0.0.1:5678')
                n8n_webhook_url = f"{n8n_base}/webhook/9c8d7e6f-5a4b-3c2d-1e0f-9876543210fe/webhook/configurar-cameras"
                
                print(f"[CONFIGURAR] Encaminhando configuração para o n8n: {n8n_webhook_url}")
                
                req = urllib.request.Request(
                    n8n_webhook_url,
                    data=post_data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                try:
                    with urllib.request.urlopen(req, timeout=15) as response:
                        res_body = response.read().decode('utf-8')
                        n8n_response = json.loads(res_body)
                        status_code = response.getcode()
                except urllib.error.HTTPError as he:
                    res_body = he.read().decode('utf-8')
                    try:
                        n8n_response = json.loads(res_body)
                    except Exception:
                        n8n_response = {"success": False, "message": "Erro de comunicação com o n8n."}
                    status_code = he.code
                except Exception as e:
                    print(f"[ERROR] Falha na comunicação com o n8n para configurar: {e}")
                    self.send_error_response("Serviço de configuração offline.")
                    return
                
                # Forward response to frontend
                self.send_response(status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(n8n_response).encode('utf-8'))
                
            except Exception as e:
                print(f"[ERROR] Erro interno durante configuração: {e}")
                self.send_error_response("Erro interno ao processar configuração.")
        elif self.path == '/api/save-settings':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                tenant_id = payload.get('tenant_id', '').strip()
                ai_sensitivity = int(payload.get('ai_sensitivity', 75))
                ai_fps = int(payload.get('ai_fps', 10))
                n8n_webhook_url = payload.get('n8n_webhook_url', '').strip()
                recovery_master_key = payload.get('recovery_master_key', '').strip()
                
                if not tenant_id:
                    self.send_error_response("tenant_id é obrigatório.")
                    return
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO public.configuracoes (tenant_id, ai_sensitivity, ai_fps, n8n_webhook_url, recovery_master_key)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id)
                    DO UPDATE SET 
                        ai_sensitivity = EXCLUDED.ai_sensitivity,
                        ai_fps = EXCLUDED.ai_fps,
                        n8n_webhook_url = EXCLUDED.n8n_webhook_url,
                        recovery_master_key = EXCLUDED.recovery_master_key;
                """, (tenant_id, ai_sensitivity, ai_fps, n8n_webhook_url, recovery_master_key))
                conn.commit()
                cursor.close()
                conn.close()
                self.send_success_response({"success": True, "message": "Configurações salvas com sucesso."})
            except Exception as e:
                print(f"[ERROR] Falha ao salvar configuracoes: {e}")
                self.send_error_response(f"Erro ao salvar configurações: {e}")
        elif self.path == '/api/reset-password':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                user_id = payload.get('user_id', '').strip()
                current_password = payload.get('current_password', '')
                new_password = payload.get('new_password', '')
                
                if not user_id or not current_password or not new_password:
                    self.send_error_response("Todos os campos são obrigatórios.")
                    return
                
                # Validation of password strength
                if len(new_password) < 8:
                    self.send_error_response("A nova senha deve ter pelo menos 8 caracteres.")
                    return
                import re
                if not re.search(r"[a-z]", new_password) or not re.search(r"[A-Z]", new_password) or not re.search(r"[0-9]", new_password) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
                    self.send_error_response("A nova senha deve conter letras maiúsculas, minúsculas, números e caracteres especiais.")
                    return
                
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Fetch user tenant and hash
                cursor.execute("SELECT tenant_id, password_hash FROM public.users WHERE id = %s;", (user_id,))
                user_row = cursor.fetchone()
                if not user_row:
                    cursor.close()
                    conn.close()
                    self.send_error_response("Usuário não encontrado.")
                    return
                
                tenant_id, password_hash = user_row
                
                # Fetch master key for tenant
                cursor.execute("SELECT recovery_master_key FROM public.configuracoes WHERE tenant_id = %s;", (str(tenant_id),))
                cfg_row = cursor.fetchone()
                master_key = cfg_row[0] if cfg_row else "AEGISEYE_MASTER_KEY_2026"
                
                # Authentication check: either correct current password OR Master Key bypass
                is_authorized = False
                if current_password == master_key:
                    is_authorized = True
                    print(f"[SECURITY] Redefinição de senha autorizada via Chave Mestra de Recuperação para o User {user_id}")
                else:
                    try:
                        if bcrypt.checkpw(current_password.encode('utf-8'), password_hash.encode('utf-8')):
                            is_authorized = True
                    except Exception:
                        pass
                
                if not is_authorized:
                    cursor.close()
                    conn.close()
                    self.send_error_response("Senha atual incorreta (ou chave mestra inválida).")
                    return
                
                # Update user password
                new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute("UPDATE public.users SET password_hash = %s WHERE id = %s;", (new_hash, user_id))
                conn.commit()
                cursor.close()
                conn.close()
                self.send_success_response({"success": True, "message": "Senha redefinida com sucesso."})
            except Exception as e:
                print(f"[ERROR] Falha ao redefinir senha: {e}")
                self.send_error_response(f"Erro ao redefinir senha: {e}")
        elif self.path == '/api/edge-ping':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                tenant_id = payload.get('tenant_id', '').strip()
                if not tenant_id:
                    self.send_error_response("tenant_id é obrigatório.")
                    return
                active_edge_nodes[tenant_id] = time.time()
                self.send_success_response({"success": True, "message": "Heartbeat received."})
            except Exception as e:
                self.send_error_response(f"Erro ao processar heartbeat: {e}")
        elif self.path == '/api/resolve-alert':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                alert_id = payload.get('alert_id', '').strip()
                if not alert_id:
                    self.send_error_response("alert_id é obrigatório.")
                    return
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE public.alertas 
                    SET status = 'resolved'
                    WHERE id = %s;
                """, (alert_id,))
                conn.commit()
                cursor.close()
                conn.close()
                self.send_success_response({"success": True, "message": "Alerta resolvido com sucesso."})
            except Exception as e:
                print(f"[ERROR] Falha ao resolver alerta: {e}")
                self.send_error_response(f"Erro ao resolver alerta: {e}")

        elif self.path == '/api/trigger-alert':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                tenant_id = payload.get('tenant_id', 'a7974ee4-329c-4c06-a57a-0377bcae242e')
                user_id = payload.get('user_id', '')
                title = payload.get('title', 'Alerta de Segurança')
                severity = payload.get('severity', 'critical')
                camera_name = payload.get('camera_name', 'Câmera Geral')
                confidence = int(payload.get('confidence', 90))
                details = payload.get('details', 'Detecção comportamental em tempo real')
                risk_type = payload.get('risk_type', 'Detecção automática')
                video_url = payload.get('video_url', '')

                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO public.alertas 
                    (tenant_id, user_id, title, severity, camera_name, confidence_score, details, risk_type, video_url, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
                    RETURNING id, timestamp;
                """, (tenant_id, user_id if user_id else None, title, severity, camera_name, confidence, details, risk_type, video_url))
                row = cursor.fetchone()
                alert_id = str(row[0])
                timestamp_val = row[1]
                conn.commit()
                cursor.close()
                conn.close()

                alert_evt = {
                    "id": alert_id,
                    "title": title,
                    "severity": severity,
                    "label": "CRÍTICO" if severity == "critical" else ("ATENÇÃO" if severity == "warning" else "MÉDIO"),
                    "camera": camera_name,
                    "confidence": confidence,
                    "details": details,
                    "trigger": risk_type,
                    "video_url": video_url,
                    "time": timestamp_val.strftime("%H:%M") if timestamp_val else time.strftime("%H:%M"),
                    "timestamp": timestamp_val.isoformat() if timestamp_val else None
                }
                broadcast_alert_event(alert_evt)
                self.send_success_response({"success": True, "alert": alert_evt})
            except Exception as e:
                print(f"[ERROR] Falha ao disparar alerta: {e}")
                self.send_error_response(f"Erro ao disparar alerta: {e}")

        elif self.path == '/api/save-roi':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                camera_key = payload.get('camera_id', 'default')
                polygon = payload.get('polygon', [])
                
                script_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(script_dir, 'config_roi.json')
                
                config_data = {"camera_rois": {}}
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                
                if "camera_rois" not in config_data:
                    config_data["camera_rois"] = {}
                
                config_data["camera_rois"][camera_key] = {
                    "enabled": True,
                    "camera_type": "internal",
                    "polygon": polygon
                }
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4)
                    
                self.send_success_response({"success": True, "message": "ROI salva com sucesso."})
            except Exception as e:
                print(f"[ERROR] Falha ao salvar ROI: {e}")
                self.send_error_response(f"Erro ao salvar ROI: {e}")
        else:
            self.send_error(404, "Route Not Found")

    def send_success_response(self, data):
        json_str = json.dumps(data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json_str.encode('utf-8'))

    def send_error_response(self, message):
        json_str = json.dumps({"success": False, "message": message})
        self.send_response(400)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json_str.encode('utf-8'))

if __name__ == '__main__':
    # Change working directory to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Allow immediate address reuse
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    
    with http.server.ThreadingHTTPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Python Server (n8n API Proxy) running at http://localhost:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
