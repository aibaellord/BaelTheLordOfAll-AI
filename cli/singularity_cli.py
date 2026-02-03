#!/usr/bin/env python3
"""
BAEL Singularity CLI
====================

The ultimate command-line interface for BAEL.
Direct access to all 200+ capabilities from the terminal.

Usage:
    bael-singularity awaken [--mode MODE]
    bael-singularity think "Your query"
    bael-singularity collective "Problem to solve" [--strategy hybrid]
    bael-singularity reason "Query" [--engines causal,deductive]
    bael-singularity create "Request"
    bael-singularity maximum "Goal"
    bael-singularity invoke CAPABILITY METHOD [--args JSON]
    bael-singularity evolve
    bael-singularity status
    bael-singularity capabilities
    bael-singularity introspect
    bael-singularity shell
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Colors for terminal output
class Colors:
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


def print_header(title: str):
    """Print a fancy header."""
    print(f"\n{Colors.PURPLE}╔══════════════════════════════════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.PURPLE}║{Colors.CYAN}{title.center(66)}{Colors.PURPLE}║{Colors.NC}")
    print(f"{Colors.PURPLE}╚══════════════════════════════════════════════════════════════════╝{Colors.NC}\n")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.CYAN}→ {message}{Colors.NC}")


def print_result(result: Any):
    """Pretty print a result."""
    if isinstance(result, dict):
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result)


async def cmd_awaken(args):
    """Awaken the Singularity."""
    from core.singularity import SingularityMode, awaken

    print_header(f"⚡ BAEL SINGULARITY - {args.mode.upper()} MODE ⚡")

    mode = SingularityMode(args.mode)
    singularity = await awaken(mode)

    status = singularity.get_status()
    print_success(f"Singularity awakened in {args.mode} mode")
    print()
    print(f"  Mode:          {status['mode']}")
    print(f"  Loaded:        {status['capabilities_loaded']} capabilities")
    print(f"  Available:     {status['capabilities_available']} capabilities")
    print(f"  Invocations:   {status['total_invocations']}")
    print()

    return singularity


async def cmd_think(args):
    """Think deeply about a query."""
    from core.singularity import get_singularity

    print_header("💭 BAEL SINGULARITY THINKING")
    print_info(f"Query: {args.query}")
    print()

    singularity = await get_singularity()
    result = await singularity.think(
        query=args.query,
        depth=args.depth
    )

    print_result(result)


async def cmd_collective(args):
    """Solve problem using collective intelligence."""
    from core.singularity import get_singularity

    print_header("🐝 COLLECTIVE INTELLIGENCE")
    print_info(f"Problem: {args.problem}")
    print_info(f"Strategy: {args.strategy}")
    print_info(f"Agents: {args.agents}")
    print()

    singularity = await get_singularity()
    result = await singularity.collective_solve(
        problem=args.problem,
        strategy=args.strategy,
        agents=args.agents
    )

    print_result(result)


async def cmd_reason(args):
    """Apply reasoning engines."""
    from core.singularity import get_singularity

    print_header("🧠 MULTI-ENGINE REASONING")
    print_info(f"Query: {args.query}")
    if args.engines:
        print_info(f"Engines: {args.engines}")
    print()

    singularity = await get_singularity()
    engines = args.engines.split(',') if args.engines else None
    result = await singularity.reason(
        query=args.query,
        engines=engines
    )

    print_result(result)


async def cmd_create(args):
    """Creative generation."""
    from core.singularity import get_singularity

    print_header("✨ CREATIVE GENERATION")
    print_info(f"Request: {args.request}")
    print_info(f"Mode: {args.mode}")
    print()

    singularity = await get_singularity()
    result = await singularity.create(
        request=args.request,
        mode=args.mode
    )

    print_result(result)


async def cmd_maximum(args):
    """Maximum potential mode."""
    from core.singularity import get_singularity

    print_header("🔥🔥🔥 MAXIMUM POTENTIAL MODE 🔥🔥🔥")
    print_info(f"Goal: {args.goal}")
    print()

    singularity = await get_singularity()
    result = await singularity.maximum_potential(goal=args.goal)

    print_result(result)


async def cmd_invoke(args):
    """Invoke a specific capability."""
    from core.singularity import get_singularity

    print_header(f"⚡ INVOKING {args.capability.upper()}")
    print_info(f"Method: {args.method}")
    if args.args:
        print_info(f"Args: {args.args}")
    print()

    singularity = await get_singularity()
    kwargs = json.loads(args.args) if args.args else {}
    result = await singularity.invoke(
        capability=args.capability,
        method=args.method,
        **kwargs
    )

    print_result(result)


async def cmd_evolve(args):
    """Trigger self-evolution."""
    from core.singularity import get_singularity

    print_header("🧬 SELF-EVOLUTION")
    print()

    singularity = await get_singularity()
    result = await singularity.evolve()

    print_result(result)


async def cmd_status(args):
    """Show Singularity status."""
    from core.singularity import get_singularity

    print_header("📊 SINGULARITY STATUS")

    singularity = await get_singularity()
    status = singularity.get_status()

    print(f"  {Colors.CYAN}Mode:{Colors.NC}          {status['mode']}")
    print(f"  {Colors.CYAN}Uptime:{Colors.NC}        {int(status['uptime_seconds'])} seconds")
    print(f"  {Colors.CYAN}Invocations:{Colors.NC}   {status['total_invocations']}")
    print(f"  {Colors.CYAN}Loaded:{Colors.NC}        {status['capabilities_loaded']} capabilities")
    print(f"  {Colors.CYAN}Available:{Colors.NC}     {status['capabilities_available']} capabilities")
    print(f"  {Colors.CYAN}Active Tasks:{Colors.NC}  {status['active_tasks']}")
    print()
    print(f"  {Colors.PURPLE}Domains:{Colors.NC}")
    for domain, count in status.get('domains', {}).items():
        bar = "█" * min(count, 20) + "░" * max(0, 20 - count)
        print(f"    {domain.ljust(15)} {bar} {count}")
    print()


async def cmd_capabilities(args):
    """List all capabilities."""
    from core.singularity import get_singularity

    print_header("🔮 SINGULARITY CAPABILITIES")

    singularity = await get_singularity()
    caps = singularity.list_capabilities()

    domain_icons = {
        "orchestration": "🎯",
        "collective": "🐝",
        "reasoning": "🧠",
        "memory": "💾",
        "cognition": "💭",
        "perception": "👁️",
        "learning": "📚",
        "resources": "⚡",
        "knowledge": "📖",
        "tools": "🔧",
    }

    total = 0
    for domain, capabilities in caps.items():
        icon = domain_icons.get(domain, "🔮")
        print(f"{Colors.PURPLE}{icon} {domain.upper()}{Colors.NC} ({len(capabilities)} capabilities)")
        for cap in capabilities:
            print(f"    {Colors.CYAN}• {cap}{Colors.NC}")
        total += len(capabilities)
        print()

    print(f"{Colors.GREEN}Total: {total} capabilities{Colors.NC}")
    print()


async def cmd_introspect(args):
    """Deep introspection."""
    from core.singularity import get_singularity

    print_header("🔍 DEEP INTROSPECTION")

    singularity = await get_singularity()
    result = await singularity.introspect()

    print_result(result)


async def cmd_shell(args):
    """Interactive Singularity shell."""
    from core.singularity import get_singularity

    print_header("🔮 SINGULARITY INTERACTIVE SHELL")
    print(f"{Colors.CYAN}Commands:{Colors.NC}")
    print("  think <query>       - Think about something")
    print("  solve <problem>     - Collective problem solving")
    print("  reason <query>      - Multi-engine reasoning")
    print("  create <request>    - Creative generation")
    print("  maximum <goal>      - Maximum potential mode")
    print("  status              - Show status")
    print("  caps                - List capabilities")
    print("  evolve              - Trigger evolution")
    print("  quit                - Exit shell")
    print()

    singularity = await get_singularity()

    while True:
        try:
            user_input = input(f"{Colors.PURPLE}singularity> {Colors.NC}").strip()

            if not user_input:
                continue

            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "quit" or cmd == "exit":
                print_success("Goodbye!")
                break

            elif cmd == "think":
                if arg:
                    result = await singularity.think(arg)
                    print_result(result)
                else:
                    print_error("Usage: think <query>")

            elif cmd == "solve":
                if arg:
                    result = await singularity.collective_solve(arg, strategy="hybrid")
                    print_result(result)
                else:
                    print_error("Usage: solve <problem>")

            elif cmd == "reason":
                if arg:
                    result = await singularity.reason(arg)
                    print_result(result)
                else:
                    print_error("Usage: reason <query>")

            elif cmd == "create":
                if arg:
                    result = await singularity.create(arg)
                    print_result(result)
                else:
                    print_error("Usage: create <request>")

            elif cmd == "maximum":
                if arg:
                    result = await singularity.maximum_potential(arg)
                    print_result(result)
                else:
                    print_error("Usage: maximum <goal>")

            elif cmd == "status":
                status = singularity.get_status()
                print_result(status)

            elif cmd == "caps":
                caps = singularity.list_capabilities()
                for domain, capabilities in caps.items():
                    print(f"\n{domain.upper()}: {', '.join(capabilities)}")

            elif cmd == "evolve":
                result = await singularity.evolve()
                print_result(result)

            elif cmd == "help":
                print("Commands: think, solve, reason, create, maximum, status, caps, evolve, quit")

            else:
                # Default: treat as query
                result = await singularity.think(user_input)
                print_result(result)

        except KeyboardInterrupt:
            print("\n" + Colors.YELLOW + "Use 'quit' to exit" + Colors.NC)
        except Exception as e:
            print_error(str(e))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="BAEL Singularity CLI - Unified Control of 200+ Capabilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s awaken --mode godmode
  %(prog)s think "What is the meaning of consciousness?"
  %(prog)s collective "Design an AGI architecture" --strategy hybrid
  %(prog)s reason "Why do we exist?" --engines causal,deductive,abductive
  %(prog)s create "A poem about AI"
  %(prog)s maximum "Build the ultimate AI system"
  %(prog)s invoke creativity generate --args '{"prompt": "new idea"}'
  %(prog)s shell
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # awaken
    awaken_parser = subparsers.add_parser("awaken", help="Awaken the Singularity")
    awaken_parser.add_argument("--mode", default="transcendent",
                               choices=["dormant", "awakened", "empowered", "transcendent", "autonomous", "godmode"])

    # think
    think_parser = subparsers.add_parser("think", help="Think deeply about a query")
    think_parser.add_argument("query", help="Query to think about")
    think_parser.add_argument("--depth", default="deep", choices=["shallow", "medium", "deep"])

    # collective
    collective_parser = subparsers.add_parser("collective", help="Collective problem solving")
    collective_parser.add_argument("problem", help="Problem to solve")
    collective_parser.add_argument("--strategy", default="hybrid",
                                   choices=["swarm", "council", "evolution", "hybrid"])
    collective_parser.add_argument("--agents", type=int, default=10)

    # reason
    reason_parser = subparsers.add_parser("reason", help="Multi-engine reasoning")
    reason_parser.add_argument("query", help="Query to reason about")
    reason_parser.add_argument("--engines", help="Comma-separated list of engines")

    # create
    create_parser = subparsers.add_parser("create", help="Creative generation")
    create_parser.add_argument("request", help="What to create")
    create_parser.add_argument("--mode", default="creative", choices=["creative", "innovative", "blend"])

    # maximum
    maximum_parser = subparsers.add_parser("maximum", help="Maximum potential mode")
    maximum_parser.add_argument("goal", help="Goal to achieve")

    # invoke
    invoke_parser = subparsers.add_parser("invoke", help="Invoke a specific capability")
    invoke_parser.add_argument("capability", help="Capability name")
    invoke_parser.add_argument("method", help="Method to call")
    invoke_parser.add_argument("--args", help="JSON arguments")

    # evolve
    subparsers.add_parser("evolve", help="Trigger self-evolution")

    # status
    subparsers.add_parser("status", help="Show Singularity status")

    # capabilities
    subparsers.add_parser("capabilities", help="List all capabilities")

    # introspect
    subparsers.add_parser("introspect", help="Deep introspection")

    # shell
    subparsers.add_parser("shell", help="Interactive shell")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Map commands to functions
    commands = {
        "awaken": cmd_awaken,
        "think": cmd_think,
        "collective": cmd_collective,
        "reason": cmd_reason,
        "create": cmd_create,
        "maximum": cmd_maximum,
        "invoke": cmd_invoke,
        "evolve": cmd_evolve,
        "status": cmd_status,
        "capabilities": cmd_capabilities,
        "introspect": cmd_introspect,
        "shell": cmd_shell,
    }

    try:
        asyncio.run(commands[args.command](args))
    except KeyboardInterrupt:
        print("\n" + Colors.YELLOW + "Interrupted" + Colors.NC)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
