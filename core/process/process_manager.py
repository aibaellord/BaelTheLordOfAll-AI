#!/usr/bin/env python3
"""
BAEL - Process Manager
Advanced process management and orchestration.

Features:
- Process spawning and lifecycle management
- Process pools
- Inter-process communication
- Process monitoring
- Resource limits
- Signal handling
- Process groups
- Daemon processes
- Process priorities
- CPU/memory tracking
"""

import asyncio
import json
import logging
import os
import queue
import signal
import subprocess
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (Any, Awaitable, Callable, Dict, Generic, Iterator, List,
                    Optional, Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)


T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class ProcessState(Enum):
    """Process states."""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    KILLED = "killed"
    COMPLETED = "completed"


class ProcessPriority(Enum):
    """Process priorities."""
    LOWEST = 19
    LOW = 10
    NORMAL = 0
    HIGH = -10
    HIGHEST = -20


class SignalType(Enum):
    """Signal types."""
    SIGTERM = 15
    SIGKILL = 9
    SIGINT = 2
    SIGHUP = 1
    SIGUSR1 = 10
    SIGUSR2 = 12


class RestartPolicy(Enum):
    """Restart policies."""
    NEVER = "never"
    ON_FAILURE = "on_failure"
    ALWAYS = "always"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class ProcessConfig:
    """Process configuration."""
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    shell: bool = False
    priority: ProcessPriority = ProcessPriority.NORMAL
    restart_policy: RestartPolicy = RestartPolicy.NEVER
    max_restarts: int = 3
    restart_delay: float = 1.0
    timeout: Optional[float] = None
    capture_output: bool = True
    stdin_data: Optional[bytes] = None


@dataclass
class ProcessInfo:
    """Process information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pid: Optional[int] = None
    state: ProcessState = ProcessState.PENDING
    config: ProcessConfig = field(default_factory=ProcessConfig)
    exit_code: Optional[int] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    restart_count: int = 0
    cpu_percent: float = 0.0
    memory_bytes: int = 0
    stdout: bytes = b''
    stderr: bytes = b''


@dataclass
class ProcessStats:
    """Process statistics."""
    pid: int
    cpu_percent: float = 0.0
    memory_bytes: int = 0
    memory_percent: float = 0.0
    threads: int = 0
    open_files: int = 0
    uptime_seconds: float = 0.0


@dataclass
class PoolConfig:
    """Process pool configuration."""
    name: str
    min_workers: int = 1
    max_workers: int = 4
    worker_command: str = ""
    worker_args: List[str] = field(default_factory=list)
    idle_timeout: float = 60.0


@dataclass
class IPCMessage:
    """Inter-process communication message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_pid: int = 0
    target_pid: Optional[int] = None
    message_type: str = "data"
    payload: Any = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# PROCESS WRAPPER
# =============================================================================

class ManagedProcess:
    """Wrapper around a subprocess."""

    def __init__(self, info: ProcessInfo):
        self.info = info
        self._process: Optional[subprocess.Popen] = None
        self._output_thread: Optional[threading.Thread] = None
        self._error_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> bool:
        """Start the process."""
        try:
            self.info.state = ProcessState.STARTING

            config = self.info.config
            cmd = [config.command] + config.args

            env = os.environ.copy()
            env.update(config.env)

            self._process = subprocess.Popen(
                cmd,
                shell=config.shell,
                env=env,
                cwd=config.cwd,
                stdin=subprocess.PIPE if config.stdin_data else None,
                stdout=subprocess.PIPE if config.capture_output else None,
                stderr=subprocess.PIPE if config.capture_output else None,
            )

            self.info.pid = self._process.pid
            self.info.state = ProcessState.RUNNING
            self.info.started_at = datetime.utcnow()

            # Start output capture threads
            if config.capture_output:
                self._start_output_capture()

            # Send stdin data
            if config.stdin_data and self._process.stdin:
                self._process.stdin.write(config.stdin_data)
                self._process.stdin.close()

            return True

        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            self.info.state = ProcessState.FAILED
            return False

    def _start_output_capture(self) -> None:
        """Start threads to capture stdout/stderr."""
        def capture_stdout():
            if self._process and self._process.stdout:
                for line in self._process.stdout:
                    self.info.stdout += line

        def capture_stderr():
            if self._process and self._process.stderr:
                for line in self._process.stderr:
                    self.info.stderr += line

        self._output_thread = threading.Thread(target=capture_stdout, daemon=True)
        self._error_thread = threading.Thread(target=capture_stderr, daemon=True)

        self._output_thread.start()
        self._error_thread.start()

    def stop(self, timeout: float = 5.0) -> bool:
        """Stop the process gracefully."""
        if not self._process:
            return True

        self.info.state = ProcessState.STOPPING
        self._stop_event.set()

        try:
            self._process.terminate()
            self._process.wait(timeout=timeout)
            self.info.state = ProcessState.STOPPED
            self.info.exit_code = self._process.returncode
            self.info.stopped_at = datetime.utcnow()
            return True

        except subprocess.TimeoutExpired:
            self._process.kill()
            self.info.state = ProcessState.KILLED
            self.info.stopped_at = datetime.utcnow()
            return True

    def kill(self) -> bool:
        """Kill the process immediately."""
        if not self._process:
            return True

        try:
            self._process.kill()
            self._process.wait(timeout=1.0)
            self.info.state = ProcessState.KILLED
            self.info.exit_code = self._process.returncode
            self.info.stopped_at = datetime.utcnow()
            return True
        except Exception as e:
            logger.error(f"Failed to kill process: {e}")
            return False

    def send_signal(self, sig: SignalType) -> bool:
        """Send signal to process."""
        if not self._process:
            return False

        try:
            self._process.send_signal(sig.value)
            return True
        except Exception as e:
            logger.error(f"Failed to send signal: {e}")
            return False

    def is_running(self) -> bool:
        """Check if process is running."""
        if not self._process:
            return False
        return self._process.poll() is None

    def wait(self, timeout: Optional[float] = None) -> int:
        """Wait for process to complete."""
        if not self._process:
            return -1

        try:
            self._process.wait(timeout=timeout)
            self.info.exit_code = self._process.returncode
            self.info.state = ProcessState.COMPLETED if self._process.returncode == 0 else ProcessState.FAILED
            self.info.stopped_at = datetime.utcnow()
            return self._process.returncode
        except subprocess.TimeoutExpired:
            return -1

    def get_stats(self) -> ProcessStats:
        """Get process statistics."""
        if not self._process or not self.info.pid:
            return ProcessStats(pid=0)

        stats = ProcessStats(pid=self.info.pid)

        if self.info.started_at:
            stats.uptime_seconds = (datetime.utcnow() - self.info.started_at).total_seconds()

        # In production, use psutil for accurate stats
        # This is a simplified version
        try:
            # Try to read from /proc on Linux
            if sys.platform == 'linux':
                stat_file = f"/proc/{self.info.pid}/stat"
                if os.path.exists(stat_file):
                    with open(stat_file, 'r') as f:
                        parts = f.read().split()
                        stats.threads = int(parts[19]) if len(parts) > 19 else 1
        except Exception:
            pass

        return stats


# =============================================================================
# PROCESS POOL
# =============================================================================

class ProcessPool:
    """Pool of worker processes."""

    def __init__(self, config: PoolConfig):
        self.config = config
        self._workers: Dict[str, ManagedProcess] = {}
        self._task_queue: queue.Queue = queue.Queue()
        self._results: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> int:
        """Start the pool."""
        self._running = True

        for i in range(self.config.min_workers):
            self._spawn_worker()

        return len(self._workers)

    def stop(self, timeout: float = 5.0) -> int:
        """Stop all workers."""
        self._running = False
        stopped = 0

        for worker in list(self._workers.values()):
            if worker.stop(timeout):
                stopped += 1

        self._workers.clear()
        return stopped

    def _spawn_worker(self) -> Optional[str]:
        """Spawn a new worker."""
        if len(self._workers) >= self.config.max_workers:
            return None

        config = ProcessConfig(
            command=self.config.worker_command,
            args=self.config.worker_args
        )

        info = ProcessInfo(config=config)
        worker = ManagedProcess(info)

        if worker.start():
            self._workers[info.id] = worker
            return info.id

        return None

    def scale(self, count: int) -> int:
        """Scale workers to count."""
        current = len(self._workers)

        if count > current:
            # Scale up
            for _ in range(count - current):
                self._spawn_worker()
        elif count < current:
            # Scale down
            to_remove = list(self._workers.keys())[count:]
            for worker_id in to_remove:
                self._workers[worker_id].stop()
                del self._workers[worker_id]

        return len(self._workers)

    def get_workers(self) -> List[ProcessInfo]:
        """Get all worker info."""
        return [w.info for w in self._workers.values()]


# =============================================================================
# IPC HANDLER
# =============================================================================

class IPCHandler:
    """Inter-process communication handler."""

    def __init__(self):
        self._message_queue: queue.Queue[IPCMessage] = queue.Queue()
        self._handlers: Dict[str, List[Callable[[IPCMessage], None]]] = defaultdict(list)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start IPC handler."""
        self._running = True
        self._thread = threading.Thread(target=self._process_messages, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop IPC handler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def send(self, message: IPCMessage) -> None:
        """Send a message."""
        self._message_queue.put(message)

    def register_handler(
        self,
        message_type: str,
        handler: Callable[[IPCMessage], None]
    ) -> None:
        """Register message handler."""
        self._handlers[message_type].append(handler)

    def _process_messages(self) -> None:
        """Process messages from queue."""
        while self._running:
            try:
                message = self._message_queue.get(timeout=0.1)

                for handler in self._handlers.get(message.message_type, []):
                    try:
                        handler(message)
                    except Exception as e:
                        logger.error(f"Handler error: {e}")

            except queue.Empty:
                continue


# =============================================================================
# PROCESS GROUP
# =============================================================================

class ProcessGroup:
    """Group of related processes."""

    def __init__(self, name: str):
        self.name = name
        self._processes: Dict[str, ManagedProcess] = {}
        self._dependencies: Dict[str, List[str]] = defaultdict(list)

    def add(self, process: ManagedProcess) -> None:
        """Add process to group."""
        self._processes[process.info.id] = process

    def remove(self, process_id: str) -> bool:
        """Remove process from group."""
        if process_id in self._processes:
            del self._processes[process_id]
            return True
        return False

    def add_dependency(self, process_id: str, depends_on: str) -> None:
        """Add dependency between processes."""
        self._dependencies[process_id].append(depends_on)

    def start_all(self) -> int:
        """Start all processes respecting dependencies."""
        started = 0
        started_ids: Set[str] = set()

        # Topological sort for dependencies
        while len(started_ids) < len(self._processes):
            for pid, process in self._processes.items():
                if pid in started_ids:
                    continue

                deps = self._dependencies.get(pid, [])
                if all(d in started_ids for d in deps):
                    if process.start():
                        started += 1
                    started_ids.add(pid)

        return started

    def stop_all(self, timeout: float = 5.0) -> int:
        """Stop all processes in reverse order."""
        stopped = 0

        # Stop in reverse order of dependencies
        ordered = list(reversed(list(self._processes.keys())))

        for pid in ordered:
            if pid in self._processes:
                if self._processes[pid].stop(timeout):
                    stopped += 1

        return stopped

    def get_all(self) -> List[ProcessInfo]:
        """Get all process info."""
        return [p.info for p in self._processes.values()]


# =============================================================================
# PROCESS MONITOR
# =============================================================================

class ProcessMonitor:
    """Monitor process health and resources."""

    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self._processes: Dict[str, ManagedProcess] = {}
        self._stats_history: Dict[str, List[ProcessStats]] = defaultdict(list)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[str, ProcessStats], None]] = []
        self._max_history = 100

    def start(self) -> None:
        """Start monitoring."""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def add_process(self, process: ManagedProcess) -> None:
        """Add process to monitor."""
        self._processes[process.info.id] = process

    def remove_process(self, process_id: str) -> None:
        """Remove process from monitoring."""
        if process_id in self._processes:
            del self._processes[process_id]

    def on_stats(self, callback: Callable[[str, ProcessStats], None]) -> None:
        """Register stats callback."""
        self._callbacks.append(callback)

    def get_stats(self, process_id: str) -> Optional[ProcessStats]:
        """Get latest stats for process."""
        if process_id in self._stats_history and self._stats_history[process_id]:
            return self._stats_history[process_id][-1]
        return None

    def get_stats_history(self, process_id: str) -> List[ProcessStats]:
        """Get stats history for process."""
        return self._stats_history.get(process_id, [])

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            for pid, process in list(self._processes.items()):
                if process.is_running():
                    stats = process.get_stats()

                    # Store history
                    self._stats_history[pid].append(stats)
                    if len(self._stats_history[pid]) > self._max_history:
                        self._stats_history[pid] = self._stats_history[pid][-self._max_history:]

                    # Notify callbacks
                    for callback in self._callbacks:
                        try:
                            callback(pid, stats)
                        except Exception as e:
                            logger.error(f"Monitor callback error: {e}")

            time.sleep(self.interval)


# =============================================================================
# PROCESS MANAGER
# =============================================================================

class ProcessManager:
    """
    Process Manager for BAEL.

    Advanced process management and orchestration.
    """

    def __init__(self):
        self._processes: Dict[str, ManagedProcess] = {}
        self._pools: Dict[str, ProcessPool] = {}
        self._groups: Dict[str, ProcessGroup] = {}
        self._monitor = ProcessMonitor()
        self._ipc = IPCHandler()
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)

    # -------------------------------------------------------------------------
    # LIFECYCLE
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start the process manager."""
        self._monitor.start()
        self._ipc.start()

    def stop(self) -> None:
        """Stop the process manager."""
        # Stop all processes
        for process in list(self._processes.values()):
            process.stop()

        # Stop all pools
        for pool in list(self._pools.values()):
            pool.stop()

        # Stop all groups
        for group in list(self._groups.values()):
            group.stop_all()

        self._monitor.stop()
        self._ipc.stop()

    # -------------------------------------------------------------------------
    # PROCESS MANAGEMENT
    # -------------------------------------------------------------------------

    def spawn(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        capture_output: bool = True,
        restart_policy: RestartPolicy = RestartPolicy.NEVER
    ) -> ProcessInfo:
        """Spawn a new process."""
        config = ProcessConfig(
            command=command,
            args=args or [],
            env=env or {},
            cwd=cwd,
            capture_output=capture_output,
            restart_policy=restart_policy
        )

        info = ProcessInfo(config=config)
        process = ManagedProcess(info)

        self._processes[info.id] = process
        self._monitor.add_process(process)

        if process.start():
            self._emit('process_started', info)

            # Start restart watcher if needed
            if restart_policy != RestartPolicy.NEVER:
                self._start_restart_watcher(process)
        else:
            self._emit('process_failed', info)

        return info

    def spawn_async(
        self,
        command: str,
        args: Optional[List[str]] = None,
        **kwargs
    ) -> ProcessInfo:
        """Spawn process asynchronously."""
        return self.spawn(command, args, **kwargs)

    def terminate(self, process_id: str, timeout: float = 5.0) -> bool:
        """Terminate a process."""
        process = self._processes.get(process_id)
        if not process:
            return False

        result = process.stop(timeout)

        if result:
            self._emit('process_stopped', process.info)

        return result

    def kill(self, process_id: str) -> bool:
        """Kill a process immediately."""
        process = self._processes.get(process_id)
        if not process:
            return False

        result = process.kill()

        if result:
            self._emit('process_killed', process.info)

        return result

    def send_signal(self, process_id: str, signal: SignalType) -> bool:
        """Send signal to process."""
        process = self._processes.get(process_id)
        if not process:
            return False

        return process.send_signal(signal)

    def get_process(self, process_id: str) -> Optional[ProcessInfo]:
        """Get process info."""
        process = self._processes.get(process_id)
        return process.info if process else None

    def list_processes(self) -> List[ProcessInfo]:
        """List all processes."""
        return [p.info for p in self._processes.values()]

    def wait(self, process_id: str, timeout: Optional[float] = None) -> int:
        """Wait for process to complete."""
        process = self._processes.get(process_id)
        if not process:
            return -1

        return process.wait(timeout)

    def is_running(self, process_id: str) -> bool:
        """Check if process is running."""
        process = self._processes.get(process_id)
        return process.is_running() if process else False

    def _start_restart_watcher(self, process: ManagedProcess) -> None:
        """Start watching process for restarts."""
        def watcher():
            while process.info.restart_count < process.info.config.max_restarts:
                exit_code = process.wait()

                if not self._should_restart(process, exit_code):
                    break

                time.sleep(process.info.config.restart_delay)

                process.info.restart_count += 1
                process.start()
                self._emit('process_restarted', process.info)

        thread = threading.Thread(target=watcher, daemon=True)
        thread.start()

    def _should_restart(self, process: ManagedProcess, exit_code: int) -> bool:
        """Check if process should be restarted."""
        policy = process.info.config.restart_policy

        if policy == RestartPolicy.NEVER:
            return False
        elif policy == RestartPolicy.ON_FAILURE:
            return exit_code != 0
        elif policy == RestartPolicy.ALWAYS:
            return True

        return False

    # -------------------------------------------------------------------------
    # POOLS
    # -------------------------------------------------------------------------

    def create_pool(
        self,
        name: str,
        worker_command: str,
        worker_args: Optional[List[str]] = None,
        min_workers: int = 1,
        max_workers: int = 4
    ) -> ProcessPool:
        """Create a process pool."""
        config = PoolConfig(
            name=name,
            worker_command=worker_command,
            worker_args=worker_args or [],
            min_workers=min_workers,
            max_workers=max_workers
        )

        pool = ProcessPool(config)
        self._pools[name] = pool

        return pool

    def get_pool(self, name: str) -> Optional[ProcessPool]:
        """Get a pool by name."""
        return self._pools.get(name)

    def scale_pool(self, name: str, count: int) -> int:
        """Scale a pool."""
        pool = self._pools.get(name)
        if pool:
            return pool.scale(count)
        return 0

    # -------------------------------------------------------------------------
    # GROUPS
    # -------------------------------------------------------------------------

    def create_group(self, name: str) -> ProcessGroup:
        """Create a process group."""
        group = ProcessGroup(name)
        self._groups[name] = group
        return group

    def get_group(self, name: str) -> Optional[ProcessGroup]:
        """Get a group by name."""
        return self._groups.get(name)

    def add_to_group(self, group_name: str, process_id: str) -> bool:
        """Add process to group."""
        group = self._groups.get(group_name)
        process = self._processes.get(process_id)

        if group and process:
            group.add(process)
            return True

        return False

    # -------------------------------------------------------------------------
    # IPC
    # -------------------------------------------------------------------------

    def send_message(
        self,
        target_pid: int,
        message_type: str,
        payload: Any
    ) -> None:
        """Send message to process."""
        message = IPCMessage(
            source_pid=os.getpid(),
            target_pid=target_pid,
            message_type=message_type,
            payload=payload
        )
        self._ipc.send(message)

    def on_message(
        self,
        message_type: str,
        handler: Callable[[IPCMessage], None]
    ) -> None:
        """Register message handler."""
        self._ipc.register_handler(message_type, handler)

    # -------------------------------------------------------------------------
    # MONITORING
    # -------------------------------------------------------------------------

    def get_stats(self, process_id: str) -> Optional[ProcessStats]:
        """Get process stats."""
        return self._monitor.get_stats(process_id)

    def get_stats_history(self, process_id: str) -> List[ProcessStats]:
        """Get process stats history."""
        return self._monitor.get_stats_history(process_id)

    def on_stats(self, callback: Callable[[str, ProcessStats], None]) -> None:
        """Register stats callback."""
        self._monitor.on_stats(callback)

    # -------------------------------------------------------------------------
    # OUTPUT
    # -------------------------------------------------------------------------

    def get_stdout(self, process_id: str) -> bytes:
        """Get process stdout."""
        process = self._processes.get(process_id)
        return process.info.stdout if process else b''

    def get_stderr(self, process_id: str) -> bytes:
        """Get process stderr."""
        process = self._processes.get(process_id)
        return process.info.stderr if process else b''

    def get_output(self, process_id: str) -> Tuple[bytes, bytes]:
        """Get process output (stdout, stderr)."""
        return self.get_stdout(process_id), self.get_stderr(process_id)

    # -------------------------------------------------------------------------
    # EVENTS
    # -------------------------------------------------------------------------

    def on(self, event: str, callback: Callable) -> None:
        """Register event callback."""
        self._callbacks[event].append(callback)

    def _emit(self, event: str, *args, **kwargs) -> None:
        """Emit event to callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    def run_command(
        self,
        command: str,
        args: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        check: bool = True
    ) -> Tuple[int, bytes, bytes]:
        """Run command and wait for completion."""
        info = self.spawn(command, args)

        exit_code = self.wait(info.id, timeout)
        stdout = self.get_stdout(info.id)
        stderr = self.get_stderr(info.id)

        if check and exit_code != 0:
            raise subprocess.CalledProcessError(exit_code, command, stdout, stderr)

        return exit_code, stdout, stderr

    async def run_command_async(
        self,
        command: str,
        args: Optional[List[str]] = None,
        timeout: Optional[float] = None
    ) -> Tuple[int, bytes, bytes]:
        """Run command asynchronously."""
        info = self.spawn(command, args)

        start = time.time()
        while self.is_running(info.id):
            if timeout and (time.time() - start) > timeout:
                self.kill(info.id)
                break
            await asyncio.sleep(0.1)

        exit_code = info.exit_code or -1
        stdout = self.get_stdout(info.id)
        stderr = self.get_stderr(info.id)

        return exit_code, stdout, stderr

    def cleanup(self) -> int:
        """Cleanup finished processes."""
        cleaned = 0

        for pid in list(self._processes.keys()):
            process = self._processes[pid]
            if not process.is_running():
                del self._processes[pid]
                self._monitor.remove_process(pid)
                cleaned += 1

        return cleaned


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Process Manager."""
    print("=" * 70)
    print("BAEL - PROCESS MANAGER DEMO")
    print("Advanced Process Management")
    print("=" * 70)
    print()

    manager = ProcessManager()
    manager.start()

    # 1. Spawn Simple Process
    print("1. SPAWN SIMPLE PROCESS:")
    print("-" * 40)

    info = manager.spawn("echo", ["Hello, BAEL!"])
    time.sleep(0.5)

    print(f"   Process ID: {info.id}")
    print(f"   PID: {info.pid}")
    print(f"   State: {info.state.value}")

    stdout = manager.get_stdout(info.id)
    print(f"   Output: {stdout.decode().strip()}")
    print()

    # 2. Run Python Command
    print("2. RUN PYTHON COMMAND:")
    print("-" * 40)

    py_info = manager.spawn(
        sys.executable,
        ["-c", "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')"]
    )
    manager.wait(py_info.id)

    stdout = manager.get_stdout(py_info.id)
    print(f"   Output: {stdout.decode().strip()}")
    print(f"   Exit code: {py_info.exit_code}")
    print()

    # 3. Process with Environment
    print("3. PROCESS WITH ENVIRONMENT:")
    print("-" * 40)

    env_info = manager.spawn(
        sys.executable,
        ["-c", "import os; print(os.environ.get('BAEL_TEST', 'not set'))"],
        env={"BAEL_TEST": "Hello from BAEL!"}
    )
    manager.wait(env_info.id)

    stdout = manager.get_stdout(env_info.id)
    print(f"   Output: {stdout.decode().strip()}")
    print()

    # 4. Run Command Utility
    print("4. RUN COMMAND UTILITY:")
    print("-" * 40)

    exit_code, stdout, stderr = manager.run_command(
        "ls", ["-la", "/tmp"],
        timeout=5.0,
        check=False
    )

    lines = stdout.decode().strip().split('\n')
    print(f"   Exit code: {exit_code}")
    print(f"   Lines: {len(lines)}")
    print(f"   First line: {lines[0] if lines else 'N/A'}")
    print()

    # 5. Long Running Process
    print("5. LONG RUNNING PROCESS:")
    print("-" * 40)

    long_info = manager.spawn(
        sys.executable,
        ["-c", "import time; time.sleep(2); print('Done!')"]
    )

    print(f"   Started: {long_info.id[:8]}...")
    print(f"   Running: {manager.is_running(long_info.id)}")

    # Wait a bit
    await asyncio.sleep(0.5)
    print(f"   Still running: {manager.is_running(long_info.id)}")

    # Terminate
    manager.terminate(long_info.id, timeout=1.0)
    print(f"   After terminate: {manager.is_running(long_info.id)}")
    print()

    # 6. Event Callbacks
    print("6. EVENT CALLBACKS:")
    print("-" * 40)

    events = []
    manager.on('process_started', lambda i: events.append(f"started:{i.id[:8]}"))
    manager.on('process_stopped', lambda i: events.append(f"stopped:{i.id[:8]}"))

    event_info = manager.spawn("echo", ["test"])
    time.sleep(0.5)
    manager.terminate(event_info.id)

    print(f"   Events captured: {len(events)}")
    for event in events:
        print(f"      - {event}")
    print()

    # 7. Process Groups
    print("7. PROCESS GROUPS:")
    print("-" * 40)

    group = manager.create_group("my_group")

    p1 = manager.spawn("echo", ["process 1"])
    p2 = manager.spawn("echo", ["process 2"])

    group.add(manager._processes[p1.id])
    group.add(manager._processes[p2.id])

    print(f"   Group: {group.name}")
    print(f"   Processes: {len(group.get_all())}")

    time.sleep(0.5)
    stopped = group.stop_all()
    print(f"   Stopped: {stopped}")
    print()

    # 8. Async Command
    print("8. ASYNC COMMAND:")
    print("-" * 40)

    exit_code, stdout, stderr = await manager.run_command_async(
        sys.executable,
        ["-c", "print('Async hello!')"],
        timeout=5.0
    )

    print(f"   Output: {stdout.decode().strip()}")
    print(f"   Exit code: {exit_code}")
    print()

    # 9. List All Processes
    print("9. LIST ALL PROCESSES:")
    print("-" * 40)

    all_processes = manager.list_processes()
    print(f"   Total processes: {len(all_processes)}")

    for proc in all_processes[:5]:
        print(f"      - {proc.id[:8]}... State: {proc.state.value}")
    print()

    # 10. Cleanup
    print("10. CLEANUP:")
    print("-" * 40)

    cleaned = manager.cleanup()
    print(f"   Cleaned up: {cleaned} finished processes")

    remaining = len(manager.list_processes())
    print(f"   Remaining: {remaining}")
    print()

    # Stop manager
    manager.stop()

    print("=" * 70)
    print("DEMO COMPLETE - Process Manager Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
