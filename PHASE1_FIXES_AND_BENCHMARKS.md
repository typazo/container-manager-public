# Phase 1 Backend Fixes, Benchmarks & Poster Study Guide (Team 34)

This fork (`typazo/container-manager-public`) contains the **Phase 1 CPU backend fixes, multi-container scaling benchmarks, end-to-end verification harness, and poster figures** for **CS 5470 Team 34** (*Accelerating Agentic RL Post-Training on Cloud TPUs with TVCache*).

---

## 1. Summary of Engineering Fixes Made in `container-manager`

### Fix 1: Silent `/fork` Deadlock & Docker CLI Version Mismatch (`rlhf_server/fork/fork_pipeline.py`)
- **What broke:**
  1. In [`rlhf_server/fork/fork_pipeline.py`](rlhf_server/fork/fork_pipeline.py), `call_docker_commit()` ran `docker commit --no-pause <container> <new_image>`. The `--no-pause` flag was only added in **Docker v29+** (replacing `--pause=false`). On **Docker v27/v28** (standard on Ubuntu 20.04/22.04 hosts), `docker commit --no-pause` immediately fails with `unknown flag: --no-pause`.
  2. Worse, when `call_docker_commit()` returned an error in the background commit worker thread (`commit_container()`), the function exited early (`return f"Failed to commit..."`) **without** setting `fork_request.error` or `fork_request.fork_complete = True`.
  3. Meanwhile, the HTTP request thread handling `/fork` sits in `fork_priority()` inside `while not fork_req.fork_complete:`, causing any failed commit to **hang the `/fork` HTTP endpoint forever**.
- **How we fixed it:**
  - Replaced `'--no-pause'` with `'--pause=false'` in `call_docker_commit()` (which works across Docker v27, v28, and v29).
  - Updated `commit_container()` to set `fork_request.error`, `fork_request.commit_complete = True`, and `fork_request.fork_complete = True` on commit failure.
  - Updated `fork_priority()` to check `while not fork_req.fork_complete and not fork_req.error:` and immediately raise `RuntimeError(fork_req.error)` if the background commit or container startup fails.

### Fix 2: Docker Bridge Subnet Pool Exhaustion (`rlhf_server/server.py` & `rlhf_server/run_server.sh`)
- **What broke:**
  - Some multi-container `terminal-bench` tasks need a private virtual network ("bridge network") so containers in the same rollout can talk to each other without talking to other rollouts.
  - Because creating a Docker network takes ~0.5s, [`rlhf_server/server.py`](rlhf_server/server.py) pre-creates a pool of bridge networks (`test-network-0`, `test-network-1`, ...) when the server starts.
  - However, `server.py` hardcoded `BridgeNetworks(100)`. A standard out-of-the-box Docker daemon only reserves **31 subnet address blocks** (`172.17.0.0/16`–`192.168.x.0/20`). Unless `/etc/docker/daemon.json` is overwritten as `root` and the global Docker daemon is restarted, creating network #29 crashes `server.py` on startup with `Pool overlaps with other one on this address space`.
- **How we fixed it:**
  - Updated [`rlhf_server/server.py`](rlhf_server/server.py) and [`rlhf_server/run_server.sh`](rlhf_server/run_server.sh) to read `NUM_BRIDGE_NETWORKS` from an environment variable (defaulting to `10`), allowing `container-manager` to start cleanly on any standard or shared Docker host without modifying global `/etc/docker/daemon.json`.

### Fix 3: `x86_64`-Only Task Images on an `aarch64` (ARM64) CPU Host
- **What broke:**
  - Our Phase 1 server is an 8-OCPU, 24 GB RAM Oracle Cloud `aarch64` (ARM64) Ubuntu VM (used so we could save our \$1,000 Google Cloud TPU budget for Phase 2/3).
  - While base `terminal-bench` images (`ubuntu-24-04`, `python-3-13`) publish native `linux/arm64` manifests, tasks like `accelerate-maximal-square` pull `x86_64`-only base images (`taichidev/taichi:v0.7.26`), which fail to start on ARM64 with `exec format error`.
- **How we fixed it:**
  - Installed `qemu-user-static` and `binfmt-support` on the host so Docker transparently runs `x86_64` containers via QEMU user-mode binary translation.
  - Benchmarked the exact QEMU translation overhead (`2.2x` slower fork times on `x86_64`-emulated images vs. native ARM64 images), motivating our Phase 3 plan to run `container-manager` on an `x86_64` GCP CPU VM alongside the Cloud TPU VM.

---

## 2. Benchmark Results & How to Explain Them at the Poster Session

All benchmark data is saved in [`rlhf_server/benchmarks/fork_performance.jsonl`](rlhf_server/benchmarks/fork_performance.jsonl) (with the original repo's baseline data backed up in [`rlhf_server/benchmarks/fork_performance_bhaskar_backup.jsonl`](rlhf_server/benchmarks/fork_performance_bhaskar_backup.jsonl)).

### A. End-to-End Rollout Speedup (`scripts/test_phase1_e2e.py` on `hello-world`)
We ran 3 sequential agent rollouts against live `tvcache-rust` (`:7878`) and `container-manager` (`:9901`, `ENABLE_CACHING=1`):
1. **Rollout 1 — Cold Start (`10.97s`):**
   - Cache is empty (`0%` hit rate). Starts a fresh Docker container (`/start`), executes all 3 bash commands (`ls -la`, `echo 'Hello, world!' > hello.txt`, `cat hello.txt`), snapshots the container, and runs `/test` (`passed: True`).
2. **Rollout 2 — 100% Cache Hit (`0.22s` — `50.2x` speedup):**
   - Executes the exact same 3 commands + test. `TvcacheToolExecutor` finds the full path in `tvcache-rust` (`<2 ms` TCP lookup) and returns the cached terminal outputs and `"True"` test result **without booting or touching any Docker container** (`0/3` executions).
3. **Rollout 3 — Branching Rollout / Partial Prefix Hit (`4.03s` — `2.7x` speedup):**
   - Runs the same Step 1 (`ls -la`) -> **Cache Hit** (`0` container executions), then diverges on Step 2 (`uname -a && pwd`).
   - On Step 2's cache miss, `TvcacheToolExecutor` restores the saved snapshot from Step 1 via `/fork` and executes *only* the new Step 2 command + `/test`.

### B. Multi-Container Fork & Teardown Scaling (`rlhf_server/test.py`)
We tested 4 `tasks_easy` tasks simultaneously (`aimo-airline-departures`, `amuse-install`, `analyze-access-logs`, `accelerate-maximal-square`) with $N = 2, 4, 8, 16$ forks per task (`8, 16, 32, 64` concurrent forks, or **`12, 20, 36, 68` total active containers** including the 4 base containers):

| Forks / Task ($N$) | Total Forks | Total Active Containers | Total Fork Batch Time (s) | Fork Throughput (cont/s) | Total Stop Batch Time (s) | Stop Throughput (cont/s) | Native ARM64 Avg Fork Latency (s) | `x86_64` Emulated Avg Fork Latency (s) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2** | 8 | **12** | `4.96s` | `1.61 /s` | `2.54s` | `4.72 /s` | `2.72s` | `4.90s` |
| **4** | 16 | **20** | `8.29s` | `1.93 /s` | `3.33s` | `6.00 /s` | `4.90s` | `8.29s` |
| **8** | 32 | **36** | `16.92s` | `1.89 /s` | `5.97s` | `6.03 /s` | `7.43s` | `15.02s` |
| **16** | 64 | **68** | `33.54s` | `1.91 /s` | `12.69s` | `5.36 /s` | `14.12s` | `31.01s` |

- **Why Fork & Stop Batch Times Scale Linearly:** Server fork throughput holds steady at **`~1.8–1.9 containers/sec`** on our 8-OCPU host. Because all $4 \times N$ fork requests arrive in a simultaneous burst, individual requests wait in the commit/startup worker queue (`2.7s` average wait at 8 forks $\rightarrow$ `14.1s` at 64 forks for native ARM tasks).
- **Why Stop Throughput (`~5.4–6.0 containers/sec`) is ~3× Faster than Fork Throughput:** Stopping containers is parallelized across 20 worker threads (`MAX_PARALLELISM=20`) without needing to commit a filesystem layer. At small batch sizes (`12` containers), fixed teardown overhead gives `4.72/s`; at `20–68` containers, the worker pool stays saturated at `5.4–6.0/s`. Because teardown is ~3× faster than creation, containers will not accumulate unboundedly as long as idle/completed containers are stopped between steps.
- **Native ARM64 vs. `x86_64` QEMU Emulation Overhead:** The 3 native ARM64 tasks fork in `14.1s` at 64 concurrent forks, whereas `accelerate-maximal-square` (`x86_64`-only `taichi` image under QEMU) takes `31.0s` (**2.2× slower**). Moving `container-manager` to a native `x86_64` GCP VM in Phase 3 removes this emulation penalty.

### C. `tvcache-rust` Stress Test (32 Concurrent Rollout Workers)
- Running `tvcache-rust/load_test.py` with **32 concurrent async workers** (matching Tunix's default `max_concurrency=32`, i.e., 4 tasks × 8 rollouts) sustains **3,661 prefix lookups/sec** with **`1.58 ms` median (`p50`) latency** and **`3.64 ms` `p95` latency**, confirming the Rust cache server is never a bottleneck.

---

## 3. Repository File Map (What Was Added / Modified)

- [`rlhf_server/fork/fork_pipeline.py`](rlhf_server/fork/fork_pipeline.py) — Fixed `docker commit --pause=false` and added error propagation to prevent `/fork` infinite hangs.
- [`rlhf_server/server.py`](rlhf_server/server.py) & [`rlhf_server/run_server.sh`](rlhf_server/run_server.sh) — Added configurable `NUM_BRIDGE_NETWORKS` environment variable.
- [`rlhf_server/benchmarks/fork_performance.jsonl`](rlhf_server/benchmarks/fork_performance.jsonl) — Scaling benchmark measurements (`N = 2, 4, 8, 16` forks/task across 4 tasks).
- [`rlhf_server/benchmarks/make_poster_charts.py`](rlhf_server/benchmarks/make_poster_charts.py) — Generates [`chart1_scaling_and_throughput.png`](rlhf_server/benchmarks/chart1_scaling_and_throughput.png) and [`chart2_arm_vs_x86_and_e2e.png`](rlhf_server/benchmarks/chart2_arm_vs_x86_and_e2e.png).
- [`rlhf_server/benchmarks/make_arch_diagram.py`](rlhf_server/benchmarks/make_arch_diagram.py) — Generates [`chart3_architecture_diagram.png`](rlhf_server/benchmarks/chart3_architecture_diagram.png).
- [`scripts/test_phase1_e2e.py`](scripts/test_phase1_e2e.py) — Standalone end-to-end verification script testing cold start, 100% cache hit, and branching fork rollouts on `hello-world`.
- [`scripts/start_backend.sh`](scripts/start_backend.sh) & [`scripts/stop_backend.sh`](scripts/stop_backend.sh) — Helper scripts to start/stop `tvcache-rust` (`:7878`) and `container-manager` (`:9901`) and clean up temporary `test-network-*` Docker networks.
