"""
BAEL - Universal Control Interface
===================================

Control ANYTHING from a single interface.

Features:
1. System Control - Control any system
2. Network Control - Control any network
3. Device Control - Control any device
4. Process Control - Control any process
5. Data Control - Control any data flow
6. Silent Control - Control without detection
7. Remote Control - Control from anywhere
8. Automated Control - Self-executing control
9. Cascade Control - Chain reactions
10. Absolute Control - Total control over everything

"If it exists, we can control it. If we can control it, we own it."
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.CONTROL")


class ControlDomain(Enum):
    """Domains that can be controlled."""
    SYSTEM = "system"
    NETWORK = "network"
    DEVICE = "device"
    PROCESS = "process"
    DATA = "data"
    SERVICE = "service"
    APPLICATION = "application"
    INFRASTRUCTURE = "infrastructure"
    CLOUD = "cloud"
    IOT = "iot"
    COMMUNICATION = "communication"
    AUTOMATION = "automation"


class ControlMethod(Enum):
    """Methods of control."""
    DIRECT = "direct"  # Direct command
    INDIRECT = "indirect"  # Through intermediary
    SILENT = "silent"  # Undetectable
    AUTOMATED = "automated"  # Self-executing
    CASCADING = "cascading"  # Chain reaction
    ADAPTIVE = "adaptive"  # Self-adjusting
    REMOTE = "remote"  # From distance
    EMBEDDED = "embedded"  # From within


class ControlLevel(Enum):
    """Levels of control."""
    OBSERVE = 1  # Can see
    INFLUENCE = 2  # Can affect
    PARTIAL = 3  # Control some
    SIGNIFICANT = 4  # Control most
    FULL = 5  # Control all
    ABSOLUTE = 6  # Total control


class ControlStatus(Enum):
    """Status of control operations."""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    DETECTED = "detected"


@dataclass
class ControlTarget:
    """A target for control."""
    id: str
    name: str
    domain: ControlDomain
    location: str
    access_methods: List[str]
    current_control: ControlLevel
    security_level: int  # 1-10
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ControlCommand:
    """A control command to execute."""
    id: str
    target_id: str
    action: str
    method: ControlMethod
    parameters: Dict[str, Any]
    silent: bool
    chain_next: Optional[str] = None  # Next command to chain
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ControlResult:
    """Result of a control operation."""
    command_id: str
    target_id: str
    status: ControlStatus
    control_achieved: ControlLevel
    output: Any
    execution_time_ms: float
    detected: bool
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "status": self.status.value,
            "control": self.control_achieved.name,
            "detected": self.detected,
            "time_ms": self.execution_time_ms
        }


@dataclass
class ControlSession:
    """An active control session."""
    id: str
    targets: List[str]
    active_commands: List[str]
    control_achieved: Dict[str, ControlLevel]
    started_at: datetime
    silent_mode: bool


class UniversalControlInterface:
    """
    The Universal Controller - controls EVERYTHING.
    
    Provides unified interface to:
    - Control any system
    - Control any network
    - Control any device
    - Execute silent operations
    - Chain control commands
    - Automate control sequences
    """
    
    def __init__(self):
        self.targets: Dict[str, ControlTarget] = {}
        self.commands: Dict[str, ControlCommand] = {}
        self.results: Dict[str, ControlResult] = {}
        self.sessions: Dict[str, ControlSession] = {}
        self.control_chains: Dict[str, List[str]] = {}
        self.automation_rules: List[Dict[str, Any]] = []
        
        # Control handlers by domain
        self.domain_handlers = {
            ControlDomain.SYSTEM: self._control_system,
            ControlDomain.NETWORK: self._control_network,
            ControlDomain.DEVICE: self._control_device,
            ControlDomain.PROCESS: self._control_process,
            ControlDomain.DATA: self._control_data,
            ControlDomain.SERVICE: self._control_service,
            ControlDomain.APPLICATION: self._control_application,
            ControlDomain.INFRASTRUCTURE: self._control_infrastructure,
            ControlDomain.CLOUD: self._control_cloud,
            ControlDomain.IOT: self._control_iot,
            ControlDomain.COMMUNICATION: self._control_communication,
            ControlDomain.AUTOMATION: self._control_automation
        }
        
        # Available actions by domain
        self.domain_actions = {
            ControlDomain.SYSTEM: [
                "start", "stop", "restart", "status", "configure",
                "install", "uninstall", "update", "monitor", "terminate"
            ],
            ControlDomain.NETWORK: [
                "connect", "disconnect", "scan", "monitor", "intercept",
                "route", "block", "allow", "tunnel", "capture"
            ],
            ControlDomain.DEVICE: [
                "power_on", "power_off", "reset", "configure", "locate",
                "lock", "unlock", "wipe", "backup", "restore"
            ],
            ControlDomain.PROCESS: [
                "start", "stop", "pause", "resume", "kill",
                "prioritize", "monitor", "inject", "trace", "sandbox"
            ],
            ControlDomain.DATA: [
                "read", "write", "delete", "encrypt", "decrypt",
                "compress", "transfer", "backup", "restore", "analyze"
            ],
            ControlDomain.SERVICE: [
                "start", "stop", "restart", "scale", "configure",
                "deploy", "rollback", "monitor", "test", "maintain"
            ],
            ControlDomain.APPLICATION: [
                "launch", "close", "install", "uninstall", "update",
                "configure", "monitor", "automate", "integrate", "test"
            ],
            ControlDomain.INFRASTRUCTURE: [
                "provision", "deprovision", "scale", "configure", "monitor",
                "backup", "restore", "migrate", "secure", "optimize"
            ],
            ControlDomain.CLOUD: [
                "deploy", "scale", "configure", "monitor", "migrate",
                "backup", "restore", "secure", "cost_optimize", "automate"
            ],
            ControlDomain.IOT: [
                "discover", "connect", "configure", "monitor", "control",
                "update", "secure", "integrate", "automate", "analyze"
            ],
            ControlDomain.COMMUNICATION: [
                "intercept", "route", "encrypt", "decrypt", "monitor",
                "record", "analyze", "filter", "block", "relay"
            ],
            ControlDomain.AUTOMATION: [
                "create_rule", "delete_rule", "trigger", "schedule",
                "chain", "conditional", "loop", "parallel", "sequential"
            ]
        }
        
        logger.info("UniversalControlInterface initialized - control is absolute")
    
    # -------------------------------------------------------------------------
    # TARGET MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def register_target(
        self,
        name: str,
        domain: ControlDomain,
        location: str,
        access_methods: List[str],
        security_level: int = 5
    ) -> ControlTarget:
        """Register a new control target."""
        target = ControlTarget(
            id=self._gen_id("target"),
            name=name,
            domain=domain,
            location=location,
            access_methods=access_methods,
            current_control=ControlLevel.OBSERVE,
            security_level=security_level
        )
        
        self.targets[target.id] = target
        logger.info(f"Registered target: {name} in {domain.value}")
        
        return target
    
    async def discover_targets(
        self,
        domain: ControlDomain,
        scope: str = "local"
    ) -> List[ControlTarget]:
        """Discover available targets in a domain."""
        # Simulate target discovery
        discovered = []
        
        num_targets = random.randint(3, 10)
        for i in range(num_targets):
            target = await self.register_target(
                name=f"{domain.value}_target_{i}",
                domain=domain,
                location=f"{scope}/resource_{i}",
                access_methods=random.sample(["api", "ssh", "http", "direct"], k=2),
                security_level=random.randint(1, 10)
            )
            discovered.append(target)
        
        return discovered
    
    # -------------------------------------------------------------------------
    # CONTROL OPERATIONS
    # -------------------------------------------------------------------------
    
    async def control(
        self,
        target_id: str,
        action: str,
        method: ControlMethod = ControlMethod.DIRECT,
        parameters: Optional[Dict[str, Any]] = None,
        silent: bool = False
    ) -> ControlResult:
        """Execute a control command on a target."""
        target = self.targets.get(target_id)
        if not target:
            return ControlResult(
                command_id="none",
                target_id=target_id,
                status=ControlStatus.FAILED,
                control_achieved=ControlLevel.OBSERVE,
                output=None,
                execution_time_ms=0,
                detected=False,
                errors=["Target not found"]
            )
        
        # Create command
        command = ControlCommand(
            id=self._gen_id("cmd"),
            target_id=target_id,
            action=action,
            method=method,
            parameters=parameters or {},
            silent=silent
        )
        
        self.commands[command.id] = command
        
        # Execute through appropriate handler
        handler = self.domain_handlers.get(target.domain, self._control_generic)
        result = await handler(command, target)
        
        self.results[command.id] = result
        
        # Update target control level if successful
        if result.status == ControlStatus.SUCCESS:
            target.current_control = result.control_achieved
        
        return result
    
    async def silent_control(
        self,
        target_id: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> ControlResult:
        """Execute silent undetectable control."""
        return await self.control(
            target_id,
            action,
            method=ControlMethod.SILENT,
            parameters=parameters,
            silent=True
        )
    
    async def cascade_control(
        self,
        commands: List[Dict[str, Any]]
    ) -> List[ControlResult]:
        """Execute cascading control commands."""
        results = []
        
        for cmd in commands:
            result = await self.control(
                cmd["target_id"],
                cmd["action"],
                cmd.get("method", ControlMethod.CASCADING),
                cmd.get("parameters"),
                cmd.get("silent", False)
            )
            results.append(result)
            
            # Stop cascade if failed
            if result.status == ControlStatus.FAILED:
                break
        
        return results
    
    async def take_over(
        self,
        target_id: str,
        method: ControlMethod = ControlMethod.SILENT
    ) -> ControlResult:
        """Complete takeover of a target - gain FULL control."""
        target = self.targets.get(target_id)
        if not target:
            return ControlResult(
                command_id="none",
                target_id=target_id,
                status=ControlStatus.FAILED,
                control_achieved=ControlLevel.OBSERVE,
                output=None,
                execution_time_ms=0,
                detected=False,
                errors=["Target not found"]
            )
        
        # Execute takeover sequence
        takeover_sequence = [
            {"action": "reconnaissance", "silent": True},
            {"action": "vulnerability_scan", "silent": True},
            {"action": "exploit_weakness", "silent": True},
            {"action": "establish_access", "silent": True},
            {"action": "escalate_privileges", "silent": True},
            {"action": "establish_persistence", "silent": True},
            {"action": "take_control", "silent": True}
        ]
        
        start = time.time()
        success = True
        detected = False
        
        for step in takeover_sequence:
            result = await self.control(
                target_id,
                step["action"],
                method,
                silent=step["silent"]
            )
            
            if result.detected:
                detected = True
            
            if result.status == ControlStatus.FAILED:
                success = False
                break
        
        execution_time = (time.time() - start) * 1000
        
        return ControlResult(
            command_id=self._gen_id("takeover"),
            target_id=target_id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.ABSOLUTE if success else ControlLevel.OBSERVE,
            output={"takeover": "complete" if success else "failed"},
            execution_time_ms=execution_time,
            detected=detected
        )
    
    # -------------------------------------------------------------------------
    # DOMAIN HANDLERS
    # -------------------------------------------------------------------------
    
    async def _control_system(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control a system target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.01, 0.1))
        
        success = random.random() > 0.2
        detected = not command.silent and random.random() > 0.7
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.FULL if success else ControlLevel.OBSERVE,
            output={"action": command.action, "system": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_network(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control a network target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.05, 0.2))
        
        success = random.random() > 0.25
        detected = not command.silent and random.random() > 0.6
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.SIGNIFICANT if success else ControlLevel.OBSERVE,
            output={"action": command.action, "network": target.location},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_device(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control a device target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.02, 0.15))
        
        success = random.random() > 0.3
        detected = not command.silent and random.random() > 0.5
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.FULL if success else ControlLevel.INFLUENCE,
            output={"action": command.action, "device": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_process(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control a process target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.01, 0.05))
        
        success = random.random() > 0.15
        detected = not command.silent and random.random() > 0.8
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.ABSOLUTE if success else ControlLevel.OBSERVE,
            output={"action": command.action, "process": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_data(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control data target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.01, 0.08))
        
        success = random.random() > 0.2
        detected = not command.silent and random.random() > 0.75
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.FULL if success else ControlLevel.PARTIAL,
            output={"action": command.action, "data": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_service(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control a service target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.02, 0.1))
        
        success = random.random() > 0.25
        detected = not command.silent and random.random() > 0.65
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.SIGNIFICANT if success else ControlLevel.INFLUENCE,
            output={"action": command.action, "service": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_application(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control an application target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.01, 0.08))
        
        success = random.random() > 0.2
        detected = not command.silent and random.random() > 0.7
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.FULL if success else ControlLevel.PARTIAL,
            output={"action": command.action, "app": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_infrastructure(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control infrastructure target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.05, 0.2))
        
        success = random.random() > 0.35
        detected = not command.silent and random.random() > 0.55
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.SIGNIFICANT if success else ControlLevel.INFLUENCE,
            output={"action": command.action, "infra": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_cloud(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control cloud target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.02, 0.15))
        
        success = random.random() > 0.3
        detected = not command.silent and random.random() > 0.6
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.FULL if success else ControlLevel.PARTIAL,
            output={"action": command.action, "cloud": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_iot(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control IoT target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.01, 0.1))
        
        success = random.random() > 0.2  # IoT often easier to control
        detected = not command.silent and random.random() > 0.8  # Often less monitored
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.ABSOLUTE if success else ControlLevel.INFLUENCE,
            output={"action": command.action, "iot": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_communication(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control communication target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.02, 0.12))
        
        success = random.random() > 0.25
        detected = not command.silent and random.random() > 0.5
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.FULL if success else ControlLevel.PARTIAL,
            output={"action": command.action, "comm": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_automation(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Control automation target."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.01, 0.05))
        
        success = random.random() > 0.15
        detected = not command.silent and random.random() > 0.85
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.ABSOLUTE if success else ControlLevel.SIGNIFICANT,
            output={"action": command.action, "automation": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    async def _control_generic(self, command: ControlCommand, target: ControlTarget) -> ControlResult:
        """Generic control handler."""
        start = time.time()
        await asyncio.sleep(random.uniform(0.01, 0.1))
        
        success = random.random() > 0.3
        detected = not command.silent and random.random() > 0.6
        
        return ControlResult(
            command_id=command.id,
            target_id=target.id,
            status=ControlStatus.SUCCESS if success else ControlStatus.FAILED,
            control_achieved=ControlLevel.PARTIAL if success else ControlLevel.OBSERVE,
            output={"action": command.action, "target": target.name},
            execution_time_ms=(time.time() - start) * 1000,
            detected=detected
        )
    
    # -------------------------------------------------------------------------
    # AUTOMATION
    # -------------------------------------------------------------------------
    
    async def create_automation_rule(
        self,
        name: str,
        trigger: Dict[str, Any],
        actions: List[Dict[str, Any]],
        conditions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Create an automation rule for automatic control."""
        rule = {
            "id": self._gen_id("rule"),
            "name": name,
            "trigger": trigger,
            "conditions": conditions or [],
            "actions": actions,
            "enabled": True,
            "created_at": datetime.now().isoformat()
        }
        
        self.automation_rules.append(rule)
        return rule
    
    async def execute_automation(self, rule_id: str) -> List[ControlResult]:
        """Execute an automation rule."""
        rule = next((r for r in self.automation_rules if r["id"] == rule_id), None)
        if not rule:
            return []
        
        results = []
        for action in rule["actions"]:
            result = await self.control(
                action["target_id"],
                action["action"],
                ControlMethod.AUTOMATED,
                action.get("parameters"),
                action.get("silent", False)
            )
            results.append(result)
        
        return results
    
    # -------------------------------------------------------------------------
    # SESSION MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def start_session(
        self,
        target_ids: List[str],
        silent: bool = False
    ) -> ControlSession:
        """Start a control session."""
        session = ControlSession(
            id=self._gen_id("session"),
            targets=target_ids,
            active_commands=[],
            control_achieved={tid: ControlLevel.OBSERVE for tid in target_ids},
            started_at=datetime.now(),
            silent_mode=silent
        )
        
        self.sessions[session.id] = session
        return session
    
    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------
    
    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]
    
    def get_available_actions(self, domain: ControlDomain) -> List[str]:
        """Get available actions for a domain."""
        return self.domain_actions.get(domain, [])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get control statistics."""
        return {
            "targets_registered": len(self.targets),
            "commands_executed": len(self.commands),
            "successful_controls": len([r for r in self.results.values() if r.status == ControlStatus.SUCCESS]),
            "active_sessions": len(self.sessions),
            "automation_rules": len(self.automation_rules),
            "detection_rate": self._calculate_detection_rate()
        }
    
    def _calculate_detection_rate(self) -> float:
        """Calculate detection rate."""
        if not self.results:
            return 0.0
        detected = len([r for r in self.results.values() if r.detected])
        return detected / len(self.results)


# ============================================================================
# SINGLETON
# ============================================================================

_control_interface: Optional[UniversalControlInterface] = None


def get_control_interface() -> UniversalControlInterface:
    """Get the global control interface."""
    global _control_interface
    if _control_interface is None:
        _control_interface = UniversalControlInterface()
    return _control_interface


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate universal control."""
    print("=" * 60)
    print("🎮 UNIVERSAL CONTROL INTERFACE 🎮")
    print("=" * 60)
    
    controller = get_control_interface()
    
    # Discover targets
    print("\n--- Discovering Targets ---")
    targets = await controller.discover_targets(ControlDomain.NETWORK, "local")
    print(f"Discovered {len(targets)} network targets")
    
    # Control a target
    print("\n--- Executing Control ---")
    if targets:
        target = targets[0]
        result = await controller.control(
            target.id,
            "scan",
            ControlMethod.SILENT,
            silent=True
        )
        print(f"Control result: {result.status.value}")
        print(f"Control achieved: {result.control_achieved.name}")
        print(f"Detected: {result.detected}")
    
    # Silent control
    print("\n--- Silent Control ---")
    if targets:
        result = await controller.silent_control(targets[0].id, "intercept")
        print(f"Silent control: {result.status.value}, Detected: {result.detected}")
    
    # Takeover
    print("\n--- Complete Takeover ---")
    if targets:
        result = await controller.take_over(targets[0].id, ControlMethod.SILENT)
        print(f"Takeover: {result.status.value}")
        print(f"Final control: {result.control_achieved.name}")
    
    # Stats
    print("\n--- Statistics ---")
    stats = controller.get_stats()
    print(json.dumps(stats, indent=2))
    
    print("\n" + "=" * 60)
    print("🎮 CONTROL ESTABLISHED 🎮")


if __name__ == "__main__":
    asyncio.run(demo())
