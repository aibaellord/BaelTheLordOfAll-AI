/**
 * BAEL JavaScript/TypeScript SDK - Official client for BAEL AI Agent System
 *
 * @packageDocumentation
 */

import axios, { AxiosInstance, AxiosError } from "axios";
import { EventEmitter } from "eventemitter3";

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

/**
 * Configuration for BAEL client
 */
export interface BAELClientConfig {
  baseUrl: string;
  apiKey?: string;
  timeout?: number;
  headers?: Record<string, string>;
  maxRetries?: number;
  retryDelay?: number;
}

/**
 * Chat request parameters
 */
export interface ChatRequest {
  message: string;
  persona?: string;
  context?: Record<string, any>;
  stream?: boolean;
}

/**
 * Chat response
 */
export interface ChatResponse {
  response: string;
  persona: string;
  tokens_used: number;
  timestamp: string;
}

/**
 * Task submission request
 */
export interface TaskRequest {
  task_type: string;
  task_data: Record<string, any>;
  priority?: number;
}

/**
 * Task response
 */
export interface TaskResponse {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
}

/**
 * Task status response
 */
export interface TaskStatus {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress?: number;
  result?: any;
  error?: string;
}

/**
 * Health check response
 */
export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  components: Record<string, "healthy" | "degraded" | "unhealthy">;
  timestamp: string;
}

/**
 * System capabilities
 */
export interface Capabilities {
  reasoning: boolean;
  memory: boolean;
  tools: string[];
  personas: string[];
  plugins: string[];
}

/**
 * Metrics response
 */
export interface MetricsResponse {
  timestamp: string;
  metrics: Record<string, number>;
}

// ============================================================================
// EXCEPTIONS
// ============================================================================

/**
 * Base API error class
 */
export class APIError extends Error {
  constructor(
    public statusCode: number,
    public message: string,
    public data?: any,
  ) {
    super(message);
    this.name = "APIError";
  }
}

/**
 * Rate limit error (429)
 */
export class RateLimitError extends APIError {
  constructor(public retryAfter: number = 60) {
    super(429, "Rate limited - too many requests");
    this.name = "RateLimitError";
  }
}

/**
 * Authentication error (401)
 */
export class AuthenticationError extends APIError {
  constructor() {
    super(401, "Unauthorized - invalid API key");
    this.name = "AuthenticationError";
  }
}

/**
 * Validation error (400)
 */
export class ValidationError extends APIError {
  constructor(public errors: Record<string, string>) {
    super(400, "Validation error - invalid request parameters");
    this.name = "ValidationError";
  }
}

// ============================================================================
// BAEL CLIENT
// ============================================================================

/**
 * Official BAEL SDK client for JavaScript/TypeScript
 *
 * @example
 * ```typescript
 * const client = new BAELClient({
 *   baseUrl: 'http://localhost:8000',
 *   apiKey: 'your_api_key'
 * });
 *
 * const response = await client.chat('Hello, BAEL!');
 * console.log(response.response);
 * ```
 */
export class BAELClient extends EventEmitter {
  private axiosInstance: AxiosInstance;
  private config: Required<BAELClientConfig>;
  private retries: Map<string, number> = new Map();

  constructor(config: BAELClientConfig) {
    super();

    this.config = {
      baseUrl: config.baseUrl,
      apiKey: config.apiKey || "",
      timeout: config.timeout || 30000,
      headers: config.headers || {},
      maxRetries: config.maxRetries || 3,
      retryDelay: config.retryDelay || 1000,
    };

    this.axiosInstance = axios.create({
      baseURL: this.config.baseUrl,
      timeout: this.config.timeout,
      headers: this._getHeaders(),
    });

    // Add response interceptor for error handling
    this.axiosInstance.interceptors.response.use(
      (response) => response,
      (error) => this._handleError(error),
    );
  }

  /**
   * Send a chat message to BAEL
   */
  async chat(params: ChatRequest | string): Promise<ChatResponse> {
    const request: ChatRequest =
      typeof params === "string" ? { message: params } : params;

    const response = await this._request<ChatResponse>("POST", "/v1/chat", {
      message: request.message,
      persona: request.persona || "default",
      context: request.context,
    });

    this.emit("chat", response);
    return response;
  }

  /**
   * Stream chat response (server-sent events)
   */
  async *streamChat(request: ChatRequest): AsyncGenerator<string> {
    const response = await this._request<NodeJS.ReadableStream>(
      "GET",
      "/v1/chat/stream",
      {
        message: request.message,
        persona: request.persona || "default",
      },
    );

    // Note: Full SSE implementation would go here
    yield* this._parseStreamResponse(response);
  }

  /**
   * Submit a background task
   */
  async submitTask(
    request: TaskRequest | string,
    data?: Record<string, any>,
  ): Promise<TaskResponse> {
    const taskRequest: TaskRequest =
      typeof request === "string"
        ? { task_type: request, task_data: data || {} }
        : request;

    const response = await this._request<TaskResponse>("POST", "/v1/tasks", {
      task_type: taskRequest.task_type,
      task_data: taskRequest.task_data,
      priority: taskRequest.priority || 0,
    });

    this.emit("task_submitted", response);
    return response;
  }

  /**
   * Get task status
   */
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    return await this._request<TaskStatus>("GET", `/v1/tasks/${taskId}`);
  }

  /**
   * Check system health
   */
  async healthCheck(): Promise<HealthResponse> {
    return await this._request<HealthResponse>("GET", "/health");
  }

  /**
   * Get system capabilities
   */
  async getCapabilities(): Promise<Capabilities> {
    return await this._request<Capabilities>("GET", "/v1/capabilities");
  }

  /**
   * List available personas
   */
  async listPersonas(): Promise<string[]> {
    const response = await this._request<{ personas: string[] }>(
      "GET",
      "/v1/personas",
    );
    return response.personas;
  }

  /**
   * Get system metrics
   */
  async getMetrics(): Promise<MetricsResponse> {
    return await this._request<MetricsResponse>("GET", "/metrics");
  }

  /**
   * Batch chat requests
   */
  async batchChat(messages: string[]): Promise<ChatResponse[]> {
    return Promise.all(messages.map((msg) => this.chat(msg)));
  }

  /**
   * Watch task status with polling
   */
  async watchTask(
    taskId: string,
    interval: number = 1000,
    timeout: number = 300000,
  ): Promise<TaskStatus> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const status = await this.getTaskStatus(taskId);

      if (status.status === "completed" || status.status === "failed") {
        this.emit("task_completed", status);
        return status;
      }

      this.emit("task_progress", status);
      await new Promise((resolve) => setTimeout(resolve, interval));
    }

    throw new Error(`Task ${taskId} timed out after ${timeout}ms`);
  }

  /**
   * Close client and cleanup
   */
  async close(): Promise<void> {
    this.removeAllListeners();
  }

  /**
   * Private method: Make HTTP request with retry logic
   */
  private async _request<T>(
    method: "GET" | "POST" | "PUT" | "DELETE",
    path: string,
    data?: any,
  ): Promise<T> {
    const key = `${method}:${path}`;
    const retryCount = this.retries.get(key) || 0;

    try {
      const response = await this.axiosInstance({
        method,
        url: path,
        data,
      });

      this.retries.delete(key);
      return response.data;
    } catch (error) {
      if (retryCount < this.config.maxRetries && this._isRetryable(error)) {
        this.retries.set(key, retryCount + 1);
        await new Promise((resolve) =>
          setTimeout(resolve, this.config.retryDelay * Math.pow(2, retryCount)),
        );
        return this._request<T>(method, path, data);
      }

      throw error;
    }
  }

  /**
   * Private method: Handle HTTP errors
   */
  private _handleError(error: AxiosError): never {
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data as any;

      if (status === 429) {
        throw new RateLimitError(
          parseInt(error.response.headers["retry-after"] as string) || 60,
        );
      } else if (status === 401) {
        throw new AuthenticationError();
      } else if (status === 400 && data?.errors) {
        throw new ValidationError(data.errors);
      } else {
        throw new APIError(status, data?.message || error.message, data);
      }
    }

    throw new APIError(0, error.message || "Unknown error");
  }

  /**
   * Private method: Check if error is retryable
   */
  private _isRetryable(error: any): boolean {
    if (error instanceof RateLimitError) return true;
    if (error.code === "ECONNRESET") return true;
    if (error.code === "ETIMEDOUT") return true;
    return false;
  }

  /**
   * Private method: Get headers with auth
   */
  private _getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "User-Agent": "bael-sdk-js/2.1.0",
      ...this.config.headers,
    };

    if (this.config.apiKey) {
      headers["Authorization"] = `Bearer ${this.config.apiKey}`;
    }

    return headers;
  }

  /**
   * Private method: Parse stream response
   */
  private async *_parseStreamResponse(response: any): AsyncGenerator<string> {
    // Implementation for parsing server-sent events
    yield "";
  }
}

// ============================================================================
// CONVENIENCE FUNCTIONS
// ============================================================================

/**
 * Quick chat without creating a client
 */
export async function quickChat(
  message: string,
  baseUrl: string = "http://localhost:8000",
): Promise<ChatResponse> {
  const client = new BAELClient({ baseUrl });
  return await client.chat(message);
}

/**
 * Create a pre-configured client for development
 */
export function createDevelopmentClient(): BAELClient {
  return new BAELClient({
    baseUrl: "http://localhost:8000",
    timeout: 30000,
  });
}

/**
 * Create a pre-configured client for production
 */
export function createProductionClient(
  apiKey: string,
  baseUrl: string,
): BAELClient {
  return new BAELClient({
    baseUrl,
    apiKey,
    timeout: 60000,
    maxRetries: 5,
  });
}

// ============================================================================
// EXPORTS
// ============================================================================

export default BAELClient;
export {
  BAELClient,
  APIError,
  RateLimitError,
  AuthenticationError,
  ValidationError,
};
