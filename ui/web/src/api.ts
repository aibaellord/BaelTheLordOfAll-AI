/**
 * BAEL API Configuration
 *
 * Central configuration for all API calls.
 * Uses the Vite proxy to forward requests to the backend.
 */

// Base URLs for different API sections
export const API_BASE = "/api";
export const API_V1 = "/api/v1";

// API Endpoints
export const endpoints = {
  // Health & Status
  health: "/health",
  status: "/status",

  // Chat
  chat: {
    stream: `${API_V1}/stream`,
    quick: `${API_V1}/chat`,
    personas: `${API_V1}/personas`,
    models: `${API_V1}/models`,
    capabilities: `${API_V1}/capabilities`,
    status: `${API_V1}/status`,
  },

  // Settings
  settings: {
    all: `${API_V1}/settings`,
    llm: `${API_V1}/settings/llm`,
    memory: `${API_V1}/settings/memory`,
    reasoning: `${API_V1}/settings/reasoning`,
    security: `${API_V1}/settings/security`,
    appearance: `${API_V1}/settings/appearance`,
    advanced: `${API_V1}/settings/advanced`,
    keys: `${API_V1}/settings/keys`,
    export: `${API_V1}/settings/export`,
    import: `${API_V1}/settings/import`,
    reset: `${API_V1}/settings/reset`,
  },

  // Files
  files: {
    tree: `${API_V1}/files/tree`,
    list: `${API_V1}/files/list`,
    read: `${API_V1}/files/read`,
    write: `${API_V1}/files/write`,
    create: `${API_V1}/files/create`,
    rename: `${API_V1}/files/rename`,
    delete: `${API_V1}/files/delete`,
    upload: `${API_V1}/files/upload`,
    download: `${API_V1}/files/download`,
    search: `${API_V1}/files/search`,
    workspace: `${API_V1}/files/workspace`,
  },

  // Singularity
  singularity: {
    awaken: `${API_BASE}/singularity/awaken`,
    think: `${API_BASE}/singularity/think`,
    collective: `${API_BASE}/singularity/collective`,
    reason: `${API_BASE}/singularity/reason`,
    create: `${API_BASE}/singularity/create`,
    maximum: `${API_BASE}/singularity/maximum`,
    invoke: `${API_BASE}/singularity/invoke`,
    status: `${API_BASE}/singularity/status`,
    capabilities: `${API_BASE}/singularity/capabilities`,
    introspect: `${API_BASE}/singularity/introspect`,
    evolve: `${API_BASE}/singularity/evolve`,
  },
};

// Helper function to make API calls
export async function apiCall<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(endpoint, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// POST helper
export async function apiPost<T>(endpoint: string, data: any): Promise<T> {
  return apiCall<T>(endpoint, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// PUT helper
export async function apiPut<T>(endpoint: string, data: any): Promise<T> {
  return apiCall<T>(endpoint, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// DELETE helper
export async function apiDelete<T>(endpoint: string): Promise<T> {
  return apiCall<T>(endpoint, { method: "DELETE" });
}

// Stream helper for SSE
export async function apiStream(
  endpoint: string,
  data: any,
  onChunk: (chunk: any) => void,
  onDone: (metadata: any) => void,
  onError: (error: Error) => void,
): Promise<void> {
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error("No response body");
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.error) {
              onError(new Error(data.error));
            } else if (data.done) {
              onDone(data.metadata);
            } else if (data.content) {
              onChunk(data);
            }
          } catch (e) {
            // Skip invalid JSON lines
          }
        }
      }
    }
  } catch (error) {
    onError(error instanceof Error ? error : new Error(String(error)));
  }
}

export default endpoints;
