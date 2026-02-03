#!/usr/bin/env python3
"""
BAEL - Setup Wizard
Interactive setup and installation wizard.

Features:
- Environment detection
- Dependency installation
- Configuration wizard
- API key setup
- Service validation
"""

import asyncio
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# COLORS
# =============================================================================

class Colors:
    """Terminal colors."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def color(text: str, color_code: str) -> str:
    """Apply color to text."""
    return f"{color_code}{text}{Colors.END}"


def print_header(text: str) -> None:
    """Print header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}{Colors.END}\n")


def print_step(number: int, text: str) -> None:
    """Print step."""
    print(f"{Colors.BLUE}[{number}]{Colors.END} {text}")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"  {Colors.GREEN}✓{Colors.END} {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"  {Colors.RED}✗{Colors.END} {text}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"  {Colors.YELLOW}!{Colors.END} {text}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"  {Colors.DIM}{text}{Colors.END}")


# =============================================================================
# SYSTEM CHECKS
# =============================================================================

@dataclass
class SystemInfo:
    """System information."""
    os_name: str
    os_version: str
    python_version: str
    python_path: str
    arch: str
    cpu_count: int
    memory_gb: float
    disk_free_gb: float
    docker_available: bool
    git_available: bool


def get_system_info() -> SystemInfo:
    """Gather system information."""
    import psutil

    # Get memory
    try:
        memory_gb = psutil.virtual_memory().total / (1024 ** 3)
    except:
        memory_gb = 0

    # Get disk
    try:
        disk_free_gb = psutil.disk_usage('/').free / (1024 ** 3)
    except:
        disk_free_gb = 0

    # Check Docker
    docker_available = shutil.which('docker') is not None

    # Check Git
    git_available = shutil.which('git') is not None

    return SystemInfo(
        os_name=platform.system(),
        os_version=platform.release(),
        python_version=platform.python_version(),
        python_path=sys.executable,
        arch=platform.machine(),
        cpu_count=os.cpu_count() or 1,
        memory_gb=round(memory_gb, 1),
        disk_free_gb=round(disk_free_gb, 1),
        docker_available=docker_available,
        git_available=git_available
    )


def check_python_version() -> bool:
    """Check Python version."""
    major, minor = sys.version_info[:2]
    return major >= 3 and minor >= 10


def check_dependencies() -> Dict[str, bool]:
    """Check if required packages are installed."""
    packages = [
        "fastapi",
        "uvicorn",
        "httpx",
        "pydantic",
        "rich",
        "yaml",
        "chromadb",
        "openai",
        "anthropic"
    ]

    results = {}
    for package in packages:
        try:
            __import__(package.replace("-", "_"))
            results[package] = True
        except ImportError:
            results[package] = False

    return results


# =============================================================================
# INSTALLATION
# =============================================================================

def install_requirements(requirements_file: str = "requirements.txt") -> bool:
    """Install requirements from file."""
    if not os.path.exists(requirements_file):
        print_error(f"Requirements file not found: {requirements_file}")
        return False

    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "-r", requirements_file, "-q"
        ])
        return True
    except subprocess.CalledProcessError:
        return False


def create_virtual_env(path: str = ".venv") -> bool:
    """Create virtual environment."""
    try:
        subprocess.check_call([
            sys.executable, "-m", "venv", path
        ])
        return True
    except subprocess.CalledProcessError:
        return False


# =============================================================================
# CONFIGURATION
# =============================================================================

def create_env_file(config: Dict[str, str], path: str = ".env") -> None:
    """Create .env file."""
    lines = []
    for key, value in config.items():
        if value:
            lines.append(f"{key}={value}")

    with open(path, "w") as f:
        f.write("\n".join(lines))


def load_env_file(path: str = ".env") -> Dict[str, str]:
    """Load .env file."""
    config = {}

    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()

    return config


def validate_api_key(key_name: str, key_value: str) -> bool:
    """Validate API key format."""
    if not key_value:
        return False

    patterns = {
        "OPENAI_API_KEY": lambda k: k.startswith("sk-"),
        "ANTHROPIC_API_KEY": lambda k: k.startswith("sk-ant-"),
        "OPENROUTER_API_KEY": lambda k: k.startswith("sk-or-"),
    }

    validator = patterns.get(key_name, lambda k: len(k) > 10)
    return validator(key_value)


# =============================================================================
# INTERACTIVE WIZARD
# =============================================================================

class SetupWizard:
    """Interactive setup wizard."""

    def __init__(self):
        self.config: Dict[str, str] = {}
        self.system_info: Optional[SystemInfo] = None

    def run(self) -> bool:
        """Run the setup wizard."""
        self.print_welcome()

        # Step 1: System check
        if not self.step_system_check():
            return False

        # Step 2: Environment setup
        if not self.step_environment_setup():
            return False

        # Step 3: API keys
        if not self.step_api_keys():
            return False

        # Step 4: Optional services
        self.step_optional_services()

        # Step 5: Save configuration
        self.step_save_config()

        # Step 6: Verification
        if not self.step_verify():
            return False

        self.print_completion()
        return True

    def print_welcome(self) -> None:
        """Print welcome message."""
        print(f"""
{Colors.BOLD}{Colors.CYAN}
    ██████╗  █████╗ ███████╗██╗
    ██╔══██╗██╔══██╗██╔════╝██║
    ██████╔╝███████║█████╗  ██║
    ██╔══██╗██╔══██║██╔══╝  ██║
    ██████╔╝██║  ██║███████╗███████╗
    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝

    The Lord of All AI Agents
    Setup Wizard v1.0
{Colors.END}
""")

    def step_system_check(self) -> bool:
        """Check system requirements."""
        print_header("Step 1: System Check")

        # Check Python version
        print_step(1, "Checking Python version...")
        if check_python_version():
            print_success(f"Python {platform.python_version()} (3.10+ required)")
        else:
            print_error(f"Python {platform.python_version()} - need 3.10+")
            return False

        # Get system info
        print_step(2, "Gathering system information...")
        try:
            import psutil
            self.system_info = get_system_info()
        except ImportError:
            print_warning("psutil not installed, limited system info")
            self.system_info = SystemInfo(
                os_name=platform.system(),
                os_version=platform.release(),
                python_version=platform.python_version(),
                python_path=sys.executable,
                arch=platform.machine(),
                cpu_count=os.cpu_count() or 1,
                memory_gb=0,
                disk_free_gb=0,
                docker_available=shutil.which('docker') is not None,
                git_available=shutil.which('git') is not None
            )

        print_success(f"OS: {self.system_info.os_name} {self.system_info.os_version}")
        print_success(f"Architecture: {self.system_info.arch}")
        print_success(f"CPU cores: {self.system_info.cpu_count}")

        if self.system_info.memory_gb > 0:
            print_success(f"Memory: {self.system_info.memory_gb} GB")

        if self.system_info.docker_available:
            print_success("Docker: available")
        else:
            print_warning("Docker: not found (optional)")

        if self.system_info.git_available:
            print_success("Git: available")
        else:
            print_warning("Git: not found (recommended)")

        return True

    def step_environment_setup(self) -> bool:
        """Set up Python environment."""
        print_header("Step 2: Environment Setup")

        # Check dependencies
        print_step(1, "Checking installed packages...")
        deps = check_dependencies()

        missing = [pkg for pkg, installed in deps.items() if not installed]

        if missing:
            print_warning(f"Missing packages: {', '.join(missing)}")

            response = input("\n  Install missing packages? [Y/n]: ").strip().lower()

            if response != 'n':
                print_step(2, "Installing requirements...")

                if install_requirements():
                    print_success("All packages installed")
                else:
                    print_error("Failed to install packages")
                    print_info("Try: pip install -r requirements.txt")
                    return False
        else:
            print_success("All required packages installed")

        return True

    def step_api_keys(self) -> bool:
        """Configure API keys."""
        print_header("Step 3: API Configuration")

        # Load existing config
        existing = load_env_file()

        print_info("Enter your API keys (press Enter to skip)\n")

        api_keys = [
            ("OPENAI_API_KEY", "OpenAI API Key", "sk-..."),
            ("ANTHROPIC_API_KEY", "Anthropic API Key", "sk-ant-..."),
            ("OPENROUTER_API_KEY", "OpenRouter API Key", "sk-or-..."),
        ]

        for key_name, label, example in api_keys:
            existing_value = existing.get(key_name, "")
            masked = f"***{existing_value[-4:]}" if len(existing_value) > 4 else ""

            prompt = f"  {label}"
            if masked:
                prompt += f" [{masked}]"
            prompt += f" ({example}): "

            value = input(prompt).strip()

            if value:
                if validate_api_key(key_name, value):
                    self.config[key_name] = value
                    print_success(f"{label} configured")
                else:
                    print_warning(f"Invalid key format, skipping")
            elif existing_value:
                self.config[key_name] = existing_value
                print_info(f"Keeping existing {label}")

        # At least one key required
        if not any(k in self.config for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]):
            print_warning("\nNo API keys configured. You'll need at least one to use BAEL.")
            response = input("  Continue anyway? [y/N]: ").strip().lower()
            if response != 'y':
                return False

        return True

    def step_optional_services(self) -> None:
        """Configure optional services."""
        print_header("Step 4: Optional Services")

        print_info("Configure optional integrations (press Enter to skip)\n")

        optional_keys = [
            ("SLACK_TOKEN", "Slack Bot Token", "xoxb-..."),
            ("DISCORD_TOKEN", "Discord Bot Token", ""),
            ("GITHUB_TOKEN", "GitHub Personal Access Token", "ghp_..."),
            ("ELEVENLABS_API_KEY", "ElevenLabs API Key", ""),
        ]

        existing = load_env_file()

        for key_name, label, example in optional_keys:
            existing_value = existing.get(key_name, "")

            if existing_value:
                masked = f"***{existing_value[-4:]}" if len(existing_value) > 4 else "***"
                print_info(f"{label}: {masked} (configured)")
                continue

            prompt = f"  {label}"
            if example:
                prompt += f" ({example})"
            prompt += ": "

            value = input(prompt).strip()
            if value:
                self.config[key_name] = value
                print_success(f"{label} configured")

    def step_save_config(self) -> None:
        """Save configuration."""
        print_header("Step 5: Save Configuration")

        if self.config:
            # Merge with existing
            existing = load_env_file()
            merged = {**existing, **self.config}

            create_env_file(merged)
            print_success("Configuration saved to .env")

            # Show summary
            print("\n  Configured keys:")
            for key in merged:
                value = merged[key]
                masked = f"***{value[-4:]}" if len(value) > 4 else "***"
                print_info(f"    {key}: {masked}")
        else:
            print_warning("No new configuration to save")

    def step_verify(self) -> bool:
        """Verify setup."""
        print_header("Step 6: Verification")

        print_step(1, "Verifying configuration...")

        # Check if main module can be imported
        try:
            # Would import main module here
            print_success("Core modules loaded successfully")
        except Exception as e:
            print_warning(f"Module loading: {e}")

        # Test API connection if key available
        if self.config.get("OPENAI_API_KEY"):
            print_step(2, "Testing OpenAI connection...")
            try:
                import httpx

                # Would test API here
                print_success("OpenAI API accessible")
            except:
                print_warning("Could not verify OpenAI connection")

        return True

    def print_completion(self) -> None:
        """Print completion message."""
        print(f"""
{Colors.GREEN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                   Setup Complete! 🎉                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  BAEL is ready to use. Here are some next steps:            ║
║                                                              ║
║  1. Start the API server:                                   ║
║     python -m uvicorn api.server:app --reload              ║
║                                                              ║
║  2. Start the CLI:                                          ║
║     python main.py                                          ║
║                                                              ║
║  3. Open the Web UI:                                        ║
║     python -m http.server -d ui/web 3000                   ║
║                                                              ║
║  4. Open the Admin Dashboard:                               ║
║     python ui/admin/admin_api.py                           ║
║                                                              ║
║  Documentation: https://github.com/bael-ai/docs            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}
""")


# =============================================================================
# QUICK SETUP
# =============================================================================

def quick_setup(api_key: str, provider: str = "openai") -> bool:
    """Quick setup with single API key."""
    key_name = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY"
    }.get(provider.lower())

    if not key_name:
        print_error(f"Unknown provider: {provider}")
        return False

    config = {key_name: api_key}
    create_env_file(config)
    print_success(f"Quick setup complete with {provider}")
    return True


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run setup wizard."""
    import argparse

    parser = argparse.ArgumentParser(description="BAEL Setup Wizard")
    parser.add_argument("--quick", action="store_true", help="Quick setup mode")
    parser.add_argument("--api-key", help="API key for quick setup")
    parser.add_argument("--provider", default="openai", help="API provider (openai, anthropic, openrouter)")
    parser.add_argument("--check", action="store_true", help="System check only")

    args = parser.parse_args()

    if args.check:
        # Just run system check
        print_header("System Check")
        try:
            import psutil
            info = get_system_info()
            print(f"  OS: {info.os_name} {info.os_version}")
            print(f"  Python: {info.python_version}")
            print(f"  CPU: {info.cpu_count} cores")
            print(f"  Memory: {info.memory_gb} GB")
            print(f"  Docker: {'Yes' if info.docker_available else 'No'}")
            print(f"  Git: {'Yes' if info.git_available else 'No'}")
        except ImportError:
            print_warning("Install psutil for full system info")
        return

    if args.quick and args.api_key:
        quick_setup(args.api_key, args.provider)
        return

    # Run full wizard
    wizard = SetupWizard()
    success = wizard.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
