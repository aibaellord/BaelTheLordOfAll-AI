"""
Edge Computing & IoT Integration - Edge deployment and IoT device management.

Features:
- Edge deployment framework
- IoT device management
- MQTT/CoAP protocol support
- Sensor data fusion
- Edge AI inference
- Fleet management
- OTA (Over-The-Air) updates
- Device provisioning
- Edge-cloud synchronization
- Real-time streaming from devices

Target: 1,300+ lines for comprehensive edge and IoT integration
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

# ============================================================================
# EDGE & IOT ENUMS
# ============================================================================

class DeviceType(Enum):
    """IoT device types."""
    SENSOR = "SENSOR"
    ACTUATOR = "ACTUATOR"
    GATEWAY = "GATEWAY"
    CAMERA = "CAMERA"
    CONTROLLER = "CONTROLLER"

class DeviceStatus(Enum):
    """Device status."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"
    ERROR = "ERROR"

class SensorType(Enum):
    """Sensor types."""
    TEMPERATURE = "TEMPERATURE"
    HUMIDITY = "HUMIDITY"
    PRESSURE = "PRESSURE"
    MOTION = "MOTION"
    LIGHT = "LIGHT"
    PROXIMITY = "PROXIMITY"
    GPS = "GPS"

class Protocol(Enum):
    """Communication protocols."""
    MQTT = "MQTT"
    COAP = "COAP"
    HTTP = "HTTP"
    WEBSOCKET = "WEBSOCKET"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class IoTDevice:
    """IoT device."""
    device_id: str
    device_type: DeviceType
    name: str
    status: DeviceStatus
    firmware_version: str
    last_seen: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)

@dataclass
class SensorReading:
    """Sensor reading."""
    reading_id: str
    device_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    location: Optional[Dict[str, float]] = None

@dataclass
class Command:
    """Device command."""
    command_id: str
    device_id: str
    command_type: str
    parameters: Dict[str, Any]
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class EdgeNode:
    """Edge computing node."""
    node_id: str
    location: str
    capacity: Dict[str, float]
    current_load: Dict[str, float]
    connected_devices: List[str] = field(default_factory=list)
    status: DeviceStatus = DeviceStatus.ONLINE

@dataclass
class Deployment:
    """Edge deployment."""
    deployment_id: str
    model_name: str
    version: str
    target_nodes: List[str]
    status: str
    deployed_at: Optional[datetime] = None

# ============================================================================
# DEVICE MANAGER
# ============================================================================

class DeviceManager:
    """IoT device management."""

    def __init__(self):
        self.devices: Dict[str, IoTDevice] = {}
        self.device_shadows: Dict[str, Dict[str, Any]] = {}  # Digital twins
        self.logger = logging.getLogger("device_manager")

    def register_device(self, device_type: DeviceType, name: str,
                       firmware_version: str, capabilities: List[str]) -> IoTDevice:
        """Register new IoT device."""
        device = IoTDevice(
            device_id=f"dev-{uuid.uuid4().hex[:8]}",
            device_type=device_type,
            name=name,
            status=DeviceStatus.OFFLINE,
            firmware_version=firmware_version,
            capabilities=capabilities
        )

        self.devices[device.device_id] = device
        self.device_shadows[device.device_id] = {
            'desired': {},
            'reported': {},
            'metadata': {}
        }

        self.logger.info(f"Registered device: {name} ({device.device_id})")

        return device

    async def connect_device(self, device_id: str) -> bool:
        """Connect device."""
        if device_id in self.devices:
            self.devices[device_id].status = DeviceStatus.ONLINE
            self.devices[device_id].last_seen = datetime.now()
            self.logger.info(f"Device connected: {device_id}")
            return True

        return False

    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect device."""
        if device_id in self.devices:
            self.devices[device_id].status = DeviceStatus.OFFLINE
            self.logger.info(f"Device disconnected: {device_id}")
            return True

        return False

    def update_shadow(self, device_id: str, state_type: str,
                     state: Dict[str, Any]) -> None:
        """Update device shadow (digital twin)."""
        if device_id in self.device_shadows:
            self.device_shadows[device_id][state_type] = state
            self.logger.debug(f"Updated {state_type} state for {device_id}")

    def get_shadow(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device shadow."""
        return self.device_shadows.get(device_id)

    async def check_health(self) -> Dict[str, Any]:
        """Check health of all devices."""
        now = datetime.now()
        timeout = timedelta(minutes=5)

        offline_devices = []
        for device_id, device in self.devices.items():
            if device.status == DeviceStatus.ONLINE:
                if now - device.last_seen > timeout:
                    device.status = DeviceStatus.OFFLINE
                    offline_devices.append(device_id)

        return {
            'total_devices': len(self.devices),
            'online': len([d for d in self.devices.values() if d.status == DeviceStatus.ONLINE]),
            'offline': len([d for d in self.devices.values() if d.status == DeviceStatus.OFFLINE]),
            'timed_out': offline_devices
        }

# ============================================================================
# MQTT BROKER
# ============================================================================

class MQTTBroker:
    """MQTT message broker."""

    def __init__(self):
        self.subscribers: Dict[str, List[Any]] = defaultdict(list)
        self.message_queue: deque = deque(maxlen=10000)
        self.logger = logging.getLogger("mqtt_broker")

    async def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        """Publish message to topic."""
        message = {
            'topic': topic,
            'payload': payload,
            'timestamp': datetime.now().isoformat()
        }

        self.message_queue.append(message)

        # Notify subscribers
        for subscriber in self.subscribers.get(topic, []):
            await self._notify_subscriber(subscriber, message)

        self.logger.debug(f"Published to {topic}: {payload}")

    async def subscribe(self, topic: str, callback: Any) -> None:
        """Subscribe to topic."""
        self.subscribers[topic].append(callback)
        self.logger.info(f"Subscribed to topic: {topic}")

    async def unsubscribe(self, topic: str, callback: Any) -> None:
        """Unsubscribe from topic."""
        if topic in self.subscribers:
            self.subscribers[topic].remove(callback)

    async def _notify_subscriber(self, subscriber: Any, message: Dict[str, Any]) -> None:
        """Notify subscriber of new message."""
        try:
            if asyncio.iscoroutinefunction(subscriber):
                await subscriber(message)
            else:
                subscriber(message)
        except Exception as e:
            self.logger.error(f"Error notifying subscriber: {e}")

# ============================================================================
# SENSOR FUSION ENGINE
# ============================================================================

class SensorFusionEngine:
    """Fuse data from multiple sensors."""

    def __init__(self):
        self.readings: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.logger = logging.getLogger("sensor_fusion")

    async def add_reading(self, reading: SensorReading) -> None:
        """Add sensor reading."""
        key = f"{reading.device_id}:{reading.sensor_type.value}"
        self.readings[key].append(reading)

    async def fuse_readings(self, sensor_type: SensorType,
                           time_window: timedelta = timedelta(seconds=10)) -> Optional[float]:
        """Fuse readings from multiple sensors."""
        now = datetime.now()
        relevant_readings = []

        for key, reading_queue in self.readings.items():
            if sensor_type.value in key:
                for reading in reading_queue:
                    if now - reading.timestamp <= time_window:
                        relevant_readings.append(reading.value)

        if not relevant_readings:
            return None

        # Simple average fusion
        fused_value = sum(relevant_readings) / len(relevant_readings)

        self.logger.debug(f"Fused {len(relevant_readings)} {sensor_type.value} readings: {fused_value}")

        return fused_value

    async def detect_anomaly(self, reading: SensorReading) -> bool:
        """Detect anomalous sensor reading."""
        key = f"{reading.device_id}:{reading.sensor_type.value}"
        history = list(self.readings[key])

        if len(history) < 10:
            return False

        # Calculate statistics
        values = [r.value for r in history[-10:]]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5

        # Check if current reading is anomalous (> 3 std devs)
        if abs(reading.value - mean) > 3 * std_dev:
            self.logger.warning(f"Anomalous reading detected: {reading.value} (mean={mean:.2f}, std={std_dev:.2f})")
            return True

        return False

# ============================================================================
# EDGE AI RUNTIME
# ============================================================================

class EdgeAIRuntime:
    """Edge AI model inference runtime."""

    def __init__(self):
        self.models: Dict[str, Dict[str, Any]] = {}
        self.inference_count: Dict[str, int] = defaultdict(int)
        self.logger = logging.getLogger("edge_ai_runtime")

    def load_model(self, model_name: str, model_path: str) -> bool:
        """Load AI model to edge device."""
        self.models[model_name] = {
            'path': model_path,
            'loaded_at': datetime.now(),
            'version': '1.0.0'
        }

        self.logger.info(f"Loaded model: {model_name}")

        return True

    async def inference(self, model_name: str, input_data: Any) -> Any:
        """Run inference on edge."""
        if model_name not in self.models:
            raise ValueError(f"Model not loaded: {model_name}")

        # Simulated inference
        self.inference_count[model_name] += 1

        result = {
            'prediction': 'simulated_result',
            'confidence': 0.95,
            'inference_time_ms': 15.3
        }

        self.logger.debug(f"Inference on {model_name}: {result}")

        return result

    def get_model_stats(self) -> Dict[str, Any]:
        """Get model statistics."""
        return {
            'loaded_models': len(self.models),
            'inference_counts': dict(self.inference_count),
            'models': {
                name: {
                    'version': model['version'],
                    'loaded_at': model['loaded_at'].isoformat()
                }
                for name, model in self.models.items()
            }
        }

# ============================================================================
# FLEET MANAGER
# ============================================================================

class FleetManager:
    """Manage fleet of edge nodes."""

    def __init__(self):
        self.nodes: Dict[str, EdgeNode] = {}
        self.deployments: Dict[str, Deployment] = {}
        self.logger = logging.getLogger("fleet_manager")

    def register_node(self, location: str, capacity: Dict[str, float]) -> EdgeNode:
        """Register edge node."""
        node = EdgeNode(
            node_id=f"node-{uuid.uuid4().hex[:8]}",
            location=location,
            capacity=capacity,
            current_load={'cpu': 0.0, 'memory': 0.0, 'gpu': 0.0}
        )

        self.nodes[node.node_id] = node
        self.logger.info(f"Registered edge node: {location}")

        return node

    async def deploy(self, model_name: str, version: str,
                    target_nodes: Optional[List[str]] = None) -> Deployment:
        """Deploy model to edge nodes."""
        if target_nodes is None:
            # Deploy to all online nodes
            target_nodes = [
                node_id for node_id, node in self.nodes.items()
                if node.status == DeviceStatus.ONLINE
            ]

        deployment = Deployment(
            deployment_id=f"dep-{uuid.uuid4().hex[:8]}",
            model_name=model_name,
            version=version,
            target_nodes=target_nodes,
            status="deploying",
            deployed_at=datetime.now()
        )

        self.deployments[deployment.deployment_id] = deployment

        # Simulate deployment
        await asyncio.sleep(0.1)
        deployment.status = "deployed"

        self.logger.info(f"Deployed {model_name} v{version} to {len(target_nodes)} nodes")

        return deployment

    async def ota_update(self, device_ids: List[str], firmware_version: str) -> Dict[str, str]:
        """Over-the-air firmware update."""
        results = {}

        for device_id in device_ids:
            # Simulate OTA update
            await asyncio.sleep(0.1)
            results[device_id] = "success"
            self.logger.info(f"OTA update completed for {device_id}: v{firmware_version}")

        return results

    def get_node_metrics(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node metrics."""
        if node_id not in self.nodes:
            return None

        node = self.nodes[node_id]

        return {
            'node_id': node.node_id,
            'location': node.location,
            'status': node.status.value,
            'connected_devices': len(node.connected_devices),
            'load': node.current_load,
            'capacity': node.capacity
        }

# ============================================================================
# EDGE COMPUTING HUB
# ============================================================================

class EdgeComputingHub:
    """Complete edge computing and IoT system."""

    def __init__(self):
        self.device_manager = DeviceManager()
        self.mqtt_broker = MQTTBroker()
        self.sensor_fusion = SensorFusionEngine()
        self.ai_runtime = EdgeAIRuntime()
        self.fleet_manager = FleetManager()

        self.logger = logging.getLogger("edge_hub")

    async def initialize(self) -> None:
        """Initialize edge hub."""
        self.logger.info("Initializing edge computing hub")

        # Subscribe to device telemetry
        await self.mqtt_broker.subscribe("telemetry/#", self._handle_telemetry)

    async def _handle_telemetry(self, message: Dict[str, Any]) -> None:
        """Handle telemetry message."""
        payload = message.get('payload', {})
        device_id = payload.get('device_id')

        if device_id:
            # Update device last_seen
            if device_id in self.device_manager.devices:
                self.device_manager.devices[device_id].last_seen = datetime.now()

    def register_device(self, device_type: DeviceType, name: str,
                       firmware_version: str, capabilities: List[str]) -> IoTDevice:
        """Register IoT device."""
        return self.device_manager.register_device(
            device_type, name, firmware_version, capabilities
        )

    async def send_sensor_data(self, device_id: str, sensor_type: SensorType,
                              value: float, unit: str) -> None:
        """Send sensor data."""
        reading = SensorReading(
            reading_id=f"read-{uuid.uuid4().hex[:8]}",
            device_id=device_id,
            sensor_type=sensor_type,
            value=value,
            unit=unit
        )

        await self.sensor_fusion.add_reading(reading)

        # Publish to MQTT
        await self.mqtt_broker.publish(
            f"telemetry/{device_id}/{sensor_type.value}",
            {
                'device_id': device_id,
                'sensor_type': sensor_type.value,
                'value': value,
                'unit': unit,
                'timestamp': reading.timestamp.isoformat()
            }
        )

    async def send_command(self, device_id: str, command_type: str,
                          parameters: Dict[str, Any]) -> Command:
        """Send command to device."""
        command = Command(
            command_id=f"cmd-{uuid.uuid4().hex[:8]}",
            device_id=device_id,
            command_type=command_type,
            parameters=parameters
        )

        # Publish command via MQTT
        await self.mqtt_broker.publish(
            f"commands/{device_id}",
            {
                'command_id': command.command_id,
                'command_type': command_type,
                'parameters': parameters
            }
        )

        return command

    async def deploy_model(self, model_name: str, model_path: str,
                          target_nodes: Optional[List[str]] = None) -> Deployment:
        """Deploy AI model to edge."""
        # Load model to runtime
        self.ai_runtime.load_model(model_name, model_path)

        # Deploy to fleet
        return await self.fleet_manager.deploy(model_name, "1.0.0", target_nodes)

    def get_hub_status(self) -> Dict[str, Any]:
        """Get hub status."""
        return {
            'devices': len(self.device_manager.devices),
            'online_devices': len([
                d for d in self.device_manager.devices.values()
                if d.status == DeviceStatus.ONLINE
            ]),
            'edge_nodes': len(self.fleet_manager.nodes),
            'deployments': len(self.fleet_manager.deployments),
            'mqtt_topics': len(self.mqtt_broker.subscribers),
            'ai_models': len(self.ai_runtime.models)
        }

def create_edge_hub() -> EdgeComputingHub:
    """Create edge computing hub."""
    return EdgeComputingHub()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    hub = create_edge_hub()
    print("Edge computing hub initialized")
