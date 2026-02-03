# BAEL JavaScript/TypeScript SDK

Official TypeScript/JavaScript SDK for BAEL - The Lord of All AI Agents.

## Features

- ✅ **Fully Typed** - 100% TypeScript with complete type safety
- ✅ **Async/Await** - Modern promise-based API
- ✅ **Streaming** - Server-sent event streaming support
- ✅ **Error Handling** - Comprehensive exception types
- ✅ **Retry Logic** - Automatic exponential backoff
- ✅ **Event Emitter** - Real-time event handling
- ✅ **Browser & Node.js** - Universal JavaScript support

## Installation

```bash
npm install bael-sdk
# or
yarn add bael-sdk
# or
pnpm add bael-sdk
```

## Quick Start

### Basic Usage

```typescript
import BAELClient from "bael-sdk";

const client = new BAELClient({
  baseUrl: "http://localhost:8000",
  apiKey: "your_api_key",
});

// Chat with BAEL
const response = await client.chat("Hello, BAEL!");
console.log(response.response);
```

### Async/Await Pattern

```typescript
async function main() {
  const client = new BAELClient({
    baseUrl: "http://localhost:8000",
  });

  try {
    // Send message
    const chat = await client.chat({
      message: "What is AI?",
      persona: "researcher",
      context: { user_id: "123" },
    });
    console.log(chat.response);

    // Submit task
    const task = await client.submitTask({
      task_type: "analysis",
      task_data: { content: "Analyze this..." },
    });
    console.log(`Task: ${task.task_id}`);

    // Check status
    const status = await client.getTaskStatus(task.task_id);
    console.log(`Status: ${status.status}`);
  } catch (error) {
    console.error("Error:", error);
  }
}

main();
```

### Event-Driven Usage

```typescript
const client = new BAELClient({
  baseUrl: "http://localhost:8000",
});

// Listen for events
client.on("chat", (response) => {
  console.log("Chat response:", response);
});

client.on("task_submitted", (task) => {
  console.log("Task submitted:", task.task_id);
});

client.on("task_progress", (status) => {
  console.log(`Progress: ${status.progress}%`);
});

client.on("task_completed", (status) => {
  console.log("Task completed:", status.result);
});

// Use client
await client.chat("Hello!");
const task = await client.submitTask("analysis", { data: "test" });
```

## API Reference

### Constructor

```typescript
new BAELClient(config: BAELClientConfig)

// Config options
{
  baseUrl: string;              // BAEL API base URL (required)
  apiKey?: string;              // API key for authentication
  timeout?: number;             // Request timeout in ms (default: 30000)
  headers?: Record<string, string>; // Custom headers
  maxRetries?: number;          // Max retry attempts (default: 3)
  retryDelay?: number;          // Retry delay in ms (default: 1000)
}
```

### Methods

#### `chat(params: ChatRequest | string): Promise<ChatResponse>`

Send a chat message to BAEL.

```typescript
// Simple string
const response = await client.chat("Hello!");

// With options
const response = await client.chat({
  message: "What is AI?",
  persona: "researcher",
  context: { topic: "artificial-intelligence" },
  stream: false,
});
```

#### `submitTask(request: TaskRequest | string, data?: any): Promise<TaskResponse>`

Submit a background task.

```typescript
// Simple form
const task = await client.submitTask("analysis", { data: "content" });

// Full form
const task = await client.submitTask({
  task_type: "analysis",
  task_data: { content: "Analyze this..." },
  priority: 5,
});
```

#### `getTaskStatus(taskId: string): Promise<TaskStatus>`

Get task status.

```typescript
const status = await client.getTaskStatus("task_123");
console.log(status.status); // 'pending', 'running', 'completed', 'failed'
```

#### `watchTask(taskId: string, interval?: number, timeout?: number): Promise<TaskStatus>`

Poll task status until completion.

```typescript
const status = await client.watchTask("task_123", 1000, 300000);
console.log(status.result);
```

#### `healthCheck(): Promise<HealthResponse>`

Check system health.

```typescript
const health = await client.healthCheck();
console.log(health.status); // 'healthy', 'degraded', 'unhealthy'
console.log(health.components);
```

#### `getCapabilities(): Promise<Capabilities>`

Get system capabilities.

```typescript
const caps = await client.getCapabilities();
console.log(caps.tools);
console.log(caps.personas);
```

#### `listPersonas(): Promise<string[]>`

List available personas.

```typescript
const personas = await client.listPersonas();
console.log(personas); // ['default', 'researcher', 'assistant', ...]
```

#### `getMetrics(): Promise<MetricsResponse>`

Get system metrics.

```typescript
const metrics = await client.getMetrics();
console.log(metrics.metrics);
```

#### `batchChat(messages: string[]): Promise<ChatResponse[]>`

Send multiple chat messages in parallel.

```typescript
const responses = await client.batchChat([
  "Message 1",
  "Message 2",
  "Message 3",
]);
```

### Error Handling

```typescript
import {
  APIError,
  RateLimitError,
  AuthenticationError,
  ValidationError,
} from "bael-sdk";

try {
  await client.chat("Hello");
} catch (error) {
  if (error instanceof RateLimitError) {
    console.log(`Rate limited. Retry after ${error.retryAfter}s`);
  } else if (error instanceof AuthenticationError) {
    console.log("Invalid API key");
  } else if (error instanceof ValidationError) {
    console.log("Validation errors:", error.errors);
  } else if (error instanceof APIError) {
    console.log(`API error: ${error.statusCode} ${error.message}`);
  }
}
```

### Events

```typescript
// Listen to specific events
client.on("chat", (response: ChatResponse) => {});
client.on("task_submitted", (task: TaskResponse) => {});
client.on("task_progress", (status: TaskStatus) => {});
client.on("task_completed", (status: TaskStatus) => {});

// Remove listeners
client.off("chat", handler);
client.removeAllListeners();
```

## Examples

### Example 1: Sentiment Analysis

```typescript
const client = new BAELClient({
  baseUrl: "http://localhost:8000",
});

const sentiment = await client.chat({
  message: "Analyze the sentiment: I love this product!",
  persona: "sentiment-analyzer",
});

console.log(sentiment.response);
```

### Example 2: Task Processing

```typescript
const client = new BAELClient({
  baseUrl: "http://localhost:8000",
});

// Submit task
const task = await client.submitTask("data-processing", {
  dataset: "large_dataset.csv",
  operation: "aggregate",
  timeout: 300,
});

console.log(`Processing: ${task.task_id}`);

// Watch for completion
const result = await client.watchTask(task.task_id);

console.log("Result:", result.result);
```

### Example 3: Multi-Persona Conversation

```typescript
const client = new BAELClient({
  baseUrl: "http://localhost:8000",
});

const question = "How does machine learning work?";

const responses = await Promise.all([
  client.chat({ message: question, persona: "educator" }),
  client.chat({ message: question, persona: "researcher" }),
  client.chat({ message: question, persona: "engineer" }),
]);

responses.forEach((r, i) => {
  console.log(`${["Educator", "Researcher", "Engineer"][i]}: ${r.response}`);
});
```

### Example 4: Streaming Responses

```typescript
const client = new BAELClient({
  baseUrl: "http://localhost:8000",
});

// Stream long response
for await (const chunk of client.streamChat({
  message: "Write a long story...",
})) {
  process.stdout.write(chunk);
}
```

## Configuration

### Development

```typescript
import { createDevelopmentClient } from "bael-sdk";

const client = createDevelopmentClient();
```

### Production

```typescript
import { createProductionClient } from "bael-sdk";

const client = createProductionClient(
  process.env.BAEL_API_KEY!,
  process.env.BAEL_API_URL!,
);
```

### Custom

```typescript
const client = new BAELClient({
  baseUrl: process.env.BAEL_API_URL || "http://localhost:8000",
  apiKey: process.env.BAEL_API_KEY,
  timeout: 60000,
  maxRetries: 5,
  retryDelay: 2000,
});
```

## Browser Usage

```html
<script src="https://cdn.jsdelivr.net/npm/bael-sdk"></script>

<script>
  const client = new BAEL.BAELClient({
    baseUrl: "https://api.bael.io",
  });

  client.chat("Hello!").then((response) => {
    console.log(response.response);
  });
</script>
```

## Debugging

Enable debug logging:

```typescript
const client = new BAELClient({
  baseUrl: "http://localhost:8000",
});

// All events logged
client.on("chat", console.log);
client.on("task_submitted", console.log);
client.on("task_progress", console.log);
client.on("task_completed", console.log);
```

## Testing

```bash
npm test
npm run test:watch
npm run test:coverage
```

## Type Safety

100% TypeScript with complete type definitions:

```typescript
import type {
  ChatResponse,
  TaskStatus,
  HealthResponse,
  Capabilities,
} from "bael-sdk";

const response: ChatResponse = await client.chat("Hello");
const status: TaskStatus = await client.getTaskStatus("id");
```

## License

MIT - See LICENSE file for details.

## Support

- **Docs:** https://docs.bael.ai
- **Discord:** https://discord.gg/bael
- **Issues:** https://github.com/bael/bael-sdk-js/issues
- **Email:** support@bael.ai

---

Made with ❤️ by the BAEL Team
