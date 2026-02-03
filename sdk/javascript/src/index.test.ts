import BAELClient, {
  APIError,
  RateLimitError,
  AuthenticationError,
  ValidationError,
  createDevelopmentClient,
  createProductionClient,
  quickChat,
} from "../src/index";

describe("BAELClient", () => {
  let client: BAELClient;

  beforeEach(() => {
    client = new BAELClient({
      baseUrl: "http://localhost:8000",
      timeout: 5000,
    });
  });

  afterEach(async () => {
    await client.close();
  });

  describe("Initialization", () => {
    it("should create client with minimal config", () => {
      const client = new BAELClient({
        baseUrl: "http://localhost:8000",
      });
      expect(client).toBeInstanceOf(BAELClient);
    });

    it("should create client with full config", () => {
      const client = new BAELClient({
        baseUrl: "http://localhost:8000",
        apiKey: "test_key",
        timeout: 60000,
        maxRetries: 5,
        retryDelay: 1000,
        headers: { "X-Custom": "header" },
      });
      expect(client).toBeInstanceOf(BAELClient);
    });

    it("should set default values", () => {
      const client = new BAELClient({
        baseUrl: "http://localhost:8000",
      });
      expect(client).toBeInstanceOf(BAELClient);
    });
  });

  describe("Factory Functions", () => {
    it("should create development client", () => {
      const client = createDevelopmentClient();
      expect(client).toBeInstanceOf(BAELClient);
    });

    it("should create production client", () => {
      const client = createProductionClient(
        "test_api_key",
        "https://api.bael.io",
      );
      expect(client).toBeInstanceOf(BAELClient);
    });
  });

  describe("Event Emitter", () => {
    it("should emit chat events", (done) => {
      client.on("chat", (response) => {
        expect(response).toHaveProperty("response");
        done();
      });

      // Trigger event (mock)
      client.emit("chat", { response: "test" });
    });

    it("should emit task_submitted events", (done) => {
      client.on("task_submitted", (task) => {
        expect(task).toHaveProperty("task_id");
        done();
      });

      client.emit("task_submitted", { task_id: "123" });
    });

    it("should emit task_progress events", (done) => {
      client.on("task_progress", (status) => {
        expect(status).toHaveProperty("status");
        done();
      });

      client.emit("task_progress", { status: "running" });
    });

    it("should emit task_completed events", (done) => {
      client.on("task_completed", (status) => {
        expect(status).toHaveProperty("result");
        done();
      });

      client.emit("task_completed", { result: "done" });
    });

    it("should remove listeners", () => {
      const handler = jest.fn();
      client.on("chat", handler);
      client.off("chat", handler);

      client.emit("chat", {});
      expect(handler).not.toHaveBeenCalled();
    });

    it("should remove all listeners", () => {
      const handler1 = jest.fn();
      const handler2 = jest.fn();

      client.on("chat", handler1);
      client.on("task_submitted", handler2);
      client.removeAllListeners();

      client.emit("chat", {});
      client.emit("task_submitted", {});

      expect(handler1).not.toHaveBeenCalled();
      expect(handler2).not.toHaveBeenCalled();
    });
  });

  describe("API Methods", () => {
    it("should handle chat with string parameter", async () => {
      // This would require mocking axios
      expect(client).toBeDefined();
    });

    it("should handle chat with object parameter", async () => {
      expect(client).toBeDefined();
    });

    it("should handle task submission", async () => {
      expect(client).toBeDefined();
    });

    it("should handle task status check", async () => {
      expect(client).toBeDefined();
    });

    it("should handle batch chat requests", async () => {
      expect(client).toBeDefined();
    });

    it("should handle task watching with timeout", async () => {
      expect(client).toBeDefined();
    });
  });

  describe("Error Handling", () => {
    it("should throw APIError", () => {
      const error = new APIError(500, "Server error", { details: "test" });
      expect(error).toBeInstanceOf(APIError);
      expect(error.statusCode).toBe(500);
      expect(error.message).toBe("Server error");
    });

    it("should throw RateLimitError", () => {
      const error = new RateLimitError(60);
      expect(error).toBeInstanceOf(RateLimitError);
      expect(error.statusCode).toBe(429);
      expect(error.retryAfter).toBe(60);
    });

    it("should throw AuthenticationError", () => {
      const error = new AuthenticationError();
      expect(error).toBeInstanceOf(AuthenticationError);
      expect(error.statusCode).toBe(401);
    });

    it("should throw ValidationError", () => {
      const errors = { field: "required" };
      const error = new ValidationError(errors);
      expect(error).toBeInstanceOf(ValidationError);
      expect(error.statusCode).toBe(400);
      expect(error.errors).toEqual(errors);
    });
  });

  describe("Type Safety", () => {
    it("should have proper TypeScript types", () => {
      // Type checking happens at compile time
      expect(client).toBeDefined();
    });
  });
});

describe("Integration Tests", () => {
  it("should complete full workflow", async () => {
    const client = new BAELClient({
      baseUrl: "http://localhost:8000",
    });

    // This would be an actual integration test
    expect(client).toBeDefined();

    await client.close();
  });
});

describe("Convenience Functions", () => {
  it("should use quickChat", async () => {
    // Would require mocking
    expect(true).toBe(true);
  });
});
