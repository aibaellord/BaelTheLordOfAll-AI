#!/bin/zsh
# ============================================================================
# BAEL Development Shell Configuration
# Source this file in your .zshrc: source /path/to/bael_shell.zsh
# ============================================================================

# =============================================================================
# AUTO VIRTUAL ENVIRONMENT ACTIVATION
# Automatically activates venv when entering a project directory
# =============================================================================

auto_activate_venv() {
    local venv_path=""
    local current_dir="$PWD"

    # Look for .venv in current or parent directories
    while [[ "$current_dir" != "/" ]]; do
        if [[ -f "$current_dir/.venv/bin/activate" ]]; then
            venv_path="$current_dir/.venv/bin/activate"
            break
        fi
        current_dir="$(dirname "$current_dir")"
    done

    # Activate if found and different from current
    if [[ -n "$venv_path" ]]; then
        local venv_dir="$(dirname "$(dirname "$venv_path")")"
        if [[ "$VIRTUAL_ENV" != "$venv_dir" ]]; then
            source "$venv_path"
            echo "🐍 Activated: $(basename "$venv_dir")/.venv"
        fi
    fi
}

# Hook into directory change
autoload -U add-zsh-hook
add-zsh-hook chpwd auto_activate_venv

# Run on shell start too
auto_activate_venv

# =============================================================================
# BAEL COMMANDS
# =============================================================================

# BAEL Project Root
export BAEL_ROOT="/Volumes/SSD320/BaelTheLordOfAll-AI"

# Quick navigation
alias bael="cd $BAEL_ROOT && source .venv/bin/activate 2>/dev/null"
alias bael-api="cd $BAEL_ROOT && source .venv/bin/activate && uvicorn api.server:app --reload --port 8000"
alias bael-ui="cd $BAEL_ROOT/ui/web && npm run dev"
alias bael-setup="cd $BAEL_ROOT && make setup"

# Quick package installation (auto uses correct pip)
pinstall() {
    if [[ -n "$VIRTUAL_ENV" ]]; then
        pip install "$@"
    else
        echo "⚠️  No virtual environment active. Use 'bael' first or create one with:"
        echo "   python3 -m venv .venv && source .venv/bin/activate"
    fi
}

# Create new project with venv
newproject() {
    local name="${1:-myproject}"
    mkdir -p "$name" && cd "$name"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    echo "# $name" > README.md
    echo ".venv/" > .gitignore
    echo "🎉 Project '$name' created with Python $(python --version)"
}

# Clone and setup (auto creates venv)
clonesetup() {
    local repo="$1"
    local name="${2:-$(basename "$repo" .git)}"

    git clone "$repo" "$name"
    cd "$name"

    # Create venv
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip

    # Install requirements if they exist
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        echo "📦 Installed requirements.txt"
    elif [[ -f "pyproject.toml" ]]; then
        pip install -e .
        echo "📦 Installed from pyproject.toml"
    elif [[ -f "setup.py" ]]; then
        pip install -e .
        echo "📦 Installed from setup.py"
    fi

    echo "✅ Project cloned and ready!"
}

# =============================================================================
# PYTHON HELPERS
# =============================================================================

# List installed packages nicely
alias piplist="pip list --format=columns"

# Freeze requirements
alias freeze="pip freeze > requirements.txt && echo '📦 requirements.txt updated'"

# Python version info
pyinfo() {
    echo "🐍 Python: $(python --version 2>/dev/null || echo 'not found')"
    echo "📍 Path: $(which python 2>/dev/null || echo 'not found')"
    echo "📦 Pip: $(pip --version 2>/dev/null | cut -d' ' -f1-2 || echo 'not found')"
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo "🔷 Venv: $VIRTUAL_ENV"
    else
        echo "⚪ Venv: none active"
    fi
}

# =============================================================================
# GIT HELPERS
# =============================================================================

# Quick git status
alias gs="git status -sb"
alias gp="git pull"
alias gpp="git pull && git push"

# =============================================================================
# PROMPT ENHANCEMENT (Optional - adds venv to prompt)
# =============================================================================

# Show venv name in prompt
show_venv() {
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo "($(basename "$VIRTUAL_ENV")) "
    fi
}

# If you want venv in prompt, add this to PROMPT:
# export PROMPT='$(show_venv)'"$PROMPT"

# =============================================================================
# MESSAGES
# =============================================================================

echo "🔥 BAEL Shell Extensions Loaded"
echo "   Type 'bael' to enter BAEL project"
echo "   Type 'pyinfo' for Python environment info"
