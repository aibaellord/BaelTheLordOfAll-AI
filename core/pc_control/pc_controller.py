"""
BAEL - Universal PC Control System
====================================

Complete computer automation and control system.

Features:
1. Filesystem Operations - Create, read, write, delete, search
2. Process Management - Launch, kill, monitor processes
3. Keyboard Control - Type, hotkeys, macros
4. Mouse Control - Move, click, drag, scroll
5. Window Management - Focus, resize, move windows
6. Screen Capture - Screenshots, screen recording
7. Clipboard Operations - Copy, paste, monitor
8. System Monitoring - CPU, RAM, disk, network
9. Application Control - Open, close, interact with apps
10. Task Automation - Complex multi-step workflows

This gives Ba'el complete control over the host system,
enabling fully automated workflows and assistance.

WARNING: Use responsibly with proper authorization!
"""

import asyncio
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import threading

logger = logging.getLogger("BAEL.PC_CONTROL")


# ============================================================================
# PLATFORM DETECTION
# ============================================================================

class Platform(Enum):
    """Supported platforms."""
    MACOS = "darwin"
    WINDOWS = "windows"
    LINUX = "linux"


CURRENT_PLATFORM: Platform = Platform.MACOS
system = platform.system().lower()
if "darwin" in system:
    CURRENT_PLATFORM = Platform.MACOS
elif "windows" in system:
    CURRENT_PLATFORM = Platform.WINDOWS
else:
    CURRENT_PLATFORM = Platform.LINUX

logger.info(f"Platform detected: {CURRENT_PLATFORM.value}")


# ============================================================================
# KEYBOARD KEYS
# ============================================================================

class Key(Enum):
    """Keyboard keys."""
    # Modifier keys
    COMMAND = "command"
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    
    # Special keys
    ENTER = "enter"
    TAB = "tab"
    SPACE = "space"
    BACKSPACE = "backspace"
    DELETE = "delete"
    ESCAPE = "escape"
    
    # Arrow keys
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    
    # Function keys
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"


class MouseButton(Enum):
    """Mouse buttons."""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class FileInfo:
    """Information about a file."""
    path: Path
    name: str
    is_file: bool
    is_directory: bool
    size: int = 0
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    accessed: Optional[datetime] = None
    extension: str = ""
    permissions: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "name": self.name,
            "is_file": self.is_file,
            "is_directory": self.is_directory,
            "size": self.size,
            "created": self.created.isoformat() if self.created else None,
            "modified": self.modified.isoformat() if self.modified else None,
            "extension": self.extension,
            "permissions": self.permissions
        }


@dataclass
class ProcessInfo:
    """Information about a process."""
    pid: int
    name: str
    status: str = "running"
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    command: str = ""
    parent_pid: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "status": self.status,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "command": self.command,
            "parent_pid": self.parent_pid
        }


@dataclass
class WindowInfo:
    """Information about a window."""
    id: str
    title: str
    app_name: str
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    is_focused: bool = False
    is_minimized: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "app_name": self.app_name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "is_focused": self.is_focused,
            "is_minimized": self.is_minimized
        }


@dataclass
class SystemInfo:
    """System resource information."""
    cpu_percent: float = 0.0
    cpu_count: int = 0
    memory_total: int = 0
    memory_available: int = 0
    memory_percent: float = 0.0
    disk_total: int = 0
    disk_used: int = 0
    disk_free: int = 0
    disk_percent: float = 0.0
    uptime_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "cpu_count": self.cpu_count,
            "memory_total_gb": self.memory_total / (1024**3),
            "memory_available_gb": self.memory_available / (1024**3),
            "memory_percent": self.memory_percent,
            "disk_total_gb": self.disk_total / (1024**3),
            "disk_used_gb": self.disk_used / (1024**3),
            "disk_free_gb": self.disk_free / (1024**3),
            "disk_percent": self.disk_percent,
            "uptime_hours": self.uptime_seconds / 3600
        }


# ============================================================================
# FILESYSTEM CONTROLLER
# ============================================================================

class FilesystemController:
    """
    Complete filesystem control.
    
    Provides:
    - File/directory CRUD
    - Search and filtering
    - Path traversal
    - Permissions management
    """
    
    def __init__(self, sandbox_paths: List[str] = None):
        self.sandbox_paths = sandbox_paths or []  # If set, restricts operations
        self.home = Path.home()
        self.cwd = Path.cwd()
    
    def _check_sandbox(self, path: Path) -> bool:
        """Check if path is within sandbox (if sandbox enabled)."""
        if not self.sandbox_paths:
            return True
        path_str = str(path.resolve())
        return any(path_str.startswith(sb) for sb in self.sandbox_paths)
    
    def list_directory(
        self,
        path: Union[str, Path] = ".",
        pattern: str = "*",
        recursive: bool = False
    ) -> List[FileInfo]:
        """List directory contents."""
        path = Path(path).expanduser().resolve()
        
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        if not self._check_sandbox(path):
            raise PermissionError(f"Path outside sandbox: {path}")
        
        files = []
        
        if recursive:
            items = path.rglob(pattern)
        else:
            items = path.glob(pattern)
        
        for item in items:
            try:
                stat = item.stat()
                files.append(FileInfo(
                    path=item,
                    name=item.name,
                    is_file=item.is_file(),
                    is_directory=item.is_dir(),
                    size=stat.st_size if item.is_file() else 0,
                    created=datetime.fromtimestamp(stat.st_ctime),
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    accessed=datetime.fromtimestamp(stat.st_atime),
                    extension=item.suffix,
                    permissions=oct(stat.st_mode)[-3:]
                ))
            except (OSError, PermissionError):
                continue
        
        return files
    
    def read_file(
        self,
        path: Union[str, Path],
        binary: bool = False
    ) -> Union[str, bytes]:
        """Read file contents."""
        path = Path(path).expanduser().resolve()
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if not self._check_sandbox(path):
            raise PermissionError(f"Path outside sandbox: {path}")
        
        mode = "rb" if binary else "r"
        encoding = None if binary else "utf-8"
        
        with open(path, mode, encoding=encoding) as f:
            return f.read()
    
    def write_file(
        self,
        path: Union[str, Path],
        content: Union[str, bytes],
        create_dirs: bool = True
    ) -> bool:
        """Write content to file."""
        path = Path(path).expanduser().resolve()
        
        if not self._check_sandbox(path):
            raise PermissionError(f"Path outside sandbox: {path}")
        
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        
        is_binary = isinstance(content, bytes)
        mode = "wb" if is_binary else "w"
        encoding = None if is_binary else "utf-8"
        
        with open(path, mode, encoding=encoding) as f:
            f.write(content)
        
        return True
    
    def append_file(
        self,
        path: Union[str, Path],
        content: str
    ) -> bool:
        """Append content to file."""
        path = Path(path).expanduser().resolve()
        
        if not self._check_sandbox(path):
            raise PermissionError(f"Path outside sandbox: {path}")
        
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        
        return True
    
    def delete_file(self, path: Union[str, Path]) -> bool:
        """Delete a file."""
        path = Path(path).expanduser().resolve()
        
        if not self._check_sandbox(path):
            raise PermissionError(f"Path outside sandbox: {path}")
        
        if path.exists():
            path.unlink()
            return True
        return False
    
    def create_directory(
        self,
        path: Union[str, Path],
        parents: bool = True
    ) -> bool:
        """Create a directory."""
        path = Path(path).expanduser().resolve()
        
        if not self._check_sandbox(path):
            raise PermissionError(f"Path outside sandbox: {path}")
        
        path.mkdir(parents=parents, exist_ok=True)
        return True
    
    def delete_directory(
        self,
        path: Union[str, Path],
        recursive: bool = False
    ) -> bool:
        """Delete a directory."""
        path = Path(path).expanduser().resolve()
        
        if not self._check_sandbox(path):
            raise PermissionError(f"Path outside sandbox: {path}")
        
        if not path.exists():
            return False
        
        if recursive:
            shutil.rmtree(path)
        else:
            path.rmdir()
        
        return True
    
    def copy(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
        recursive: bool = True
    ) -> bool:
        """Copy file or directory."""
        src = Path(src).expanduser().resolve()
        dst = Path(dst).expanduser().resolve()
        
        if not self._check_sandbox(src) or not self._check_sandbox(dst):
            raise PermissionError("Path outside sandbox")
        
        if src.is_file():
            shutil.copy2(src, dst)
        elif src.is_dir() and recursive:
            shutil.copytree(src, dst)
        else:
            return False
        
        return True
    
    def move(
        self,
        src: Union[str, Path],
        dst: Union[str, Path]
    ) -> bool:
        """Move file or directory."""
        src = Path(src).expanduser().resolve()
        dst = Path(dst).expanduser().resolve()
        
        if not self._check_sandbox(src) or not self._check_sandbox(dst):
            raise PermissionError("Path outside sandbox")
        
        shutil.move(str(src), str(dst))
        return True
    
    def search(
        self,
        directory: Union[str, Path],
        pattern: str,
        recursive: bool = True,
        content_match: str = None
    ) -> List[FileInfo]:
        """Search for files matching pattern."""
        results = self.list_directory(directory, pattern, recursive)
        
        if content_match:
            filtered = []
            for f in results:
                if f.is_file:
                    try:
                        content = self.read_file(f.path)
                        if content_match in content:
                            filtered.append(f)
                    except:
                        pass
            return filtered
        
        return results
    
    def get_file_info(self, path: Union[str, Path]) -> FileInfo:
        """Get detailed file information."""
        path = Path(path).expanduser().resolve()
        
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        stat = path.stat()
        return FileInfo(
            path=path,
            name=path.name,
            is_file=path.is_file(),
            is_directory=path.is_dir(),
            size=stat.st_size if path.is_file() else 0,
            created=datetime.fromtimestamp(stat.st_ctime),
            modified=datetime.fromtimestamp(stat.st_mtime),
            accessed=datetime.fromtimestamp(stat.st_atime),
            extension=path.suffix,
            permissions=oct(stat.st_mode)[-3:]
        )


# ============================================================================
# PROCESS CONTROLLER
# ============================================================================

class ProcessController:
    """
    Process management and control.
    
    Provides:
    - Process listing
    - Process launching
    - Process termination
    - Resource monitoring
    """
    
    def __init__(self):
        self._processes: Dict[int, subprocess.Popen] = {}
    
    def list_processes(
        self,
        filter_name: str = None
    ) -> List[ProcessInfo]:
        """List running processes."""
        processes = []
        
        try:
            if CURRENT_PLATFORM == Platform.MACOS or CURRENT_PLATFORM == Platform.LINUX:
                # Use ps command
                result = subprocess.run(
                    ["ps", "-axo", "pid,comm,%cpu,%mem,ppid"],
                    capture_output=True,
                    text=True
                )
                
                lines = result.stdout.strip().split("\n")[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = int(parts[0])
                        name = parts[1]
                        cpu = float(parts[2]) if parts[2].replace(".", "").isdigit() else 0.0
                        mem = float(parts[3]) if parts[3].replace(".", "").isdigit() else 0.0
                        ppid = int(parts[4]) if parts[4].isdigit() else None
                        
                        if filter_name and filter_name.lower() not in name.lower():
                            continue
                        
                        processes.append(ProcessInfo(
                            pid=pid,
                            name=name,
                            cpu_percent=cpu,
                            memory_percent=mem,
                            parent_pid=ppid
                        ))
            
            elif CURRENT_PLATFORM == Platform.WINDOWS:
                result = subprocess.run(
                    ["tasklist", "/fo", "csv"],
                    capture_output=True,
                    text=True
                )
                
                lines = result.stdout.strip().split("\n")[1:]
                for line in lines:
                    # Parse CSV
                    parts = line.replace('"', '').split(",")
                    if len(parts) >= 2:
                        name = parts[0]
                        pid = int(parts[1])
                        
                        if filter_name and filter_name.lower() not in name.lower():
                            continue
                        
                        processes.append(ProcessInfo(pid=pid, name=name))
        
        except Exception as e:
            logger.error(f"Error listing processes: {e}")
        
        return processes
    
    def start_process(
        self,
        command: Union[str, List[str]],
        cwd: str = None,
        env: Dict[str, str] = None,
        background: bool = True
    ) -> ProcessInfo:
        """Start a new process."""
        if isinstance(command, str):
            command = command.split()
        
        kwargs = {
            "stdout": subprocess.PIPE if background else None,
            "stderr": subprocess.PIPE if background else None,
            "cwd": cwd,
            "env": {**os.environ, **(env or {})}
        }
        
        proc = subprocess.Popen(command, **kwargs)
        
        self._processes[proc.pid] = proc
        
        return ProcessInfo(
            pid=proc.pid,
            name=command[0],
            command=" ".join(command)
        )
    
    def stop_process(
        self,
        pid: int,
        force: bool = False
    ) -> bool:
        """Stop a process by PID."""
        try:
            import signal
            
            if force:
                os.kill(pid, signal.SIGKILL)
            else:
                os.kill(pid, signal.SIGTERM)
            
            if pid in self._processes:
                del self._processes[pid]
            
            return True
        
        except ProcessLookupError:
            return False
        except Exception as e:
            logger.error(f"Error stopping process {pid}: {e}")
            return False
    
    def run_command(
        self,
        command: Union[str, List[str]],
        timeout: int = 30,
        shell: bool = False
    ) -> Dict[str, Any]:
        """Run a command and wait for completion."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=shell
            )
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out",
                "timeout": timeout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """Get information about a specific process."""
        processes = self.list_processes()
        for p in processes:
            if p.pid == pid:
                return p
        return None


# ============================================================================
# KEYBOARD CONTROLLER
# ============================================================================

class KeyboardController:
    """
    Keyboard input control.
    
    Provides:
    - Text typing
    - Key presses
    - Hotkey combinations
    - Macro recording
    """
    
    def __init__(self):
        self._macros: Dict[str, List[Dict[str, Any]]] = {}
    
    def type_text(
        self,
        text: str,
        delay: float = 0.02
    ) -> bool:
        """Type text character by character."""
        try:
            if CURRENT_PLATFORM == Platform.MACOS:
                # Use AppleScript
                escaped = text.replace('"', '\\"').replace("\\", "\\\\")
                script = f'''
                tell application "System Events"
                    keystroke "{escaped}"
                end tell
                '''
                subprocess.run(["osascript", "-e", script], check=True)
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                # Use xdotool
                subprocess.run(["xdotool", "type", "--delay", str(int(delay * 1000)), text], check=True)
            
            elif CURRENT_PLATFORM == Platform.WINDOWS:
                # Use PowerShell
                ps_script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.SendKeys]::SendWait("{text}")
                '''
                subprocess.run(["powershell", "-Command", ps_script], check=True)
            
            return True
        
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False
    
    def press_key(self, key: Union[Key, str]) -> bool:
        """Press a single key."""
        key_str = key.value if isinstance(key, Key) else key
        
        try:
            if CURRENT_PLATFORM == Platform.MACOS:
                key_map = {
                    "enter": "return",
                    "ctrl": "control"
                }
                key_str = key_map.get(key_str, key_str)
                
                script = f'''
                tell application "System Events"
                    key code {self._get_mac_keycode(key_str)}
                end tell
                '''
                subprocess.run(["osascript", "-e", script], check=True)
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                subprocess.run(["xdotool", "key", key_str], check=True)
            
            return True
        
        except Exception as e:
            logger.error(f"Error pressing key: {e}")
            return False
    
    def _get_mac_keycode(self, key: str) -> int:
        """Get macOS key code."""
        # Simplified key code mapping
        codes = {
            "return": 36, "enter": 36,
            "tab": 48,
            "space": 49,
            "delete": 51, "backspace": 51,
            "escape": 53,
            "command": 55,
            "shift": 56,
            "capslock": 57,
            "alt": 58, "option": 58,
            "control": 59, "ctrl": 59,
            "up": 126,
            "down": 125,
            "left": 123,
            "right": 124,
            "f1": 122, "f2": 120, "f3": 99, "f4": 118,
            "f5": 96, "f6": 97, "f7": 98, "f8": 100,
            "f9": 101, "f10": 109, "f11": 103, "f12": 111
        }
        return codes.get(key.lower(), 0)
    
    def hotkey(self, *keys: Union[Key, str]) -> bool:
        """Press a key combination (hotkey)."""
        key_strs = [k.value if isinstance(k, Key) else k for k in keys]
        
        try:
            if CURRENT_PLATFORM == Platform.MACOS:
                # Build AppleScript for key combo
                modifiers = []
                regular_keys = []
                
                for k in key_strs:
                    if k.lower() in ["command", "cmd"]:
                        modifiers.append("command down")
                    elif k.lower() in ["control", "ctrl"]:
                        modifiers.append("control down")
                    elif k.lower() in ["alt", "option"]:
                        modifiers.append("option down")
                    elif k.lower() == "shift":
                        modifiers.append("shift down")
                    else:
                        regular_keys.append(k)
                
                modifier_str = ", ".join(modifiers)
                for key in regular_keys:
                    script = f'''
                    tell application "System Events"
                        keystroke "{key}" using {{{modifier_str}}}
                    end tell
                    '''
                    subprocess.run(["osascript", "-e", script], check=True)
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                combo = "+".join(key_strs)
                subprocess.run(["xdotool", "key", combo], check=True)
            
            return True
        
        except Exception as e:
            logger.error(f"Error pressing hotkey: {e}")
            return False
    
    def register_macro(
        self,
        name: str,
        actions: List[Dict[str, Any]]
    ) -> None:
        """Register a keyboard macro."""
        self._macros[name] = actions
    
    def play_macro(self, name: str) -> bool:
        """Play a registered macro."""
        if name not in self._macros:
            return False
        
        for action in self._macros[name]:
            action_type = action.get("type")
            
            if action_type == "type":
                self.type_text(action.get("text", ""))
            elif action_type == "key":
                self.press_key(action.get("key", ""))
            elif action_type == "hotkey":
                self.hotkey(*action.get("keys", []))
            elif action_type == "delay":
                time.sleep(action.get("seconds", 0.1))
        
        return True


# ============================================================================
# MOUSE CONTROLLER
# ============================================================================

class MouseController:
    """
    Mouse input control.
    
    Provides:
    - Mouse movement
    - Clicking
    - Dragging
    - Scrolling
    """
    
    def get_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        try:
            if CURRENT_PLATFORM == Platform.MACOS:
                script = '''
                use framework "Foundation"
                set pos to current application's NSEvent's mouseLocation()
                return {pos's x as integer, pos's y as integer}
                '''
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True
                )
                # Parse result
                parts = result.stdout.strip().split(", ")
                if len(parts) == 2:
                    return int(parts[0]), int(parts[1])
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                result = subprocess.run(
                    ["xdotool", "getmouselocation"],
                    capture_output=True,
                    text=True
                )
                # Parse "x:123 y:456 screen:0 window:123456"
                parts = result.stdout.strip().split()
                x = int(parts[0].split(":")[1])
                y = int(parts[1].split(":")[1])
                return x, y
        
        except Exception as e:
            logger.error(f"Error getting mouse position: {e}")
        
        return 0, 0
    
    def move_to(self, x: int, y: int, duration: float = 0) -> bool:
        """Move mouse to position."""
        try:
            if CURRENT_PLATFORM == Platform.MACOS:
                script = f'''
                tell application "System Events"
                    set mouseLocation to {{{x}, {y}}}
                end tell
                '''
                # Use cliclick for more reliable mouse control
                subprocess.run(["cliclick", f"m:{x},{y}"], check=False)
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                subprocess.run(["xdotool", "mousemove", str(x), str(y)], check=True)
            
            return True
        
        except Exception as e:
            logger.error(f"Error moving mouse: {e}")
            return False
    
    def click(
        self,
        button: MouseButton = MouseButton.LEFT,
        x: int = None,
        y: int = None,
        clicks: int = 1
    ) -> bool:
        """Click mouse button."""
        try:
            if x is not None and y is not None:
                self.move_to(x, y)
            
            button_map = {
                MouseButton.LEFT: "1",
                MouseButton.RIGHT: "2",
                MouseButton.MIDDLE: "3"
            }
            
            if CURRENT_PLATFORM == Platform.MACOS:
                click_type = "c" if button == MouseButton.LEFT else "rc" if button == MouseButton.RIGHT else "m"
                pos = self.get_position()
                for _ in range(clicks):
                    subprocess.run(["cliclick", f"{click_type}:{pos[0]},{pos[1]}"], check=False)
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                btn = button_map.get(button, "1")
                for _ in range(clicks):
                    subprocess.run(["xdotool", "click", btn], check=True)
            
            return True
        
        except Exception as e:
            logger.error(f"Error clicking: {e}")
            return False
    
    def double_click(self, x: int = None, y: int = None) -> bool:
        """Double-click."""
        return self.click(MouseButton.LEFT, x, y, clicks=2)
    
    def right_click(self, x: int = None, y: int = None) -> bool:
        """Right-click."""
        return self.click(MouseButton.RIGHT, x, y)
    
    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: MouseButton = MouseButton.LEFT
    ) -> bool:
        """Drag from one position to another."""
        try:
            if CURRENT_PLATFORM == Platform.MACOS:
                subprocess.run([
                    "cliclick",
                    f"dd:{start_x},{start_y}",
                    f"du:{end_x},{end_y}"
                ], check=False)
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                subprocess.run([
                    "xdotool",
                    "mousemove", str(start_x), str(start_y),
                    "mousedown", "1",
                    "mousemove", str(end_x), str(end_y),
                    "mouseup", "1"
                ], check=True)
            
            return True
        
        except Exception as e:
            logger.error(f"Error dragging: {e}")
            return False
    
    def scroll(
        self,
        clicks: int,
        x: int = None,
        y: int = None
    ) -> bool:
        """Scroll mouse wheel."""
        try:
            if x is not None and y is not None:
                self.move_to(x, y)
            
            if CURRENT_PLATFORM == Platform.MACOS:
                direction = "up" if clicks > 0 else "down"
                for _ in range(abs(clicks)):
                    subprocess.run(["cliclick", f"w:{direction}:1"], check=False)
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                button = "4" if clicks > 0 else "5"
                for _ in range(abs(clicks)):
                    subprocess.run(["xdotool", "click", button], check=True)
            
            return True
        
        except Exception as e:
            logger.error(f"Error scrolling: {e}")
            return False


# ============================================================================
# WINDOW CONTROLLER
# ============================================================================

class WindowController:
    """
    Window management and control.
    
    Provides:
    - Window listing
    - Focus control
    - Resize and move
    - Minimize/maximize
    """
    
    def list_windows(self, app_name: str = None) -> List[WindowInfo]:
        """List all windows."""
        windows = []
        
        try:
            if CURRENT_PLATFORM == Platform.MACOS:
                script = '''
                tell application "System Events"
                    set windowList to {}
                    repeat with proc in (every process whose background only is false)
                        set procName to name of proc
                        repeat with win in (every window of proc)
                            set winName to name of win
                            set winPos to position of win
                            set winSize to size of win
                            set end of windowList to {procName, winName, item 1 of winPos, item 2 of winPos, item 1 of winSize, item 2 of winSize}
                        end repeat
                    end repeat
                    return windowList
                end tell
                '''
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True
                )
                # Parse result (simplified)
                # Real implementation would properly parse the output
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                result = subprocess.run(
                    ["wmctrl", "-l", "-G"],
                    capture_output=True,
                    text=True
                )
                
                for line in result.stdout.strip().split("\n"):
                    parts = line.split()
                    if len(parts) >= 8:
                        win_id = parts[0]
                        x = int(parts[2])
                        y = int(parts[3])
                        width = int(parts[4])
                        height = int(parts[5])
                        title = " ".join(parts[7:])
                        
                        if app_name and app_name.lower() not in title.lower():
                            continue
                        
                        windows.append(WindowInfo(
                            id=win_id,
                            title=title,
                            app_name=parts[6],
                            x=x,
                            y=y,
                            width=width,
                            height=height
                        ))
        
        except Exception as e:
            logger.error(f"Error listing windows: {e}")
        
        return windows
    
    def focus_window(self, window_id: str = None, app_name: str = None) -> bool:
        """Focus a window."""
        try:
            if CURRENT_PLATFORM == Platform.MACOS and app_name:
                script = f'''
                tell application "{app_name}"
                    activate
                end tell
                '''
                subprocess.run(["osascript", "-e", script], check=True)
                return True
            
            elif CURRENT_PLATFORM == Platform.LINUX and window_id:
                subprocess.run(["wmctrl", "-i", "-a", window_id], check=True)
                return True
        
        except Exception as e:
            logger.error(f"Error focusing window: {e}")
        
        return False
    
    def move_window(
        self,
        window_id: str,
        x: int,
        y: int
    ) -> bool:
        """Move a window."""
        try:
            if CURRENT_PLATFORM == Platform.LINUX:
                subprocess.run([
                    "wmctrl", "-i", "-r", window_id,
                    "-e", f"0,{x},{y},-1,-1"
                ], check=True)
                return True
        
        except Exception as e:
            logger.error(f"Error moving window: {e}")
        
        return False
    
    def resize_window(
        self,
        window_id: str,
        width: int,
        height: int
    ) -> bool:
        """Resize a window."""
        try:
            if CURRENT_PLATFORM == Platform.LINUX:
                subprocess.run([
                    "wmctrl", "-i", "-r", window_id,
                    "-e", f"0,-1,-1,{width},{height}"
                ], check=True)
                return True
        
        except Exception as e:
            logger.error(f"Error resizing window: {e}")
        
        return False
    
    def minimize_window(self, window_id: str = None, app_name: str = None) -> bool:
        """Minimize a window."""
        try:
            if CURRENT_PLATFORM == Platform.MACOS and app_name:
                script = f'''
                tell application "System Events"
                    tell process "{app_name}"
                        set miniaturized of window 1 to true
                    end tell
                end tell
                '''
                subprocess.run(["osascript", "-e", script], check=True)
                return True
        
        except Exception as e:
            logger.error(f"Error minimizing window: {e}")
        
        return False


# ============================================================================
# CLIPBOARD CONTROLLER
# ============================================================================

class ClipboardController:
    """Clipboard operations."""
    
    def get_text(self) -> str:
        """Get clipboard text."""
        try:
            if CURRENT_PLATFORM == Platform.MACOS:
                result = subprocess.run(
                    ["pbpaste"],
                    capture_output=True,
                    text=True
                )
                return result.stdout
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    text=True
                )
                return result.stdout
            
            elif CURRENT_PLATFORM == Platform.WINDOWS:
                result = subprocess.run(
                    ["powershell", "Get-Clipboard"],
                    capture_output=True,
                    text=True
                )
                return result.stdout.strip()
        
        except Exception as e:
            logger.error(f"Error getting clipboard: {e}")
        
        return ""
    
    def set_text(self, text: str) -> bool:
        """Set clipboard text."""
        try:
            if CURRENT_PLATFORM == Platform.MACOS:
                subprocess.run(["pbcopy"], input=text.encode(), check=True)
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode(),
                    check=True
                )
            
            elif CURRENT_PLATFORM == Platform.WINDOWS:
                subprocess.run(
                    ["powershell", "Set-Clipboard", "-Value", text],
                    check=True
                )
            
            return True
        
        except Exception as e:
            logger.error(f"Error setting clipboard: {e}")
            return False


# ============================================================================
# SYSTEM MONITOR
# ============================================================================

class SystemMonitor:
    """System resource monitoring."""
    
    def get_system_info(self) -> SystemInfo:
        """Get current system resource usage."""
        info = SystemInfo()
        
        try:
            # CPU count
            info.cpu_count = os.cpu_count() or 1
            
            if CURRENT_PLATFORM in [Platform.MACOS, Platform.LINUX]:
                # CPU usage via top/vmstat
                result = subprocess.run(
                    ["top", "-l", "1", "-n", "0"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # Parse CPU usage
                for line in result.stdout.split("\n"):
                    if "CPU usage" in line:
                        # Extract percentage
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if "user" in p.lower() and i > 0:
                                info.cpu_percent = float(parts[i-1].replace("%", ""))
                                break
                
                # Memory via vm_stat (macOS) or free (Linux)
                if CURRENT_PLATFORM == Platform.MACOS:
                    result = subprocess.run(
                        ["vm_stat"],
                        capture_output=True,
                        text=True
                    )
                    # Parse (simplified)
                    page_size = 4096
                    for line in result.stdout.split("\n"):
                        if "Pages free" in line:
                            pages = int(line.split()[-1].replace(".", ""))
                            info.memory_available = pages * page_size
                
                # Disk via df
                result = subprocess.run(
                    ["df", "-k", "/"],
                    capture_output=True,
                    text=True
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        info.disk_total = int(parts[1]) * 1024
                        info.disk_used = int(parts[2]) * 1024
                        info.disk_free = int(parts[3]) * 1024
                        info.disk_percent = (info.disk_used / info.disk_total) * 100
        
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
        
        return info
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds."""
        try:
            if CURRENT_PLATFORM == Platform.MACOS:
                result = subprocess.run(
                    ["sysctl", "-n", "kern.boottime"],
                    capture_output=True,
                    text=True
                )
                # Parse boot time
                import re
                match = re.search(r'sec = (\d+)', result.stdout)
                if match:
                    boot_time = int(match.group(1))
                    return time.time() - boot_time
            
            elif CURRENT_PLATFORM == Platform.LINUX:
                with open("/proc/uptime") as f:
                    return float(f.read().split()[0])
        
        except Exception as e:
            logger.error(f"Error getting uptime: {e}")
        
        return 0.0


# ============================================================================
# UNIFIED PC CONTROLLER
# ============================================================================

class PCController:
    """
    Unified PC Control interface.
    
    Integrates all control systems:
    - Filesystem
    - Processes
    - Keyboard
    - Mouse
    - Windows
    - Clipboard
    - System monitoring
    """
    
    def __init__(self, sandbox_paths: List[str] = None):
        self.filesystem = FilesystemController(sandbox_paths)
        self.process = ProcessController()
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
        self.window = WindowController()
        self.clipboard = ClipboardController()
        self.system = SystemMonitor()
        
        self.platform = CURRENT_PLATFORM
        
        logger.info(f"PCController initialized on {self.platform.value}")
    
    # Convenience methods
    
    def run(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Run a shell command."""
        return self.process.run_command(command, timeout=timeout, shell=True)
    
    def type(self, text: str) -> bool:
        """Type text."""
        return self.keyboard.type_text(text)
    
    def press(self, *keys) -> bool:
        """Press key(s)."""
        if len(keys) == 1:
            return self.keyboard.press_key(keys[0])
        return self.keyboard.hotkey(*keys)
    
    def click(self, x: int = None, y: int = None) -> bool:
        """Click at position."""
        return self.mouse.click(MouseButton.LEFT, x, y)
    
    def read(self, path: str) -> str:
        """Read file."""
        return self.filesystem.read_file(path)
    
    def write(self, path: str, content: str) -> bool:
        """Write file."""
        return self.filesystem.write_file(path, content)
    
    def ls(self, path: str = ".") -> List[FileInfo]:
        """List directory."""
        return self.filesystem.list_directory(path)
    
    def ps(self, name: str = None) -> List[ProcessInfo]:
        """List processes."""
        return self.process.list_processes(name)
    
    def copy(self, text: str) -> bool:
        """Copy to clipboard."""
        return self.clipboard.set_text(text)
    
    def paste(self) -> str:
        """Paste from clipboard."""
        return self.clipboard.get_text()
    
    def info(self) -> SystemInfo:
        """Get system info."""
        return self.system.get_system_info()
    
    def open_app(self, app_name: str) -> bool:
        """Open an application."""
        try:
            if self.platform == Platform.MACOS:
                subprocess.run(["open", "-a", app_name], check=True)
            elif self.platform == Platform.LINUX:
                subprocess.Popen([app_name])
            elif self.platform == Platform.WINDOWS:
                subprocess.Popen(["start", app_name], shell=True)
            return True
        except Exception as e:
            logger.error(f"Error opening app: {e}")
            return False
    
    def focus_app(self, app_name: str) -> bool:
        """Focus an application."""
        return self.window.focus_window(app_name=app_name)
    
    def screenshot(self, path: str = None) -> str:
        """Take a screenshot."""
        if path is None:
            path = f"/tmp/screenshot_{int(time.time())}.png"
        
        try:
            if self.platform == Platform.MACOS:
                subprocess.run(["screencapture", "-x", path], check=True)
            elif self.platform == Platform.LINUX:
                subprocess.run(["scrot", path], check=True)
            return path
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return ""


# ============================================================================
# SINGLETON
# ============================================================================

_pc_controller: Optional[PCController] = None


def get_pc_controller(sandbox_paths: List[str] = None) -> PCController:
    """Get the global PC controller."""
    global _pc_controller
    if _pc_controller is None:
        _pc_controller = PCController(sandbox_paths)
    return _pc_controller


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate PC control capabilities."""
    print("=" * 60)
    print("UNIVERSAL PC CONTROL SYSTEM")
    print("=" * 60)
    
    pc = get_pc_controller()
    
    print(f"\nPlatform: {pc.platform.value}")
    
    # System info
    print("\n--- System Info ---")
    info = pc.info()
    print(json.dumps(info.to_dict(), indent=2))
    
    # Filesystem
    print("\n--- Filesystem ---")
    files = pc.ls(".")[:5]
    for f in files:
        print(f"  {f.name} - {'DIR' if f.is_directory else f'{f.size} bytes'}")
    
    # Processes
    print("\n--- Processes (top 5) ---")
    procs = pc.ps()[:5]
    for p in procs:
        print(f"  {p.pid}: {p.name} (CPU: {p.cpu_percent}%)")
    
    # Clipboard
    print("\n--- Clipboard ---")
    pc.copy("Ba'el Universal PC Control")
    print(f"Clipboard: {pc.paste()}")
    
    print("\n" + "=" * 60)
    print("PC CONTROL DEMONSTRATION COMPLETE")


if __name__ == "__main__":
    asyncio.run(demo())
