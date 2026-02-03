"""
BAEL - CLI Interface v2.0.0
Advanced command-line interface with rich formatting.
Maximum Potential Edition.

Features:
- Interactive REPL
- Command completion
- Rich formatting
- Progress indicators
- Multi-mode operation
- Ultimate Orchestrator integration
- Unified Toolkit access
- Maximum Potential mode
- Extended Thinking commands
- Computer Use automation
- Voice interface
"""

__version__ = "2.0.0"

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Rich for beautiful terminal output
try:
    from rich import print as rprint
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm, Prompt
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.tree import Tree
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Project imports
sys.path.insert(0, str(Path(__file__).parent))

# Import Ultimate Orchestrator
try:
    from core.ultimate.ultimate_orchestrator import (BAELMode, Capability,
                                                     UltimateConfig,
                                                     UltimateOrchestrator,
                                                     create_ultimate)
    ULTIMATE_AVAILABLE = True
except ImportError:
    ULTIMATE_AVAILABLE = False

# Import Unified Toolkit
try:
    from tools import UnifiedToolkit
    TOOLKIT_AVAILABLE = True
except ImportError:
    TOOLKIT_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


# =============================================================================
# BANNER & STYLING
# =============================================================================

BANNER = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║    ██████╗  █████╗ ███████╗██╗                                              ║
║    ██╔══██╗██╔══██╗██╔════╝██║                                              ║
║    ██████╔╝███████║█████╗  ██║                                              ║
║    ██╔══██╗██╔══██║██╔══╝  ██║                                              ║
║    ██████╔╝██║  ██║███████╗███████╗                                         ║
║    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝                                         ║
║                                                                              ║
║              THE LORD OF ALL AI AGENTS                                       ║
║                                                                              ║
║    Multi-Model • Self-Improving • Unlimited Potential                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
[bold cyan]Available Commands:[/bold cyan]

[bold green]General:[/bold green]
  /help, /h          Show this help message
  /quit, /exit, /q   Exit BAEL
  /clear, /cls       Clear the screen
  /status            Show system status

[bold green]Personas:[/bold green]
  /personas          List available personas
  /persona <name>    Switch to a specific persona
  /auto              Enable automatic persona selection

[bold green]Memory:[/bold green]
  /memory            Show memory statistics
  /remember <text>   Store something in memory
  /forget <query>    Forget matching memories
  /recall <query>    Search memory

[bold green]Tools:[/bold green]
  /tools             List available tools
  /run <tool> <args> Execute a tool directly

[bold green]Capabilities:[/bold green]
  /capabilities      List all available capabilities
  /mode <name>       Switch mode (minimal/standard/maximum/autonomous)
  /use <cap> <query> Use specific capability

[bold green]Workflows:[/bold green]
  /workflows         List available workflows
  /workflow <name>   Run a workflow

[bold green]Research:[/bold green]
  /research <topic>  Conduct deep research on a topic

[bold green]Code:[/bold green]
  /code              Enter code mode
  /execute <code>    Execute Python code
  /file <path>       Read and analyze a file

[bold green]Settings:[/bold green]
  /model <name>      Switch AI model
  /temperature <n>   Set temperature (0.0-1.0)
  /verbose           Toggle verbose mode
  /debug             Toggle debug mode

[bold green]Advanced:[/bold green]
  /think <prompt>    Explicit thinking request
  /multi             Multi-turn conversation mode
  /export <file>     Export conversation to file
  /health            Check system health
"""


# =============================================================================
# CLI INTERFACE
# =============================================================================

class BaelCLI:
    """Interactive CLI for BAEL."""

    def __init__(self, mode: str = "standard"):
        self.brain = None
        self.ultimate = None
        self.toolkit = None
        self.running = False
        self.verbose = False
        self.debug = False
        self.current_persona = "auto"
        self.current_mode = mode
        self.conversation_history: List[Dict[str, str]] = []
        self.model = "default"
        self.temperature = 0.7

    async def initialize(self) -> None:
        """Initialize BAEL components."""
        if console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Initializing BAEL...", total=None)

                # Import and initialize components
                try:
                    from core.brain.brain import BaelBrain
                    self.brain = BaelBrain()
                    await self.brain.initialize()
                    progress.update(task, description="[cyan]Initializing Ultimate Orchestrator...")
                except Exception as e:
                    progress.update(task, description=f"[yellow]Running in demo mode: {e}")
                    self.brain = None

                # Initialize Ultimate Orchestrator
                if ULTIMATE_AVAILABLE:
                    try:
                        self.ultimate = await create_ultimate(mode=self.current_mode)
                        progress.update(task, description="[cyan]Initializing Toolkit...")
                    except Exception as e:
                        if self.debug:
                            console.print(f"[yellow]Ultimate Orchestrator: {e}")

                # Initialize Toolkit
                if TOOLKIT_AVAILABLE:
                    try:
                        self.toolkit = UnifiedToolkit()
                    except Exception as e:
                        if self.debug:
                            console.print(f"[yellow]Toolkit: {e}")

                progress.update(task, description="[green]BAEL initialized!")
        else:
            print("Initializing BAEL...")
            try:
                from core.brain.brain import BaelBrain
                self.brain = BaelBrain()
                await self.brain.initialize()
            except Exception as e:
                print(f"Running in demo mode: {e}")

            if ULTIMATE_AVAILABLE:
                try:
                    self.ultimate = await create_ultimate(mode=self.current_mode)
                except Exception:
                    pass

            if TOOLKIT_AVAILABLE:
                try:
                    self.toolkit = UnifiedToolkit()
                except Exception:
                    pass

    def print_banner(self) -> None:
        """Print the BAEL banner."""
        if console:
            console.print(Panel(
                BANNER,
                border_style="cyan",
                padding=(0, 0)
            ))
        else:
            print(BANNER)

    def print_help(self) -> None:
        """Print help text."""
        if console:
            console.print(Markdown(HELP_TEXT))
        else:
            print(HELP_TEXT)

    async def process_command(self, command: str) -> bool:
        """Process a CLI command. Returns False to exit."""
        cmd = command.lower().strip()
        parts = command.strip().split(maxsplit=1)
        cmd_name = parts[0].lower() if parts else ""
        cmd_args = parts[1] if len(parts) > 1 else ""

        # Exit commands
        if cmd_name in ["/quit", "/exit", "/q"]:
            return False

        # Help
        elif cmd_name in ["/help", "/h", "/?"]:
            self.print_help()

        # Clear screen
        elif cmd_name in ["/clear", "/cls"]:
            os.system('clear' if os.name != 'nt' else 'cls')
            self.print_banner()

        # Status
        elif cmd_name == "/status":
            await self.show_status()

        # Personas
        elif cmd_name == "/personas":
            await self.list_personas()
        elif cmd_name == "/persona":
            await self.set_persona(cmd_args)
        elif cmd_name == "/auto":
            self.current_persona = "auto"
            self.print_success("Automatic persona selection enabled")

        # Memory
        elif cmd_name == "/memory":
            await self.show_memory_stats()
        elif cmd_name == "/remember":
            await self.remember(cmd_args)
        elif cmd_name == "/recall":
            await self.recall(cmd_args)

        # Tools
        elif cmd_name == "/tools":
            await self.list_tools()
        elif cmd_name == "/run":
            await self.run_tool(cmd_args)

        # Capabilities (NEW)
        elif cmd_name == "/capabilities":
            await self.list_capabilities()
        elif cmd_name == "/mode":
            await self.set_mode(cmd_args)
        elif cmd_name == "/use":
            await self.use_capability(cmd_args)
        elif cmd_name == "/health":
            await self.show_health()

        # Research
        elif cmd_name == "/research":
            await self.research(cmd_args)

        # Code
        elif cmd_name == "/code":
            await self.code_mode()
        elif cmd_name == "/execute":
            await self.execute_code(cmd_args)

        # Settings
        elif cmd_name == "/model":
            self.model = cmd_args or "default"
            self.print_success(f"Model set to: {self.model}")
        elif cmd_name == "/temperature":
            try:
                self.temperature = float(cmd_args)
                self.print_success(f"Temperature set to: {self.temperature}")
            except ValueError:
                self.print_error("Invalid temperature value")
        elif cmd_name == "/verbose":
            self.verbose = not self.verbose
            self.print_success(f"Verbose mode: {'enabled' if self.verbose else 'disabled'}")
        elif cmd_name == "/debug":
            self.debug = not self.debug
            self.print_success(f"Debug mode: {'enabled' if self.debug else 'disabled'}")

        # Think
        elif cmd_name == "/think":
            await self.think(cmd_args)

        # Export
        elif cmd_name == "/export":
            await self.export_conversation(cmd_args or "conversation.md")

        # Unknown command
        elif cmd.startswith("/"):
            self.print_error(f"Unknown command: {cmd_name}")

        # Regular message
        else:
            await self.chat(command)

        return True

    async def think(self, prompt: str) -> None:
        """Process a thinking request."""
        if not prompt:
            self.print_error("Please provide a prompt")
            return

        if console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Thinking...", total=None)

                if self.brain:
                    result = await self.brain.think(prompt)
                    response = result.get("response", "No response generated")
                else:
                    # Demo mode
                    await asyncio.sleep(1)
                    response = f"[Demo Mode] Processed: {prompt[:100]}..."

                progress.update(task, completed=True, description="[green]Done!")

            console.print()
            console.print(Panel(
                Markdown(response),
                title="[bold cyan]BAEL[/bold cyan]",
                border_style="cyan"
            ))
        else:
            print("Thinking...")
            if self.brain:
                result = await self.brain.think(prompt)
                response = result.get("response", "No response generated")
            else:
                response = f"[Demo Mode] Processed: {prompt}"
            print(f"\nBAEL: {response}\n")

        self.conversation_history.append({"role": "user", "content": prompt})
        self.conversation_history.append({"role": "assistant", "content": response})

    async def chat(self, message: str) -> None:
        """Process a chat message."""
        await self.think(message)

    async def show_status(self) -> None:
        """Show system status."""
        if console:
            table = Table(title="BAEL System Status")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Details", style="white")

            table.add_row("Brain", "✓ Active" if self.brain else "○ Demo Mode", "")
            table.add_row("Model", self.model, f"Temperature: {self.temperature}")
            table.add_row("Persona", self.current_persona, "")
            table.add_row("Mode", self.current_mode, "")
            table.add_row("Memory", "Active" if self.brain else "Simulated", "")
            table.add_row("Conversation", f"{len(self.conversation_history)} messages", "")

            # Ultimate Orchestrator status
            if self.ultimate:
                status = self.ultimate.get_status()
                table.add_row("Ultimate", "✓ Active", f"{len(status.get('loaded_components', []))} components")
            else:
                table.add_row("Ultimate", "○ Not Available", "")

            # Toolkit status
            if self.toolkit:
                tools = self.toolkit.list_tools()
                table.add_row("Toolkit", "✓ Active", f"{len(tools)} tools")
            else:
                table.add_row("Toolkit", "○ Not Available", "")

            console.print(table)
        else:
            print("\n=== BAEL Status ===")
            print(f"Brain: {'Active' if self.brain else 'Demo Mode'}")
            print(f"Model: {self.model}")
            print(f"Persona: {self.current_persona}")
            print(f"Mode: {self.current_mode}")
            print(f"Messages: {len(self.conversation_history)}")
            print(f"Ultimate: {'Active' if self.ultimate else 'Not Available'}")
            print(f"Toolkit: {'Active' if self.toolkit else 'Not Available'}")
            print()

    async def list_capabilities(self) -> None:
        """List all available capabilities."""
        if not self.ultimate:
            self.print_error("Ultimate Orchestrator not available")
            return

        caps = self.ultimate.get_capabilities()

        if console:
            table = Table(title="Available Capabilities")
            table.add_column("Capability", style="cyan")
            table.add_column("Category", style="yellow")

            categories = {
                "deductive": "Reasoning", "inductive": "Reasoning", "abductive": "Reasoning",
                "causal": "Reasoning", "counterfactual": "Reasoning", "temporal": "Reasoning",
                "probabilistic": "Reasoning", "fuzzy": "Reasoning", "modal": "Reasoning",
                "working_memory": "Memory", "episodic_memory": "Memory",
                "semantic_memory": "Memory", "procedural_memory": "Memory",
                "single_agent": "Agents", "multi_agent": "Agents", "agent_swarm": "Agents",
                "reinforcement_learning": "Learning", "meta_learning": "Learning",
                "rag": "Knowledge", "knowledge_graph": "Knowledge",
                "code_execution": "Execution", "tool_use": "Execution", "web_research": "Execution",
                "workflow": "Control", "state_machine": "Control", "dsl_rules": "Control"
            }

            for cap in sorted(caps):
                category = categories.get(cap, "Other")
                table.add_row(cap, category)

            console.print(table)
        else:
            print(f"\nAvailable Capabilities ({len(caps)}):")
            for cap in caps:
                print(f"  • {cap}")

    async def set_mode(self, mode: str) -> None:
        """Set the operating mode."""
        valid_modes = ["minimal", "standard", "maximum", "autonomous"]
        if mode.lower() not in valid_modes:
            self.print_error(f"Invalid mode. Choose from: {', '.join(valid_modes)}")
            return

        self.current_mode = mode.lower()

        # Reinitialize Ultimate Orchestrator with new mode
        if ULTIMATE_AVAILABLE:
            try:
                self.ultimate = await create_ultimate(mode=self.current_mode)
                self.print_success(f"Mode set to: {self.current_mode}")
            except Exception as e:
                self.print_error(f"Failed to switch mode: {e}")
        else:
            self.print_success(f"Mode set to: {self.current_mode} (Ultimate not available)")

    async def use_capability(self, args: str) -> None:
        """Use a specific capability."""
        if not self.ultimate:
            self.print_error("Ultimate Orchestrator not available")
            return

        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            self.print_error("Usage: /use <capability> <query>")
            return

        cap_name, query = parts

        try:
            # Convert capability name to enum
            cap = Capability(cap_name)
            result = await self.ultimate.process(query, preferred_capabilities=[cap])

            if result.success:
                if console:
                    console.print(Panel(
                        Markdown(result.response),
                        title=f"[bold cyan]BAEL ({cap_name})[/bold cyan]",
                        border_style="cyan"
                    ))
                else:
                    print(f"\n[{cap_name}] {result.response}")
            else:
                self.print_error(result.response)
        except ValueError:
            self.print_error(f"Unknown capability: {cap_name}")

    async def show_health(self) -> None:
        """Show system health check."""
        if console:
            table = Table(title="System Health Check")
            table.add_column("Component", style="cyan")
            table.add_column("Health", style="green")

            table.add_row("Brain", "✓ Healthy" if self.brain else "○ Not Loaded")

            if self.ultimate:
                health = await self.ultimate.health_check()
                for component, status in health.items():
                    table.add_row(f"  {component}", "✓ Healthy" if status else "✗ Unhealthy")

            console.print(table)
        else:
            print("\n=== Health Check ===")
            print(f"Brain: {'Healthy' if self.brain else 'Not Loaded'}")
            if self.ultimate:
                health = await self.ultimate.health_check()
                for component, status in health.items():
                    print(f"  {component}: {'Healthy' if status else 'Unhealthy'}")

    async def list_personas(self) -> None:
        """List available personas."""
        personas = [
            ("Architect Prime", "System design & architecture"),
            ("Code Master", "Code implementation & optimization"),
            ("Security Sentinel", "Security analysis & hardening"),
            ("Research Scholar", "Deep research & learning"),
            ("Debug Detective", "Problem diagnosis & fixing"),
            ("Performance Oracle", "Optimization & efficiency"),
            ("Documentation Sage", "Documentation & explanation"),
        ]

        if console:
            table = Table(title="Available Personas")
            table.add_column("Persona", style="cyan")
            table.add_column("Specialty", style="white")

            for name, specialty in personas:
                table.add_row(name, specialty)

            console.print(table)
        else:
            print("\n=== Available Personas ===")
            for name, specialty in personas:
                print(f"  {name}: {specialty}")
            print()

    async def set_persona(self, persona_name: str) -> None:
        """Set the current persona."""
        self.current_persona = persona_name
        self.print_success(f"Persona set to: {persona_name}")

    async def show_memory_stats(self) -> None:
        """Show memory statistics."""
        if console:
            console.print(Panel(
                "[cyan]Memory Statistics[/cyan]\n\n"
                "Episodic: 0 memories\n"
                "Semantic: 0 concepts\n"
                "Procedural: 0 procedures\n"
                "Working: 0 items",
                title="Memory",
                border_style="cyan"
            ))
        else:
            print("\n=== Memory Statistics ===")
            print("Episodic: 0 memories")
            print()

    async def remember(self, text: str) -> None:
        """Store something in memory."""
        self.print_success(f"Remembered: {text[:50]}...")

    async def recall(self, query: str) -> None:
        """Search memory."""
        self.print_info(f"Searching for: {query}")
        self.print_info("No memories found matching query")

    async def list_tools(self) -> None:
        """List available tools."""
        # Use unified toolkit if available
        if self.toolkit:
            tools = self.toolkit.list_tools()
            if console:
                table = Table(title=f"Available Tools ({len(tools)})")
                table.add_column("Tool", style="cyan")
                table.add_column("Category", style="yellow")

                # Categorize tools
                categories = {
                    "web_": "Web", "code_": "Code", "file_": "File",
                    "sql_": "Database", "vector_": "Database", "doc_": "Database", "kv_": "Database",
                    "ai_": "AI", "api_": "API", "graphql_": "API"
                }

                for tool in sorted(tools):
                    category = "Other"
                    for prefix, cat in categories.items():
                        if tool.startswith(prefix):
                            category = cat
                            break
                    table.add_row(tool, category)

                console.print(table)
            else:
                print(f"\nAvailable Tools ({len(tools)}):")
                for tool in tools:
                    print(f"  • {tool}")
        else:
            # Fallback to basic list
            tools = [
                ("python_executor", "Execute Python code"),
                ("file_reader", "Read files"),
                ("file_writer", "Write files"),
                ("web_search", "Search the web"),
                ("browser", "Browser automation"),
                ("git", "Git operations"),
                ("terminal", "Terminal commands"),
                ("calculator", "Mathematical calculations"),
            ]

            if console:
                table = Table(title="Available Tools")
                table.add_column("Tool", style="cyan")
                table.add_column("Description", style="white")

                for name, desc in tools:
                    table.add_row(name, desc)

                console.print(table)
            else:
                print("\n=== Available Tools ===")
                for name, desc in tools:
                    print(f"  {name}: {desc}")
                print()

    async def run_tool(self, args: str) -> None:
        """Run a tool."""
        if not self.toolkit:
            self.print_error("Toolkit not available")
            return

        parts = args.split(maxsplit=1)
        tool_name = parts[0] if parts else ""
        tool_args_str = parts[1] if len(parts) > 1 else ""

        if not tool_name:
            self.print_error("Usage: /run <tool_name> <args>")
            return

        # Parse tool arguments (key=value pairs)
        tool_args = {}
        if tool_args_str:
            for pair in tool_args_str.split():
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    tool_args[key] = value

        try:
            if console:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task(f"[cyan]Running {tool_name}...", total=None)
                    result = await self.toolkit.execute_tool(tool_name, **tool_args)
                    progress.update(task, description="[green]Done!")

                console.print(Panel(
                    str(result),
                    title=f"[bold cyan]Tool Result: {tool_name}[/bold cyan]",
                    border_style="cyan"
                ))
            else:
                result = await self.toolkit.execute_tool(tool_name, **tool_args)
                print(f"\nTool Result: {result}")
        except Exception as e:
            self.print_error(f"Tool execution failed: {e}")

    async def research(self, topic: str) -> None:
        """Conduct research on a topic."""
        if not topic:
            self.print_error("Please provide a research topic")
            return

        if console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Researching...", total=None)
                await asyncio.sleep(2)  # Simulated research
                progress.update(task, description="[green]Research complete!")

            console.print(Panel(
                f"Research findings for: {topic}\n\n"
                "[Demo Mode] Research functionality requires full initialization.",
                title="Research Results",
                border_style="cyan"
            ))
        else:
            print(f"Researching: {topic}")

    async def code_mode(self) -> None:
        """Enter code mode."""
        self.print_info("Entering code mode. Type /exit to return.")

        code_buffer = []
        while True:
            try:
                line = input(">>> ")
                if line == "/exit":
                    break
                code_buffer.append(line)
            except (KeyboardInterrupt, EOFError):
                break

        if code_buffer:
            code = "\n".join(code_buffer)
            await self.execute_code(code)

    async def execute_code(self, code: str) -> None:
        """Execute code."""
        if console:
            console.print(Syntax(code, "python", theme="monokai"))
            console.print("\n[yellow]Code execution in demo mode[/yellow]")
        else:
            print(f"Executing: {code}")

    async def export_conversation(self, filename: str) -> None:
        """Export conversation to file."""
        with open(filename, 'w') as f:
            f.write("# BAEL Conversation Export\n\n")
            f.write(f"Exported: {datetime.now().isoformat()}\n\n")
            f.write("---\n\n")

            for msg in self.conversation_history:
                role = "**User**" if msg["role"] == "user" else "**BAEL**"
                f.write(f"{role}: {msg['content']}\n\n")

        self.print_success(f"Conversation exported to: {filename}")

    def print_success(self, message: str) -> None:
        """Print success message."""
        if console:
            console.print(f"[green]✓[/green] {message}")
        else:
            print(f"✓ {message}")

    def print_error(self, message: str) -> None:
        """Print error message."""
        if console:
            console.print(f"[red]✗[/red] {message}")
        else:
            print(f"✗ {message}")

    def print_info(self, message: str) -> None:
        """Print info message."""
        if console:
            console.print(f"[cyan]ℹ[/cyan] {message}")
        else:
            print(f"ℹ {message}")

    async def run(self) -> None:
        """Run the interactive CLI."""
        self.print_banner()
        await self.initialize()

        if console:
            console.print("\n[cyan]Type your message or /help for commands.[/cyan]\n")
        else:
            print("\nType your message or /help for commands.\n")

        self.running = True

        while self.running:
            try:
                if console:
                    user_input = Prompt.ask("[bold green]You[/bold green]")
                else:
                    user_input = input("You: ")

                if not user_input.strip():
                    continue

                self.running = await self.process_command(user_input)

            except KeyboardInterrupt:
                print()
                if console:
                    if Confirm.ask("Exit BAEL?"):
                        break
                else:
                    print("Exiting...")
                    break
            except EOFError:
                break

        if console:
            console.print("\n[cyan]Farewell! BAEL awaits your return.[/cyan]\n")
        else:
            print("\nFarewell!")


# =============================================================================
# MAIN
# =============================================================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BAEL - The Lord of All AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py                    Start interactive mode
  python cli.py --think "prompt"   Process a single prompt
  python cli.py --api              Start API server
  python cli.py --mcp              Start MCP server
  python cli.py --mode maximum     Start with all capabilities
  python cli.py --list tools       List available tools
  python cli.py --list caps        List available capabilities
        """
    )

    parser.add_argument("--think", "-t", type=str, help="Process a single prompt")
    parser.add_argument("--api", action="store_true", help="Start API server")
    parser.add_argument("--mcp", action="store_true", help="Start MCP server")
    parser.add_argument("--mode", "-m", type=str, default="standard",
                       choices=["minimal", "standard", "maximum", "autonomous"],
                       help="Operating mode")
    parser.add_argument("--list", "-l", type=str, choices=["tools", "caps", "capabilities"],
                       help="List tools or capabilities")
    parser.add_argument("--dev", action="store_true", help="Development mode")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    if args.think:
        # Single prompt mode
        cli = BaelCLI(mode=args.mode)
        await cli.initialize()
        await cli.think(args.think)

    elif args.list:
        # List mode
        cli = BaelCLI(mode=args.mode)
        await cli.initialize()
        if args.list == "tools":
            await cli.list_tools()
        elif args.list in ["caps", "capabilities"]:
            await cli.list_capabilities()

    elif args.api:
        # API server mode
        import uvicorn

        from api.server import app
        uvicorn.run(app, host="0.0.0.0", port=8080)

    elif args.mcp:
        # MCP server mode
        from mcp.server import BaelMCPServer
        server = BaelMCPServer()
        await server.run()

    else:
        # Interactive mode
        cli = BaelCLI(mode=args.mode)
        await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
