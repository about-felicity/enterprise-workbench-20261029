"""Local-only login display tunnel, using the existing private SSH configuration."""
import select,socketserver,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'redroid-deploy'))
from remote import connect
client,_=connect();transport=client.get_transport();transport.set_keepalive(20)
class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        channel=transport.open_channel('direct-tcpip',('127.0.0.1',8820),self.request.getpeername())
        try:
            while True:
                ready,_,_=select.select([self.request,channel],[],[],30)
                for src in ready:
                    data=src.recv(65536)
                    if not data:return
                    (channel if src is self.request else self.request).sendall(data)
        finally:channel.close()
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True
with Server(('127.0.0.1',18820),Handler) as server:server.serve_forever()
