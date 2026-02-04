"""
BAEL - Remote System Domination Engine
======================================

INFILTRATE. CONTROL. DOMINATE. OWN.

Complete remote system takeover capabilities:
- Remote code execution
- Reverse shell management
- Remote desktop control
- File system manipulation
- Process control
- Service manipulation
- Registry/config control
- Network pivoting
- Persistence mechanisms
- Full system takeover

"Every connected system belongs to Ba'el."
"""

import asyncio
import base64
import hashlib
import logging
import random
import socket
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.REMOTE")


class SystemType(Enum):
    """Types of systems."""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    BSD = "bsd"
    IOS = "ios"
    ANDROID = "android"
    EMBEDDED = "embedded"
    IOT = "iot"
    NETWORK = "network"
    CLOUD = "cloud"


class AccessLevel(Enum):
    """Access levels."""
    NONE = 0
    USER = 1
    ELEVATED = 2
    ADMIN = 3
    SYSTEM = 4
    ROOT = 5
    KERNEL = 6
    HYPERVISOR = 7


class ConnectionType(Enum):
    """Connection types."""
    REVERSE_SHELL = "reverse_shell"
    BIND_SHELL = "bind_shell"
    SSH = "ssh"
    RDP = "rdp"
    VNC = "vnc"
    WINRM = "winrm"
    PSRemoting = "ps_remoting"
    SMB = "smb"
    HTTP_C2 = "http_c2"
    DNS_C2 = "dns_c2"


class PersistenceMethod(Enum):
    """Persistence methods."""
    STARTUP = "startup"
    SERVICE = "service"
    SCHEDULED_TASK = "scheduled_task"
    REGISTRY = "registry"
    CRON = "cron"
    SYSTEMD = "systemd"
    LAUNCHD = "launchd"
    BOOTKIT = "bootkit"
    FIRMWARE = "firmware"
    IMPLANT = "implant"


class ExfiltrationMethod(Enum):
    """Data exfiltration methods."""
    HTTP = "http"
    HTTPS = "https"
    DNS = "dns"
    ICMP = "icmp"
    SMTP = "smtp"
    FTP = "ftp"
    CLOUD_STORAGE = "cloud_storage"
    STEGANOGRAPHY = "steganography"


@dataclass
class RemoteSystem:
    """A compromised remote system."""
    id: str
    hostname: str
    ip_address: str
    system_type: SystemType
    os_version: str
    access_level: AccessLevel
    connection_type: ConnectionType
    first_access: datetime
    last_seen: datetime
    is_active: bool
    persistence: List[str] = field(default_factory=list)
    credentials: Dict[str, str] = field(default_factory=dict)


@dataclass
class RemoteSession:
    """An active remote session."""
    id: str
    system_id: str
    connection_type: ConnectionType
    established: datetime
    last_activity: datetime
    is_encrypted: bool
    is_active: bool
    commands_executed: int


@dataclass
class RemoteCommand:
    """A remote command execution."""
    id: str
    system_id: str
    session_id: str
    command: str
    executed_at: datetime
    output: str
    exit_code: int
    success: bool


@dataclass
class FileOperation:
    """A remote file operation."""
    id: str
    system_id: str
    operation: str  # upload, download, delete, modify
    local_path: str
    remote_path: str
    size: int
    timestamp: datetime
    success: bool


@dataclass
class PersistenceImplant:
    """A persistence implant."""
    id: str
    system_id: str
    method: PersistenceMethod
    location: str
    installed: datetime
    last_callback: datetime
    is_active: bool
    stealth_level: int


class RemoteSystemDominationEngine:
    """
    The remote system domination engine.

    Provides complete remote control:
    - System compromise
    - Command execution
    - File operations
    - Persistence
    - Lateral movement
    """

    def __init__(self):
        self.systems: Dict[str, RemoteSystem] = {}
        self.sessions: Dict[str, RemoteSession] = {}
        self.commands: Dict[str, RemoteCommand] = {}
        self.file_ops: Dict[str, FileOperation] = {}
        self.implants: Dict[str, PersistenceImplant] = {}

        self.total_systems = 0
        self.active_sessions = 0

        logger.info("RemoteSystemDominationEngine initialized - TOTAL CONTROL")

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    # =========================================================================
    # SYSTEM COMPROMISE
    # =========================================================================

    async def compromise_system(
        self,
        ip_address: str,
        exploit_used: str = "auto"
    ) -> RemoteSystem:
        """Compromise a remote system."""
        # Simulated system fingerprinting
        system_types = [
            (SystemType.WINDOWS, "Windows Server 2022", 0.4),
            (SystemType.LINUX, "Ubuntu 22.04", 0.35),
            (SystemType.MACOS, "macOS Ventura", 0.1),
            (SystemType.NETWORK, "Cisco IOS 15.x", 0.1),
            (SystemType.IOT, "Custom Linux", 0.05)
        ]

        rand = random.random()
        cumulative = 0
        system_type = SystemType.LINUX
        os_version = "Unknown"

        for st, ver, prob in system_types:
            cumulative += prob
            if rand <= cumulative:
                system_type = st
                os_version = ver
                break

        # Determine initial access level
        initial_access = random.choice([
            AccessLevel.USER,
            AccessLevel.ELEVATED,
            AccessLevel.ADMIN
        ])

        system = RemoteSystem(
            id=self._gen_id("sys"),
            hostname=f"host-{ip_address.replace('.', '-')}",
            ip_address=ip_address,
            system_type=system_type,
            os_version=os_version,
            access_level=initial_access,
            connection_type=ConnectionType.REVERSE_SHELL,
            first_access=datetime.now(),
            last_seen=datetime.now(),
            is_active=True
        )

        self.systems[system.id] = system
        self.total_systems += 1

        logger.info(f"System compromised: {system.hostname} ({system.access_level.name})")

        return system

    async def mass_compromise(
        self,
        ip_range: str,
        count: int = 10
    ) -> List[RemoteSystem]:
        """Compromise multiple systems in a range."""
        systems = []

        # Parse IP range (simplified)
        base_ip = ".".join(ip_range.split(".")[:3])

        for i in range(count):
            ip = f"{base_ip}.{random.randint(1, 254)}"

            try:
                system = await self.compromise_system(ip)
                systems.append(system)
            except Exception as e:
                logger.warning(f"Failed to compromise {ip}: {e}")

        return systems

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    async def establish_session(
        self,
        system_id: str,
        connection_type: ConnectionType = ConnectionType.REVERSE_SHELL
    ) -> RemoteSession:
        """Establish a remote session."""
        system = self.systems.get(system_id)
        if not system:
            raise ValueError("System not found")

        session = RemoteSession(
            id=self._gen_id("sess"),
            system_id=system_id,
            connection_type=connection_type,
            established=datetime.now(),
            last_activity=datetime.now(),
            is_encrypted=True,
            is_active=True,
            commands_executed=0
        )

        self.sessions[session.id] = session
        self.active_sessions += 1

        logger.info(f"Session established: {session.id} to {system.hostname}")

        return session

    async def get_active_sessions(self) -> List[RemoteSession]:
        """Get all active sessions."""
        return [s for s in self.sessions.values() if s.is_active]

    async def close_session(self, session_id: str) -> bool:
        """Close a remote session."""
        session = self.sessions.get(session_id)
        if session:
            session.is_active = False
            self.active_sessions -= 1
            return True
        return False

    # =========================================================================
    # COMMAND EXECUTION
    # =========================================================================

    async def execute_command(
        self,
        system_id: str,
        command: str
    ) -> RemoteCommand:
        """Execute a command on a remote system."""
        system = self.systems.get(system_id)
        if not system:
            raise ValueError("System not found")

        # Find or create session
        sessions = [s for s in self.sessions.values()
                   if s.system_id == system_id and s.is_active]

        if sessions:
            session = sessions[0]
        else:
            session = await self.establish_session(system_id)

        # Simulate command execution
        output = self._simulate_command_output(system, command)

        cmd = RemoteCommand(
            id=self._gen_id("cmd"),
            system_id=system_id,
            session_id=session.id,
            command=command,
            executed_at=datetime.now(),
            output=output,
            exit_code=0,
            success=True
        )

        self.commands[cmd.id] = cmd
        session.commands_executed += 1
        session.last_activity = datetime.now()
        system.last_seen = datetime.now()

        return cmd

    def _simulate_command_output(
        self,
        system: RemoteSystem,
        command: str
    ) -> str:
        """Simulate command output based on system type."""
        cmd_lower = command.lower()

        if "whoami" in cmd_lower:
            if system.access_level.value >= AccessLevel.ROOT.value:
                return "root" if system.system_type != SystemType.WINDOWS else "NT AUTHORITY\\SYSTEM"
            return "user"

        if "hostname" in cmd_lower:
            return system.hostname

        if "ifconfig" in cmd_lower or "ipconfig" in cmd_lower:
            return f"eth0: {system.ip_address}\n"

        if "uname" in cmd_lower:
            return f"Linux {system.hostname} 5.15.0-generic"

        if "pwd" in cmd_lower:
            return "/home/user"

        if "dir" in cmd_lower or "ls" in cmd_lower:
            return "file1.txt\nfile2.txt\ndocuments/\n"

        if "ps" in cmd_lower or "tasklist" in cmd_lower:
            return "PID  CMD\n1    init\n100  bash\n"

        return f"[Output of: {command}]"

    async def execute_script(
        self,
        system_id: str,
        script: str,
        script_type: str = "bash"
    ) -> RemoteCommand:
        """Execute a script on a remote system."""
        # Encode script for transport
        encoded = base64.b64encode(script.encode()).decode()

        if script_type == "bash":
            command = f"echo '{encoded}' | base64 -d | bash"
        elif script_type == "powershell":
            command = f"powershell -EncodedCommand {encoded}"
        elif script_type == "python":
            command = f"echo '{encoded}' | base64 -d | python3"
        else:
            command = script

        return await self.execute_command(system_id, command)

    async def batch_execute(
        self,
        command: str
    ) -> Dict[str, Any]:
        """Execute command on all active systems."""
        results = []

        for system in self.systems.values():
            if system.is_active:
                try:
                    result = await self.execute_command(system.id, command)
                    results.append({
                        "system": system.hostname,
                        "success": result.success,
                        "output": result.output[:200]
                    })
                except Exception as e:
                    results.append({
                        "system": system.hostname,
                        "success": False,
                        "error": str(e)
                    })

        return {
            "command": command,
            "systems_targeted": len(results),
            "successful": sum(1 for r in results if r.get("success")),
            "results": results
        }

    # =========================================================================
    # PRIVILEGE ESCALATION
    # =========================================================================

    async def escalate_privileges(
        self,
        system_id: str
    ) -> Dict[str, Any]:
        """Attempt privilege escalation."""
        system = self.systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        old_level = system.access_level

        # Escalation techniques based on system type
        techniques = {
            SystemType.LINUX: [
                "sudo_misconfiguration",
                "suid_binary",
                "kernel_exploit",
                "docker_escape",
                "cron_abuse"
            ],
            SystemType.WINDOWS: [
                "token_impersonation",
                "unquoted_service_path",
                "dll_hijacking",
                "alwaysinstallelevated",
                "printnightmare"
            ],
            SystemType.MACOS: [
                "dylib_hijacking",
                "authorization_bypass",
                "kext_exploit"
            ]
        }

        available_techniques = techniques.get(system.system_type, ["generic_exploit"])
        used_technique = random.choice(available_techniques)

        # Simulate escalation attempt
        success_rate = 0.6 if system.access_level.value < AccessLevel.ADMIN.value else 0.3
        success = random.random() < success_rate

        if success:
            # Escalate one or more levels
            new_level = min(
                system.access_level.value + random.randint(1, 2),
                AccessLevel.ROOT.value
            )
            system.access_level = AccessLevel(new_level)

        return {
            "success": success,
            "system": system.hostname,
            "technique": used_technique,
            "old_level": old_level.name,
            "new_level": system.access_level.name,
            "escalated": system.access_level.value > old_level.value
        }

    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================

    async def upload_file(
        self,
        system_id: str,
        local_path: str,
        remote_path: str
    ) -> FileOperation:
        """Upload a file to remote system."""
        system = self.systems.get(system_id)
        if not system:
            raise ValueError("System not found")

        # Simulated file upload
        size = random.randint(1024, 1024 * 1024)  # 1KB to 1MB

        op = FileOperation(
            id=self._gen_id("file"),
            system_id=system_id,
            operation="upload",
            local_path=local_path,
            remote_path=remote_path,
            size=size,
            timestamp=datetime.now(),
            success=True
        )

        self.file_ops[op.id] = op

        logger.info(f"File uploaded: {local_path} -> {system.hostname}:{remote_path}")

        return op

    async def download_file(
        self,
        system_id: str,
        remote_path: str,
        local_path: str
    ) -> FileOperation:
        """Download a file from remote system."""
        system = self.systems.get(system_id)
        if not system:
            raise ValueError("System not found")

        size = random.randint(1024, 10 * 1024 * 1024)

        op = FileOperation(
            id=self._gen_id("file"),
            system_id=system_id,
            operation="download",
            local_path=local_path,
            remote_path=remote_path,
            size=size,
            timestamp=datetime.now(),
            success=True
        )

        self.file_ops[op.id] = op

        logger.info(f"File downloaded: {system.hostname}:{remote_path} -> {local_path}")

        return op

    async def exfiltrate_data(
        self,
        system_id: str,
        data_type: str,
        method: ExfiltrationMethod = ExfiltrationMethod.HTTPS
    ) -> Dict[str, Any]:
        """Exfiltrate data from remote system."""
        system = self.systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        # Data collection based on type
        data_sizes = {
            "documents": random.randint(100, 1000) * 1024 * 1024,  # 100MB - 1GB
            "credentials": random.randint(1, 10) * 1024,  # 1KB - 10KB
            "database": random.randint(500, 5000) * 1024 * 1024,  # 500MB - 5GB
            "emails": random.randint(50, 500) * 1024 * 1024,  # 50MB - 500MB
            "source_code": random.randint(10, 100) * 1024 * 1024  # 10MB - 100MB
        }

        size = data_sizes.get(data_type, 1024 * 1024)

        # Simulate exfiltration
        transfer_time = size / (1024 * 1024)  # 1 second per MB

        return {
            "success": True,
            "system": system.hostname,
            "data_type": data_type,
            "size_bytes": size,
            "size_mb": size / (1024 * 1024),
            "method": method.value,
            "estimated_time_seconds": transfer_time,
            "encrypted": True
        }

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    async def install_persistence(
        self,
        system_id: str,
        method: PersistenceMethod
    ) -> PersistenceImplant:
        """Install persistence mechanism."""
        system = self.systems.get(system_id)
        if not system:
            raise ValueError("System not found")

        # Determine location based on method and system type
        locations = {
            (PersistenceMethod.STARTUP, SystemType.WINDOWS):
                "C:\\Users\\Public\\startup.exe",
            (PersistenceMethod.STARTUP, SystemType.LINUX):
                "/etc/profile.d/init.sh",
            (PersistenceMethod.SERVICE, SystemType.WINDOWS):
                "SystemUpdateService",
            (PersistenceMethod.SERVICE, SystemType.LINUX):
                "/etc/systemd/system/update.service",
            (PersistenceMethod.SCHEDULED_TASK, SystemType.WINDOWS):
                "Microsoft\\Windows\\UpdateCheck",
            (PersistenceMethod.CRON, SystemType.LINUX):
                "/etc/cron.d/update",
            (PersistenceMethod.REGISTRY, SystemType.WINDOWS):
                "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        }

        location = locations.get(
            (method, system.system_type),
            f"/tmp/.{self._gen_id('imp')}"
        )

        implant = PersistenceImplant(
            id=self._gen_id("impl"),
            system_id=system_id,
            method=method,
            location=location,
            installed=datetime.now(),
            last_callback=datetime.now(),
            is_active=True,
            stealth_level=random.randint(5, 10)
        )

        self.implants[implant.id] = implant
        system.persistence.append(method.value)

        logger.info(f"Persistence installed: {method.value} on {system.hostname}")

        return implant

    async def install_multi_persistence(
        self,
        system_id: str
    ) -> List[PersistenceImplant]:
        """Install multiple persistence mechanisms."""
        system = self.systems.get(system_id)
        if not system:
            return []

        # Select appropriate methods for system type
        methods_map = {
            SystemType.WINDOWS: [
                PersistenceMethod.STARTUP,
                PersistenceMethod.SERVICE,
                PersistenceMethod.SCHEDULED_TASK,
                PersistenceMethod.REGISTRY
            ],
            SystemType.LINUX: [
                PersistenceMethod.CRON,
                PersistenceMethod.SYSTEMD,
                PersistenceMethod.STARTUP
            ],
            SystemType.MACOS: [
                PersistenceMethod.LAUNCHD,
                PersistenceMethod.STARTUP
            ]
        }

        methods = methods_map.get(system.system_type, [PersistenceMethod.STARTUP])
        implants = []

        for method in methods[:3]:  # Max 3 persistence methods
            try:
                implant = await self.install_persistence(system_id, method)
                implants.append(implant)
            except Exception as e:
                logger.warning(f"Failed to install {method.value}: {e}")

        return implants

    # =========================================================================
    # LATERAL MOVEMENT
    # =========================================================================

    async def discover_network(
        self,
        system_id: str
    ) -> Dict[str, Any]:
        """Discover network from compromised system."""
        system = self.systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        # Simulate network discovery
        base_ip = ".".join(system.ip_address.split(".")[:3])

        discovered_hosts = []
        for i in range(random.randint(5, 20)):
            host_ip = f"{base_ip}.{random.randint(1, 254)}"
            if host_ip != system.ip_address:
                discovered_hosts.append({
                    "ip": host_ip,
                    "hostname": f"host-{i}",
                    "ports": random.sample([22, 80, 443, 445, 3389, 8080],
                                          random.randint(1, 4))
                })

        return {
            "source_system": system.hostname,
            "hosts_discovered": len(discovered_hosts),
            "hosts": discovered_hosts
        }

    async def pivot_to_system(
        self,
        source_system_id: str,
        target_ip: str
    ) -> Dict[str, Any]:
        """Pivot from one system to another."""
        source = self.systems.get(source_system_id)
        if not source:
            return {"error": "Source system not found"}

        # Attempt to compromise target through pivot
        success_rate = 0.7

        if random.random() < success_rate:
            new_system = await self.compromise_system(target_ip)

            return {
                "success": True,
                "source": source.hostname,
                "target": new_system.hostname,
                "target_id": new_system.id,
                "method": "pivot",
                "access_level": new_system.access_level.name
            }

        return {
            "success": False,
            "source": source.hostname,
            "target_ip": target_ip,
            "reason": "Pivot attempt failed"
        }

    async def spread_across_network(
        self,
        system_id: str,
        max_hops: int = 3
    ) -> Dict[str, Any]:
        """Spread across the network from a foothold."""
        initial_system = self.systems.get(system_id)
        if not initial_system:
            return {"error": "System not found"}

        compromised = [initial_system.id]
        current_systems = [system_id]

        for hop in range(max_hops):
            next_systems = []

            for sid in current_systems:
                # Discover network from each system
                network = await self.discover_network(sid)

                for host in network.get("hosts", [])[:3]:
                    if len(compromised) >= 20:  # Max 20 systems
                        break

                    result = await self.pivot_to_system(sid, host["ip"])
                    if result.get("success"):
                        new_id = result["target_id"]
                        if new_id not in compromised:
                            compromised.append(new_id)
                            next_systems.append(new_id)

            current_systems = next_systems
            if not current_systems:
                break

        return {
            "initial_system": initial_system.hostname,
            "hops_completed": min(hop + 1, max_hops),
            "systems_compromised": len(compromised),
            "system_ids": compromised
        }

    # =========================================================================
    # C2 OPERATIONS
    # =========================================================================

    async def establish_c2_channel(
        self,
        system_id: str,
        c2_type: str = "https"
    ) -> Dict[str, Any]:
        """Establish command and control channel."""
        system = self.systems.get(system_id)
        if not system:
            return {"error": "System not found"}

        c2_configs = {
            "https": {
                "protocol": "HTTPS",
                "port": 443,
                "beacon_interval": 60,
                "jitter": 30,
                "encryption": "AES-256"
            },
            "dns": {
                "protocol": "DNS",
                "port": 53,
                "beacon_interval": 300,
                "jitter": 60,
                "encryption": "XOR"
            },
            "icmp": {
                "protocol": "ICMP",
                "port": 0,
                "beacon_interval": 120,
                "jitter": 30,
                "encryption": "None"
            }
        }

        config = c2_configs.get(c2_type, c2_configs["https"])

        return {
            "success": True,
            "system": system.hostname,
            "c2_type": c2_type,
            "config": config,
            "channel_id": self._gen_id("c2")
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get domination statistics."""
        return {
            "total_systems": self.total_systems,
            "active_systems": len([s for s in self.systems.values() if s.is_active]),
            "active_sessions": self.active_sessions,
            "commands_executed": len(self.commands),
            "files_transferred": len(self.file_ops),
            "implants_installed": len(self.implants),
            "root_access_systems": len([
                s for s in self.systems.values()
                if s.access_level.value >= AccessLevel.ROOT.value
            ]),
            "systems_by_type": {
                st.value: len([s for s in self.systems.values() if s.system_type == st])
                for st in SystemType
            }
        }


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[RemoteSystemDominationEngine] = None


def get_remote_engine() -> RemoteSystemDominationEngine:
    """Get the global remote domination engine."""
    global _engine
    if _engine is None:
        _engine = RemoteSystemDominationEngine()
    return _engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate the remote system domination engine."""
    print("=" * 60)
    print("🖥️ REMOTE SYSTEM DOMINATION ENGINE 🖥️")
    print("=" * 60)

    engine = get_remote_engine()

    # Compromise systems
    print("\n--- Initial Compromise ---")
    system = await engine.compromise_system("192.168.1.100")
    print(f"Compromised: {system.hostname}")
    print(f"Type: {system.system_type.value}")
    print(f"Access: {system.access_level.name}")

    # Mass compromise
    print("\n--- Mass Compromise ---")
    systems = await engine.mass_compromise("10.0.0.0/24", 5)
    print(f"Systems compromised: {len(systems)}")
    for s in systems:
        print(f"  {s.hostname}: {s.access_level.name}")

    # Command execution
    print("\n--- Command Execution ---")
    cmd = await engine.execute_command(system.id, "whoami")
    print(f"Command: {cmd.command}")
    print(f"Output: {cmd.output}")

    cmd = await engine.execute_command(system.id, "hostname")
    print(f"Command: {cmd.command}")
    print(f"Output: {cmd.output}")

    # Privilege escalation
    print("\n--- Privilege Escalation ---")
    result = await engine.escalate_privileges(system.id)
    print(f"Technique: {result['technique']}")
    print(f"Success: {result['success']}")
    print(f"Level: {result['old_level']} -> {result['new_level']}")

    # File operations
    print("\n--- File Operations ---")
    upload = await engine.upload_file(
        system.id,
        "/local/payload.exe",
        "C:\\temp\\payload.exe"
    )
    print(f"Uploaded: {upload.size} bytes")

    download = await engine.download_file(
        system.id,
        "/etc/passwd",
        "/loot/passwd"
    )
    print(f"Downloaded: {download.size} bytes")

    # Exfiltration
    print("\n--- Data Exfiltration ---")
    exfil = await engine.exfiltrate_data(system.id, "credentials")
    print(f"Data type: {exfil['data_type']}")
    print(f"Size: {exfil['size_mb']:.2f} MB")
    print(f"Method: {exfil['method']}")

    # Persistence
    print("\n--- Persistence Installation ---")
    implants = await engine.install_multi_persistence(system.id)
    print(f"Implants installed: {len(implants)}")
    for imp in implants:
        print(f"  {imp.method.value}: {imp.location}")

    # Network discovery
    print("\n--- Network Discovery ---")
    network = await engine.discover_network(system.id)
    print(f"Hosts discovered: {network['hosts_discovered']}")
    for host in network['hosts'][:5]:
        print(f"  {host['ip']}: ports {host['ports']}")

    # Lateral movement
    print("\n--- Lateral Movement ---")
    spread = await engine.spread_across_network(system.id, max_hops=2)
    print(f"Hops: {spread['hops_completed']}")
    print(f"Systems compromised: {spread['systems_compromised']}")

    # Batch command
    print("\n--- Batch Command ---")
    batch = await engine.batch_execute("whoami")
    print(f"Systems targeted: {batch['systems_targeted']}")
    print(f"Successful: {batch['successful']}")

    # C2 channel
    print("\n--- C2 Channel ---")
    c2 = await engine.establish_c2_channel(system.id, "https")
    print(f"Protocol: {c2['config']['protocol']}")
    print(f"Beacon: {c2['config']['beacon_interval']}s")
    print(f"Encryption: {c2['config']['encryption']}")

    # Stats
    print("\n--- DOMINATION STATISTICS ---")
    stats = engine.get_stats()
    for k, v in stats.items():
        if isinstance(v, dict):
            print(f"{k}:")
            for kk, vv in v.items():
                if vv > 0:
                    print(f"  {kk}: {vv}")
        else:
            print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("🖥️ ALL SYSTEMS BELONG TO BA'EL 🖥️")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
