#!/usr/bin/env python3
"""
BAEL MCP Hub - Health Monitor
Monitors all MCP containers and reports status to BAEL API
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

import httpx

import docker

# Configuration
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))
BAEL_API_URL = os.getenv("BAEL_API_URL", "http://bael:8000")
MCP_CONTAINER_PREFIX = "bael-mcp-"


class MCPHealthMonitor:
    """Monitors health of all MCP containers."""

    def __init__(self):
        self.docker_client = docker.from_env()
        self.http_client = httpx.AsyncClient(timeout=10.0)
        self.status_cache: Dict[str, dict] = {}
        self.start_time = datetime.now()

    def get_mcp_containers(self) -> List[docker.models.containers.Container]:
        """Get all MCP-related containers."""
        containers = self.docker_client.containers.list(all=True)
        return [c for c in containers if c.name.startswith(MCP_CONTAINER_PREFIX)]

    def check_container_health(self, container) -> dict:
        """Check health status of a single container."""
        try:
            container.reload()

            # Extract MCP name from container name
            mcp_name = container.name.replace(MCP_CONTAINER_PREFIX, "")

            # Get container stats
            stats = container.stats(stream=False)

            # Calculate resource usage
            cpu_percent = self._calculate_cpu_percent(stats)
            memory_usage = stats.get("memory_stats", {}).get("usage", 0)
            memory_limit = stats.get("memory_stats", {}).get("limit", 1)
            memory_percent = (memory_usage / memory_limit) * 100 if memory_limit else 0

            return {
                "name": mcp_name,
                "container_id": container.short_id,
                "status": container.status,
                "health": self._get_health_status(container),
                "running": container.status == "running",
                "cpu_percent": round(cpu_percent, 2),
                "memory_mb": round(memory_usage / (1024 * 1024), 2),
                "memory_percent": round(memory_percent, 2),
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs.get("Created", ""),
                "ports": self._get_exposed_ports(container),
                "last_checked": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "name": container.name.replace(MCP_CONTAINER_PREFIX, ""),
                "container_id": container.short_id,
                "status": "error",
                "health": "unhealthy",
                "running": False,
                "error": str(e),
                "last_checked": datetime.now().isoformat()
            }

    def _calculate_cpu_percent(self, stats: dict) -> float:
        """Calculate CPU percentage from Docker stats."""
        try:
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                        stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]

            if system_delta > 0:
                cpu_count = len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1]))
                return (cpu_delta / system_delta) * cpu_count * 100
        except (KeyError, TypeError, ZeroDivisionError):
            pass
        return 0.0

    def _get_health_status(self, container) -> str:
        """Get container health status."""
        try:
            health = container.attrs.get("State", {}).get("Health", {})
            return health.get("Status", "unknown")
        except:
            return "unknown" if container.status == "running" else "stopped"

    def _get_exposed_ports(self, container) -> List[str]:
        """Get exposed ports from container."""
        try:
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            exposed = []
            for port, bindings in ports.items():
                if bindings:
                    for binding in bindings:
                        exposed.append(f"{binding.get('HostPort', '?')}:{port}")
                else:
                    exposed.append(port)
            return exposed
        except:
            return []

    async def check_all_containers(self) -> dict:
        """Check health of all MCP containers."""
        containers = self.get_mcp_containers()

        statuses = []
        healthy_count = 0
        running_count = 0

        for container in containers:
            status = self.check_container_health(container)
            statuses.append(status)

            if status.get("running"):
                running_count += 1
            if status.get("health") in ("healthy", "unknown") and status.get("running"):
                healthy_count += 1

        # Calculate tier distribution
        tiers = {
            "essential": ["filesystem", "brave-search", "github", "sqlite", "memory"],
            "power": ["playwright", "docker", "git", "postgres", "redis", "slack"],
            "enhanced": ["fetch", "puppeteer", "sequential-thinking", "time", "exa", "firecrawl", "context7", "everything"],
            "specialized": ["youtube", "google-drive", "google-maps", "aws-kb", "s3", "cloudflare", "sentry", "raygun", "linear", "notion", "obsidian", "todoist", "e2b"]
        }

        tier_status = {}
        for tier_name, mcps in tiers.items():
            tier_running = sum(1 for s in statuses if s["name"] in mcps and s.get("running"))
            tier_status[tier_name] = {
                "total": len(mcps),
                "running": tier_running,
                "percentage": round((tier_running / len(mcps)) * 100, 1) if mcps else 0
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "summary": {
                "total_containers": len(containers),
                "running": running_count,
                "healthy": healthy_count,
                "stopped": len(containers) - running_count
            },
            "tiers": tier_status,
            "containers": statuses
        }

    async def report_to_bael(self, status: dict):
        """Report status to BAEL API."""
        try:
            response = await self.http_client.post(
                f"{BAEL_API_URL}/api/v1/mcp/status",
                json=status,
                timeout=5.0
            )
            if response.status_code == 200:
                print(f"[{datetime.now().isoformat()}] Status reported to BAEL")
            else:
                print(f"[{datetime.now().isoformat()}] Failed to report: {response.status_code}")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Cannot reach BAEL API: {e}")

    async def run(self):
        """Main monitoring loop."""
        print(f"""
╔══════════════════════════════════════════════════════════════════╗
║           🔥 BAEL MCP Health Monitor Started 🔥                  ║
╠══════════════════════════════════════════════════════════════════╣
║  Check Interval: {CHECK_INTERVAL}s                                          ║
║  BAEL API: {BAEL_API_URL:<52} ║
╚══════════════════════════════════════════════════════════════════╝
        """)

        while True:
            try:
                status = await self.check_all_containers()

                # Print summary
                summary = status["summary"]
                print(f"[{status['timestamp']}] MCP Status: "
                      f"{summary['running']}/{summary['total_containers']} running, "
                      f"{summary['healthy']} healthy")

                # Report to BAEL
                await self.report_to_bael(status)

                # Cache status
                self.status_cache = status

            except Exception as e:
                print(f"[{datetime.now().isoformat()}] Monitor error: {e}")

            await asyncio.sleep(CHECK_INTERVAL)


async def main():
    monitor = MCPHealthMonitor()
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())
