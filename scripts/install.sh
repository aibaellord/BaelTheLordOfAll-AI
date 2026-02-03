#!/bin/bash
# BAEL Installation Script
# Sets up the BAEL environment from scratch

set -e

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                    BAEL Installation Script                       ║"
echo "║              The All-Knowing AI Assistant                        ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# =============================================================================
# CHECK PREREQUISITES
# =============================================================================

echo "Checking prerequisites..."

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d '.' -f 1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d '.' -f 2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        echo "❌ Python 3.10+ required. Found: Python $PYTHON_VERSION"
        exit 1
    fi
    echo "✅ Python $PYTHON_VERSION found"
else
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install pip"
    exit 1
fi
echo "✅ pip3 found"

# Check git
if ! command -v git &> /dev/null; then
    echo "❌ git not found. Please install git"
    exit 1
fi
echo "✅ git found"

echo ""

# =============================================================================
# CREATE VIRTUAL ENVIRONMENT
# =============================================================================

echo "Creating virtual environment..."

if [ -d "venv" ]; then
    echo "Virtual environment already exists. Skipping..."
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate
echo "✅ Virtual environment activated"

echo ""

# =============================================================================
# INSTALL DEPENDENCIES
# =============================================================================

echo "Installing dependencies..."

# Upgrade pip
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "⚠️  requirements.txt not found"
fi

# Install development dependencies if available
if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt
    echo "✅ Development dependencies installed"
fi

echo ""

# =============================================================================
# CREATE DIRECTORY STRUCTURE
# =============================================================================

echo "Creating directory structure..."

directories=(
    "config/settings"
    "config/secrets"
    "config/profiles"
    "memory/episodic"
    "memory/semantic"
    "memory/procedural"
    "memory/working"
    "memory/vector"
    "outputs/logs"
    "outputs/reports"
    "outputs/exports"
    "outputs/cache"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
done
echo "✅ Directory structure created"

echo ""

# =============================================================================
# CREATE CONFIGURATION FILES
# =============================================================================

echo "Setting up configuration files..."

# Copy templates if they don't exist
if [ ! -f "config/settings/settings.yaml" ] && [ -f "config/settings/settings.template.yaml" ]; then
    cp config/settings/settings.template.yaml config/settings/settings.yaml
    echo "✅ Created settings.yaml from template"
fi

if [ ! -f "config/secrets/secrets.yaml" ] && [ -f "config/secrets/secrets.template.yaml" ]; then
    cp config/secrets/secrets.template.yaml config/secrets/secrets.yaml
    echo "✅ Created secrets.yaml from template"
    echo "⚠️  Remember to add your API keys to config/secrets/secrets.yaml"
fi

if [ ! -f "config/profiles/developer.yaml" ] && [ -f "config/profiles/developer.template.yaml" ]; then
    cp config/profiles/developer.template.yaml config/profiles/developer.yaml
    echo "✅ Created developer.yaml profile from template"
fi

# Create .gitignore for secrets if it doesn't exist
if [ ! -f "config/secrets/.gitignore" ]; then
    echo "secrets.yaml" > config/secrets/.gitignore
    echo "*.key" >> config/secrets/.gitignore
    echo "✅ Created secrets .gitignore"
fi

echo ""

# =============================================================================
# INITIALIZE DATABASES
# =============================================================================

echo "Initializing databases..."

# Run initialization script if available
if [ -f "scripts/init_db.py" ]; then
    python scripts/init_db.py
    echo "✅ Databases initialized"
else
    echo "ℹ️  Database initialization script not found"
fi

echo ""

# =============================================================================
# VERIFY INSTALLATION
# =============================================================================

echo "Verifying installation..."

# Try importing main module
python3 -c "import bael; print('✅ BAEL module imported successfully')" || echo "⚠️  BAEL module import failed"

# Check if main.py exists and is runnable
if [ -f "main.py" ]; then
    python3 -c "import main" 2>/dev/null && echo "✅ main.py is valid" || echo "⚠️  main.py has issues"
fi

echo ""

# =============================================================================
# DISPLAY SUMMARY
# =============================================================================

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                    Installation Complete!                         ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Add your API keys to config/secrets/secrets.yaml"
echo "  2. Review settings in config/settings/settings.yaml"
echo "  3. Customize your profile in config/profiles/developer.yaml"
echo ""
echo "To start BAEL:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "For CLI mode:"
echo "  python cli.py"
echo ""
echo "For API server:"
echo "  python -m api.server"
echo ""
echo "For help:"
echo "  python main.py --help"
echo ""
