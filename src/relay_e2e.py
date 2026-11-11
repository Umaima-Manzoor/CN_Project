import socket
import ssl

def main():
    HOST = '0.0.0.0'
    PORT = 9997

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(
        certfile='../certs/server.crt',
        keyfile='../certs/server.key'
    )
    context.minimum_version = ssl.TLSVersion.TLSv1_3

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"[RELAY-E2E] Listening on {HOST}:{PORT} ...")

    raw_conn, addr = server.accept()
    print(f"[RELAY-E2E] TCP connection from {addr}")

    conn = context.wrap_socket(raw_conn, server_side=True)
    print(f"[RELAY-E2E] TLS handshake done! Version: {conn.version()}")

    while True:
        data = conn.recv(65536)
        if not data:
            break
        conn.sendall(data)

    print("[RELAY-E2E] Client disconnected.")
    conn.close()
    server.close()

if __name__ == '__main__':
    main()
