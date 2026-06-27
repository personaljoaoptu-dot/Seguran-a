import http.server
import socketserver
import os
import urllib.parse
import json
import pg8000
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
                
                # Connect to PostgreSQL and query user
                conn = pg8000.connect(
                    host='144.91.121.55',
                    port=5432,
                    user='postgres',
                    password='KtnYcxnVOGjD4thzS6tlBcW9',
                    database='aegisyear'
                )
                cursor = conn.cursor()
                
                # Fetch user details + Tenant name
                cursor.execute("""
                    SELECT u.password_hash, u.tenant_id, u.name, t.name AS tenant_name
                    FROM users u
                    JOIN tenants t ON u.tenant_id = t.id
                    WHERE u.email = %s AND u.deleted_at IS NULL AND t.deleted_at IS NULL;
                """, (email,))
                
                user_row = cursor.fetchone()
                
                if user_row:
                    password_hash, tenant_id, user_name, tenant_name = user_row
                    
                    # Verify bcrypt hash
                    if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                        # Successful login - generate token
                        session_token = str(uuid.uuid4())
                        
                        response_data = {
                            "success": True,
                            "session_token": session_token,
                            "user_name": user_name,
                            "tenant_id": str(tenant_id),
                            "tenant_name": tenant_name
                        }
                        self.send_success_response(response_data)
                        
                        # Session audit trace - set RLS current_tenant_id for verification in DB
                        # (Normally, RLS is set during active database queries. Here we successfully validated
                        # and returned the verified tenant ID to the SaaS frontend).
                        print(f"[AUTH] Login bem-sucedido para {email} no Tenant {tenant_name} (RLS ID: {tenant_id})")
                    else:
                        print(f"[AUTH] Senha inválida para o e-mail: {email}")
                        self.send_error_response("E-mail ou senha incorretos.")
                else:
                    print(f"[AUTH] Usuário não encontrado ou inativo: {email}")
                    self.send_error_response("E-mail ou senha incorretos.")
                    
                cursor.close()
                conn.close()
                
            except Exception as e:
                print(f"[ERROR] Erro interno durante autenticação: {e}")
                self.send_error_response("Erro interno de comunicação com o banco de dados.")
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
        print(f"Python Server with Auth running at http://localhost:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
