"""
BAEL - System Status Reporter
═══════════════════════════════════════════════════════════════
CLI-accessible module for checking the full health of all BAEL
subsystems. Can be run standalone or imported.

Usage:
    python -m core.system_status          # Full status report
    python -m core.system_status --json   # JSON output

    # From code:
    from core.system_status import get_system_status
    status = await get_system_status()
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger("BAEL.SystemStatus")


async def get_system_status() -> Dict[str, Any]:
    """
    Get complete system status by initializing the Enhanced Brain
    and querying all subsystems. This is the definitive health check.
    """
    try:
        from core.brain.enhanced_brain import get_enhanced_brain

        brain = get_enhanced_brain()

        if not brain._initialized:
            init_result = await brain.initialize()
        else:
            init_result = {"already_initialized": True}

        full_status = brain.get_full_status()
        full_status["init_result"] = init_result

        return full_status

    except Exception as e:
        return {
            "system": "BAEL",
            "error": str(e),
            "status": "CRITICAL_FAILURE",
            "timestamp": datetime.now().isoformat(),
        }


async def print_status_report():
    """Print a formatted status report to stdout."""
    try:
        from core.brain.enhanced_brain import get_enhanced_brain

        brain = get_enhanced_brain()
        await brain.initialize()
        print(brain.get_power_report())
    except Exception as e:
        print(f"BAEL STATUS ERROR: {e}")
        import traceback

        traceback.print_exc()


async def print_json_status():
    """Print status as JSON."""
    status = await get_system_status()
    print(json.dumps(status, indent=2, default=str))


def main():
    """CLI entry point."""
    use_json = "--json" in sys.argv

    if use_json:
        asyncio.run(print_json_status())
    else:
        asyncio.run(print_status_report())


if __name__ == "__main__":
    main()


__all__ = ["get_system_status", "print_status_report", "main"]
