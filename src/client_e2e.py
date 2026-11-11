import socket
import ssl
import time
from nacl.public import PrivateKey, Box
from nacl.utils import random

def main():
    HOST = '10.0.3.2'
    PORT = 9997
    NUM_MSGS = 5
    SIZE = 64

    msg = b'A' * SIZE

    client_sk = PrivateKey.generate()
    server_pk = PrivateKey.generate().public_key
    box = Box(client_sk, server_pk)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.minimum_version = ssl.TLSVersion.TLSv1_3

    start_tcp = time.perf_counter()
    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_sock.connect((HOST, PORT))
    end_tcp = time.perf_counter()
    tcp_ms = (end_tcp - start_tcp) * 1000

    start_tls = time.perf_counter()
    sock = context.wrap_socket(raw_sock, server_hostname='relay')
    end_tls = time.perf_counter()
    tls_ms = (end_tls - start_tls) * 1000

    start_e2e = time.perf_counter()
    nonce = random(Box.NONCE_SIZE)
    encrypted_msg = box.encrypt(msg, nonce)
    end_e2e = time.perf_counter()
    e2e_ms = (end_e2e - start_e2e) * 1000

    total_ms = tcp_ms + tls_ms + e2e_ms
    print(f"[CLIENT-E2E] Connected!")
    print(f"  TCP handshake:   {tcp_ms:.3f} ms")
    print(f"  TLS handshake:   {tls_ms:.3f} ms")
    print(f"  E2E setup:       {e2e_ms:.3f} ms")
    print(f"  Total handshake: {total_ms:.3f} ms")
    print(f"  Plaintext size:  {len(msg)} bytes")
    print(f"  Encrypted size:  {len(encrypted_msg)} bytes")
    print(f"  E2E overhead:    {len(encrypted_msg) - len(msg)} bytes")

    for i in range(NUM_MSGS):
        nonce = random(Box.NONCE_SIZE)
        start = time.perf_counter()
        encrypted = box.encrypt(msg, nonce)
        sock.sendall(encrypted)
        resp = sock.recv(65536)
        decrypted = box.decrypt(resp)
        end = time.perf_counter()
        rtt = (end - start) * 1000
        print(f"[CLIENT-E2E] Msg {i+1}/{NUM_MSGS} | {SIZE}B | RTT: {rtt:.3f} ms")

    sock.close()
    print("[CLIENT-E2E] Done.")

if __name__ == '__main__':
    main()
