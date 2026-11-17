import socket
import ssl
import sys
import os

# WHAT: Calculate dynamic absolute path to certs directory relative to this script's location
# WHY: Allows server to run reliably regardless of current working directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CERTS_DIR = os.path.join(SCRIPT_DIR, "..", "certs")
CERT_FILE = os.path.join(CERTS_DIR, "server.crt")
KEY_FILE = os.path.join(CERTS_DIR, "server.key")

HOST = '10.0.3.2'
PORTS = {
    'plaintext': 9999,
    'tls': 9998,
    'e2e': 9997
}

def recv_exact(sock, nbytes):
    data = bytearray()
    while len(data) < nbytes:
        packet = sock.recv(nbytes - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def handle_plaintext(conn):
    try:
        while True:
            data = conn.recv(65536)
            if not data:
                break
            conn.sendall(data)
    except Exception:
        pass
    finally:
        conn.close()

def handle_tls(conn):
    try:
        while True:
            data = conn.recv(65536)
            if not data:
                break
            conn.sendall(data)
    except Exception:
        pass
    finally:
        conn.close()

def handle_e2e(conn):
    try:
        # First connection is Client 1 (sender) or Client 2 (recipient)
        c1, _ = conn.accept()
        c2, _ = conn.accept()
        
        # Simple bidirectional relay between c1 and c2
        def relay(src, dst):
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception:
                pass

        import threading
        t1 = threading.Thread(target=relay, args=(c1, c2))
        t2 = threading.Thread(target=relay, args=(c2, c1))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception:
        pass
    finally:
        conn.close()

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'plaintext'
    port = PORTS.get(mode, 9999)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, port))
    server_sock.listen(5)

    if mode in ['tls', 'e2e']:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
        server_sock = context.wrap_socket(server_sock, server_side=True)

    if mode == 'e2e':
        while True:
            try:
                handle_e2e(server_sock)
            except Exception:
                break
    else:
        while True:
            try:
                conn, _ = server_sock.accept()
                if mode == 'plaintext':
                    handle_plaintext(conn)
                else:
                    handle_tls(conn)
            except Exception:
                break

if __name__ == "__main__":
    main()
