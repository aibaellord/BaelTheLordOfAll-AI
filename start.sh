#!/bin/bash
# BAEL - Quick Start Script
# Starts BAEL in the specified mode

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                           ║"
    echo "║    ██████╗  █████╗ ███████╗██╗                                           ║"
    echo "║    ██╔══██╗██╔══██╗██╔════╝██║                                           ║"
    echo "║    ██████╔╝███████║█████╗  ██║                                           ║"
    echo "║    ██╔══██╗██╔══██║██╔══╝  ██║                                           ║"
    echo "║    ██████╔╝██║  ██║███████╗███████╗                                      ║"
    echo "║    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝                                      ║"
    echo "║                                                                           ║"
    echo "║                   The All-Knowing AI Assistant                            ║"
    echo "║                                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed${NC}"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
}

check_venv() {
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi

    echo -e "${GREEN}✓ Virtual environment ready${NC}"
}

activate_venv() {
    source venv/bin/activate
}

install_deps() {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

check_env() {
    if [ ! -f ".env" ]; then
        if [ -f "config/templates/.env.template" ]; then
            echo -e "${YELLOW}Creating .env from template...${NC}"
            cp config/templates/.env.template .env
            echo -e "${YELLOW}⚠ Please edit .env with your API keys${NC}"
        else
            echo -e "${YELLOW}⚠ No .env file found. Some features may not work.${NC}"
        fi
    else
        echo -e "${GREEN}✓ Environment file found${NC}"
    fi
}

run_bael() {
    MODE=${1:-interactive}

    case $MODE in
        interactive|i)
            echo -e "${GREEN}Starting BAEL in interactive mode...${NC}"
            python3 run.py interactive --mode standard
            ;;
        api|server|s)
            echo -e "${GREEN}Starting BAEL API server...${NC}"
            python3 run.py api --port 8000
            ;;
        mcp|m)
            echo -e "${GREEN}Starting BAEL MCP server...${NC}"
            python3 run.py mcp
            ;;
        status|st)
            echo -e "${GREEN}Checking BAEL status...${NC}"
            python3 run.py status
            ;;
        setup)
            echo -e "${GREEN}Running setup wizard...${NC}"
            python3 setup_wizard.py
            ;;
        test|t)
            echo -e "${GREEN}Running tests...${NC}"
            python3 -m pytest tests/ -v
            ;;
        *)
            echo -e "${RED}Unknown mode: $MODE${NC}"
            echo ""
            echo "Available modes:"
            echo "  interactive (i)  - Start interactive chat"
            echo "  api (s)          - Start API server"
            echo "  mcp (m)          - Start MCP server"
            echo "  status (st)      - Show system status"
            echo "  setup            - Run setup wizard"
            echo "  test (t)         - Run tests"
            exit 1
            ;;
    esac
}

# Main
print_banner
check_python
check_venv
activate_venv
check_env

if [ "$1" == "install" ] || [ "$1" == "setup" ]; then
    install_deps
fi

run_bael "$1"
