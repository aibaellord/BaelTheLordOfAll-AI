#!/bin/bash
# ============================================================================
# BAEL Environment Setup Script
# Automatically creates and activates Python virtual environment
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_VERSION="3.11.13"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${PURPLE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           🔥 BAEL - The Lord of All AI Agents 🔥               ║"
echo "║                   Environment Setup v1.0                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check for pyenv
if command -v pyenv &> /dev/null; then
    echo -e "${GREEN}✓${NC} pyenv found"

    # Check if Python version exists
    if pyenv versions | grep -q "$PYTHON_VERSION"; then
        echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION available"
        PYTHON_PATH="$HOME/.pyenv/versions/$PYTHON_VERSION/bin/python"
    else
        echo -e "${YELLOW}!${NC} Installing Python $PYTHON_VERSION via pyenv..."
        pyenv install "$PYTHON_VERSION"
        PYTHON_PATH="$HOME/.pyenv/versions/$PYTHON_VERSION/bin/python"
    fi
else
    echo -e "${YELLOW}!${NC} pyenv not found, using system Python"
    PYTHON_PATH=$(which python3)
fi

# Create or update virtual environment
if [ -d "$VENV_DIR" ]; then
    echo -e "${CYAN}→${NC} Virtual environment exists at $VENV_DIR"
else
    echo -e "${CYAN}→${NC} Creating virtual environment..."
    $PYTHON_PATH -m venv "$VENV_DIR"
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

# Activate virtual environment
echo -e "${CYAN}→${NC} Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓${NC} Virtual environment activated"

# Upgrade pip
echo -e "${CYAN}→${NC} Upgrading pip..."
pip install --upgrade pip --quiet

# Install requirements
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo -e "${CYAN}→${NC} Installing requirements..."
    pip install -r "$PROJECT_ROOT/requirements.txt" --quiet
    echo -e "${GREEN}✓${NC} Requirements installed"
else
    echo -e "${YELLOW}!${NC} No requirements.txt found, installing core dependencies..."
    pip install uvicorn fastapi pydantic httpx aiohttp python-dotenv --quiet
    echo -e "${GREEN}✓${NC} Core dependencies installed"
fi

# Create .python-version for pyenv
echo "$PYTHON_VERSION" > "$PROJECT_ROOT/.python-version"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ Environment Ready!                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Python: $(python --version)"
echo -e "Pip: $(pip --version | cut -d' ' -f1-2)"
echo -e "Venv: $VENV_DIR"
echo ""
echo -e "${CYAN}Quick Commands:${NC}"
echo -e "  ${YELLOW}bael${NC}          - Start BAEL API server"
echo -e "  ${YELLOW}bael-ui${NC}       - Start BAEL UI"
echo -e "  ${YELLOW}bael-dev${NC}      - Start both in development mode"
echo ""
