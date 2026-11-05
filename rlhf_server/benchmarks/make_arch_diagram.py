import matplotlib.pyplot as plt
import matplotlib.patches as patches

def make_arch_diagram():
    fig, ax = plt.subplots(figsize=(9.2, 11.4), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 15.3)
    ax.axis('off')
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')

    def draw_box(x, y, w, h, facecolor, edgecolor, lw=2.0, radius=0.22, alpha=1.0, linestyle='-'):
        box = patches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle=f"round,pad=0.04,rounding_size={radius}",
            facecolor=facecolor, edgecolor=edgecolor, linewidth=lw, alpha=alpha, linestyle=linestyle
        )
        ax.add_patch(box)
        return box

    def draw_badge(x, y, text, bg_color, text_color, border_color=None, w=2.55, h=0.34, fontsize=7.6):
        ec = border_color if border_color else bg_color
        badge = patches.FancyBboxPatch(
            (x - w/2, y - h/2), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.14",
            facecolor=bg_color, edgecolor=ec, linewidth=1.2
        )
        ax.add_patch(badge)
        ax.text(x, y, text, ha='center', va='center', fontsize=fontsize, fontweight='bold', color=text_color)

    # ==================== TOP LEGEND BAR ====================
    draw_box(0.4, 14.32, 9.2, 0.72, facecolor='#F8FAFC', edgecolor='#CBD5E1', lw=1.5, radius=0.18)
    ax.text(0.65, 14.68, "Midpoint Status:", ha='left', va='center', fontsize=8.9, fontweight='bold', color='#1E293B')
    draw_badge(3.55, 14.68, "✓ Working & Tested Locally", '#DCFCE7', '#166534', '#22C55E', w=2.25, h=0.36, fontsize=7.7)
    draw_badge(6.15, 14.68, "◐ Merged in Tunix (Not on TPU Yet)", '#FEF3C7', '#92400E', '#F59E0B', w=2.62, h=0.36, fontsize=7.7)
    draw_badge(8.58, 14.68, "○ To Set Up (Phase 2/3)", '#F1F5F9', '#475569', '#94A3B8', w=1.85, h=0.36, fontsize=7.7)

    # ==================== TIER 1: CLOUD TPU VM ====================
    draw_box(0.4, 10.12, 9.2, 3.95, facecolor='#EBF3FA', edgecolor='#2B5B84', lw=2.2, radius=0.28)
    ax.text(3.55, 13.75, "Cloud TPU VM  —  Tunix Fork (tunix/rl/agentic)",
            ha='center', va='center', fontsize=11.3, fontweight='bold', color='#1B3B58')
    draw_badge(7.95, 13.75, "◐ Env Merged; GCloud TPU Run Next", '#FEF3C7', '#92400E', '#F59E0B', w=2.85, h=0.34, fontsize=7.4)

    # Inner Box 1A: TrajectoryCollectEngine & ToolAgent
    draw_box(0.75, 12.15, 8.5, 1.22, facecolor='#FFFFFF', edgecolor='#D97706', lw=1.6, radius=0.18)
    ax.text(3.35, 13.04, "TrajectoryCollectEngine.collect()  +  ToolAgent",
            ha='center', va='center', fontsize=9.6, fontweight='bold', color='#1B3B58')
    draw_badge(7.68, 13.04, "◐ Scripted E2E Done; Live TPU Next", '#FEF3C7', '#92400E', '#F59E0B', w=2.75, h=0.30, fontsize=7.1)
    ax.text(5.0, 12.50, "Emits <tool_call>{\"name\": \"terminal\", \"arguments\": {\"command\": ...}}</tool_call> across 32 rollouts",
            ha='center', va='center', fontsize=8.2, color='#334E68')

    # Inner Box 1B: TVCacheEnv & _BackgroundLoop
    draw_box(0.75, 10.35, 5.95, 1.52, facecolor='#FFFFFF', edgecolor='#22C55E', lw=1.8, radius=0.18)
    ax.text(2.45, 11.58, "TVCacheEnv  +  _BackgroundLoop",
            ha='center', va='center', fontsize=9.6, fontweight='bold', color='#1B3B58')
    draw_badge(5.38, 11.58, "✓ Merged & Integration-Tested", '#DCFCE7', '#166534', '#22C55E', w=2.25, h=0.30, fontsize=7.2)
    ax.text(3.72, 11.10, "• _initial_observation() → _step_impl() → final_reward_fn() → close()",
            ha='center', va='center', fontsize=8.0, color='#334E68')
    ax.text(3.72, 10.66, "• Dedicated daemon event-loop thread + metrics (cache_hits, tool_wait_s)",
            ha='center', va='center', fontsize=8.0, color='#334E68')

    # Inner Box 1C: ForkBank
    draw_box(6.95, 10.35, 2.30, 1.52, facecolor='#F8FAFC', edgecolor='#64748B', lw=1.5, radius=0.18, linestyle='--')
    ax.text(8.10, 11.60, "ForkBank",
            ha='center', va='center', fontsize=9.6, fontweight='bold', color='#1B3B58')
    draw_badge(8.10, 11.20, "○ To Set Up", '#F1F5F9', '#475569', '#94A3B8', w=1.55, h=0.28, fontsize=7.2)
    ax.text(8.10, 10.70, "Pre-warms sandboxes\nbetween RL steps",
            ha='center', va='center', fontsize=7.9, color='#475569')

    # Arrow from TrajectoryCollectEngine -> TVCacheEnv
    ax.annotate("", xy=(3.72, 11.89), xytext=(3.72, 12.15),
                arrowprops=dict(arrowstyle="->", color='#2B5B84', lw=1.8))

    # ==================== ARROW TIER 1 -> TIER 2 ====================
    ax.annotate("", xy=(3.72, 9.25), xytext=(3.72, 10.12),
                arrowprops=dict(arrowstyle="->,head_width=0.35,head_length=0.35", color='#4A3B76', lw=2.5))
    ax.text(3.92, 9.68, "_loop.run(executor.lookup_or_execute(history))  /  executor.test(history)",
            ha='left', va='center', fontsize=8.5, fontweight='bold', color='#4A3B76')

    # ==================== TIER 2: TVCLIENT + SANDBOX ADAPTER ====================
    draw_box(0.4, 5.10, 9.2, 4.12, facecolor='#F3EFFA', edgecolor='#5E4B8B', lw=2.2, radius=0.28)
    ax.text(3.55, 8.90, "Client & Sandbox Layer  —  tvclient + Tunix Adapter",
            ha='center', va='center', fontsize=11.2, fontweight='bold', color='#382B5C')
    draw_badge(7.85, 8.90, "✓ Merged in Tunix & Verified E2E", '#DCFCE7', '#166534', '#22C55E', w=2.95, h=0.34, fontsize=7.5)

    # Inner Box 2A: TvcacheToolExecutor
    draw_box(0.75, 6.72, 8.5, 1.88, facecolor='#FFFFFF', edgecolor='#22C55E', lw=1.8, radius=0.18)
    ax.text(3.60, 8.32, "TvcacheToolExecutor  (Prefix Match & Snapshotting)",
            ha='center', va='center', fontsize=9.8, fontweight='bold', color='#382B5C')
    draw_badge(7.92, 8.32, "✓ Working (50.2× Hit Speedup)", '#DCFCE7', '#166534', '#22C55E', w=2.45, h=0.30, fontsize=7.3)
    ax.text(1.0, 7.86, "1. Full Cache Hit:", ha='left', va='center', fontsize=8.3, fontweight='bold', color='#1E7E34')
    ax.text(3.15, 7.86, "Return cached terminal output directly in < 2 ms (0 executions)", ha='left', va='center', fontsize=8.3, color='#2D3748')
    ax.text(1.0, 7.46, "2. Partial Hit (Branch):", ha='left', va='center', fontsize=8.3, fontweight='bold', color='#C05621')
    ax.text(3.60, 7.46, "start() calls /fork on cached env_id so snapshot stays untouched (2.7×)", ha='left', va='center', fontsize=8.3, color='#2D3748')
    ax.text(1.0, 7.06, "3. Cache Miss:", ha='left', va='center', fontsize=8.3, fontweight='bold', color='#9B2C2C')
    ax.text(3.15, 7.06, "Execute in container; snapshot only if work > 2× fork cost", ha='left', va='center', fontsize=8.3, color='#2D3748')

    # Inner Box 2B: TerminalBenchSandbox & ShellToolCall
    draw_box(0.75, 5.32, 8.5, 1.12, facecolor='#FFFFFF', edgecolor='#22C55E', lw=1.8, radius=0.18)
    ax.text(3.60, 6.14, "TerminalBenchSandbox  &  ShellToolCall  (httpx)",
            ha='center', va='center', fontsize=9.5, fontweight='bold', color='#382B5C')
    draw_badge(7.78, 6.14, "✓ Merged in Tunix (521-line Test Suite)", '#DCFCE7', '#166534', '#22C55E', w=2.70, h=0.30, fontsize=7.2)
    ax.text(5.0, 5.64, "Normalizes hostnames (`user@terminal:`) & strips `; tmux wait -S done`  •  Diffs settled pane logs",
            ha='center', va='center', fontsize=8.1, color='#2D3748')

    ax.annotate("", xy=(5.0, 6.46), xytext=(5.0, 6.72),
                arrowprops=dict(arrowstyle="->", color='#5E4B8B', lw=1.8))

    # ==================== ARROWS TIER 2 -> TIER 3 ====================
    ax.annotate("", xy=(2.8, 4.15), xytext=(2.8, 5.10),
                arrowprops=dict(arrowstyle="<->,head_width=0.35,head_length=0.35", color='#236B43', lw=2.5))
    ax.text(3.0, 4.62, "1. Prefix Lookup / Insert\nTCP :7878  (< 2 ms, Working)",
            ha='left', va='center', fontsize=8.4, fontweight='bold', color='#1E5E3A')

    ax.annotate("", xy=(7.2, 4.15), xytext=(7.2, 5.10),
                arrowprops=dict(arrowstyle="<->,head_width=0.35,head_length=0.35", color='#B85014', lw=2.5))
    ax.text(7.4, 4.62, "2. On Miss / Branch\nHTTP :9901  (Working)",
            ha='left', va='center', fontsize=8.4, fontweight='bold', color='#9C4221')

    # ==================== TIER 3: CPU CONTAINER HOST VM ====================
    draw_box(0.4, 0.30, 9.2, 3.85, facecolor='#F0FDF4', edgecolor='#15803D', lw=2.2, radius=0.28)
    ax.text(3.45, 3.84, "CPU Container Host VM  —  Backend Servers",
            ha='center', va='center', fontsize=11.2, fontweight='bold', color='#14532D')
    draw_badge(7.65, 3.84, "✓ Working on ARM Host (Move to GCloud x86)", '#DCFCE7', '#166534', '#22C55E', w=3.45, h=0.34, fontsize=7.4)

    # Bottom-Left: tvcache-rust
    draw_box(0.75, 0.58, 4.1, 2.92, facecolor='#FFFFFF', edgecolor='#22C55E', lw=1.8, radius=0.2)
    ax.text(2.8, 3.22, "tvcache-rust Server (:7878)",
            ha='center', va='center', fontsize=10.0, fontweight='bold', color='#1B5E3A')
    draw_badge(2.8, 2.82, "✓ Working (3,661 lookups/sec)", '#DCFCE7', '#166534', '#22C55E', w=2.55, h=0.28, fontsize=7.3)
    ax.text(2.8, 2.30, "• In-Memory Tool Call Graph\n  (1 prefix tree per task)",
            ha='center', va='center', fontsize=8.2, color='#1F2937')
    ax.text(2.8, 1.68, "• Stores command outputs &\n  committed container IDs",
            ha='center', va='center', fontsize=8.2, color='#1F2937')
    draw_badge(2.8, 0.96, "○ SandboxManager Eviction: To Start", '#F1F5F9', '#475569', '#94A3B8', w=3.35, h=0.30, fontsize=7.2)

    # Bottom-Right: container-manager
    draw_box(5.15, 0.58, 4.1, 2.92, facecolor='#FFFFFF', edgecolor='#22C55E', lw=1.8, radius=0.2)
    ax.text(7.2, 3.22, "container-manager (:9901)",
            ha='center', va='center', fontsize=10.0, fontweight='bold', color='#8C3A10')
    draw_badge(7.2, 2.82, "✓ Working & Fixed (Up to 68 Containers)", '#DCFCE7', '#166534', '#22C55E', w=3.2, h=0.28, fontsize=7.3)
    ax.text(7.2, 2.30, "• Fixed 2-Phase ForkPipeline:\n  docker commit --pause=false",
            ha='center', va='center', fontsize=8.2, color='#1F2937')
    ax.text(7.2, 1.68, "• Endpoints: /start, /fork,\n  /execute, /get_pane_logs, /test",
            ha='center', va='center', fontsize=8.2, color='#1F2937')
    draw_badge(7.2, 0.96, "○ Cold Snapshot vs Running Fork: Phase 2", '#F1F5F9', '#475569', '#94A3B8', w=3.45, h=0.30, fontsize=7.1)

    plt.tight_layout(pad=0.2)
    out_png = "/home/ubuntu/workspace/tvcache/container-manager-public/rlhf_server/benchmarks/chart3_architecture_diagram.png"
    out_pdf = "/home/ubuntu/workspace/tvcache/container-manager-public/rlhf_server/benchmarks/chart3_architecture_diagram.pdf"
    plt.savefig(out_png, dpi=300, bbox_inches='tight', facecolor='white')
    plt.savefig(out_pdf, bbox_inches='tight', facecolor='white')
    print("Saved:", out_png, out_pdf)

if __name__ == "__main__":
    make_arch_diagram()
