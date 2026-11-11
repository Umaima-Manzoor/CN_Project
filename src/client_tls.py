import socket
import ssl
import time

def main():
    HOST = '10.0.3.2'
    PORT = 9998
    NUM_MSGS = 5
    SIZE = 64

    msg = b'A' * SIZE

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

    total_ms = tcp_ms + tls_ms
    print(f"[CLIENT-TLS] Connected!")
    print(f"  TCP handshake:   {tcp_ms:.3f} ms")
    print(f"  TLS handshake:   {tls_ms:.3f} ms")
    print(f"  Total handshake: {total_ms:.3f} ms")
    print(f"  TLS version:     {sock.version()}")

    for i in range(NUM_MSGS):
        start = time.perf_counter()
        sock.sendall(msg)
        resp = sock.recv(SIZE)
        end = time.perf_counter()
        rtt = (end - start) * 1000
        print(f"[CLIENT-TLS] Msg {i+1}/{NUM_MSGS} | {SIZE}B | RTT: {rtt:.3f} ms")

    sock.close()
    print("[CLIENT-TLS] Done.")

if __name__ == '__main__':
    main()
