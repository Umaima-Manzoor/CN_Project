import socket
import ssl
import time
import sys

# WHAT: Helper to receive exact byte count over TCP
# WHY: Prevents incomplete reads for large packets (e.g. 16KB)
def recv_exact(sock, n):
    data = bytearray()
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'plaintext'
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    is_recipient = (len(sys.argv) > 4 and sys.argv[4] == 'recipient')

    ports = {'plaintext': 9999, 'tls': 9998, 'e2e': 9997}
    HOST = '10.0.3.2'
    PORT = ports[mode]
    msg = b'A' * size

    # TLS Context Setup
    if mode in ('tls', 'e2e'):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.minimum_version = ssl.TLSVersion.TLSv1_3

    # TCP Handshake Measurement
    start_tcp = time.perf_counter()
    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_sock.connect((HOST, PORT))
    end_tcp = time.perf_counter()
    tcp_ms = (end_tcp - start_tcp) * 1000

    # TLS Handshake Measurement
    tls_ms = 0.0
    if mode in ('tls', 'e2e'):
        start_tls = time.perf_counter()
        sock = context.wrap_socket(raw_sock, server_hostname='relay')
        end_tls = time.perf_counter()
        tls_ms = (end_tls - start_tls) * 1000
    else:
        sock = raw_sock

    # E2E Key Exchange & Setup
    e2e_ms = 0.0
    e2e_overhead = 0
    box = None
    if mode == 'e2e':
        from nacl.public import PrivateKey, Box
        from nacl.utils import random

        # Reproducible complementary Curve25519 keypairs for ECDH key agreement
        sk1 = PrivateKey(b'\x01' * 32)
        pk1 = sk1.public_key
        sk2 = PrivateKey(b'\x02' * 32)
        pk2 = sk2.public_key

        start_e2e = time.perf_counter()
        if is_recipient:
            box = Box(sk2, pk1)
        else:
            box = Box(sk1, pk2)
        end_e2e = time.perf_counter()

        # Overhead measurement (24B nonce + 16B Poly1305 MAC tag = 40 bytes)
        nonce = random(Box.NONCE_SIZE)
        enc_test = box.encrypt(msg, nonce)
        e2e_ms = (end_e2e - start_e2e) * 1000
        e2e_overhead = len(enc_test) - len(msg)

    if not is_recipient:
        total_handshake = tcp_ms + tls_ms + e2e_ms
        print(f"HANDSHAKE:tcp={tcp_ms:.3f}:tls={tls_ms:.3f}:e2e={e2e_ms:.3f}:total={total_handshake:.3f}", flush=True)
        print(f"OVERHEAD:{e2e_overhead}", flush=True)

    # Message Transmission Loop
    rtts = []

    if mode == 'e2e' and is_recipient:
        # Client 2 (Recipient): Echoes back decrypted and re-encrypted payload
        enc_len = size + 40
        for _ in range(count):
            enc_data = recv_exact(sock, enc_len)
            if not enc_data:
                break
            decrypted = box.decrypt(enc_data)
            # Send back same message
            reply_nonce = random(Box.NONCE_SIZE)
            reply_enc = box.encrypt(decrypted, reply_nonce)
            sock.sendall(reply_enc)
    else:
        # Client 1 (Sender) or Echo mode (Plaintext / TLS)
        for _ in range(count):
            if mode == 'e2e':
                nonce = random(Box.NONCE_SIZE)
                enc_msg = box.encrypt(msg, nonce)
                start = time.perf_counter()
                sock.sendall(enc_msg)
                resp = recv_exact(sock, len(enc_msg))
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
