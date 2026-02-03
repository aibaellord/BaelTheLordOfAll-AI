# BAEL Python SDK

Official Python client library for **BAEL** - The Lord of All AI Agents.

## Installation

```bash
pip install bael-sdk
```

Or install from source:

```bash
git clone https://github.com/yourusername/bael.git
cd bael/sdk/python
pip install -e .
```

## Quick Start

### Asynchronous Usage

```python
import asyncio
from bael_sdk import BAELClient

async def main():
    async with BAELClient(api_url="http://localhost:8000") as client:
        # Simple chat
        response = await client.chat("What is the capital of France?")
        print(response.response)

        # Chat with options
        response = await client.chat(
            "Write a Python function to calculate fibonacci",
            mode="maximum",
            persona="coder",
            temperature=0.7
        )
        print(response.response)

        # Submit autonomous task
        task = await client.submit_task(
            task="Research quantum computing and create a summary",
            priority="high"
        )

        # Wait for completion
        completed_task = await client.wait_for_task(task.id, timeout=300)
        print(completed_task.result)

asyncio.run(main())
```

### Synchronous Usage

```python
from bael_sdk import BAELSyncClient

with BAELSyncClient(api_url="http://localhost:8000") as client:
    # Simple chat
    response = client.chat("Hello, BAEL!")
    print(response.response)

    # Check system health
    health = client.health()
    print(f"Status: {health.status}, Uptime: {health.uptime_seconds}s")
```

### Quick Functions

```python
from bael_sdk import quick_chat_sync

# One-liner for quick interactions
response = quick_chat_sync("What is 2+2?")
print(response)  # "4"
```

## Features

- ✅ **Asynchronous & Synchronous** - Use async/await or synchronous calls
- ✅ **Type-Safe** - Full type hints for IDE autocomplete
- ✅ **Streaming Support** - Stream responses in real-time
- ✅ **Task Management** - Submit and track background tasks
- ✅ **Multiple Modes** - minimal, standard, maximum, autonomous
- ✅ **Persona System** - Choose from 8+ specialist personas
- ✅ **Error Handling** - Clear exception hierarchy
- ✅ **Rate Limiting** - Built-in rate limit handling

## API Reference

### BAELClient

Main asynchronous client for BAEL API.

#### Methods

##### `chat(message, mode='standard', persona=None, **kwargs)`

Send a chat message to BAEL.

**Parameters:**

- `message` (str | List[Message]): Message to send
- `mode` (OperatingMode): Operating mode (minimal, standard, maximum, autonomous)
- `persona` (str, optional): Persona to use (orchestrator, architect, coder, etc.)
- `model` (str, optional): Preferred model
- `temperature` (float, optional): Temperature (0-2)
- `max_tokens` (int, optional): Maximum tokens to generate

**Returns:** `ChatResponse`

##### `submit_task(task, context=None, priority='normal', deadline=None)`

Submit an autonomous task.

**Parameters:**

- `task` (str): Task description
- `context` (dict, optional): Context data
- `priority` (str): Priority level (critical, high, normal, low, background)
- `deadline` (datetime, optional): Task deadline

**Returns:** `Task`

##### `get_task(task_id)`

Get task status.

**Returns:** `Task`

##### `wait_for_task(task_id, poll_interval=1.0, timeout=None)`

Wait for task to complete.

**Returns:** `Task`

##### `health()`

Check system health.

**Returns:** `HealthStatus`

##### `list_personas()`

List available personas.

**Returns:** `List[Dict]`

##### `list_capabilities()`

List capabilities by mode.

**Returns:** `Dict[str, List[str]]`

### Operating Modes

```python
from bael_sdk import OperatingMode

OperatingMode.MINIMAL      # Basic completion only
OperatingMode.STANDARD     # Web search, RAG, workflows
OperatingMode.MAXIMUM      # Multi-agent, research, analysis
OperatingMode.AUTONOMOUS   # Full autonomy with self-improvement
```

### Available Personas

- **orchestrator** - Master coordinator
- **architect** - System design specialist
- **coder** - Code implementation expert
- **researcher** - Research and analysis
- **analyst** - Data analysis
- **reviewer** - Code review specialist
- **debugger** - Bug diagnosis
- **teacher** - Education and explanation

## Examples

### Multi-Turn Conversation

```python
from bael_sdk import BAELClient, Message

async def conversation():
    async with BAELClient() as client:
        messages = [
            Message(role="user", content="What is machine learning?"),
        ]

        response = await client.chat(messages)
        print(response.response)

        # Continue conversation
        messages.append(Message(role="assistant", content=response.response))
        messages.append(Message(role="user", content="Can you give an example?"))

        response = await client.chat(messages)
        print(response.response)
```

### Background Task Processing

```python
async def process_task():
    async with BAELClient() as client:
        # Submit multiple tasks
        tasks = []
        for i in range(5):
            task = await client.submit_task(
                f"Analyze dataset_{i}.csv",
                priority="normal"
            )
            tasks.append(task.id)

        # Wait for all to complete
        results = []
        for task_id in tasks:
            task = await client.wait_for_task(task_id, timeout=600)
            results.append(task.result)

        print(f"Completed {len(results)} tasks")
```

### Error Handling

```python
from bael_sdk import BAELClient, APIError, RateLimitError

async def with_error_handling():
    async with BAELClient() as client:
        try:
            response = await client.chat("Hello!")
        except RateLimitError:
            print("Rate limit exceeded, waiting...")
            await asyncio.sleep(60)
        except APIError as e:
            print(f"API error {e.status_code}: {e.message}")
        except Exception as e:
            print(f"Unexpected error: {e}")
```

## Configuration

### Environment Variables

```bash
export BAEL_API_URL="http://localhost:8000"
export BAEL_API_KEY="your-api-key"
```

### Using API Key

```python
from bael_sdk import BAELClient

client = BAELClient(
    api_url="http://localhost:8000",
    api_key="your-api-key"
)
```

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

### Type Checking

```bash
mypy bael_sdk.py
```

### Code Formatting

```bash
black bael_sdk.py
```

## License

MIT License - see LICENSE file for details.

## Support

- 📖 Documentation: https://docs.bael.ai
- 💬 Discord: https://discord.gg/bael
- 🐛 Issues: https://github.com/yourusername/bael/issues
- 📧 Email: support@bael.ai

## Changelog

### 1.0.0 (2026-02-02)

- Initial release
- Asynchronous and synchronous clients
- Full API coverage
- Type-safe interface
- Comprehensive examples
