import socket
import ssl
import time
import sys

def recv_exact(sock, n):
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            break
        data += chunk
    return data

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'plaintext'
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    ports = {'plaintext': 9999, 'tls': 9998, 'e2e': 9997}
    HOST = '10.0.3.2'
    PORT = ports[mode]
    msg = b'A' * size

    if mode in ('tls', 'e2e'):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.minimum_version = ssl.TLSVersion.TLSv1_3

    start_tcp = time.perf_counter()
    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_sock.connect((HOST, PORT))
    end_tcp = time.perf_counter()
    tcp_ms = (end_tcp - start_tcp) * 1000

    tls_ms = 0.0
    if mode in ('tls', 'e2e'):
        start_tls = time.perf_counter()
        sock = context.wrap_socket(raw_sock, server_hostname='relay')
        end_tls = time.perf_counter()
        tls_ms = (end_tls - start_tls) * 1000
    else:
        sock = raw_sock

    e2e_ms = 0.0
    e2e_overhead = 0
    box = None
    if mode == 'e2e':
        from nacl.public import PrivateKey, Box
        from nacl.utils import random
        client_sk = PrivateKey.generate()
        server_pk = PrivateKey.generate().public_key
        box = Box(client_sk, server_pk)
        start_e2e = time.perf_counter()
        nonce = random(Box.NONCE_SIZE)
        enc = box.encrypt(msg, nonce)
        end_e2e = time.perf_counter()
        e2e_ms = (end_e2e - start_e2e) * 1000
        e2e_overhead = len(enc) - len(msg)

    total_handshake = tcp_ms + tls_ms + e2e_ms
    print(f"HANDSHAKE:tcp={tcp_ms:.3f}:tls={tls_ms:.3f}:e2e={e2e_ms:.3f}:total={total_handshake:.3f}", flush=True)
    print(f"OVERHEAD:{e2e_overhead}", flush=True)

    rtts = []
    for i in range(count):
        if mode == 'e2e':
            nonce = random(Box.NONCE_SIZE)
            start = time.perf_counter()
            encrypted = box.encrypt(msg, nonce)
            sock.sendall(encrypted)
            resp = recv_exact(sock, len(encrypted))
            decrypted = box.decrypt(resp)
            end = time.perf_counter()
        else:
            start = time.perf_counter()
            sock.sendall(msg)
            resp = recv_exact(sock, size)
            end = time.perf_counter()
        rtt = (end - start) * 1000
        rtts.append(rtt)

    avg_rtt = sum(rtts) / len(rtts) if rtts else 0.0
    print(f"AVG_RTT:{avg_rtt:.3f}", flush=True)

    sock.close()

if __name__ == '__main__':
    main()
