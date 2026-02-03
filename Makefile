# BAEL - The Lord of All AI Agents
# Makefile for common development tasks

.PHONY: help install dev test lint format clean docker-up docker-down run api mcp setup ui

# Detect venv Python if available
VENV_DIR := $(shell pwd)/.venv
ifeq ($(wildcard $(VENV_DIR)/bin/python),)
    PYTHON := python3
    PIP := pip3
else
    PYTHON := $(VENV_DIR)/bin/python
    PIP := $(VENV_DIR)/bin/pip
endif

# Project paths
PROJECT_DIR := $(shell pwd)
DATA_DIR := $(PROJECT_DIR)/data
LOGS_DIR := $(PROJECT_DIR)/logs

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
CYAN := \033[0;36m
PURPLE := \033[0;35m
NC := \033[0m

help: ## Show this help message
	@echo "$(PURPLE)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(PURPLE)║           🔥 BAEL - The Lord of All AI Agents 🔥               ║$(NC)"
	@echo "$(PURPLE)╚══════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | head -20 | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)Quick Start:$(NC)"
	@echo "  $(YELLOW)make setup$(NC)    - First time setup (creates venv + installs deps)"
	@echo "  $(YELLOW)make run$(NC)      - Start the BAEL API server"
	@echo "  $(YELLOW)make ui$(NC)       - Start the React UI"

# =============================================================================
# QUICK START
# =============================================================================

setup: ## First time setup - creates venv and installs everything
	@echo "$(PURPLE)🔥 BAEL Environment Setup$(NC)"
	@echo "$(CYAN)→ Creating virtual environment...$(NC)"
	@test -d $(VENV_DIR) || python3 -m venv $(VENV_DIR)
	@echo "$(GREEN)✓ Virtual environment ready$(NC)"
	@echo "$(CYAN)→ Installing dependencies...$(NC)"
	@$(VENV_DIR)/bin/pip install --upgrade pip --quiet
	@$(VENV_DIR)/bin/pip install -r requirements.txt --quiet 2>/dev/null || \
		$(VENV_DIR)/bin/pip install uvicorn fastapi pydantic httpx aiohttp python-dotenv pyyaml anthropic openai --quiet
	@echo "$(GREEN)✓ Dependencies installed$(NC)"
	@mkdir -p $(DATA_DIR) $(LOGS_DIR)
	@echo ""
	@echo "$(GREEN)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║                    ✅ Setup Complete!                            ║$(NC)"
	@echo "$(GREEN)╚══════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  source .venv/bin/activate  - Activate the environment"
	@echo "  make run                   - Start the API server"

run: ## Start the BAEL API server
	@echo "$(PURPLE)🔥 Starting BAEL API Server...$(NC)"
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	$(PYTHON) -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

ui: ## Start the React UI development server
	@echo "$(PURPLE)🔥 Starting BAEL UI...$(NC)"
	@cd ui/web && npm install && npm run dev

dev: ## Start API and show instructions for UI
	@echo "$(PURPLE)🔥 Starting BAEL Development Mode...$(NC)"
	@echo "$(CYAN)Starting API server on port 8000...$(NC)"
	@echo "$(YELLOW)In another terminal, run: make ui$(NC)"
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	$(PYTHON) -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

# =============================================================================
# INSTALLATION
# =============================================================================

install: ## Install all dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)Installation complete!$(NC)"

install-dev: ## Install development dependencies
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio pytest-cov black isort flake8 mypy
	@echo "$(GREEN)Development installation complete!$(NC)"

venv: ## Create virtual environment only
	@echo "$(GREEN)Creating virtual environment...$(NC)"
	python3 -m venv $(VENV_DIR)
	@echo "$(GREEN)Virtual environment created at $(VENV_DIR)$(NC)"
	@echo "Activate with: source $(VENV_DIR)/bin/activate"

# =============================================================================
# API & SERVERS
# =============================================================================

api: ## Start the API server on port 8080
	@echo "$(GREEN)Starting API server on 8080...$(NC)"
	$(PYTHON) -m uvicorn api.server:app --host 0.0.0.0 --port 8080 --reload

mcp: ## Start the MCP server
	@echo "$(GREEN)Starting MCP server...$(NC)"
	$(PYTHON) mcp/server.py

# =============================================================================
# TESTING
# =============================================================================

test: ## Run all tests
	@echo "$(GREEN)Running tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v

test-coverage: ## Run tests with coverage report
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	$(PYTHON) -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

# =============================================================================
# CODE QUALITY
# =============================================================================

lint: ## Run linting checks
	@echo "$(GREEN)Running linting...$(NC)"
	$(PYTHON) -m flake8 . --exclude=.venv,__pycache__,data,logs --max-line-length=100

format: ## Format code with black and isort
	@echo "$(GREEN)Formatting code...$(NC)"
	$(PYTHON) -m black . --exclude=".venv|data|logs"
	$(PYTHON) -m isort . --skip .venv --skip data --skip logs
	@echo "$(GREEN)Code formatted!$(NC)"

# =============================================================================
# DOCKER
# =============================================================================

docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t bael:latest -f docker/Dockerfile .

docker-up: ## Start all services with Docker Compose
	@echo "$(GREEN)Starting Docker services...$(NC)"
	docker-compose up -d

docker-down: ## Stop all Docker services
	@echo "$(GREEN)Stopping Docker services...$(NC)"
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

# =============================================================================
# UTILITIES
# =============================================================================

clean: ## Clean temporary files
	@echo "$(GREEN)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage
	@echo "$(GREEN)Cleanup complete!$(NC)"

status: ## Show system status
	@echo "$(GREEN)BAEL System Status$(NC)"
	@echo "===================="
	@echo ""
	@echo "Python: $$($(PYTHON) --version 2>&1)"
	@echo "Venv: $(VENV_DIR)"
	@echo "Project: $(PROJECT_DIR)"
	@echo ""
	@echo "Port 8000: $$(lsof -ti:8000 >/dev/null 2>&1 && echo 'IN USE' || echo 'Available')"

kill: ## Kill any process on port 8000
	@echo "$(YELLOW)Killing process on port 8000...$(NC)"
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "No process found"
	@echo "$(GREEN)Done$(NC)"

shell: ## Open Python shell with BAEL context
	@echo "$(GREEN)Opening BAEL Python shell...$(NC)"
	$(PYTHON) -i -c "print('BAEL Python Shell - Ready')"

version: ## Show current version
	@echo "BAEL v2.1.0 - Full Autonomy Edition"

# =============================================================================
# MCP HUB - Docker-based MCP Server Management
# =============================================================================

mcp-hub-up: ## Start the MCP Hub (33 MCP servers)
	@echo "$(PURPLE)🔥 Starting BAEL MCP Hub...$(NC)"
	@echo "$(CYAN)→ Starting 33 MCP servers in Docker...$(NC)"
	@cd mcp/docker && docker-compose -f docker-compose.mcp.yml up -d
	@echo "$(GREEN)✓ MCP Hub started$(NC)"
	@echo ""
	@echo "$(CYAN)MCP Gateway:$(NC) http://localhost:3100"
	@echo "$(CYAN)Health Check:$(NC) http://localhost:3100/health"
	@echo "$(CYAN)Server List:$(NC) http://localhost:3100/mcp/servers"

mcp-hub-down: ## Stop the MCP Hub
	@echo "$(YELLOW)Stopping MCP Hub...$(NC)"
	@cd mcp/docker && docker-compose -f docker-compose.mcp.yml down
	@echo "$(GREEN)✓ MCP Hub stopped$(NC)"

mcp-hub-status: ## Show MCP Hub status
	@echo "$(PURPLE)🔥 MCP Hub Status$(NC)"
	@echo ""
	@cd mcp/docker && docker-compose -f docker-compose.mcp.yml ps
	@echo ""
	@curl -s http://localhost:3100/health 2>/dev/null || echo "$(RED)Gateway not running$(NC)"

mcp-hub-logs: ## View MCP Hub logs
	@cd mcp/docker && docker-compose -f docker-compose.mcp.yml logs -f --tail=100

mcp-hub-essential: ## Start only Essential tier MCPs
	@echo "$(PURPLE)🔥 Starting Essential MCP Servers...$(NC)"
	@cd mcp/docker && docker-compose -f docker-compose.mcp.yml up -d mcp-gateway mcp-filesystem mcp-brave-search mcp-github mcp-sqlite mcp-memory
	@echo "$(GREEN)✓ Essential MCPs started$(NC)"

mcp-hub-export: ## Export MCP Hub as portable package
	@echo "$(PURPLE)🔥 Exporting MCP Hub...$(NC)"
	@mkdir -p exports
	@tar -czf exports/bael-mcp-hub-$$(date +%Y%m%d).tar.gz mcp/docker mcp/gateway mcp/config
	@echo "$(GREEN)✓ Exported to exports/bael-mcp-hub-$$(date +%Y%m%d).tar.gz$(NC)"

mcp-hub-env: ## Copy MCP environment template
	@cp mcp/config/.env.template mcp/docker/.env
	@echo "$(GREEN)✓ Created mcp/docker/.env - Edit with your API keys$(NC)"

# =============================================================================
# MCP ULTIMATE - 52+ MCP Servers with Full Integration
# =============================================================================

mcp-ultimate-up: ## Start the Ultimate MCP Hub (52+ servers)
	@echo "$(PURPLE)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(PURPLE)║      🔥 BAEL ULTIMATE MCP HUB - 52+ SERVERS 🔥                  ║$(NC)"
	@echo "$(PURPLE)╚══════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)→ Starting Ultimate MCP Hub with all 52+ servers...$(NC)"
	@cd mcp/docker && docker-compose -f docker-compose.ultimate.yml up -d
	@echo ""
	@echo "$(GREEN)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║                    ✅ Ultimate MCP Hub Ready!                    ║$(NC)"
	@echo "$(GREEN)╚══════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)Services:$(NC)"
	@echo "  MCP Gateway:    http://localhost:3100"
	@echo "  Admin API:      http://localhost:3101"
	@echo "  Metrics:        http://localhost:3102"
	@echo "  Grafana:        http://localhost:3000"
	@echo "  Prometheus:     http://localhost:9090"
	@echo "  Qdrant:         http://localhost:6333"
	@echo "  Neo4j:          http://localhost:7474"

mcp-ultimate-down: ## Stop the Ultimate MCP Hub
	@echo "$(YELLOW)Stopping Ultimate MCP Hub...$(NC)"
	@cd mcp/docker && docker-compose -f docker-compose.ultimate.yml down
	@echo "$(GREEN)✓ Ultimate MCP Hub stopped$(NC)"

mcp-ultimate-status: ## Show Ultimate MCP Hub status
	@echo "$(PURPLE)🔥 Ultimate MCP Hub Status$(NC)"
	@echo ""
	@cd mcp/docker && docker-compose -f docker-compose.ultimate.yml ps 2>/dev/null || echo "Hub not running"

mcp-ultimate-logs: ## View Ultimate MCP Hub logs
	@cd mcp/docker && docker-compose -f docker-compose.ultimate.yml logs -f --tail=100

mcp-ultimate-tier: ## Start specific tier (usage: make mcp-ultimate-tier TIER=essential)
	@echo "$(PURPLE)🔥 Starting MCP Tier: $(TIER)$(NC)"
	@cd mcp/docker && docker-compose -f docker-compose.ultimate.yml up -d $$(cat ../config/servers-ultimate.yaml | grep -A 20 "^  $(TIER):" | grep "servers:" -A 10 | grep "      -" | sed 's/.*- /mcp-/' | tr '\n' ' ')
	@echo "$(GREEN)✓ Tier $(TIER) started$(NC)"

mcp-scale: ## Scale a specific MCP server (usage: make mcp-scale SERVER=worker COUNT=5)
	@echo "$(CYAN)Scaling $(SERVER) to $(COUNT) instances...$(NC)"
	@cd mcp/docker && docker-compose -f docker-compose.ultimate.yml up -d --scale $(SERVER)=$(COUNT)
	@echo "$(GREEN)✓ Scaled$(NC)"

# =============================================================================
# APEX ORCHESTRATOR
# =============================================================================

apex: ## Start the APEX Orchestrator
	@echo "$(PURPLE)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(PURPLE)║         🧠 BAEL APEX ORCHESTRATOR - MAXIMUM POTENTIAL 🧠        ║$(NC)"
	@echo "$(PURPLE)╚══════════════════════════════════════════════════════════════════╝$(NC)"
	$(PYTHON) -c "import asyncio; from core.apex.apex_orchestrator import create_apex, APEXMode; asyncio.run(create_apex(APEXMode.MAXIMUM))"

apex-status: ## Show APEX status
	@echo "$(PURPLE)🧠 APEX Orchestrator Status$(NC)"
	@curl -s http://localhost:8000/api/v1/apex/status 2>/dev/null | $(PYTHON) -m json.tool || echo "APEX not running"

apex-test: ## Test APEX with a sample request
	@echo "$(CYAN)Testing APEX Orchestrator...$(NC)"
	@curl -s -X POST http://localhost:8000/api/v1/apex/process \
		-H "Content-Type: application/json" \
		-d '{"input": "Analyze the BAEL architecture and suggest improvements"}' \
		2>/dev/null | $(PYTHON) -m json.tool || echo "APEX not running"

# =============================================================================
# SWARM INTELLIGENCE
# =============================================================================

swarm: ## Start a swarm of agents
	@echo "$(GREEN)🐝 Starting BAEL Swarm Intelligence...$(NC)"
	$(PYTHON) -c "import asyncio; from core.swarm.swarm_intelligence import SwarmIntelligence; asyncio.run(SwarmIntelligence().demonstrate())"

swarm-spawn: ## Spawn agents for a task (usage: make swarm-spawn TASK="research AI")
	@echo "$(GREEN)🐝 Spawning swarm for: $(TASK)$(NC)"
	$(PYTHON) -c "import asyncio; from core.swarm.swarm_intelligence import SwarmIntelligence; s = SwarmIntelligence(); asyncio.run(s.optimize('$(TASK)'))"

# =============================================================================
# FULL STACK
# =============================================================================

full-stack: ## Start everything (API + UI + MCP Hub)
	@echo "$(PURPLE)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(PURPLE)║       🔥 BAEL FULL STACK - MAXIMUM POTENTIAL MODE 🔥            ║$(NC)"
	@echo "$(PURPLE)╚══════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@$(MAKE) mcp-ultimate-up &
	@sleep 5
	@$(MAKE) run &
	@sleep 3
	@$(MAKE) ui

full-stack-down: ## Stop everything
	@echo "$(YELLOW)Stopping BAEL Full Stack...$(NC)"
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	@lsof -ti:5173 | xargs kill -9 2>/dev/null || true
	@$(MAKE) mcp-ultimate-down
	@echo "$(GREEN)✓ All stopped$(NC)"

# =============================================================================
# BRAIN & COUNCILS
# =============================================================================

brain: ## Interactive BAEL Brain session
	@echo "$(PURPLE)🧠 Starting BAEL Brain...$(NC)"
	$(PYTHON) -c "from core.brain.brain import BaelBrain; brain = BaelBrain(); print('BAEL Brain ready. Use brain.think(prompt) to interact.')"

council: ## Convene the Grand Council
	@echo "$(PURPLE)👥 Convening Grand Council...$(NC)"
	$(PYTHON) -c "import asyncio; from core.councils.grand_council import GrandCouncil; council = GrandCouncil(); asyncio.run(council.convene('Strategic decision required'))"

supreme: ## Start Supreme Controller
	@echo "$(PURPLE)👑 Starting Supreme Controller...$(NC)"
	$(PYTHON) -c "import asyncio; from core.supreme.orchestrator import SupremeController; sc = SupremeController(); asyncio.run(sc.initialize())"

# =============================================================================
# REASONING ENGINES
# =============================================================================

reason: ## Test reasoning engines
	@echo "$(CYAN)🧠 Testing BAEL Reasoning Engines...$(NC)"
	$(PYTHON) -c "from core.reasoning.reasoning_engine import ReasoningEngine; r = ReasoningEngine(); print(r.reason('Why is the sky blue?'))"

think: ## Deep thinking mode (usage: make think Q="your question")
	@echo "$(CYAN)💭 BAEL Deep Thinking...$(NC)"
	$(PYTHON) -c "from core.thinking.extended_thinking import ExtendedThinking; t = ExtendedThinking(); print(t.think_deeply('$(Q)'))"

# =============================================================================
# MEMORY SYSTEMS
# =============================================================================

memory-status: ## Show memory system status
	@echo "$(PURPLE)📊 Memory System Status$(NC)"
	$(PYTHON) -c "from core.memory.manager import MemoryManager; m = MemoryManager(); print(m.get_status())"

memory-consolidate: ## Consolidate memories
	@echo "$(CYAN)🔄 Consolidating memories...$(NC)"
	$(PYTHON) -c "from core.memory.manager import MemoryManager; m = MemoryManager(); m.consolidate()"

# =============================================================================
# EVOLUTION & SELF-IMPROVEMENT
# =============================================================================

evolve: ## Trigger self-evolution
	@echo "$(PURPLE)🧬 Starting Self-Evolution...$(NC)"
	$(PYTHON) -c "import asyncio; from core.evolution.evolution_engine import EvolutionEngine; e = EvolutionEngine(); asyncio.run(e.evolve())"

analyze-self: ## Self-analysis
	@echo "$(CYAN)🔍 Running Self-Analysis...$(NC)"
	$(PYTHON) -c "from core.evolution.code_analyzer import CodeAnalyzer; a = CodeAnalyzer(); print(a.analyze_project())"

# =============================================================================
# 🔥 SINGULARITY - UNIFIED CONTROL OF 200+ CAPABILITIES 🔥
# =============================================================================

singularity: ## Awaken the BAEL Singularity (unified 200+ capabilities)
	@echo "$(PURPLE)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(PURPLE)║       ⚡ BAEL SINGULARITY - UNIFIED INTELLIGENCE ⚡              ║$(NC)"
	@echo "$(PURPLE)╚══════════════════════════════════════════════════════════════════╝$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import awaken, SingularityMode; s = asyncio.run(awaken(SingularityMode.TRANSCENDENT)); print(s.get_status())"

singularity-godmode: ## Awaken the Singularity in GOD MODE (all capabilities, no limits)
	@echo "$(PURPLE)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(PURPLE)║         🔥 BAEL SINGULARITY - GOD MODE ACTIVATED 🔥             ║$(NC)"
	@echo "$(PURPLE)╚══════════════════════════════════════════════════════════════════╝$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import awaken, SingularityMode; s = asyncio.run(awaken(SingularityMode.GODMODE)); print(s.get_status())"

singularity-think: ## Think using the Singularity (usage: make singularity-think Q="your question")
	@echo "$(CYAN)💭 Singularity Deep Thinking...$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import get_singularity; s = asyncio.run(get_singularity()); result = asyncio.run(s.think('$(Q)')); print(result)"

singularity-collective: ## Collective problem solving (usage: make singularity-collective P="your problem")
	@echo "$(CYAN)🐝 Collective Intelligence Activated...$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import get_singularity; s = asyncio.run(get_singularity()); result = asyncio.run(s.collective_solve('$(P)', strategy='hybrid')); print(result)"

singularity-reason: ## Multi-engine reasoning (usage: make singularity-reason Q="your query")
	@echo "$(CYAN)🧠 Multi-Engine Reasoning...$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import get_singularity; s = asyncio.run(get_singularity()); result = asyncio.run(s.reason('$(Q)')); print(result)"

singularity-create: ## Creative generation (usage: make singularity-create R="your request")
	@echo "$(CYAN)✨ Creative Generation...$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import get_singularity; s = asyncio.run(get_singularity()); result = asyncio.run(s.create('$(R)')); print(result)"

singularity-maximum: ## MAXIMUM POTENTIAL (usage: make singularity-maximum G="your goal")
	@echo "$(PURPLE)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(PURPLE)║           🔥🔥🔥 MAXIMUM POTENTIAL MODE 🔥🔥🔥                 ║$(NC)"
	@echo "$(PURPLE)╚══════════════════════════════════════════════════════════════════╝$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import get_singularity; s = asyncio.run(get_singularity()); result = asyncio.run(s.maximum_potential('$(G)')); print(result)"

singularity-invoke: ## Invoke any capability (usage: make singularity-invoke C="capability" M="method")
	@echo "$(CYAN)⚡ Invoking $(C).$(M)...$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import get_singularity; s = asyncio.run(get_singularity()); result = asyncio.run(s.invoke('$(C)', '$(M)')); print(result)"

singularity-capabilities: ## List all 200+ capabilities
	@echo "$(PURPLE)🔮 BAEL Singularity Capabilities$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import get_singularity; s = asyncio.run(get_singularity()); caps = s.list_capabilities(); [print(f'\\n{d.upper()}:\\n  ' + ', '.join(c)) for d, c in caps.items()]"

singularity-status: ## Show Singularity status
	@echo "$(PURPLE)📊 Singularity Status$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import get_singularity; s = asyncio.run(get_singularity()); status = s.get_status(); [print(f'{k}: {v}') for k, v in status.items()]"

singularity-evolve: ## Trigger Singularity evolution
	@echo "$(PURPLE)🧬 Singularity Self-Evolution...$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import get_singularity; s = asyncio.run(get_singularity()); result = asyncio.run(s.evolve()); print(result)"

singularity-introspect: ## Deep introspection
	@echo "$(PURPLE)🔍 Singularity Introspection...$(NC)"
	$(PYTHON) -c "import asyncio; from core.singularity import get_singularity; s = asyncio.run(get_singularity()); result = asyncio.run(s.introspect()); print(result)"

# =============================================================================
# 🌌 ULTIMATE MODE - EVERYTHING AT ONCE
# =============================================================================

ultimate: ## 🔥 Start EVERYTHING - API + UI + MCP Ultimate + Singularity
	@echo "$(PURPLE)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(PURPLE)║       ⚡⚡⚡ BAEL ULTIMATE MODE - TOTAL ASCENSION ⚡⚡⚡          ║$(NC)"
	@echo "$(PURPLE)╚══════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)Step 1: Starting 52+ MCP Servers...$(NC)"
	@$(MAKE) mcp-ultimate-up
	@sleep 5
	@echo ""
	@echo "$(CYAN)Step 2: Starting API Server with Singularity...$(NC)"
	@$(MAKE) run &
	@sleep 3
	@echo ""
	@echo "$(CYAN)Step 3: Starting God-Mode UI...$(NC)"
	@$(MAKE) ui
	@echo ""
	@echo "$(GREEN)╔══════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║               ⚡ BAEL ULTIMATE MODE ACTIVATED ⚡                 ║$(NC)"
	@echo "$(GREEN)╠══════════════════════════════════════════════════════════════════╣$(NC)"
	@echo "$(GREEN)║  API Server:    http://localhost:8000                            ║$(NC)"
	@echo "$(GREEN)║  God-Mode UI:   http://localhost:5173/god-mode                   ║$(NC)"
	@echo "$(GREEN)║  MCP Gateway:   http://localhost:3100                            ║$(NC)"
	@echo "$(GREEN)║  Capabilities:  200+                                             ║$(NC)"
	@echo "$(GREEN)╚══════════════════════════════════════════════════════════════════╝$(NC)"

ultimate-down: ## Stop ultimate mode
	@echo "$(YELLOW)Stopping BAEL Ultimate Mode...$(NC)"
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	@lsof -ti:5173 | xargs kill -9 2>/dev/null || true
	@$(MAKE) mcp-ultimate-down
	@echo "$(GREEN)✓ BAEL Ultimate Mode stopped$(NC)"
