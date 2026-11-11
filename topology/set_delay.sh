#!/bin/bash
set -e

RTT_MS=${1:-20}
ONE_WAY=$((RTT_MS / 2))

echo "=== Setting network delay: ${RTT_MS}ms RTT (${ONE_WAY}ms each way) ==="

# Remove any existing delay first
tc qdisc del dev veth-r1b root 2>/dev/null || true
tc qdisc del dev veth-r2b root 2>/dev/null || true

# Add delay on the backbone link (r1 <-> r2)
ip netns exec r1 tc qdisc add dev veth-r1b root netem delay ${ONE_WAY}ms
ip netns exec r2 tc qdisc add dev veth-r2b root netem delay ${ONE_WAY}ms

echo "=== Delay applied! ==="
echo "  r1 -> r2: ${ONE_WAY}ms"
echo "  r2 -> r1: ${ONE_WAY}ms"
echo "  Total RTT: ~${RTT_MS}ms"
