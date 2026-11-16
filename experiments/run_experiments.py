import subprocess
import time
import csv
import os

MODES = ['plaintext', 'tls', 'e2e']
SIZES = [64, 1024, 16384]
RTTS = [20, 100, 200]
REPEATS = 3
MSG_COUNT = 1000

TOPO_DIR = os.path.expanduser('~/CN_Project/topology')
SRC_DIR = os.path.expanduser('~/CN_Project/src')
OUT_FILE = os.path.expanduser('~/CN_Project/experiments/results.csv')

def run_cmd(cmd, timeout=120):
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip(), result.stderr.strip()

def set_delay(rtt_ms):
    run_cmd(f'sudo {TOPO_DIR}/set_delay.sh {rtt_ms}')

def reset_delay():
    run_cmd(f'sudo {TOPO_DIR}/set_delay.sh 0')

def parse_handshake(line):
    parts = line.split(':')
    result = {}
    for part in parts[1:]:
        key, val = part.split('=')
        result[key] = float(val)
    return result

def run_one_test(mode, size, rtt, repeat):
    set_delay(rtt)
    time.sleep(0.5)

    server_cmd = f'sudo ip netns exec relay python3 {SRC_DIR}/exp_server.py {mode}'
    server_proc = subprocess.Popen(
        server_cmd, shell=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True
    )

    ready = False
    for _ in range(50):
        line = server_proc.stdout.readline()
        if 'READY' in line:
            ready = True
            break
        time.sleep(0.1)

    if not ready:
        server_proc.kill()
        return None

    client_cmd = f'sudo ip netns exec client1 python3 {SRC_DIR}/exp_client.py {mode} {size} {MSG_COUNT}'
    client_out, client_err = run_cmd(client_cmd, timeout=300)

    server_proc.terminate()
    server_proc.wait()

    result = {
        'mode': mode, 'size': size, 'rtt': rtt, 'repeat': repeat,
        'tcp_hs': 0.0, 'tls_hs': 0.0, 'e2e_hs': 0.0, 'total_hs': 0.0,
        'overhead': 0, 'avg_rtt': 0.0
    }

    for line in client_out.split('\n'):
        if line.startswith('HANDSHAKE:'):
            hs = parse_handshake(line)
            result['tcp_hs'] = hs.get('tcp', 0.0)
            result['tls_hs'] = hs.get('tls', 0.0)
            result['e2e_hs'] = hs.get('e2e', 0.0)
            result['total_hs'] = hs.get('total', 0.0)
        elif line.startswith('OVERHEAD:'):
            result['overhead'] = int(line.split(':')[1])
        elif line.startswith('AVG_RTT:'):
            result['avg_rtt'] = float(line.split(':')[1])

    return result

def main():
    print("=== Setting up topology ===")
    run_cmd(f'sudo {TOPO_DIR}/setup_topology.sh')
    time.sleep(1)

    print(f"=== Starting 81 experiments ({MSG_COUNT} msgs each) ===")
    total = len(MODES) * len(SIZES) * len(RTTS) * REPEATS
    done = 0

    with open(OUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'mode', 'size', 'rtt', 'repeat',
            'tcp_hs_ms', 'tls_hs_ms', 'e2e_hs_ms', 'total_hs_ms',
            'e2e_overhead_bytes', 'avg_rtt_ms'
        ])

        for mode in MODES:
            for size in SIZES:
                for rtt in RTTS:
                    for rep in range(1, REPEATS + 1):
                        done += 1
                        print(f"[{done}/{total}] {mode} | {size}B | {rtt}ms | run{rep}")
                        result = run_one_test(mode, size, rtt, rep)
                        if result:
                            writer.writerow([
                                result['mode'], result['size'], result['rtt'],
                                result['repeat'], result['tcp_hs'], result['tls_hs'],
                                result['e2e_hs'], result['total_hs'],
                                result['overhead'], result['avg_rtt']
                            ])
                            f.flush()
                            print(f"  -> HS: {result['total_hs']:.1f}ms | RTT: {result['avg_rtt']:.3f}ms")
                        else:
                            print(f"  -> FAILED")

    reset_delay()
    print(f"\n=== DONE! Results saved to {OUT_FILE} ===")

if __name__ == '__main__':
    main()
