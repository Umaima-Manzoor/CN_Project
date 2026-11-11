#!/bin/bash
set -e

echo "=== Cleaning up any old topology ==="
for ns in client1 client2 r1 r2 relay observer; do
    ip netns del "$ns" 2>/dev/null || true
done

echo "=== Creating 6 namespaces ==="
for ns in client1 client2 r1 r2 relay observer; do
    ip netns add "$ns"
    ip netns exec "$ns" ip link set lo up
done

echo "=== Creating 5 veth pairs ==="
ip link add veth-c1 type veth peer name veth-r1a1
ip link add veth-c2 type veth peer name veth-r1a2
ip link add veth-r1b type veth peer name veth-r2b
ip link add veth-relay type veth peer name veth-r2r
ip link add veth-obs type veth peer name veth-r2c

echo "=== Moving interfaces into namespaces ==="
ip link set veth-c1 netns client1
ip link set veth-c2 netns client2
ip link set veth-r1a1 netns r1
ip link set veth-r1a2 netns r1
ip link set veth-r1b netns r1
ip link set veth-r2b netns r2
ip link set veth-relay netns relay
ip link set veth-r2r netns r2
ip link set veth-obs netns observer
ip link set veth-r2c netns r2

echo "=== Building bridge in r1 for client subnet ==="
ip netns exec r1 ip link add br0 type bridge
ip netns exec r1 ip link set veth-r1a1 master br0
ip netns exec r1 ip link set veth-r1a2 master br0
ip netns exec r1 ip link set br0 up
ip netns exec r1 ip link set veth-r1a1 up
ip netns exec r1 ip link set veth-r1a2 up
ip netns exec r1 ip addr add 10.0.1.1/24 dev br0

echo "=== Assigning IP addresses ==="
ip netns exec client1 ip addr add 10.0.1.2/24 dev veth-c1
ip netns exec client2 ip addr add 10.0.1.3/24 dev veth-c2
ip netns exec r1 ip addr add 10.0.2.1/30 dev veth-r1b
ip netns exec r2 ip addr add 10.0.2.2/30 dev veth-r2b
ip netns exec r2 ip addr add 10.0.3.1/24 dev veth-r2r
ip netns exec relay ip addr add 10.0.3.2/24 dev veth-relay
ip netns exec r2 ip addr add 10.0.4.1/24 dev veth-r2c
ip netns exec observer ip addr add 10.0.4.2/24 dev veth-obs

echo "=== Bringing all interfaces up ==="
ip netns exec client1 ip link set veth-c1 up
ip netns exec client2 ip link set veth-c2 up
ip netns exec r1 ip link set veth-r1b up
ip netns exec r2 ip link set veth-r2b up
ip netns exec r2 ip link set veth-r2r up
ip netns exec r2 ip link set veth-r2c up
ip netns exec relay ip link set veth-relay up
ip netns exec observer ip link set veth-obs up

echo "=== Enabling IP forwarding on routers ==="
ip netns exec r1 sysctl -w net.ipv4.ip_forward=1
ip netns exec r2 sysctl -w net.ipv4.ip_forward=1

echo "=== Configuring routes ==="
ip netns exec client1 ip route add default via 10.0.1.1
ip netns exec client2 ip route add default via 10.0.1.1
ip netns exec r1 ip route add 10.0.3.0/24 via 10.0.2.2
ip netns exec r1 ip route add 10.0.4.0/24 via 10.0.2.2
ip netns exec r2 ip route add 10.0.1.0/24 via 10.0.2.1
ip netns exec relay ip route add default via 10.0.3.1
ip netns exec observer ip route add default via 10.0.4.1

echo ""
echo "========================================="
echo "  TOPOLOGY SETUP COMPLETE!"
echo "========================================="
echo "  Clients:  10.0.1.0/24  (client1=.2 client2=.3 r1=.1)"
echo "  Backbone: 10.0.2.0/30  (r1=.1 r2=.2)"
echo "  Relay:    10.0.3.0/24  (relay=.2 r2=.1)"
echo "  Observer: 10.0.4.0/24  (observer=.2 r2=.1)"
echo "========================================="

