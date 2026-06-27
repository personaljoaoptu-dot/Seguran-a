import http.server
import socketserver
import os
import urllib.parse

PORT = 8000

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Disable browser cache to prevent loading stale resources
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

if __name__ == '__main__':
    # Change working directory to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Allow immediate address reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Python Server running at http://localhost:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
