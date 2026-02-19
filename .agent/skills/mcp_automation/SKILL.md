---
name: MCP Automation Skill
description: MCP server discovery, integration, and automation
---

# MCP Automation Skill

## Purpose
Automate MCP server management, tool discovery, and unified access.

## Configured Servers (52+)

### Tier 0: Infrastructure
- Redis, PostgreSQL, MongoDB

### Tier 1: Essential
- Filesystem, Brave Search, GitHub, SQLite, Memory

### Tier 2: Power Tools
- Puppeteer, Playwright, Sequential Thinking

### Tier 3: Enhanced
- E2B Code Executor, Exa Search

### Tier 4: AI/ML
- OpenAI, Anthropic, LangChain, Hugging Face

### Tier 5: Cloud
- AWS, GCP, Azure, Cloudflare

## Auto-Discovery Protocol

```python
from mcp.server import BaelMCPServer

# Initialize MCP gateway
server = BaelMCPServer()

# Discover available tools
tools = server.get_all_tools()

# Find tools by capability
web_tools = server.find_tools_by_category("web")
ai_tools = server.find_tools_by_category("ai")

# Execute tool
result = await server.call_tool("bael_web_search", {
    "query": "advanced AI techniques"
})
```

## Tool Categories

| Category | Tools |
|----------|-------|
| Core | think, research, analyze_code, execute_code |
| Web | fetch, search, crawl |
| Code | format, security_scan, generate |
| File | read, write, search |
| Database | sql_query, vector_search, document_store |
| AI | chat, summarize, classify, embed |

## Configuration
Config file: `mcp/config/servers-ultimate.yaml`

## Environment Variables Required
```bash
BRAVE_API_KEY=your_key
GITHUB_TOKEN=your_token
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
# See servers-ultimate.yaml for full list
```

## Best Practices
1. Prefer free-tier APIs when available
2. Cache responses to reduce API calls
3. Rate limit to avoid blocks
4. Rotate credentials when limits approached
