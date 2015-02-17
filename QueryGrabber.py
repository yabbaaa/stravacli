from __future__ import print_function

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import socket, urlparse

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.received = urlparse.parse_qs(self.path.split('?',1)[1])
        self.send_response(200)
        self.end_headers()
        self.wfile.write(self.server.response)

class QueryGrabber(HTTPServer):
    def __init__(self, response='', address=None):
        self.received = None
        self.response = response
        if address!=None:
            HTTPServer.__init__(self, self.address, handler)
        else:
            for port in xrange(1024,65536):
                try: 
                    HTTPServer.__init__(self, ('localhost', port), handler)
                except socket.error as e:
                    if e.errno!=98: # Address already in use
                        raise
                else:
                    break
            else:
                raise e
    def root_uri(self):
        return 'http://{}:{:d}'.format(*self.server_address)


# client = Client()
# webserver = SingleUseHTTPServer(address=None, response='<title>Strava auth code received!</title>This window can be closed.')
# authorize_url = client.authorization_url(client_id=CLIENT_ID, redirect_uri='http://{}:{:d}'.format(*webserver.server_address))
# webbrowser.open(authorize_url, new=2, autoraise=True)
# webserver.handle_request()
# print( webserver.received )