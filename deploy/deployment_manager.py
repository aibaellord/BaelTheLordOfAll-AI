"""
BAEL - Deployment Manager
Cloud deployment and infrastructure management.

Features:
- Multi-cloud deployment (AWS, GCP, Azure)
- Docker/Kubernetes deployment
- Infrastructure as code
- Environment management
- Scaling configuration
- Health checks
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class CloudProvider(Enum):
    """Cloud providers."""
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    DIGITALOCEAN = "digitalocean"
    LOCAL = "local"


class DeploymentType(Enum):
    """Deployment types."""
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    SERVERLESS = "serverless"
    VM = "vm"
    BARE_METAL = "bare_metal"


class DeploymentStatus(Enum):
    """Deployment status."""
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"


class EnvironmentType(Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ResourceLimits:
    """Resource limits for deployment."""
    cpu: str = "1"           # CPU cores
    memory: str = "512Mi"    # Memory limit
    storage: str = "1Gi"     # Storage
    gpu: int = 0             # GPU count


@dataclass
class ScalingConfig:
    """Scaling configuration."""
    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_percent: int = 80
    target_memory_percent: int = 80
    scale_up_delay: int = 60   # seconds
    scale_down_delay: int = 300


@dataclass
class HealthCheck:
    """Health check configuration."""
    enabled: bool = True
    path: str = "/health"
    port: int = 8000
    interval: int = 30        # seconds
    timeout: int = 10
    retries: int = 3


@dataclass
class EnvVar:
    """Environment variable."""
    name: str
    value: Optional[str] = None
    secret: bool = False
    secret_name: Optional[str] = None
    secret_key: Optional[str] = None


@dataclass
class Volume:
    """Volume mount."""
    name: str
    mount_path: str
    size: str = "1Gi"
    storage_class: str = "standard"
    read_only: bool = False


@dataclass
class DeploymentConfig:
    """Full deployment configuration."""
    name: str
    image: str
    environment: EnvironmentType = EnvironmentType.DEVELOPMENT
    provider: CloudProvider = CloudProvider.LOCAL
    deployment_type: DeploymentType = DeploymentType.DOCKER
    replicas: int = 1
    port: int = 8000
    resources: ResourceLimits = field(default_factory=ResourceLimits)
    scaling: Optional[ScalingConfig] = None
    health_check: HealthCheck = field(default_factory=HealthCheck)
    env_vars: List[EnvVar] = field(default_factory=list)
    volumes: List[Volume] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    ingress_host: Optional[str] = None
    ssl_enabled: bool = True


@dataclass
class DeploymentResult:
    """Deployment result."""
    success: bool
    deployment_id: str
    status: DeploymentStatus
    url: Optional[str] = None
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


# =============================================================================
# DEPLOYERS
# =============================================================================

class Deployer(ABC):
    """Abstract deployer base class."""

    @property
    @abstractmethod
    def provider(self) -> CloudProvider:
        pass

    @property
    @abstractmethod
    def deployment_type(self) -> DeploymentType:
        pass

    @abstractmethod
    async def deploy(self, config: DeploymentConfig) -> DeploymentResult:
        pass

    @abstractmethod
    async def status(self, deployment_id: str) -> DeploymentStatus:
        pass

    @abstractmethod
    async def stop(self, deployment_id: str) -> bool:
        pass

    @abstractmethod
    async def scale(self, deployment_id: str, replicas: int) -> bool:
        pass

    @abstractmethod
    async def logs(self, deployment_id: str, lines: int = 100) -> List[str]:
        pass


class DockerDeployer(Deployer):
    """Local Docker deployer."""

    def __init__(self, docker_host: Optional[str] = None):
        self.docker_host = docker_host
        self._deployments: Dict[str, Dict] = {}

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.LOCAL

    @property
    def deployment_type(self) -> DeploymentType:
        return DeploymentType.DOCKER

    async def deploy(self, config: DeploymentConfig) -> DeploymentResult:
        """Deploy using Docker."""
        deployment_id = f"bael-{config.name}-{config.environment.value}"
        logs = []

        try:
            # Build run command
            cmd = ["docker", "run", "-d", "--name", deployment_id]

            # Add port mapping
            cmd.extend(["-p", f"{config.port}:{config.port}"])

            # Add environment variables
            for env in config.env_vars:
                if env.secret:
                    # Would use docker secrets in production
                    cmd.extend(["-e", f"{env.name}=***"])
                else:
                    cmd.extend(["-e", f"{env.name}={env.value}"])

            # Add resource limits
            cmd.extend(["--cpus", config.resources.cpu])
            cmd.extend(["--memory", config.resources.memory])

            # Add labels
            for key, value in config.labels.items():
                cmd.extend(["--label", f"{key}={value}"])

            # Add volumes
            for vol in config.volumes:
                cmd.extend(["-v", f"{vol.name}:{vol.mount_path}"])

            # Add restart policy
            cmd.extend(["--restart", "unless-stopped"])

            # Add image
            cmd.append(config.image)

            logs.append(f"Running: {' '.join(cmd)}")

            # Execute
            result = await self._run_command(cmd)

            if result[0] == 0:
                container_id = result[1].strip()

                self._deployments[deployment_id] = {
                    "container_id": container_id,
                    "config": config,
                    "status": DeploymentStatus.RUNNING
                }

                logs.append(f"Container started: {container_id[:12]}")

                return DeploymentResult(
                    success=True,
                    deployment_id=deployment_id,
                    status=DeploymentStatus.RUNNING,
                    url=f"http://localhost:{config.port}",
                    logs=logs,
                    metadata={"container_id": container_id}
                )
            else:
                logs.append(f"Error: {result[2]}")

                return DeploymentResult(
                    success=False,
                    deployment_id=deployment_id,
                    status=DeploymentStatus.FAILED,
                    error=result[2],
                    logs=logs
                )

        except Exception as e:
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                error=str(e),
                logs=logs
            )

    async def status(self, deployment_id: str) -> DeploymentStatus:
        """Get deployment status."""
        if deployment_id not in self._deployments:
            return DeploymentStatus.STOPPED

        cmd = ["docker", "inspect", "-f", "{{.State.Status}}", deployment_id]
        result = await self._run_command(cmd)

        if result[0] == 0:
            status_map = {
                "running": DeploymentStatus.RUNNING,
                "exited": DeploymentStatus.STOPPED,
                "dead": DeploymentStatus.FAILED
            }
            return status_map.get(result[1].strip(), DeploymentStatus.PENDING)

        return DeploymentStatus.STOPPED

    async def stop(self, deployment_id: str) -> bool:
        """Stop deployment."""
        cmd = ["docker", "stop", deployment_id]
        result = await self._run_command(cmd)

        if result[0] == 0:
            cmd = ["docker", "rm", deployment_id]
            await self._run_command(cmd)

            if deployment_id in self._deployments:
                del self._deployments[deployment_id]

            return True

        return False

    async def scale(self, deployment_id: str, replicas: int) -> bool:
        """Docker doesn't support native scaling."""
        logger.warning("Docker doesn't support native scaling")
        return False

    async def logs(self, deployment_id: str, lines: int = 100) -> List[str]:
        """Get container logs."""
        cmd = ["docker", "logs", "--tail", str(lines), deployment_id]
        result = await self._run_command(cmd)

        if result[0] == 0:
            return result[1].split("\n")

        return []

    async def _run_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Run shell command."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return (
                process.returncode,
                stdout.decode(),
                stderr.decode()
            )
        except Exception as e:
            return (1, "", str(e))


class KubernetesDeployer(Deployer):
    """Kubernetes deployer."""

    def __init__(self, kubeconfig: Optional[str] = None, namespace: str = "default"):
        self.kubeconfig = kubeconfig
        self.namespace = namespace

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.LOCAL  # Can be any cloud with K8s

    @property
    def deployment_type(self) -> DeploymentType:
        return DeploymentType.KUBERNETES

    async def deploy(self, config: DeploymentConfig) -> DeploymentResult:
        """Deploy to Kubernetes."""
        deployment_id = f"{config.name}-{config.environment.value}"
        logs = []

        try:
            # Generate Kubernetes manifests
            manifests = self._generate_manifests(config)
            logs.append("Generated Kubernetes manifests")

            # Apply manifests
            for manifest in manifests:
                result = await self._apply_manifest(manifest)
                logs.append(f"Applied {manifest.get('kind', 'resource')}")

            return DeploymentResult(
                success=True,
                deployment_id=deployment_id,
                status=DeploymentStatus.DEPLOYING,
                url=f"https://{config.ingress_host}" if config.ingress_host else None,
                logs=logs
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                error=str(e),
                logs=logs
            )

    def _generate_manifests(self, config: DeploymentConfig) -> List[Dict]:
        """Generate Kubernetes manifests."""
        manifests = []

        # Deployment
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": config.name,
                "namespace": self.namespace,
                "labels": config.labels
            },
            "spec": {
                "replicas": config.replicas,
                "selector": {
                    "matchLabels": {"app": config.name}
                },
                "template": {
                    "metadata": {
                        "labels": {"app": config.name, **config.labels}
                    },
                    "spec": {
                        "containers": [{
                            "name": config.name,
                            "image": config.image,
                            "ports": [{"containerPort": config.port}],
                            "resources": {
                                "requests": {
                                    "cpu": config.resources.cpu,
                                    "memory": config.resources.memory
                                },
                                "limits": {
                                    "cpu": config.resources.cpu,
                                    "memory": config.resources.memory
                                }
                            },
                            "env": [
                                {"name": e.name, "value": e.value}
                                for e in config.env_vars if not e.secret
                            ]
                        }]
                    }
                }
            }
        }

        # Add health checks
        if config.health_check.enabled:
            deployment["spec"]["template"]["spec"]["containers"][0]["livenessProbe"] = {
                "httpGet": {
                    "path": config.health_check.path,
                    "port": config.port
                },
                "initialDelaySeconds": 30,
                "periodSeconds": config.health_check.interval
            }

        manifests.append(deployment)

        # Service
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": config.name,
                "namespace": self.namespace
            },
            "spec": {
                "selector": {"app": config.name},
                "ports": [{
                    "port": config.port,
                    "targetPort": config.port
                }]
            }
        }
        manifests.append(service)

        # Ingress (if host specified)
        if config.ingress_host:
            ingress = {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "Ingress",
                "metadata": {
                    "name": f"{config.name}-ingress",
                    "namespace": self.namespace,
                    "annotations": {
                        "kubernetes.io/ingress.class": "nginx"
                    }
                },
                "spec": {
                    "rules": [{
                        "host": config.ingress_host,
                        "http": {
                            "paths": [{
                                "path": "/",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": config.name,
                                        "port": {"number": config.port}
                                    }
                                }
                            }]
                        }
                    }]
                }
            }

            if config.ssl_enabled:
                ingress["spec"]["tls"] = [{
                    "hosts": [config.ingress_host],
                    "secretName": f"{config.name}-tls"
                }]

            manifests.append(ingress)

        # HPA (if scaling configured)
        if config.scaling:
            hpa = {
                "apiVersion": "autoscaling/v2",
                "kind": "HorizontalPodAutoscaler",
                "metadata": {
                    "name": f"{config.name}-hpa",
                    "namespace": self.namespace
                },
                "spec": {
                    "scaleTargetRef": {
                        "apiVersion": "apps/v1",
                        "kind": "Deployment",
                        "name": config.name
                    },
                    "minReplicas": config.scaling.min_replicas,
                    "maxReplicas": config.scaling.max_replicas,
                    "metrics": [{
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": config.scaling.target_cpu_percent
                            }
                        }
                    }]
                }
            }
            manifests.append(hpa)

        return manifests

    async def _apply_manifest(self, manifest: Dict) -> bool:
        """Apply Kubernetes manifest."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False
        ) as f:
            import yaml
            yaml.dump(manifest, f)
            temp_path = f.name

        try:
            cmd = ["kubectl", "apply", "-f", temp_path]
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0

        finally:
            os.unlink(temp_path)

    async def status(self, deployment_id: str) -> DeploymentStatus:
        """Get deployment status."""
        cmd = [
            "kubectl", "get", "deployment", deployment_id,
            "-n", self.namespace, "-o", "json"
        ]

        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()

        if process.returncode == 0:
            data = json.loads(stdout)
            available = data.get("status", {}).get("availableReplicas", 0)
            desired = data.get("spec", {}).get("replicas", 1)

            if available >= desired:
                return DeploymentStatus.RUNNING
            elif available > 0:
                return DeploymentStatus.DEPLOYING
            else:
                return DeploymentStatus.PENDING

        return DeploymentStatus.STOPPED

    async def stop(self, deployment_id: str) -> bool:
        """Delete deployment."""
        cmd = [
            "kubectl", "delete", "deployment", deployment_id,
            "-n", self.namespace
        ]

        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0

    async def scale(self, deployment_id: str, replicas: int) -> bool:
        """Scale deployment."""
        cmd = [
            "kubectl", "scale", "deployment", deployment_id,
            "--replicas", str(replicas), "-n", self.namespace
        ]

        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0

    async def logs(self, deployment_id: str, lines: int = 100) -> List[str]:
        """Get pod logs."""
        cmd = [
            "kubectl", "logs", f"deployment/{deployment_id}",
            "--tail", str(lines), "-n", self.namespace
        ]

        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()

        if process.returncode == 0:
            return stdout.decode().split("\n")

        return []


# =============================================================================
# TERRAFORM GENERATOR
# =============================================================================

class TerraformGenerator:
    """Generate Terraform configurations."""

    def __init__(self, output_dir: str = "./terraform"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_aws(self, config: DeploymentConfig) -> str:
        """Generate AWS Terraform config."""
        tf_config = f'''
# BAEL AWS Deployment
# Generated: {datetime.now().isoformat()}

terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = var.aws_region
}}

variable "aws_region" {{
  default = "us-west-2"
}}

# ECS Cluster
resource "aws_ecs_cluster" "bael" {{
  name = "bael-{config.environment.value}"

  setting {{
    name  = "containerInsights"
    value = "enabled"
  }}
}}

# Task Definition
resource "aws_ecs_task_definition" "bael" {{
  family                   = "{config.name}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "{config.resources.cpu}"
  memory                   = "{config.resources.memory.replace('Mi', '')}"

  container_definitions = jsonencode([{{
    name  = "{config.name}"
    image = "{config.image}"

    portMappings = [{{
      containerPort = {config.port}
      hostPort      = {config.port}
      protocol      = "tcp"
    }}]

    environment = [
      {self._format_env_vars(config.env_vars)}
    ]

    logConfiguration = {{
      logDriver = "awslogs"
      options = {{
        awslogs-group         = "/ecs/{config.name}"
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "ecs"
      }}
    }}
  }}])
}}

# ECS Service
resource "aws_ecs_service" "bael" {{
  name            = "{config.name}"
  cluster         = aws_ecs_cluster.bael.id
  task_definition = aws_ecs_task_definition.bael.arn
  desired_count   = {config.replicas}
  launch_type     = "FARGATE"

  network_configuration {{
    subnets         = var.subnets
    security_groups = var.security_groups
  }}
}}

# Auto Scaling
resource "aws_appautoscaling_target" "bael" {{
  max_capacity       = {config.scaling.max_replicas if config.scaling else 10}
  min_capacity       = {config.scaling.min_replicas if config.scaling else 1}
  resource_id        = "service/${{aws_ecs_cluster.bael.name}}/${{aws_ecs_service.bael.name}}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}}
'''

        output_path = self.output_dir / "aws_main.tf"
        with open(output_path, "w") as f:
            f.write(tf_config)

        return str(output_path)

    def generate_gcp(self, config: DeploymentConfig) -> str:
        """Generate GCP Terraform config."""
        tf_config = f'''
# BAEL GCP Deployment
# Generated: {datetime.now().isoformat()}

terraform {{
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "~> 5.0"
    }}
  }}
}}

provider "google" {{
  project = var.project_id
  region  = var.region
}}

variable "project_id" {{
  description = "GCP Project ID"
}}

variable "region" {{
  default = "us-central1"
}}

# Cloud Run Service
resource "google_cloud_run_service" "bael" {{
  name     = "{config.name}"
  location = var.region

  template {{
    spec {{
      containers {{
        image = "{config.image}"

        ports {{
          container_port = {config.port}
        }}

        resources {{
          limits = {{
            cpu    = "{config.resources.cpu}"
            memory = "{config.resources.memory}"
          }}
        }}

        {self._format_gcp_env_vars(config.env_vars)}
      }}
    }}

    metadata {{
      annotations = {{
        "autoscaling.knative.dev/minScale" = "{config.scaling.min_replicas if config.scaling else 1}"
        "autoscaling.knative.dev/maxScale" = "{config.scaling.max_replicas if config.scaling else 10}"
      }}
    }}
  }}

  traffic {{
    percent         = 100
    latest_revision = true
  }}
}}

# Make public (optional)
resource "google_cloud_run_service_iam_member" "public" {{
  service  = google_cloud_run_service.bael.name
  location = google_cloud_run_service.bael.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}}

output "url" {{
  value = google_cloud_run_service.bael.status[0].url
}}
'''

        output_path = self.output_dir / "gcp_main.tf"
        with open(output_path, "w") as f:
            f.write(tf_config)

        return str(output_path)

    def _format_env_vars(self, env_vars: List[EnvVar]) -> str:
        """Format env vars for AWS."""
        items = []
        for env in env_vars:
            if not env.secret:
                items.append(f'{{"name": "{env.name}", "value": "{env.value}"}}')
        return ",\n      ".join(items)

    def _format_gcp_env_vars(self, env_vars: List[EnvVar]) -> str:
        """Format env vars for GCP."""
        items = []
        for env in env_vars:
            if not env.secret:
                items.append(f'''
        env {{
          name  = "{env.name}"
          value = "{env.value}"
        }}''')
        return "".join(items)


# =============================================================================
# DEPLOYMENT MANAGER
# =============================================================================

class DeploymentManager:
    """Main deployment manager."""

    def __init__(self):
        self._deployers: Dict[Tuple[CloudProvider, DeploymentType], Deployer] = {}
        self._deployments: Dict[str, DeploymentConfig] = {}
        self._history: List[DeploymentResult] = []

        # Register default deployers
        self.register_deployer(DockerDeployer())
        self.register_deployer(KubernetesDeployer())

        self.terraform = TerraformGenerator()

    def register_deployer(self, deployer: Deployer) -> None:
        """Register a deployer."""
        key = (deployer.provider, deployer.deployment_type)
        self._deployers[key] = deployer
        logger.info(f"Registered deployer: {deployer.provider.value}/{deployer.deployment_type.value}")

    def get_deployer(
        self,
        provider: CloudProvider,
        deployment_type: DeploymentType
    ) -> Optional[Deployer]:
        """Get deployer for provider and type."""
        return self._deployers.get((provider, deployment_type))

    async def deploy(self, config: DeploymentConfig) -> DeploymentResult:
        """Deploy application."""
        deployer = self.get_deployer(config.provider, config.deployment_type)

        if not deployer:
            return DeploymentResult(
                success=False,
                deployment_id="",
                status=DeploymentStatus.FAILED,
                error=f"No deployer for {config.provider.value}/{config.deployment_type.value}"
            )

        result = await deployer.deploy(config)

        if result.success:
            self._deployments[result.deployment_id] = config

        self._history.append(result)
        return result

    async def status(self, deployment_id: str) -> DeploymentStatus:
        """Get deployment status."""
        config = self._deployments.get(deployment_id)

        if not config:
            return DeploymentStatus.STOPPED

        deployer = self.get_deployer(config.provider, config.deployment_type)

        if deployer:
            return await deployer.status(deployment_id)

        return DeploymentStatus.STOPPED

    async def stop(self, deployment_id: str) -> bool:
        """Stop deployment."""
        config = self._deployments.get(deployment_id)

        if not config:
            return False

        deployer = self.get_deployer(config.provider, config.deployment_type)

        if deployer:
            success = await deployer.stop(deployment_id)
            if success:
                del self._deployments[deployment_id]
            return success

        return False

    async def scale(self, deployment_id: str, replicas: int) -> bool:
        """Scale deployment."""
        config = self._deployments.get(deployment_id)

        if not config:
            return False

        deployer = self.get_deployer(config.provider, config.deployment_type)

        if deployer:
            return await deployer.scale(deployment_id, replicas)

        return False

    async def logs(self, deployment_id: str, lines: int = 100) -> List[str]:
        """Get deployment logs."""
        config = self._deployments.get(deployment_id)

        if not config:
            return []

        deployer = self.get_deployer(config.provider, config.deployment_type)

        if deployer:
            return await deployer.logs(deployment_id, lines)

        return []

    def generate_terraform(
        self,
        config: DeploymentConfig,
        provider: CloudProvider
    ) -> str:
        """Generate Terraform configuration."""
        if provider == CloudProvider.AWS:
            return self.terraform.generate_aws(config)
        elif provider == CloudProvider.GCP:
            return self.terraform.generate_gcp(config)
        else:
            raise ValueError(f"Terraform not supported for {provider.value}")

    def list_deployments(self) -> List[Dict[str, Any]]:
        """List all deployments."""
        return [
            {
                "id": dep_id,
                "name": config.name,
                "environment": config.environment.value,
                "provider": config.provider.value,
                "type": config.deployment_type.value
            }
            for dep_id, config in self._deployments.items()
        ]

    def get_history(self, limit: int = 50) -> List[DeploymentResult]:
        """Get deployment history."""
        return self._history[-limit:]


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

async def main():
    """Demonstrate deployment manager."""
    print("=== BAEL Deployment Manager ===\n")

    manager = DeploymentManager()

    # Create deployment config
    config = DeploymentConfig(
        name="bael-api",
        image="bael:latest",
        environment=EnvironmentType.DEVELOPMENT,
        provider=CloudProvider.LOCAL,
        deployment_type=DeploymentType.DOCKER,
        replicas=1,
        port=8000,
        resources=ResourceLimits(
            cpu="1",
            memory="512Mi"
        ),
        scaling=ScalingConfig(
            min_replicas=1,
            max_replicas=5
        ),
        health_check=HealthCheck(
            path="/health",
            interval=30
        ),
        env_vars=[
            EnvVar(name="ENVIRONMENT", value="development"),
            EnvVar(name="LOG_LEVEL", value="debug")
        ],
        labels={"app": "bael", "version": "1.0"}
    )

    print("--- Deployment Configuration ---")
    print(f"Name: {config.name}")
    print(f"Image: {config.image}")
    print(f"Environment: {config.environment.value}")
    print(f"Provider: {config.provider.value}")
    print(f"Type: {config.deployment_type.value}")
    print(f"Replicas: {config.replicas}")
    print(f"Port: {config.port}")

    print("\n--- Available Deployers ---")
    for (provider, dep_type), deployer in manager._deployers.items():
        print(f"  - {provider.value}/{dep_type.value}")

    # Generate Terraform
    print("\n--- Generate Terraform ---")
    try:
        aws_tf = manager.generate_terraform(config, CloudProvider.AWS)
        print(f"Generated AWS Terraform: {aws_tf}")

        gcp_tf = manager.generate_terraform(config, CloudProvider.GCP)
        print(f"Generated GCP Terraform: {gcp_tf}")
    except Exception as e:
        print(f"Terraform generation: {e}")

    # Demo deployment (would need Docker running)
    print("\n--- Deployment Demo ---")
    print("Note: Actual deployment requires Docker/Kubernetes to be running")

    # Show what would happen
    print("\nDeployment would:")
    print(f"  1. Pull image: {config.image}")
    print(f"  2. Start container: bael-{config.name}-{config.environment.value}")
    print(f"  3. Map port: {config.port}")
    print(f"  4. Apply resource limits: {config.resources.cpu} CPU, {config.resources.memory} memory")
    print(f"  5. Configure health check: {config.health_check.path}")

    print("\n=== Deployment Manager ready ===")
    print("Use with Docker or Kubernetes for actual deployments")


if __name__ == "__main__":
    asyncio.run(main())
