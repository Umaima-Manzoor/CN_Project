import socket

def main():
    HOST = '0.0.0.0'
    PORT = 9999

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"[RELAY] Listening on {HOST}:{PORT} ...")

    conn, addr = server.accept()
    print(f"[RELAY] Client connected from {addr}")

    while True:
        data = conn.recv(65536)
        if not data:
            break
        conn.sendall(data)

    print("[RELAY] Client disconnected.")
    conn.close()
    server.close()

if __name__ == '__main__':
    main()
