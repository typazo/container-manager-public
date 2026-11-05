#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="/home/ubuntu/.local/bin:/home/ubuntu/.cargo/bin:$PATH"

echo "=== Starting Phase 1 Backend (tvcache-rust + container-manager) ==="

# 1. Start tvcache-rust on 0.0.0.0:7878 if not already running
if ss -tln | grep -q ':7878 '; then
    echo "[tvcache-rust] Already running on port 7878."
else
    echo "[tvcache-rust] Starting on port 7878..."
    nohup "$SCRIPT_DIR/tvcache-rust/target/release/tvcache" \
        > "$SCRIPT_DIR/tvcache-rust.log" 2>&1 &
    echo $! > "$SCRIPT_DIR/tvcache-rust.pid"
    sleep 1
    echo "[tvcache-rust] Started (PID $(cat "$SCRIPT_DIR/tvcache-rust.pid")). Logs: $SCRIPT_DIR/tvcache-rust.log"
fi

# 2. Start container-manager RLHF server on 0.0.0.0:9901 if not already running
if ss -tln | grep -q ':9901 '; then
    echo "[container-manager] Already running on port 9901."
else
    echo "[container-manager] Starting RLHF server on port 9901..."
    cd "$SCRIPT_DIR/container-manager-public/rlhf_server"
    nohup ./run_server.sh > "$SCRIPT_DIR/container-manager.log" 2>&1 &
    echo $! > "$SCRIPT_DIR/container-manager.pid"
    sleep 2
    echo "[container-manager] Started (PID $(cat "$SCRIPT_DIR/container-manager.pid")). Logs: $SCRIPT_DIR/container-manager.log"
fi

echo "=== Backend Ready ==="
echo "  - tvcache-rust:      127.0.0.1:7878"
echo "  - container-manager: http://127.0.0.1:9901"
echo "  - Run E2E Demo:      $SCRIPT_DIR/container-manager-public/.venv/bin/python $SCRIPT_DIR/test_phase1_e2e.py"

