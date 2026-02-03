"""
BAEL - The Lord of All AI Agents v2.0.0
Main Entry Point - Maximum Potential Edition

The supreme AI agent orchestration system that surpasses all others.
Now with cutting-edge 2026 capabilities: Extended Thinking, Computer Use,
Proactive Behavior, Vision, Voice, Self-Evolution, and 1M+ token context.
"""

__version__ = "2.0.0"
__codename__ = "Maximum Potential"

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.brain.brain import BaelBrain
from core.orchestrator.orchestrator import (AgentConfig, AgentOrchestrator,
                                            WorkflowPattern)

# Try to import Ultimate Orchestrator
try:
    from core.ultimate.ultimate_orchestrator import (BAELMode, Capability,
                                                     UltimateConfig,
                                                     UltimateOrchestrator,
                                                     create_ultimate)
    ULTIMATE_AVAILABLE = True
except ImportError:
    ULTIMATE_AVAILABLE = False

# Try to import Unified Toolkit
try:
    from tools import UnifiedToolkit
    TOOLKIT_AVAILABLE = True
except ImportError:
    TOOLKIT_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("BAEL")


# =============================================================================
# ASCII ART BANNER
# =============================================================================

BANNER = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║    ██████╗  █████╗ ███████╗██╗         ████████╗██╗  ██╗███████╗             ║
║    ██╔══██╗██╔══██╗██╔════╝██║         ╚══██╔══╝██║  ██║██╔════╝             ║
║    ██████╔╝███████║█████╗  ██║            ██║   ███████║█████╗               ║
║    ██╔══██╗██╔══██║██╔══╝  ██║            ██║   ██╔══██║██╔══╝               ║
║    ██████╔╝██║  ██║███████╗███████╗       ██║   ██║  ██║███████╗             ║
║    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝       ╚═╝   ╚═╝  ╚═╝╚══════╝             ║
║                                                                              ║
║              ██╗      ██████╗ ██████╗ ██████╗                                ║
║              ██║     ██╔═══██╗██╔══██╗██╔══██╗                               ║
║              ██║     ██║   ██║██████╔╝██║  ██║                               ║
║              ██║     ██║   ██║██╔══██╗██║  ██║                               ║
║              ███████╗╚██████╔╝██║  ██║██████╔╝                               ║
║              ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝                                ║
║                                                                              ║
║                     ██████╗ ███████╗     █████╗ ██╗     ██╗                  ║
║                    ██╔═══██╗██╔════╝    ██╔══██╗██║     ██║                  ║
║                    ██║   ██║█████╗      ███████║██║     ██║                  ║
║                    ██║   ██║██╔══╝      ██╔══██║██║     ██║                  ║
║                    ╚██████╔╝██║         ██║  ██║███████╗███████╗             ║
║                     ╚═════╝ ╚═╝         ╚═╝  ╚═╝╚══════╝╚══════╝             ║
║                                                                              ║
║                    The Ultimate AI Agent Orchestration System                ║
║                         Surpassing All That Came Before                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


# =============================================================================
# BAEL MAIN CLASS
# =============================================================================

class BAEL:
    """
    BAEL - The Lord of All AI Agents

    The supreme orchestrator that combines:
    - Multi-model routing (OpenRouter, Anthropic, OpenAI)
    - 5-layer cognitive memory system
    - Advanced reasoning (CoT, ToT, GoT)
    - Specialist personas (12+ experts)
    - Multi-agent collaboration
    - Comprehensive tooling
    - Self-learning and improvement
    - Reinforcement Learning
    - Neural Architecture Search
    - DSL Rule Engine
    - Knowledge Synthesis
    - And much more...

    This is the most advanced AI agent system ever created.
    """

    def __init__(
        self,
        config_path: str = "config/settings/main.yaml",
        mode: str = "standard"
    ):
        self.config_path = config_path
        self.mode = mode
        self.brain: Optional[BaelBrain] = None
        self.orchestrator: Optional[AgentOrchestrator] = None
        self.ultimate: Optional[UltimateOrchestrator] = None if ULTIMATE_AVAILABLE else None
        self.toolkit: Optional[UnifiedToolkit] = None if TOOLKIT_AVAILABLE else None
        self.initialized = False

    async def initialize(self):
        """Initialize BAEL."""
        logger.info("=" * 60)
        print(BANNER)
        logger.info("=" * 60)
        logger.info("🚀 Initializing BAEL - The Lord of All AI Agents...")

        # Initialize brain
        self.brain = BaelBrain(self.config_path)
        await self.brain.initialize()

        # Initialize orchestrator
        self.orchestrator = AgentOrchestrator(self.brain)

        # Initialize Ultimate Orchestrator if available
        if ULTIMATE_AVAILABLE:
            try:
                mode_enum = BAELMode(self.mode)
                self.ultimate = await create_ultimate(mode=self.mode)
                logger.info(f"✅ Ultimate Orchestrator initialized in {self.mode} mode")
            except Exception as e:
                logger.warning(f"Could not initialize Ultimate Orchestrator: {e}")

        # Initialize Unified Toolkit if available
        if TOOLKIT_AVAILABLE:
            try:
                self.toolkit = UnifiedToolkit()
                tool_count = len(self.toolkit.list_tools())
                logger.info(f"✅ Unified Toolkit initialized with {tool_count} tools")
            except Exception as e:
                logger.warning(f"Could not initialize Unified Toolkit: {e}")

        self.initialized = True
        logger.info("✅ BAEL is fully operational and ready to serve")
        logger.info("=" * 60)

    async def think(self, input_text: str, context: Optional[dict] = None) -> str:
        """
        Process input and generate response.

        This is the main entry point for interacting with BAEL.
        Uses Ultimate Orchestrator when available for enhanced capabilities.
        """
        if not self.initialized:
            await self.initialize()

        # Use Ultimate Orchestrator if available for enhanced processing
        if self.ultimate:
            result = await self.ultimate.process(input_text, context)
            if result.success:
                return result.response

        # Fallback to brain processing
        return await self.brain.process(input_text, context)

    async def think_with_capabilities(
        self,
        input_text: str,
        capabilities: Optional[list] = None,
        context: Optional[dict] = None
    ) -> dict:
        """
        Process input with specific capabilities.

        Returns full result including reasoning path and metadata.
        """
        if not self.initialized:
            await self.initialize()

        if not self.ultimate:
            return {
                "success": True,
                "response": await self.brain.process(input_text, context),
                "capabilities_used": [],
                "reasoning_path": []
            }

        # Convert string capability names to Capability enum
        preferred_caps = None
        if capabilities and ULTIMATE_AVAILABLE:
            preferred_caps = []
            for cap_name in capabilities:
                try:
                    preferred_caps.append(Capability(cap_name))
                except ValueError:
                    logger.warning(f"Unknown capability: {cap_name}")

        result = await self.ultimate.process(input_text, context, preferred_caps)
        return result.to_dict()

    async def use_tool(self, tool_name: str, **kwargs) -> dict:
        """
        Use a specific tool from the Unified Toolkit.
        """
        if not self.initialized:
            await self.initialize()

        if not self.toolkit:
            return {"error": "Toolkit not available"}

        try:
            result = await self.toolkit.execute_tool(tool_name, **kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_available_tools(self) -> list:
        """List all available tools."""
        if not self.toolkit:
            return []
        return self.toolkit.list_tools()

    async def get_capabilities(self) -> list:
        """Get list of available capabilities."""
        if not self.ultimate:
            return ["basic_reasoning"]
        return self.ultimate.get_capabilities()

    async def execute_workflow(
        self,
        task: str,
        workflow_name: str = "full_development"
    ) -> dict:
        """Execute a predefined workflow."""
        if not self.initialized:
            await self.initialize()

        workflows = {
            'code_review': WorkflowPattern.code_review(),
            'research_and_implement': WorkflowPattern.research_and_implement(),
            'full_development': WorkflowPattern.full_development()
        }

        workflow = workflows.get(workflow_name, WorkflowPattern.full_development())

        return await self.orchestrator.run_workflow(task, workflow)

    async def spawn_team(self, task: str, roles: Optional[list] = None) -> list:
        """Spawn a team of agents for a task."""
        if not self.initialized:
            await self.initialize()

        return await self.orchestrator.spawn_team(task, roles)

    async def chat(self):
        """Interactive chat mode."""
        if not self.initialized:
            await self.initialize()

        print("\n🔥 BAEL Interactive Mode")
        print("Type 'exit' to quit, 'help' for commands")
        print("-" * 40)

        while True:
            try:
                user_input = input("\n👤 You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() == 'exit':
                    print("\n👋 BAEL signing off. Until we meet again...")
                    break

                if user_input.lower() == 'help':
                    self._print_help()
                    continue

                if user_input.lower() == 'status':
                    self._print_status()
                    continue

                if user_input.lower() == 'capabilities':
                    caps = await self.get_capabilities()
                    print(f"\n📋 Available Capabilities ({len(caps)}):")
                    for cap in caps:
                        print(f"  • {cap}")
                    continue

                if user_input.lower() == 'tools':
                    tools = await self.list_available_tools()
                    print(f"\n🔧 Available Tools ({len(tools)}):")
                    for tool in tools:
                        print(f"  • {tool}")
                    continue

                # Process input
                response = await self.think(user_input)
                print(f"\n🤖 BAEL: {response}")

            except KeyboardInterrupt:
                print("\n\n👋 BAEL signing off. Until we meet again...")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"\n❌ Error: {e}")

    def _print_help(self):
        """Print help message."""
        help_text = """
Available Commands:
  exit         - Exit BAEL
  status       - Show current status
  capabilities - List all available capabilities
  tools        - List all available tools
  help         - Show this help message

You can also just type any question or task and BAEL will process it.

Examples:
  - "Help me design a REST API for a todo app"
  - "Research best practices for Python async programming"
  - "Implement a binary search tree in Python"
  - "Review this code for security issues: [paste code]"
  - "Create a web scraper to extract product data"
  - "Analyze the causal factors behind system failure"
"""
        print(help_text)

    def _print_status(self):
        """Print current status."""
        if not self.brain:
            print("❌ BAEL not initialized")
            return

        state = self.brain.get_state()

        ultimate_status = "Not Available"
        if self.ultimate:
            status = self.ultimate.get_status()
            ultimate_status = f"Active ({status['mode']} mode, {len(status['loaded_components'])} components)"

        toolkit_status = "Not Available"
        if self.toolkit:
            toolkit_status = f"Active ({len(self.toolkit.list_tools())} tools)"

        print(f"""
BAEL Status:
  Session ID: {state['session_id']}
  Active Task: {state['active_task'] or 'None'}
  Active Personas: {', '.join(state['active_personas']) or 'None'}
  Confidence: {state['confidence']:.2%}
  Creativity Mode: {state['creativity_mode']}
  Energy Level: {state['energy_level']:.2%}
  Tasks Completed: {state['tasks_completed']}
  Tasks Pending: {state['tasks_pending']}

  Ultimate Orchestrator: {ultimate_status}
  Unified Toolkit: {toolkit_status}
""")

    async def shutdown(self):
        """Shutdown BAEL."""
        logger.info("🛑 Shutting down BAEL...")

        if self.orchestrator:
            await self.orchestrator.terminate_all()

        if self.brain:
            await self.brain.shutdown()

        logger.info("✅ BAEL shutdown complete")


# =============================================================================
# CLI INTERFACE
# =============================================================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BAEL - The Lord of All AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py chat                    # Interactive chat mode
  python main.py chat --mode maximum     # Chat with all capabilities
  python main.py process "Your task"     # Process a single task
  python main.py workflow "task" -w code_review  # Run workflow
  python main.py team "task" -r executor reviewer  # Spawn agent team
  python main.py tool web_search --query "AI news"  # Use a specific tool
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Interactive chat mode')
    chat_parser.add_argument('--mode', default='standard',
                            choices=['minimal', 'standard', 'maximum', 'autonomous'],
                            help='BAEL operating mode')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process a single task')
    process_parser.add_argument('task', help='Task to process')
    process_parser.add_argument('--mode', default='standard',
                               choices=['minimal', 'standard', 'maximum', 'autonomous'],
                               help='BAEL operating mode')
    process_parser.add_argument('--capabilities', nargs='+',
                               help='Specific capabilities to use')

    # Workflow command
    workflow_parser = subparsers.add_parser('workflow', help='Run a workflow')
    workflow_parser.add_argument('task', help='Task for the workflow')
    workflow_parser.add_argument('-w', '--workflow', default='full_development',
                                 choices=['code_review', 'research_and_implement', 'full_development'],
                                 help='Workflow to run')

    # Team command
    team_parser = subparsers.add_parser('team', help='Spawn a team of agents')
    team_parser.add_argument('task', help='Task for the team')
    team_parser.add_argument('-r', '--roles', nargs='+', default=['coordinator', 'executor', 'reviewer'],
                            help='Roles for the team')

    # Tool command
    tool_parser = subparsers.add_parser('tool', help='Use a specific tool')
    tool_parser.add_argument('tool_name', help='Name of the tool to use')
    tool_parser.add_argument('--args', nargs='*', help='Tool arguments as key=value pairs')

    # List command
    list_parser = subparsers.add_parser('list', help='List capabilities or tools')
    list_parser.add_argument('what', choices=['capabilities', 'tools', 'workflows'],
                            help='What to list')

    # Global options
    parser.add_argument('-c', '--config', default='config/settings/main.yaml',
                       help='Path to configuration file')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('-m', '--mode', default='standard',
                       choices=['minimal', 'standard', 'maximum', 'autonomous'],
                       help='Default BAEL operating mode')

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get mode from command-specific or global option
    mode = getattr(args, 'mode', 'standard')

    # Initialize BAEL
    bael = BAEL(config_path=args.config, mode=mode)

    try:
        if args.command == 'chat' or args.command is None:
            await bael.chat()

        elif args.command == 'process':
            if hasattr(args, 'capabilities') and args.capabilities:
                result = await bael.think_with_capabilities(
                    args.task,
                    capabilities=args.capabilities
                )
                print(f"\n🤖 BAEL Response:")
                print(f"  {result.get('response', '')}")
                print(f"\n📋 Capabilities Used: {', '.join(result.get('capabilities_used', []))}")
                print(f"🧠 Reasoning Path: {' → '.join(result.get('reasoning_path', []))}")
            else:
                response = await bael.think(args.task)
                print(f"\n🤖 BAEL: {response}")

        elif args.command == 'workflow':
            result = await bael.execute_workflow(args.task, args.workflow)
            print(f"\n📋 Workflow Result:")
            print(json.dumps(result, indent=2, default=str))

        elif args.command == 'team':
            agents = await bael.spawn_team(args.task, args.roles)
            result = await bael.orchestrator.run_all()
            print(f"\n👥 Team Result:")
            print(json.dumps(result, indent=2, default=str))

        elif args.command == 'tool':
            # Parse tool arguments
            tool_args = {}
            if args.args:
                for arg in args.args:
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        tool_args[key] = value

            result = await bael.use_tool(args.tool_name, **tool_args)
            print(f"\n🔧 Tool Result:")
            print(json.dumps(result, indent=2, default=str))

        elif args.command == 'list':
            if args.what == 'capabilities':
                await bael.initialize()
                caps = await bael.get_capabilities()
                print(f"\n📋 Available Capabilities ({len(caps)}):")
                for cap in caps:
                    print(f"  • {cap}")

            elif args.what == 'tools':
                await bael.initialize()
                tools = await bael.list_available_tools()
                print(f"\n🔧 Available Tools ({len(tools)}):")
                for tool in tools:
                    print(f"  • {tool}")

            elif args.what == 'workflows':
                print("\n📋 Available Workflows:")
                print("  • code_review - Review code for quality and issues")
                print("  • research_and_implement - Research then implement")
                print("  • full_development - Complete development cycle")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

    finally:
        await bael.shutdown()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import json
    asyncio.run(main())
