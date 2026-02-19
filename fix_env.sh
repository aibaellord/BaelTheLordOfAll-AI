#!/bin/bash
# BAEL Environment Fix Script
# Fixes corrupted virtual environment issues

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

# Colors
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║            🔧 BAEL Environment Fix Script                     ║${NC}"
echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Remove corrupted venv
echo -e "${CYAN}→ Removing corrupted virtual environment...${NC}"
if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
    echo -e "${GREEN}✓ Old environment removed${NC}"
else
    echo -e "${YELLOW}⚠ No existing environment found${NC}"
fi

# Step 2: Find Python 3.11
echo -e "${CYAN}→ Finding Python 3.11...${NC}"
PYTHON_CMD=""

# Check pyenv first
if [ -f "$HOME/.pyenv/versions/3.11.13/bin/python3.11" ]; then
    PYTHON_CMD="$HOME/.pyenv/versions/3.11.13/bin/python3.11"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ "$VERSION" == "3.11" ]] || [[ "$VERSION" == "3.10" ]] || [[ "$VERSION" == "3.12" ]]; then
        PYTHON_CMD="python3"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}✗ No suitable Python found. Please install Python 3.10-3.12${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Using: $PYTHON_CMD ($($PYTHON_CMD --version))${NC}"

# Step 3: Create new venv
echo -e "${CYAN}→ Creating fresh virtual environment...${NC}"
$PYTHON_CMD -m venv "$VENV_DIR"
echo -e "${GREEN}✓ Virtual environment created${NC}"

# Step 4: Upgrade pip
echo -e "${CYAN}→ Upgrading pip...${NC}"
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
echo -e "${GREEN}✓ Pip upgraded${NC}"

# Step 5: Install core dependencies
echo -e "${CYAN}→ Installing core dependencies...${NC}"

# Try requirements.txt first
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "${CYAN}  Installing from requirements.txt...${NC}"
    "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt" --quiet 2>/dev/null || {
        echo -e "${YELLOW}  ⚠ Some packages failed, installing minimal set...${NC}"
        "$VENV_DIR/bin/pip" install \
            fastapi uvicorn pydantic httpx aiohttp \
            python-dotenv pyyaml anthropic openai \
            rich click pytest pytest-asyncio \
            --quiet
    }
else
    echo -e "${YELLOW}  Installing minimal dependencies...${NC}"
    "$VENV_DIR/bin/pip" install \
        fastapi uvicorn pydantic httpx aiohttp \
        python-dotenv pyyaml anthropic openai \
        rich click pytest pytest-asyncio \
        --quiet
fi

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 6: Create data directories
echo -e "${CYAN}→ Creating data directories...${NC}"
mkdir -p "$PROJECT_DIR/data" "$PROJECT_DIR/logs"
echo -e "${GREEN}✓ Directories ready${NC}"

# Step 7: Verify installation
echo -e "${CYAN}→ Verifying installation...${NC}"
"$VENV_DIR/bin/python" -c "import fastapi, uvicorn, pydantic; print('Core packages: OK')"
echo -e "${GREEN}✓ Installation verified${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ Environment Fixed Successfully!               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  source .venv/bin/activate"
echo "  make run"
echo ""
echo -e "${CYAN}Or use the quick start:${NC}"
echo "  python3 quickstart.py"
echo ""
