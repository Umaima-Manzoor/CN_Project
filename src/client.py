import socket
import time
import sys

def main():
    HOST = '10.0.3.2'
    PORT = 9999
    NUM_MSGS = 5
    SIZE = 64

    msg = b'A' * SIZE

    start_handshake = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    end_handshake = time.perf_counter()

    handshake_ms = (end_handshake - start_handshake) * 1000
    print(f"[CLIENT] Connected! Handshake: {handshake_ms:.3f} ms")

    for i in range(NUM_MSGS):
        start = time.perf_counter()
        sock.sendall(msg)
        resp = sock.recv(SIZE)
        end = time.perf_counter()
        rtt = (end - start) * 1000
        print(f"[CLIENT] Msg {i+1}/{NUM_MSGS} | {SIZE}B | RTT: {rtt:.3f} ms")

    sock.close()
    print("[CLIENT] Done.")

if __name__ == '__main__':
    main()
