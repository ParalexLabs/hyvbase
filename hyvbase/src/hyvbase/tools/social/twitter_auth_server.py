from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser
import threading
import time

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle the OAuth callback."""
        # Parse the URL and get the code and state
        query_components = parse_qs(urlparse(self.path).query)
        
        # Send response to browser
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Store both code and state in the server
        if 'code' in query_components and 'state' in query_components:
            self.server.oauth_code = query_components['code'][0]
            self.server.oauth_state = query_components['state'][0]
            response = "<html><body><h1>Authorization successful!</h1><p>You can close this window now.</p></body></html>"
        else:
            self.server.oauth_code = None
            self.server.oauth_state = None
            response = "<html><body><h1>Authorization failed!</h1><p>Missing code or state parameter.</p></body></html>"
            
        self.wfile.write(response.encode())
    
    def log_message(self, format, *args):
        """Suppress logging."""
        pass

def get_oauth_code_and_state(port=8000):
    """Start server and get OAuth code and state."""
    # Create server
    server = HTTPServer(('localhost', port), OAuthCallbackHandler)
    server.oauth_code = None
    server.oauth_state = None
    
    # Start server in a thread
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    
    print(f"\nStarting local server on port {port}")
    print("Waiting for OAuth callback...")
    
    # Wait for the code and state
    while server.oauth_code is None or server.oauth_state is None:
        time.sleep(0.1)
    
    # Get values before shutdown
    code = server.oauth_code
    state = server.oauth_state
    
    # Shutdown server
    server.shutdown()
    server.server_close()
    
    return code, state 