#!/bin/bash
set -e

SUDO_USER=${SUDO_USER:-$USER}
PROJECT_DIR="/home/${SUDO_USER}/CN_Project"
CAPTURES_DIR="${PROJECT_DIR}/captures"

mkdir -p "$CAPTURES_DIR"

echo "=== Initializing Network Topology for Captures ==="
bash "${PROJECT_DIR}/topology/setup_topology.sh"
bash "${PROJECT_DIR}/topology/set_delay.sh" 20ms

# 1. PLAIN TEXT CAPTURE
echo "=== Capturing Plaintext Traffic (Port 9999) ==="
ip netns exec relay python3 "${PROJECT_DIR}/src/exp_server.py" plaintext &
SERVER_PID=$!
sleep 2

ip netns exec relay tshark -i veth-relay -f "tcp port 9999" -w "${CAPTURES_DIR}/plaintext_capture.pcap" &
TSHARK_PID=$!
sleep 2

ip netns exec client1 python3 "${PROJECT_DIR}/src/exp_client.py" plaintext 64 5
sleep 1

kill $TSHARK_PID 2>/dev/null || true
kill $SERVER_PID 2>/dev/null || true
sleep 1

# 2. TLS 1.3 CAPTURE
echo "=== Capturing TLS 1.3 Traffic (Port 9998) ==="
ip netns exec relay python3 "${PROJECT_DIR}/src/exp_server.py" tls &
SERVER_PID=$!
sleep 2

ip netns exec relay tshark -i veth-relay -f "tcp port 9998" -w "${CAPTURES_DIR}/tls_capture.pcap" &
TSHARK_PID=$!
sleep 2

ip netns exec client1 python3 "${PROJECT_DIR}/src/exp_client.py" tls 64 5
sleep 1

kill $TSHARK_PID 2>/dev/null || true
kill $SERVER_PID 2>/dev/null || true
sleep 1

# 3. E2E CAPTURE
echo "=== Capturing E2E Traffic (Port 9997) ==="
ip netns exec relay python3 "${PROJECT_DIR}/src/exp_server.py" e2e &
SERVER_PID=$!
sleep 2

ip netns exec client2 python3 "${PROJECT_DIR}/src/exp_client.py" e2e 64 5 recipient &
sleep 1.5

ip netns exec relay tshark -i veth-relay -f "tcp port 9997" -w "${CAPTURES_DIR}/e2e_capture.pcap" &
TSHARK_PID=$!
sleep 2

ip netns exec client1 python3 "${PROJECT_DIR}/src/exp_client.py" e2e 64 5
sleep 1

kill $TSHARK_PID 2>/dev/null || true
kill $SERVER_PID 2>/dev/null || true
sleep 1

echo "=== ALL CAPTURES GENERATED SUCCESSFULLY! ==="
echo "Files saved in: ${CAPTURES_DIR}"
ls -lh "$CAPTURES_DIR"
