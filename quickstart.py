#!/usr/bin/env python3
"""
BAEL Quick Start - Ultimate Developer Experience
One command to rule them all.
"""

import asyncio
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# Colors
class Colors:
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

def print_banner():
    banner = f"""{Colors.PURPLE}
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║    ██████╗  █████╗ ███████╗██╗         {Colors.CYAN}Quick Start{Colors.PURPLE}                            ║
║    ██╔══██╗██╔══██╗██╔════╝██║         {Colors.DIM}The Lord of All AI Agents{Colors.RESET}{Colors.PURPLE}           ║
║    ██████╔╝███████║█████╗  ██║                                               ║
║    ██╔══██╗██╔══██║██╔══╝  ██║         {Colors.GREEN}v3.0 Transcendent Edition{Colors.PURPLE}             ║
║    ██████╔╝██║  ██║███████╗███████╗                                          ║
║    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝    {Colors.YELLOW}⚡ 500+ modules ready{Colors.PURPLE}                 ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
{Colors.RESET}"""
    print(banner)

def status(msg, state="info"):
    icons = {"info": "→", "ok": "✓", "warn": "⚠", "error": "✗", "wait": "◌"}
    colors = {"info": Colors.CYAN, "ok": Colors.GREEN, "warn": Colors.YELLOW, "error": Colors.RED, "wait": Colors.DIM}
    print(f"  {colors.get(state, Colors.CYAN)}{icons.get(state, '→')}{Colors.RESET} {msg}")

def check_python():
    """Verify Python version."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        status(f"Python {version.major}.{version.minor}.{version.micro}", "ok")
        return True
    else:
        status(f"Python {version.major}.{version.minor} - need 3.8+", "error")
        return False

def check_venv():
    """Check if virtual environment exists."""
    venv_path = Path(__file__).parent / ".venv"
    if venv_path.exists() and (venv_path / "bin" / "python").exists():
        status("Virtual environment exists", "ok")
        return True
    else:
        status("Virtual environment not found - will create", "warn")
        return False

def create_venv():
    """Create virtual environment."""
    status("Creating virtual environment...", "wait")
    subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
    status("Virtual environment created", "ok")

def install_deps():
    """Install dependencies."""
    status("Installing dependencies...", "wait")
    pip_path = Path(".venv/bin/pip")

    # Upgrade pip first
    subprocess.run([str(pip_path), "install", "--upgrade", "pip", "-q"], check=True)

    # Install requirements
    if Path("requirements.txt").exists():
        result = subprocess.run(
            [str(pip_path), "install", "-r", "requirements.txt", "-q"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            # Fall back to minimal deps
            status("Installing minimal dependencies...", "warn")
            minimal = ["fastapi", "uvicorn", "pydantic", "httpx", "aiohttp", "python-dotenv", "pyyaml", "anthropic", "openai"]
            subprocess.run([str(pip_path), "install"] + minimal + ["-q"], check=True)

    status("Dependencies installed", "ok")

def check_api_keys():
    """Check for required API keys."""
    from dotenv import load_dotenv
    load_dotenv()

    keys = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
    }

    has_any = False
    for key, value in keys.items():
        if value:
            masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            status(f"{key}: {masked}", "ok")
            has_any = True

    if not has_any:
        status("No API keys found - create a .env file", "warn")
        print(f"\n    {Colors.DIM}Example .env file:{Colors.RESET}")
        print(f"    {Colors.YELLOW}ANTHROPIC_API_KEY=sk-ant-...{Colors.RESET}")
        print(f"    {Colors.YELLOW}OPENROUTER_API_KEY=sk-or-...{Colors.RESET}")
        print()

    return has_any

def check_port(port: int) -> bool:
    """Check if a port is available."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def kill_port(port: int):
    """Kill process on port."""
    subprocess.run(f"lsof -ti:{port} | xargs kill -9 2>/dev/null", shell=True)
    time.sleep(0.5)

def start_api_server():
    """Start the API server."""
    status("Starting API server on port 8000...", "wait")

    if not check_port(8000):
        status("Port 8000 in use, killing existing process...", "warn")
        kill_port(8000)

    # Start server in background
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent)

    process = subprocess.Popen(
        [".venv/bin/python", "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True
    )

    # Wait for server to be ready
    for _ in range(30):
        time.sleep(0.5)
        if not check_port(8000):
            status(f"API server running at http://localhost:8000", "ok")
            return process

    status("API server failed to start - check logs", "error")
    return None

def test_api():
    """Quick API health check."""
    import json
    import urllib.request

    status("Testing API health...", "wait")
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as response:
            data = json.loads(response.read().decode())
            status(f"API healthy - version: {data.get('version', 'unknown')}", "ok")
            return True
    except Exception as e:
        status(f"API test failed: {e}", "error")
        return False

def print_quick_commands():
    """Print helpful commands."""
    print(f"""
{Colors.CYAN}═══════════════════════════════════════════════════════════════════════════════{Colors.RESET}
{Colors.BOLD}Quick Commands:{Colors.RESET}

  {Colors.YELLOW}API Endpoints:{Colors.RESET}
    curl -X POST http://localhost:8000/think -H "Content-Type: application/json" \\
         -d '{{"input": "Hello BAEL"}}'

  {Colors.YELLOW}Interactive Mode:{Colors.RESET}
    source .venv/bin/activate && python cli.py

  {Colors.YELLOW}VS Code Tasks:{Colors.RESET}
    Cmd+Shift+P → "Tasks: Run Task" → Select BAEL task

  {Colors.YELLOW}Makefile Commands:{Colors.RESET}
    make run     - Start API server
    make ui      - Start web UI
    make test    - Run tests
    make lint    - Check code quality

{Colors.CYAN}═══════════════════════════════════════════════════════════════════════════════{Colors.RESET}
""")

def main():
    """Main quick start flow."""
    os.chdir(Path(__file__).parent)

    print_banner()
    print(f"{Colors.BOLD}Preflight Checks:{Colors.RESET}")

    # Check Python
    if not check_python():
        print(f"\n{Colors.RED}Error: Python 3.8+ required{Colors.RESET}")
        sys.exit(1)

    # Check/create venv
    if not check_venv():
        create_venv()

    # Install dependencies
    install_deps()

    print(f"\n{Colors.BOLD}API Keys:{Colors.RESET}")
    check_api_keys()

    print(f"\n{Colors.BOLD}Starting Services:{Colors.RESET}")
    api_process = start_api_server()

    if api_process:
        time.sleep(2)
        test_api()

    print_quick_commands()

    print(f"{Colors.GREEN}{Colors.BOLD}🔥 BAEL is ready!{Colors.RESET}")
    print(f"{Colors.DIM}Press Ctrl+C to stop the server{Colors.RESET}\n")

    # Keep running
    if api_process:
        try:
            api_process.wait()
        except KeyboardInterrupt:
            status("\nShutting down...", "info")
            api_process.terminate()
            status("BAEL stopped", "ok")

if __name__ == "__main__":
    main()
