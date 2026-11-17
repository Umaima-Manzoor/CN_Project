import os
import subprocess
import time

SUDO_USER = os.environ.get('SUDO_USER', os.environ.get('USER', 'umaima'))
USER_HOME = f"/home/{SUDO_USER}"
PROJECT_DIR = f"{USER_HOME}/CN_Project"
RESULTS_FILE = f"{PROJECT_DIR}/experiments/results.csv"

MODES = ["plaintext", "tls", "e2e"]
SIZES = [64, 1024, 16384]
RTTS = [20, 100, 200]
REPEATS = [1, 2, 3]

# WHAT: Timeout increased to 1200 seconds (20 minutes)
# WHY: Prevents subprocess timeout on high-latency 16KB E2E runs traversing 4 network hops
def run_cmd(cmd, timeout=1200):
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip(), result.stderr.strip()

def get_completed_tests():
    completed = set()
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 4 and parts[0] in MODES:
                    try:
                        mode = parts[0]
                        size = int(parts[1])
                        rtt = int(parts[2])
                        rep = int(parts[3])
                        completed.add((mode, size, rtt, rep))
                    except ValueError:
                        pass
    return completed

def setup_topology():
    print("=== Setting up topology ===")
    run_cmd(f"bash {PROJECT_DIR}/topology/setup_topology.sh")

def set_delay(rtt_ms):
    one_way_delay = rtt_ms / 2.0
    run_cmd(f"bash {PROJECT_DIR}/topology/set_delay.sh {one_way_delay}ms")

def parse_handshake(output):
    tcp_hs, tls_hs, e2e_hs, total_hs = 0.0, 0.0, 0.0, 0.0
    for line in output.split("\n"):
        if line.startswith("HANDSHAKE:"):
            parts = line.split(":")
            for p in parts[1:]:
                if "=" in p:
                    k, v = p.split("=")
                    try:
                        val = float(v)
                        if k == "tcp": tcp_hs = val
                        elif k == "tls": tls_hs = val
                        elif k == "e2e": e2e_hs = val
                        elif k == "total": total_hs = val
                    except ValueError:
                        pass
    return tcp_hs, tls_hs, e2e_hs, total_hs

def parse_overhead(output):
    for line in output.split("\n"):
        if line.startswith("OVERHEAD:"):
            try:
                return int(line.split(":")[1])
            except ValueError:
                pass
    return 0

def parse_avg_rtt(output):
    for line in output.split("\n"):
        if line.startswith("AVG_RTT:"):
            try:
                return float(line.split(":")[1])
            except ValueError:
                pass
    return 0.0

def run_one_test(mode, size, rtt, rep):
    set_delay(rtt)
    time.sleep(1)
    
    server_cmd = f"ip netns exec relay python3 {PROJECT_DIR}/src/exp_server.py {mode}"
    server_proc = subprocess.Popen(server_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    
    try:
        if mode == "e2e":
            c2_cmd = f"ip netns exec client2 python3 {PROJECT_DIR}/src/exp_client.py {mode} {size} 1000 recipient"
            c2_proc = subprocess.Popen(c2_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(1.5)
            
            c1_cmd = f"ip netns exec client1 python3 {PROJECT_DIR}/src/exp_client.py {mode} {size} 1000"
            client_out, client_err = run_cmd(c1_cmd, timeout=1200)
            c2_proc.kill()
        else:
            client_cmd = f"ip netns exec client1 python3 {PROJECT_DIR}/src/exp_client.py {mode} {size} 1000"
            client_out, client_err = run_cmd(client_cmd, timeout=1200)
            
    finally:
        server_proc.kill()
        time.sleep(1)

    tcp_hs, tls_hs, e2e_hs, total_hs = parse_handshake(client_out)
    overhead = parse_overhead(client_out)
    avg_rtt = parse_avg_rtt(client_out)

    return f"{mode},{size},{rtt},{rep},{tcp_hs:.3f},{tls_hs:.3f},{e2e_hs:.3f},{total_hs:.3f},{overhead},{avg_rtt:.3f}", avg_rtt, total_hs

def main():
    setup_topology()
    
    completed = get_completed_tests()
    print(f"Found {len(completed)} already completed tests in results.csv.")

    if not os.path.exists(RESULTS_FILE):
        os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
        with open(RESULTS_FILE, "w") as f:
            f.write("mode,size,rtt,repeat,tcp_hs_ms,tls_hs_ms,e2e_hs_ms,total_hs_ms,e2e_overhead_bytes,avg_rtt_ms\n")

    total_tests = len(MODES) * len(SIZES) * len(RTTS) * len(REPEATS)
    count = 0

    print(f"=== Running remaining tests out of {total_tests} (1000 msgs each) ===")

    for mode in MODES:
        for size in SIZES:
            for rtt in RTTS:
                for rep in REPEATS:
                    count += 1
                    if (mode, size, rtt, rep) in completed:
                        print(f"[{count}/{total_tests}] {mode} | {size}B | {rtt}ms | run{rep} -> [SKIPPED - Already Completed]")
                        continue
                    
                    print(f"[{count}/{total_tests}] {mode} | {size}B | {rtt}ms | run{rep}", end="", flush=True)
                    csv_line, avg_rtt, total_hs = run_one_test(mode, size, rtt, rep)
                    
                    with open(RESULTS_FILE, "a") as f:
                        f.write(csv_line + "\n")
                    
                    print(f" -> HS: {total_hs:.1f}ms | RTT: {avg_rtt:.3f}ms")

    print("\nDONE! All 81 experiments complete.")
    print(f"Results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    main()
