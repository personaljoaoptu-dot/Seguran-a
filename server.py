import http.server
import socketserver
import os
import urllib.parse
import urllib.request
import json
import bcrypt
import uuid

PORT = 8000

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Disable browser cache
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        # Parse path to strip query parameters (e.g. ?v=2)
        parsed_url = urllib.parse.urlparse(self.path)
        clean_path = parsed_url.path
        
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
                n8n_webhook_url = f"{n8n_base}/webhook/aegiseye-auth"
                
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
        else:
            self.send_error(404, "Route Not Found")

    def send_success_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_response(self, message):
        self.send_response(400)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"success": False, "message": message}).encode('utf-8'))

if __name__ == '__main__':
    # Change working directory to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Allow immediate address reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Python Server (n8n API Proxy) running at http://localhost:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
