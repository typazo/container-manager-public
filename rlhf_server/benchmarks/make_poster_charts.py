#!/usr/bin/env python3
"""
Generate midpoint poster charts from Tyler's ARM server benchmark runs.
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

BENCH_DIR = Path(__file__).resolve().parent
OUT_DIR = Path("/home/ubuntu/.gemini/antigravity/brain/5d9de5a1-e51b-4451-9bf9-9df3e53efe2f")

# Load fork_performance.jsonl
records = []
with open(BENCH_DIR / "fork_performance.jsonl", "r") as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelweight": "bold",
    "figure.dpi": 200,
})

# -------------------------------------------------------------------------
# Chart 1: Container Creation (Fork) vs. Deletion Throughput & Total Time
# -------------------------------------------------------------------------
total_containers = [r["total_containers"] for r in records]
total_forks = [r["total_forks"] for r in records]
fork_rates = [r["start_rate_containers_per_sec"] for r in records]
stop_rates = [r["stop_rate_containers_per_sec"] for r in records]
fork_durations = [r["start_duration"] for r in records]
stop_durations = [r["stop_duration"] for r in records]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.4))

x_labels_c1 = [f"{c} total\n({f} forks)" for c, f in zip(total_containers, total_forks)]

# Left panel: Total Phase Duration vs Total Containers (Linear scaling)
ax1.plot(total_containers, fork_durations, marker="o", linewidth=2.2, color="#1f77b4", label="Fork Phase Total Time (s)")
ax1.plot(total_containers, stop_durations, marker="s", linewidth=2.2, color="#d62728", label="Stop Phase Total Time (s)")
for x, yf, ys in zip(total_containers, fork_durations, stop_durations):
    ax1.annotate(f"{yf:.1f}s", (x, yf), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9, color="#1f77b4")
    ax1.annotate(f"{ys:.1f}s", (x, ys), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=9, color="#d62728")

ax1.set_title("A. Total Batch Fork & Stop Time (Seconds)")
ax1.set_xticks(total_containers)
ax1.set_xticklabels(x_labels_c1, fontsize=9.5)
ax1.set_xlabel("Total Active Containers (4 Base Tasks + N Forks)")
ax1.set_ylabel("Total Wall-Clock Time (seconds)")
ax1.set_ylim(0, max(fork_durations) * 1.18)
ax1.grid(True, linestyle="--", alpha=0.4)
ax1.legend(loc="upper left")

# Right panel: Throughput (containers/sec)
ax2.plot(total_containers, stop_rates, marker="s", linewidth=2.2, color="#d62728", label="Stop Speed (containers/sec)")
ax2.plot(total_containers, fork_rates, marker="o", linewidth=2.2, color="#1f77b4", label="Fork Speed (containers/sec)")
for x, rf, rs in zip(total_containers, fork_rates, stop_rates):
    ax2.annotate(f"{rf:.2f}/s", (x, rf), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9, color="#1f77b4")
    ax2.annotate(f"{rs:.2f}/s", (x, rs), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=9, color="#d62728")

ax2.set_title("B. Server Processing Speed (Containers / Sec)")
ax2.set_xticks(total_containers)
ax2.set_xticklabels(x_labels_c1, fontsize=9.5)
ax2.set_xlabel("Total Active Containers (4 Base Tasks + N Forks)")
ax2.set_ylabel("Speed (containers / sec)")
ax2.set_ylim(0, max(stop_rates) * 1.25)
ax2.grid(True, linestyle="--", alpha=0.4)
ax2.legend(loc="center right")

plt.tight_layout(w_pad=2.5)
for dest in [BENCH_DIR / "chart1_scaling_and_throughput.png", BENCH_DIR / "chart1_scaling_and_throughput.pdf", OUT_DIR / "chart1_scaling_and_throughput.png"]:
    plt.savefig(dest, bbox_inches="tight")
plt.close()

# -------------------------------------------------------------------------
# Chart 2: Native ARM64 Tasks vs. Emulated x86_64 Task Fork Latency
# -------------------------------------------------------------------------
# Extracted directly from our test.py per-task runs for N=2, 4, 8, 16 forks per task
forks_per_task = [2, 4, 8, 16]
native_arm_avg_s = [
    (2.64 + 2.51 + 3.01) / 3,   # N=2: 2.72s
    (4.60 + 4.41 + 4.80) / 3,   # N=4: 4.60s
    (7.38 + 7.21 + 7.55) / 3,   # N=8: 7.38s
    (13.70 + 14.96 + 13.77) / 3 # N=16: 14.14s
]
emulated_x86_avg_s = [
    4.90,   # N=2
    8.44,   # N=4
    15.01,  # N=8
    30.96,  # N=16
]
overall_avg_s = [3.26, 5.56, 9.29, 18.35]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.4))

x = np.arange(len(forks_per_task))
width = 0.35

rects1 = ax1.bar(x - width/2, native_arm_avg_s, width, label="Native ARM64 Tasks (3 tasks avg)", color="#2ca02c")
rects2 = ax1.bar(x + width/2, emulated_x86_avg_s, width, label="x86_64 Emulated Task (accelerate-maximal-square)", color="#ff7f0e")

for rect in rects1:
    h = rect.get_height()
    ax1.annotate(f"{h:.1f}s", (rect.get_x() + rect.get_width()/2, h), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=9)
for rect in rects2:
    h = rect.get_height()
    ax1.annotate(f"{h:.1f}s", (rect.get_x() + rect.get_width()/2, h), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=9)

ax1.set_title("A. Fork Latency: Native ARM vs. x86 Emulation")
ax1.set_xticks(x)
ax1.set_xticklabels([f"{n} forks/task\n({n*4} total)" for n in forks_per_task])
ax1.set_ylabel("Avg Time per Fork Request (seconds)")
ax1.set_ylim(0, 36)
ax1.grid(True, axis="y", linestyle="--", alpha=0.4)
ax1.legend(loc="upper left", fontsize=9.5)

# Right panel: End-to-End Prototype Rollout Comparison (hello-world task)
scenarios = ["Uncached Rollout\n(Cold Boot + Exec)", "Branching Rollout\n(Prefix Hit + Fork)", "Cached Rollout\n(100% Cache Hit)"]
times = [10.97, 4.03, 0.22]
colors = ["#7f7f7f", "#1f77b4", "#2ca02c"]

bars = ax2.bar(scenarios, times, color=colors, width=0.52)
for bar, t in zip(bars, times):
    speedup = f" ({10.97/t:.1f}x)" if t < 10.97 else ""
    ax2.annotate(f"{t:.2f}s{speedup}", (bar.get_x() + bar.get_width()/2, t), textcoords="offset points", xytext=(0, 4), ha="center", fontweight="bold", fontsize=10)

ax2.set_title("B. E2E Rollout Time with TVCache (hello-world)")
ax2.set_ylabel("Rollout Wall-Clock Time (seconds)")
ax2.set_ylim(0, 13.0)
ax2.grid(True, axis="y", linestyle="--", alpha=0.4)

plt.tight_layout(w_pad=2.5)
for dest in [BENCH_DIR / "chart2_arm_vs_x86_and_e2e.png", BENCH_DIR / "chart2_arm_vs_x86_and_e2e.pdf", OUT_DIR / "chart2_arm_vs_x86_and_e2e.png"]:
    plt.savefig(dest, bbox_inches="tight")
plt.close()

print("Saved charts successfully!")
