#!/bin/bash
set -e

RTT_MS=${1:-20}
ONE_WAY=$((RTT_MS / 2))

echo "=== Setting network delay: ${RTT_MS}ms RTT (${ONE_WAY}ms each way) ==="

# Remove existing delay INSIDE the namespaces (this was the bug!)
ip netns exec r1 tc qdisc del dev veth-r1b root 2>/dev/null || true
ip netns exec r2 tc qdisc del dev veth-r2b root 2>/dev/null || true

# Add new delay
if [ "$ONE_WAY" -gt 0 ]; then
    ip netns exec r1 tc qdisc add dev veth-r1b root netem delay ${ONE_WAY}ms
    ip netns exec r2 tc qdisc add dev veth-r2b root netem delay ${ONE_WAY}ms
fi

echo "=== Delay applied! ==="
