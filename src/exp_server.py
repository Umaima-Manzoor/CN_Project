import socket
import ssl
import sys

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'plaintext'
    ports = {'plaintext': 9999, 'tls': 9998, 'e2e': 9997}
    PORT = ports[mode]
    HOST = '0.0.0.0'

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)

    if mode in ('tls', 'e2e'):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certfile='../certs/server.crt',
            keyfile='../certs/server.key'
        )
        context.minimum_version = ssl.TLSVersion.TLSv1_3

    print(f"READY:{mode}:{PORT}", flush=True)

    raw_conn, addr = server.accept()

    if mode in ('tls', 'e2e'):
        conn = context.wrap_socket(raw_conn, server_side=True)
    else:
        conn = raw_conn

    while True:
        data = conn.recv(65536)
        if not data:
            break
        conn.sendall(data)

    conn.close()
    server.close()

if __name__ == '__main__':
    main()
