#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Stopping Phase 1 Backend (tvcache-rust + container-manager) ==="

# Stop tvcache-rust
if [ -f "$SCRIPT_DIR/tvcache-rust.pid" ]; then
    kill "$(cat "$SCRIPT_DIR/tvcache-rust.pid")" 2>/dev/null || true
    rm -f "$SCRIPT_DIR/tvcache-rust.pid"
fi
pkill -f "tvcache-rust/target/release/tvcache" 2>/dev/null || true
echo "[tvcache-rust] Stopped."

# Stop container-manager
if [ -f "$SCRIPT_DIR/container-manager.pid" ]; then
    kill "$(cat "$SCRIPT_DIR/container-manager.pid")" 2>/dev/null || true
    rm -f "$SCRIPT_DIR/container-manager.pid"
fi
pkill -f "uv run server.py" 2>/dev/null || true
pkill -f "rlhf_server.*server.py" 2>/dev/null || true
echo "[container-manager] Stopped."

# Clean up any test-network-* bridge networks created by container-manager
for net in $(docker network ls --filter "name=test-network-" --format "{{.Name}}" 2>/dev/null); do
    docker network rm "$net" >/dev/null 2>&1 || true
done
echo "[docker] Cleaned up test bridge networks."

