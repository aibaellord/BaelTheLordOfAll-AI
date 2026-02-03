#!/usr/bin/env python3
"""
BAEL - Unified Entry Point
Single entry point for all BAEL operations.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BAEL")


def print_banner():
    """Print BAEL banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║    ██████╗  █████╗ ███████╗██╗                                           ║
║    ██╔══██╗██╔══██╗██╔════╝██║                                           ║
║    ██████╔╝███████║█████╗  ██║                                           ║
║    ██╔══██╗██╔══██║██╔══╝  ██║                                           ║
║    ██████╔╝██║  ██║███████╗███████╗                                      ║
║    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝                                      ║
║                                                                           ║
║                   The All-Knowing AI Assistant                            ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


async def run_interactive(mode: str = "standard"):
    """Run BAEL in interactive mode."""
    from core.brain.integration import CognitiveContext, brain_integration

    print(f"\nStarting BAEL in {mode} mode...")
    print("Type 'quit' or 'exit' to stop.\n")

    await brain_integration.initialize()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            context = CognitiveContext(
                query=user_input,
                mode=mode
            )

            result = await brain_integration.process(context)
            print(f"\nBAEL: {result.response}\n")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\nError: {e}\n")


async def run_api_server(host: str = "0.0.0.0", port: int = 8000):
    """Run BAEL API server."""
    import uvicorn

    from api.enhanced_server import app

    print(f"\nStarting BAEL API server on {host}:{port}...")

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def run_mcp_server():
    """Run BAEL MCP server (stdio)."""
    from mcp.stdio_server import MCPStdioServer

    server = MCPStdioServer()
    await server.run()


async def run_task(task: str, mode: str = "standard"):
    """Run a single task."""
    from core.brain.integration import CognitiveContext, brain_integration

    await brain_integration.initialize()

    context = CognitiveContext(
        query=task,
        mode=mode
    )

    result = await brain_integration.process(context)
    print(f"\nResult:\n{result.response}\n")


def show_status():
    """Show BAEL system status."""
    from core import get_core_info

    info = get_core_info()

    print("\n=== BAEL System Status ===\n")
    print(f"Version: {info['version']}")
    print(f"Modules: {info['available_count']}/{info['total_count']} available\n")

    print("Module Status:")
    for module, available in info['modules'].items():
        status = "✓" if available else "✗"
        print(f"  {status} {module}")

    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="BAEL - The All-Knowing AI Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="interactive",
        choices=["interactive", "api", "mcp", "task", "status", "setup"],
        help="Command to run (default: interactive)"
    )

    parser.add_argument(
        "--mode", "-m",
        default="standard",
        choices=["minimal", "standard", "maximum", "autonomous"],
        help="Operating mode"
    )

    parser.add_argument(
        "--task", "-t",
        help="Task to execute (for task command)"
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="API server host"
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="API server port"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress banner"
    )

    args = parser.parse_args()

    if not args.quiet:
        print_banner()

    if args.command == "interactive":
        asyncio.run(run_interactive(args.mode))

    elif args.command == "api":
        asyncio.run(run_api_server(args.host, args.port))

    elif args.command == "mcp":
        asyncio.run(run_mcp_server())

    elif args.command == "task":
        if not args.task:
            print("Error: --task is required for task command")
            sys.exit(1)
        asyncio.run(run_task(args.task, args.mode))

    elif args.command == "status":
        show_status()

    elif args.command == "setup":
        print("Running setup wizard...")
        from setup_wizard import main as setup_main
        setup_main()


if __name__ == "__main__":
    main()
