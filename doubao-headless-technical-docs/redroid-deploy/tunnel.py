"""Forward a localhost ADB port over SSH; not needed by the Linux worker."""
import argparse
import select
import socketserver

from remote import connect

parser = argparse.ArgumentParser()
parser.add_argument('--local-port', type=int, default=15557)
parser.add_argument('--remote-port', type=int, default=5557)
args = parser.parse_args()
client, _ = connect()
transport = client.get_transport()
transport.set_keepalive(20)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        channel = transport.open_channel("direct-tcpip", ("127.0.0.1", args.remote_port), self.client_address)
        try:
            while True:
                readable, _, _ = select.select([self.request, channel], [], [], 20)
                if not transport.is_active():
                    break
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    (channel if source is self.request else self.request).sendall(data)
        finally:
            channel.close()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


try:
    with Server(("127.0.0.1", args.local_port), Handler) as server:
        print(f"ADB tunnel ready: 127.0.0.1:{args.local_port}", flush=True)
        server.serve_forever()
finally:
    client.close()
