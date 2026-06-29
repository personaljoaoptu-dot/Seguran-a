import http.server
import socketserver
import os
import urllib.parse
import urllib.request
import json
import bcrypt
import uuid
import traceback

PORT = 8000

def get_db_connection():
    # Try internal docker host first, then fall back to public IP
    for host in ["postgres_db", "144.91.121.55"]:
        try:
            import pg8000
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
                conn.close()
                self.send_success_response({"success": True, "cameras": cameras})
            except Exception as e:
                print(f"[ERROR] Falha ao carregar câmeras para o tenant {tenant_id}: {e}")
                traceback.print_exc()
                self.send_error_response(f"Erro ao carregar câmeras: {e}")
            return

        elif clean_path == '/api/get-alerts':
            query_params = urllib.parse.parse_qs(parsed_url.query)
            tenant_id = query_params.get('tenant_id', [''])[0].strip()
            if not tenant_id:
                self.send_error_response("tenant_id é obrigatório.")
                return
            try:
                conn = get_db_connection()
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
                        "camera": row[3] or "Câmera Geral",
                        "confidence": int(row[4]) if row[4] is not None else 90
                    })
                cursor.close()
                conn.close()
                self.send_success_response({"success": True, "alerts": alerts})
            except Exception as e:
                print(f"[ERROR] Falha ao carregar alertas para o tenant {tenant_id}: {e}")
                traceback.print_exc()
                self.send_error_response(f"Erro ao carregar alertas: {e}")
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
                
                try:
                    with urllib.request.urlopen(req, timeout=8) as response:
                        res_body = response.read().decode('utf-8')
                        n8n_response = json.loads(res_body)
                except Exception as e:
                    print(f"[ERROR] Falha na comunicação com o n8n: {e}")
                    self.send_error_response("Falha de autenticação: Serviço de segurança offline.")
                    return
                
                # n8n PostgreSQL query output is typically an array of records
                user_row = None
                if isinstance(n8n_response, list) and len(n8n_response) > 0:
                    user_row = n8n_response[0]
                elif isinstance(n8n_response, dict):
                    # In case n8n returns directly the object
                    user_row = n8n_response
                
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
