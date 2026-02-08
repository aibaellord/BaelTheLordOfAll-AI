# BAEL API Examples

Comprehensive examples for using BAEL's APIs - REST, WebSocket, Python SDK, and more.

## Table of Contents

- [REST API Examples](#rest-api-examples)
- [Python SDK Examples](#python-sdk-examples)
- [WebSocket API Examples](#websocket-api-examples)
- [MCP Integration Examples](#mcp-integration-examples)
- [CLI Examples](#cli-examples)
- [Advanced Use Cases](#advanced-use-cases)

---

## REST API Examples

### Basic Request

```bash
# Health check
curl http://localhost:8000/health

# Get API version
curl http://localhost:8000/version
```

### Chat API

```bash
# Simple chat request
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello BAEL!",
    "agent_id": "default"
  }'

# Chat with specific persona
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Review this Python code",
    "persona": "code_master",
    "context": {
      "code": "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"
    }
  }'

# Streaming chat response
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Write a detailed explanation of quantum computing"
  }'
```

### Agent Management

```bash
# Create agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "research_bot",
    "persona": "research_oracle",
    "mission": "Research technology trends",
    "capabilities": ["web_search", "synthesis"]
  }'

# Get agent status
curl http://localhost:8000/api/v1/agents/{agent_id}

# List all agents
curl http://localhost:8000/api/v1/agents

# Update agent
curl -X PUT http://localhost:8000/api/v1/agents/{agent_id} \
  -H "Content-Type: application/json" \
  -d '{
    "mission": "Research AI developments",
    "active": true
  }'

# Delete agent
curl -X DELETE http://localhost:8000/api/v1/agents/{agent_id}
```

### Task Management

```bash
# Submit task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "analysis",
    "description": "Analyze market trends for Q4 2024",
    "priority": "high",
    "agent_id": "research_bot"
  }'

# Get task status
curl http://localhost:8000/api/v1/tasks/{task_id}

# List tasks
curl http://localhost:8000/api/v1/tasks?status=pending&limit=10

# Cancel task
curl -X DELETE http://localhost:8000/api/v1/tasks/{task_id}
```

### Memory Operations

```bash
# Store memory
curl -X POST http://localhost:8000/api/v1/memory \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "research_bot",
    "content": "Important finding about quantum computing",
    "type": "semantic",
    "importance": 0.9
  }'

# Search memory
curl -X POST http://localhost:8000/api/v1/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "quantum computing",
    "agent_id": "research_bot",
    "limit": 5
  }'

# Get agent memories
curl http://localhost:8000/api/v1/memory/agent/{agent_id}?limit=20

# Clear old memories
curl -X DELETE http://localhost:8000/api/v1/memory/cleanup?days=30
```

### Skill Management

```bash
# Create skill
curl -X POST http://localhost:8000/api/v1/skills \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sentiment_analyzer",
    "description": "Analyze sentiment of text with confidence scores",
    "generate_tests": true
  }'

# List skills
curl http://localhost:8000/api/v1/skills

# Execute skill
curl -X POST http://localhost:8000/api/v1/skills/{skill_id}/execute \
  -H "Content-Type: application/json" \
  -d '{
    "input": "I love this product! It exceeded my expectations."
  }'

# Evolve skill
curl -X POST http://localhost:8000/api/v1/skills/{skill_id}/evolve \
  -H "Content-Type: application/json" \
  -d '{
    "generations": 5,
    "fitness_goal": "accuracy"
  }'
```

---

## Python SDK Examples

### Installation

```bash
pip install bael-sdk
```

### Basic Usage

```python
import asyncio
from bael_sdk import BAELClient


async def main():
    # Create client
    async with BAELClient(base_url="http://localhost:8000") as client:
        
        # Simple chat
        response = await client.chat("Hello BAEL!")
        print(response)
        
        # Chat with persona
        response = await client.chat(
            "Explain quantum entanglement",
            persona="research_oracle"
        )
        print(response)


asyncio.run(main())
```

### Agent Management

```python
from bael_sdk import BAELClient


async def agent_example():
    async with BAELClient() as client:
        
        # Create agent
        agent = await client.create_agent(
            name="code_reviewer",
            persona="code_master",
            mission="Review code for best practices"
        )
        
        print(f"Created agent: {agent.agent_id}")
        
        # Use agent
        result = await client.send_to_agent(
            agent.agent_id,
            "Review this function: def process(data): return data.upper()"
        )
        
        print(result)
        
        # Get agent status
        status = await client.get_agent_status(agent.agent_id)
        print(f"Agent status: {status}")
        
        # List all agents
        agents = await client.list_agents()
        for a in agents:
            print(f"- {a.name} ({a.persona})")
```

### Task Submission

```python
async def task_example():
    async with BAELClient() as client:
        
        # Submit task
        task = await client.submit_task(
            task_type="analysis",
            data={
                "text": "Large document to analyze...",
                "analysis_type": "comprehensive"
            },
            priority="high"
        )
        
        print(f"Task submitted: {task.task_id}")
        
        # Poll for completion
        while True:
            status = await client.get_task_status(task.task_id)
            
            if status.state == "completed":
                result = await client.get_task_result(task.task_id)
                print("Task completed!")
                print(result)
                break
            
            elif status.state == "failed":
                print(f"Task failed: {status.error}")
                break
            
            await asyncio.sleep(2)
```

### Streaming Responses

```python
async def streaming_example():
    async with BAELClient() as client:
        
        # Stream chat response
        async for chunk in client.chat_stream(
            "Write a long story about AI"
        ):
            print(chunk, end="", flush=True)
        
        print()  # New line at end
```

### Memory Operations

```python
async def memory_example():
    async with BAELClient() as client:
        
        # Store memory
        await client.store_memory(
            agent_id="my_agent",
            content="Important fact to remember",
            memory_type="semantic",
            importance=0.8
        )
        
        # Search memory
        results = await client.search_memory(
            query="important fact",
            agent_id="my_agent"
        )
        
        for memory in results:
            print(f"- {memory.content} (score: {memory.score})")
```

### Skill Operations

```python
async def skill_example():
    async with BAELClient() as client:
        
        # Create skill
        skill = await client.create_skill(
            name="url_extractor",
            description="Extract all URLs from text"
        )
        
        print(f"Created skill: {skill.skill_id}")
        
        # Use skill
        result = await client.execute_skill(
            skill.skill_id,
            input_data="Check out https://example.com and https://test.org"
        )
        
        print(f"Extracted URLs: {result}")
```

---

## WebSocket API Examples

### JavaScript/Browser

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

// Handle connection
ws.onopen = () => {
    console.log('Connected to BAEL');
    
    // Send message
    ws.send(JSON.stringify({
        type: 'chat',
        message: 'Hello from browser!',
        agent_id: 'default'
    }));
};

// Handle messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
    
    if (data.type === 'chat_response') {
        console.log('BAEL says:', data.content);
    }
    else if (data.type === 'status_update') {
        console.log('Status:', data.status);
    }
};

// Handle errors
ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

// Handle close
ws.onclose = () => {
    console.log('Disconnected from BAEL');
};
```

### Python WebSocket Client

```python
import asyncio
import websockets
import json


async def websocket_example():
    uri = "ws://localhost:8000/ws"
    
    async with websockets.connect(uri) as websocket:
        
        # Send message
        await websocket.send(json.dumps({
            'type': 'chat',
            'message': 'Hello from Python!',
            'agent_id': 'default'
        }))
        
        # Receive response
        response = await websocket.recv()
        data = json.loads(response)
        
        print(f"BAEL says: {data['content']}")
        
        # Stream conversation
        for message in ["Tell me about AI", "What about ML?", "And deep learning?"]:
            await websocket.send(json.dumps({
                'type': 'chat',
                'message': message,
                'stream': True
            }))
            
            # Receive streaming chunks
            while True:
                chunk = await websocket.recv()
                data = json.loads(chunk)
                
                if data.get('done'):
                    break
                
                print(data.get('content', ''), end='', flush=True)
            
            print()  # New line


asyncio.run(websocket_example())
```

---

## MCP Integration Examples

### BAEL as MCP Server

```python
# Configure BAEL as MCP server
# In your MCP client configuration:
{
    "mcpServers": {
        "bael": {
            "command": "python",
            "args": ["-m", "core.mcp.server"],
            "env": {
                "BAEL_API_URL": "http://localhost:8000"
            }
        }
    }
}
```

### BAEL as MCP Client

```python
from core.mcp import MCPClient


async def mcp_client_example():
    # Connect to external MCP server
    client = MCPClient("external_mcp_server")
    
    await client.connect()
    
    # List available tools
    tools = await client.list_tools()
    print(f"Available tools: {[t.name for t in tools]}")
    
    # Use a tool
    result = await client.call_tool(
        "search_web",
        query="latest AI news"
    )
    
    print(result)
```

---

## CLI Examples

### Basic Commands

```bash
# Simple query
python cli.py "What is quantum computing?"

# Use specific persona
python cli.py --persona research_oracle "Explain relativity"

# Interactive mode
python cli.py --interactive

# Save output to file
python cli.py "Explain machine learning" > ml_explanation.txt

# Use specific agent
python cli.py --agent my_agent_id "Continue our conversation"
```

### Advanced CLI Usage

```bash
# Create and use agent
python cli.py --create-agent \
  --name "data_analyst" \
  --persona "data_sage" \
  --mission "Analyze datasets"

# Execute skill
python cli.py --execute-skill sentiment_analyzer \
  --input "I love this product!"

# Submit task
python cli.py --submit-task \
  --type analysis \
  --description "Analyze Q4 sales data" \
  --priority high

# Search memory
python cli.py --search-memory "quantum computing" \
  --agent research_bot

# Verbose mode
python cli.py --verbose "Complex query requiring detailed reasoning"
```

---

## Advanced Use Cases

### Multi-Agent Workflow

```python
from bael_sdk import BAELClient


async def multi_agent_workflow():
    async with BAELClient() as client:
        
        # Create specialized agents
        researcher = await client.create_agent(
            name="researcher",
            persona="research_oracle"
        )
        
        writer = await client.create_agent(
            name="writer",
            persona="creative_genius"
        )
        
        editor = await client.create_agent(
            name="editor",
            persona="qa_perfectionist"
        )
        
        # Step 1: Research
        research = await client.send_to_agent(
            researcher.agent_id,
            "Research latest AI developments"
        )
        
        # Step 2: Write article
        article = await client.send_to_agent(
            writer.agent_id,
            f"Write an engaging article based on: {research.content}"
        )
        
        # Step 3: Edit
        final = await client.send_to_agent(
            editor.agent_id,
            f"Edit and improve: {article.content}"
        )
        
        return final.content
```

### Batch Processing

```python
async def batch_processing():
    async with BAELClient() as client:
        
        # Create batch of tasks
        tasks = []
        
        for i, document in enumerate(documents):
            task = await client.submit_task(
                task_type="summarize",
                data={"text": document},
                task_id=f"summary_{i}"
            )
            tasks.append(task)
        
        # Wait for all completions
        results = []
        
        for task in tasks:
            while True:
                status = await client.get_task_status(task.task_id)
                
                if status.state == "completed":
                    result = await client.get_task_result(task.task_id)
                    results.append(result)
                    break
                
                await asyncio.sleep(1)
        
        return results
```

### Real-time Monitoring

```python
async def realtime_monitoring():
    async with BAELClient() as client:
        
        # Create monitoring agent
        monitor = await client.create_agent(
            name="system_monitor",
            persona="devops_commander",
            mission="Monitor system health"
        )
        
        # Subscribe to events
        async for event in client.subscribe_events(
            event_types=["error", "warning", "alert"]
        ):
            print(f"Event: {event.type}")
            print(f"Message: {event.message}")
            
            # Send to monitoring agent
            analysis = await client.send_to_agent(
                monitor.agent_id,
                f"Analyze this event: {event}"
            )
            
            if analysis.severity == "critical":
                # Take action
                await send_alert(analysis.recommendation)
```

### Custom Integration

```python
from flask import Flask, request, jsonify
from bael_sdk import BAELClient

app = Flask(__name__)
bael_client = BAELClient()


@app.route('/api/analyze', methods=['POST'])
async def analyze():
    """Analyze endpoint using BAEL."""
    
    data = request.json
    
    # Use BAEL for analysis
    result = await bael_client.submit_task(
        task_type="analysis",
        data=data
    )
    
    # Wait for completion
    while True:
        status = await bael_client.get_task_status(result.task_id)
        
        if status.state == "completed":
            result = await bael_client.get_task_result(result.task_id)
            return jsonify(result)
        
        await asyncio.sleep(0.5)


@app.route('/api/chat', methods=['POST'])
async def chat():
    """Chat endpoint using BAEL."""
    
    message = request.json.get('message')
    
    response = await bael_client.chat(message)
    
    return jsonify({'response': response})


if __name__ == '__main__':
    app.run(port=5000)
```

---

## Error Handling

### Python SDK

```python
from bael_sdk import BAELClient, BAELError, RateLimitError


async def error_handling_example():
    async with BAELClient() as client:
        
        try:
            response = await client.chat("Hello")
            
        except RateLimitError as e:
            print(f"Rate limited. Retry after: {e.retry_after}")
            await asyncio.sleep(e.retry_after)
            response = await client.chat("Hello")
            
        except BAELError as e:
            print(f"BAEL error: {e.message}")
            print(f"Error code: {e.code}")
            
        except Exception as e:
            print(f"Unexpected error: {e}")
```

### REST API

```bash
# Error responses follow this format:
{
    "error": {
        "code": "INVALID_REQUEST",
        "message": "Missing required field: agent_id",
        "details": {
            "field": "agent_id",
            "expected_type": "string"
        }
    }
}
```

---

## Rate Limiting

```python
# Handle rate limits
from tenacity import retry, wait_exponential, stop_after_attempt


@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5)
)
async def make_request():
    async with BAELClient() as client:
        return await client.chat("Hello")
```

---

## Authentication

```python
# Using API keys
client = BAELClient(
    base_url="http://localhost:8000",
    api_key="your-api-key-here"
)

# Using JWT tokens
client = BAELClient(
    base_url="http://localhost:8000",
    token="your-jwt-token"
)
```

---

## Best Practices

1. **Always use async context managers**
   ```python
   async with BAELClient() as client:
       # Your code
       pass
   ```

2. **Handle errors gracefully**
   ```python
   try:
       result = await client.chat(message)
   except BAELError as e:
       # Handle BAEL-specific errors
       pass
   ```

3. **Use streaming for long responses**
   ```python
   async for chunk in client.chat_stream(message):
       process_chunk(chunk)
   ```

4. **Reuse clients when possible**
   ```python
   # Good
   client = BAELClient()
   for msg in messages:
       await client.chat(msg)
   
   # Avoid
   for msg in messages:
       async with BAELClient() as client:  # Creates new connection each time
           await client.chat(msg)
   ```

5. **Set appropriate timeouts**
   ```python
   client = BAELClient(timeout=60)  # 60 second timeout
   ```

---

## More Examples

For more examples, see:
- [examples/](../examples/) - Complete example applications
- [tests/](../tests/) - Test files showing API usage
- [TUTORIALS.md](TUTORIALS.md) - Step-by-step tutorials

---

**Last Updated**: February 2026  
**Version**: 3.0.0

_For questions, see [FAQ.md](FAQ.md) or [TROUBLESHOOTING.md](TROUBLESHOOTING.md)_
