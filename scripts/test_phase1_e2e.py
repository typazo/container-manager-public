#!/usr/bin/env python3
"""
Phase 1 End-to-End Verification Script for TVCache + Container-Manager.

Demonstrates:
1. TerminalBenchSandbox implementing tvclient.Sandbox (start, fork, execute, stop)
   communicating with container-manager's RLHF server on localhost:9901.
2. TvcacheToolExecutor communicating with tvcache-rust on localhost:7878.
3. Rollout 1 (Uncached / Cold): Boots a real Docker container for the 'hello-world'
   terminal-bench task, executes stateful terminal commands, snapshots the container
   via fork(), and caches the outputs + snapshot handle in tvcache-rust.
4. Rollout 2 (Cached Hit): Repeats the same terminal command sequence, hitting
   tvcache-rust in <5ms and completely bypassing container execution.
5. Rollout 3 (Prefix Match + Fork Suffix): Shares the first command prefix with
   Rollout 1, forks the cached Docker snapshot from Rollout 1, and executes only
   the new suffix command in the forked container.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Optional
import aiohttp

os.chdir(Path(__file__).resolve().parent)
sys.path.insert(0, str(Path(__file__).resolve().parent / "tvclient"))
from tvclient import Sandbox, ToolCall, TestToolCall, TvcacheToolExecutor, TVCacheClient

CONTAINER_MANAGER_URL = "http://127.0.0.1:9901"
TVCACHE_HOST = "127.0.0.1"
TVCACHE_PORT = 7878


class TerminalCommandCall(ToolCall):
    """Represents a bash command tool call in terminal-bench."""

    def __init__(self, command: str, mutates: bool = True, blocking: bool = True, timeout: int = 30):
        self.command = command
        self.mutates = mutates
        self.blocking = blocking
        self.timeout = timeout

    def to_dict(self) -> dict:
        return {"command": self.command}

    def will_mutate_state(self) -> bool:
        return self.mutates


class TerminalBenchSandbox(Sandbox):
    """
    Sandbox adapter connecting tvclient to container-manager's HTTP server (rlhf_server).
    """

    # Track calls for verification reporting
    start_calls = 0
    fork_calls = 0
    execute_calls = 0
    stop_calls = 0

    def __init__(self, task_name: str, env_id: Optional[str] = None, base_url: str = CONTAINER_MANAGER_URL):
        super().__init__(task_name=task_name, env_id=env_id)
        self.base_url = base_url

    async def start(self) -> None:
        """
        If env_id is None: boot a fresh container for task_name via /start.
        If env_id is set (a snapshot handle stored in the cache): fork a new live
        container from that snapshot handle via /fork so the cached snapshot remains
        untouched for future rollouts.
        """
        TerminalBenchSandbox.start_calls += 1
        async with aiohttp.ClientSession() as session:
            if self.env_id is None:
                async with session.post(
                    f"{self.base_url}/start",
                    json={"task_name": self.task_name},
                    timeout=aiohttp.ClientTimeout(total=180),
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    self.env_id = data["id"]
            else:
                parent_id = self.env_id
                async with session.post(
                    f"{self.base_url}/fork",
                    json={"id": parent_id},
                    timeout=aiohttp.ClientTimeout(total=180),
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    self.env_id = data["id"]

    async def fork(self) -> "TerminalBenchSandbox":
        """
        Create a snapshot of the live sandbox via /fork and return a handle to it.
        """
        TerminalBenchSandbox.fork_calls += 1
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/fork",
                json={"id": self.env_id},
                timeout=aiohttp.ClientTimeout(total=180),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                snapshot_id = data["id"]
                return TerminalBenchSandbox(
                    task_name=self.task_name,
                    env_id=snapshot_id,
                    base_url=self.base_url,
                )

    async def execute(self, tool_call: ToolCall) -> str:
        """
        Execute either a TestToolCall (/test) or a TerminalCommandCall (/execute + /get_pane_logs).
        """
        TerminalBenchSandbox.execute_calls += 1
        async with aiohttp.ClientSession() as session:
            if isinstance(tool_call, TestToolCall):
                async with session.post(
                    f"{self.base_url}/test",
                    json={"id": self.env_id},
                    timeout=aiohttp.ClientTimeout(total=180),
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return str(data.get("passed", False))

            assert isinstance(tool_call, TerminalCommandCall)
            async with session.post(
                f"{self.base_url}/execute",
                json={
                    "id": self.env_id,
                    "command": tool_call.command,
                    "blocking": tool_call.blocking,
                    "timeout": tool_call.timeout,
                },
                timeout=aiohttp.ClientTimeout(total=tool_call.timeout + 30),
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    return f"Failed to execute: {err}"

            async with session.post(
                f"{self.base_url}/get_pane_logs",
                json={"id": self.env_id},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("logs", "")

    async def stop(self) -> None:
        """
        Stop and clean up the container via /stop.
        """
        if not self.env_id:
            return
        TerminalBenchSandbox.stop_calls += 1
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/stop",
                json={"id": self.env_id},
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                resp.raise_for_status()


async def main() -> None:
    task_id = "hello-world"
    # Use a low fixed snapshot threshold (0.01s) so Rollout 1 snapshots after step 1
    fixed_threshold = 0.01

    cmd1 = TerminalCommandCall("echo 'Hello, world!' > /app/hello.txt")
    cmd2 = TerminalCommandCall("cat /app/hello.txt", mutates=False)

    print("=" * 70)
    print("PHASE 1 END-TO-END PROTOTYPE DEMO: TVCache + Container-Manager")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Rollout 1: Cold cache -> executes in Docker container & snapshots state
    # -------------------------------------------------------------------------
    print("\n[Rollout 1] Cold Cache: Running commands in Docker container...")
    t0 = time.perf_counter()
    async with TvcacheToolExecutor(
        TerminalBenchSandbox,
        TerminalCommandCall,
        task_id,
        host=TVCACHE_HOST,
        port=TVCACHE_PORT,
        adaptive=False,
        fixed_threshold_seconds=fixed_threshold,
    ) as ex1:
        ex1.set_rollout_id("rollout-1-cold")
        history1 = [cmd1]
        out1_step1 = await ex1.lookup_or_execute(history1)
        history1.append(cmd2)
        out1_step2 = await ex1.lookup_or_execute(history1)
        test_res1 = await ex1.test(history1)
    r1_time = time.perf_counter() - t0

    print(f"  -> Step 1 output tail: {out1_step1.splitlines()[-2:] if out1_step1 else out1_step1}")
    print(f"  -> Step 2 output tail: {out1_step2.splitlines()[-2:] if out1_step2 else out1_step2}")
    print(f"  -> Unit test passed:   {test_res1}")
    print(f"  -> Rollout 1 total executions: {ex1.total_executions}/{ex1.total_calls}")
    print(f"  -> Rollout 1 elapsed time:     {r1_time:.3f}s")

    execs_after_r1 = TerminalBenchSandbox.execute_calls

    # -------------------------------------------------------------------------
    # Rollout 2: Warm cache -> 100% cache hit, bypasses Docker execution completely
    # -------------------------------------------------------------------------
    print("\n[Rollout 2] Warm Cache: Repeating exact trajectory...")
    t0 = time.perf_counter()
    async with TvcacheToolExecutor(
        TerminalBenchSandbox,
        TerminalCommandCall,
        task_id,
        host=TVCACHE_HOST,
        port=TVCACHE_PORT,
        adaptive=False,
        fixed_threshold_seconds=fixed_threshold,
    ) as ex2:
        ex2.set_rollout_id("rollout-2-cached")
        history2 = [cmd1]
        out2_step1 = await ex2.lookup_or_execute(history2)
        history2.append(cmd2)
        out2_step2 = await ex2.lookup_or_execute(history2)
        test_res2 = await ex2.test(history2)
    r2_time = time.perf_counter() - t0

    print(f"  -> Step 1 output matches Rollout 1: {out2_step1 == out1_step1}")
    print(f"  -> Step 2 output matches Rollout 1: {out2_step2 == out1_step2}")
    print(f"  -> Test result matches Rollout 1:   {test_res2 == test_res1} ({test_res2})")
    print(f"  -> Rollout 2 total executions:      {ex2.total_executions}/{ex2.total_calls} (0 container executions!)")
    print(f"  -> Rollout 2 elapsed time:          {r2_time:.4f}s (Speedup: {r1_time / r2_time:.1f}x)")

    assert out2_step1 == out1_step1, "Step 1 cached output mismatch!"
    assert out2_step2 == out1_step2, "Step 2 cached output mismatch!"
    assert test_res2 == test_res1 == "True", f"Expected test pass True, got {test_res2}"
    assert ex2.total_executions == 0, "Expected 0 executions on Rollout 2!"
    assert TerminalBenchSandbox.execute_calls == execs_after_r1, "Sandbox.execute should not have been called!"

    # -------------------------------------------------------------------------
    # Rollout 3: Partial prefix match -> hits cache on Step 1, forks snapshot for Step 2
    # -------------------------------------------------------------------------
    print("\n[Rollout 3] Branching Rollout: Matching Step 1 prefix, diverging on Step 2...")
    cmd_branch = TerminalCommandCall("cat /app/hello.txt && echo 'Branching works!'", mutates=True)
    t0 = time.perf_counter()
    async with TvcacheToolExecutor(
        TerminalBenchSandbox,
        TerminalCommandCall,
        task_id,
        host=TVCACHE_HOST,
        port=TVCACHE_PORT,
        adaptive=False,
        fixed_threshold_seconds=fixed_threshold,
    ) as ex3:
        ex3.set_rollout_id("rollout-3-branch")
        history3 = [cmd1]
        out3_step1 = await ex3.lookup_or_execute(history3)  # Should HIT cache
        history3.append(cmd_branch)
        out3_step2 = await ex3.lookup_or_execute(history3)  # Should FORK snapshot from Step 1 and run only cmd_branch
    r3_time = time.perf_counter() - t0

    print(f"  -> Step 1 (Cache Hit) matches: {out3_step1 == out1_step1}")
    print(f"  -> Step 2 (Forked Suffix) output tail: {out3_step2.splitlines()[-3:] if out3_step2 else out3_step2}")
    print(f"  -> Rollout 3 total executions: {ex3.total_executions}/{ex3.total_calls} (Only suffix executed!)")
    print(f"  -> Rollout 3 elapsed time:     {r3_time:.3f}s")

    assert ex3.total_executions == 1, f"Expected only 1 execution (the suffix), got {ex3.total_executions}"
    assert "Hello, world!" in out3_step2 and "Branching works!" in out3_step2, (
        "Forked container did not preserve /app/hello.txt from Step 1!"
    )

    # -------------------------------------------------------------------------
    # Inspect TVCache Server State & Clean Up Snapshot
    # -------------------------------------------------------------------------
    async with TVCacheClient(TVCACHE_HOST, TVCACHE_PORT) as client:
        cache_dump = await client.dump_all()
        tcg = cache_dump.get(task_id, {})
        print("\n[TVCache Server State Summary]")
        print(f"  -> Task ID:             {task_id}")
        print(f"  -> Total TCG Size:      {tcg.get('size_in_bytes')} bytes")
        print(f"  -> Stored Sandboxes:    {tcg.get('number_of_sandboxes')}")
        print(f"  -> Active References:   {tcg.get('sandbox_references')}")

        # Clean up any cached snapshot containers so no orphan containers remain
        def collect_sandboxes(node: dict) -> list[str]:
            sbs = []
            if node.get("sandbox_id"):
                sbs.append(node["sandbox_id"])
            for child in node.get("children", {}).values():
                sbs.extend(collect_sandboxes(child))
            return sbs

        stored_sandboxes = collect_sandboxes(tcg.get("root", {}))
        for sb_id in stored_sandboxes:
            print(f"  -> Cleaning up cached snapshot container: {sb_id}")
            await TerminalBenchSandbox(task_name=task_id, env_id=sb_id).stop()

    print("\n" + "=" * 70)
    print("SUCCESS: End-to-end TVCache + Container-Manager verification passed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
