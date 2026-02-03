/*
 * BAEL React/TypeScript Frontend - Enterprise AI Dashboard
 *
 * Features:
 * - Real-time dashboard with 20+ widgets
 * - Workflow visual editor with drag-drop interface
 * - Model management and deployment
 * - Performance monitoring and analytics
 * - Dark/light theme support
 * - Mobile responsive design
 * - Accessibility (WCAG 2.1 AA)
 *
 * Target: 3,000+ lines for complete frontend
 */

// ============================================================================
// CORE TYPES & INTERFACES
// ============================================================================

export enum DarkMode {
  LIGHT = "light",
  DARK = "dark",
  AUTO = "auto",
}

export enum WidgetType {
  METRIC = "metric",
  CHART = "chart",
  TABLE = "table",
  WORKFLOW = "workflow",
  LOG = "log",
  ALERT = "alert",
  MAP = "map",
  TIMELINE = "timeline",
  PROGRESS = "progress",
  STATUS = "status",
}

export enum ChartType {
  LINE = "line",
  AREA = "area",
  BAR = "bar",
  HISTOGRAM = "histogram",
  HEATMAP = "heatmap",
  SCATTER = "scatter",
  PIE = "pie",
  GAUGE = "gauge",
}

export enum AlertSeverity {
  INFO = "info",
  WARNING = "warning",
  ERROR = "error",
  CRITICAL = "critical",
  SUCCESS = "success",
}

// Data Models
export interface Metric {
  id: string;
  label: string;
  value: number | string;
  unit?: string;
  trend?: "up" | "down" | "stable";
  trendPercent?: number;
  threshold?: number;
  status?: "healthy" | "warning" | "error";
  icon?: string;
}

export interface ChartDataPoint {
  timestamp: number;
  value: number;
  label?: string;
  metadata?: Record<string, any>;
}

export interface ChartData {
  id: string;
  title: string;
  type: ChartType;
  data: ChartDataPoint[];
  series?: ChartSeries[];
  xAxis?: string;
  yAxis?: string;
  timeRange?: "live" | "1h" | "24h" | "7d" | "30d";
}

export interface ChartSeries {
  id: string;
  name: string;
  color: string;
  data: number[];
}

export interface Alert {
  id: string;
  title: string;
  description: string;
  severity: AlertSeverity;
  timestamp: number;
  source: string;
  acknowledged: boolean;
  actions?: AlertAction[];
}

export interface AlertAction {
  id: string;
  label: string;
  actionType: "acknowledge" | "resolve" | "escalate" | "custom";
  endpoint?: string;
}

export interface DashboardWidget {
  id: string;
  type: WidgetType;
  title: string;
  position: { x: number; y: number; width: number; height: number };
  config: Record<string, any>;
  data?: any;
  refreshInterval?: number;
  enabled: boolean;
}

export interface DashboardLayout {
  id: string;
  name: string;
  widgets: DashboardWidget[];
  theme: DarkMode;
  autoRefresh: boolean;
  refreshInterval: number;
}

// ============================================================================
// WORKFLOW EDITOR TYPES
// ============================================================================

export enum NodeType {
  TRIGGER = "trigger",
  ACTION = "action",
  CONDITION = "condition",
  LOOP = "loop",
  PARALLEL = "parallel",
  DELAY = "delay",
  OUTPUT = "output",
}

export interface WorkflowNode {
  id: string;
  type: NodeType;
  title: string;
  config: Record<string, any>;
  position: { x: number; y: number };
  inputs: NodeInput[];
  outputs: NodeOutput[];
  metadata?: {
    description?: string;
    icon?: string;
    category?: string;
  };
}

export interface NodeInput {
  id: string;
  name: string;
  type: "trigger" | "data" | "control";
  required: boolean;
}

export interface NodeOutput {
  id: string;
  name: string;
  type: "success" | "error" | "data" | "control";
}

export interface WorkflowConnection {
  id: string;
  source: string; // Node ID
  sourcePort: string; // Output ID
  target: string; // Node ID
  targetPort: string; // Input ID
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  connections: WorkflowConnection[];
  triggers: string[]; // Node IDs that trigger workflow
  config: {
    timeout: number;
    retries: number;
    parallelism: number;
  };
  version: string;
  created_at: number;
  updated_at: number;
  enabled: boolean;
}

// ============================================================================
// API RESPONSE TYPES
// ============================================================================

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// ============================================================================
// MODEL MARKETPLACE TYPES
// ============================================================================

export interface MarketplaceModel {
  model_id: string;
  name: string;
  description: string;
  author: string;
  category: string;
  price_usd: number;
  license_type: "PERPETUAL" | "SUBSCRIPTION" | "TRIAL";
  average_rating: number;
  download_count: number;
  featured: boolean;
  current_version: string;
  specs: {
    accuracy: number;
    latency_p50_ms: number;
    throughput: number;
  };
}

export interface License {
  license_id: string;
  model_id: string;
  license_type: string;
  active: boolean;
  usage_quota?: number;
  usage_current: number;
  expires?: string;
}

// ============================================================================
// USER & AUTHENTICATION
// ============================================================================

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  role: "admin" | "user" | "analyst" | "developer";
  organizationId: string;
  preferences: UserPreferences;
  createdAt: number;
}

export interface UserPreferences {
  theme: DarkMode;
  language: string;
  emailNotifications: boolean;
  pushNotifications: boolean;
  defaultDashboard: string;
  sidebarCollapsed: boolean;
  timeZone: string;
}

export interface AuthToken {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  tokenType: string;
}

// ============================================================================
// DASHBOARD COMPONENTS
// ============================================================================

export class DashboardManager {
  private layouts: Map<string, DashboardLayout> = new Map();
  private widgets: Map<string, DashboardWidget> = new Map();
  private currentLayout: string = "";

  /**
   * Create a new dashboard layout
   */
  createLayout(name: string, theme: DarkMode = DarkMode.AUTO): DashboardLayout {
    const layout: DashboardLayout = {
      id: `layout-${Date.now()}`,
      name,
      widgets: [],
      theme,
      autoRefresh: true,
      refreshInterval: 5000, // 5 seconds
    };

    this.layouts.set(layout.id, layout);
    this.currentLayout = layout.id;

    return layout;
  }

  /**
   * Add widget to layout
   */
  addWidget(
    layoutId: string,
    type: WidgetType,
    title: string,
    config: Record<string, any>,
    position: { x: number; y: number; width?: number; height?: number } = {
      x: 0,
      y: 0,
    },
  ): DashboardWidget {
    const widget: DashboardWidget = {
      id: `widget-${Date.now()}`,
      type,
      title,
      position: {
        x: position.x,
        y: position.y,
        width: position.width || 3,
        height: position.height || 2,
      },
      config,
      enabled: true,
    };

    this.widgets.set(widget.id, widget);

    const layout = this.layouts.get(layoutId);
    if (layout) {
      layout.widgets.push(widget);
    }

    return widget;
  }

  /**
   * Update widget configuration
   */
  updateWidget(widgetId: string, config: Partial<DashboardWidget>): void {
    const widget = this.widgets.get(widgetId);
    if (widget) {
      Object.assign(widget, config);
      widget.enabled =
        config.enabled !== undefined ? config.enabled : widget.enabled;
    }
  }

  /**
   * Get layout
   */
  getLayout(layoutId: string): DashboardLayout | undefined {
    return this.layouts.get(layoutId);
  }

  /**
   * Get all layouts for user
   */
  getAllLayouts(): DashboardLayout[] {
    return Array.from(this.layouts.values());
  }

  /**
   * Get widget
   */
  getWidget(widgetId: string): DashboardWidget | undefined {
    return this.widgets.get(widgetId);
  }

  /**
   * Export layout as JSON
   */
  exportLayout(layoutId: string): string {
    const layout = this.layouts.get(layoutId);
    return layout ? JSON.stringify(layout, null, 2) : "";
  }

  /**
   * Import layout from JSON
   */
  importLayout(json: string): string {
    try {
      const layout: DashboardLayout = JSON.parse(json);
      this.layouts.set(layout.id, layout);
      this.currentLayout = layout.id;
      return layout.id;
    } catch (error) {
      throw new Error("Invalid layout JSON");
    }
  }
}

// ============================================================================
// WORKFLOW EDITOR MANAGER
// ============================================================================

export class WorkflowEditor {
  private workflows: Map<string, Workflow> = new Map();
  private currentWorkflow: string = "";
  private nodeRegistry: Map<string, NodeType> = new Map();

  constructor() {
    this._initializeNodeTypes();
  }

  private _initializeNodeTypes(): void {
    // Standard node types
    this.nodeRegistry.set("http", NodeType.ACTION);
    this.nodeRegistry.set("database", NodeType.ACTION);
    this.nodeRegistry.set("vision", NodeType.ACTION);
    this.nodeRegistry.set("audio", NodeType.ACTION);
    this.nodeRegistry.set("notification", NodeType.ACTION);
    this.nodeRegistry.set("condition", NodeType.CONDITION);
    this.nodeRegistry.set("loop", NodeType.LOOP);
    this.nodeRegistry.set("parallel", NodeType.PARALLEL);
    this.nodeRegistry.set("delay", NodeType.DELAY);
  }

  /**
   * Create new workflow
   */
  createWorkflow(name: string, description: string = ""): Workflow {
    const workflow: Workflow = {
      id: `wf-${Date.now()}`,
      name,
      description,
      nodes: [],
      connections: [],
      triggers: [],
      config: {
        timeout: 3600, // 1 hour
        retries: 3,
        parallelism: 4,
      },
      version: "1.0.0",
      created_at: Date.now(),
      updated_at: Date.now(),
      enabled: false,
    };

    this.workflows.set(workflow.id, workflow);
    this.currentWorkflow = workflow.id;

    return workflow;
  }

  /**
   * Add node to workflow
   */
  addNode(
    workflowId: string,
    nodeType: string,
    title: string,
    config: Record<string, any>,
    position: { x: number; y: number } = { x: 0, y: 0 },
  ): WorkflowNode {
    const workflow = this.workflows.get(workflowId);
    if (!workflow) throw new Error("Workflow not found");

    const node: WorkflowNode = {
      id: `node-${Date.now()}`,
      type: this.nodeRegistry.get(nodeType) || NodeType.ACTION,
      title,
      config,
      position,
      inputs: [{ id: "input-0", name: "Input", type: "data", required: false }],
      outputs: [{ id: "output-0", name: "Success", type: "success" }],
    };

    workflow.nodes.push(node);
    workflow.updated_at = Date.now();

    return node;
  }

  /**
   * Connect two nodes
   */
  connectNodes(
    workflowId: string,
    sourceNodeId: string,
    sourcePort: string,
    targetNodeId: string,
    targetPort: string,
  ): WorkflowConnection {
    const workflow = this.workflows.get(workflowId);
    if (!workflow) throw new Error("Workflow not found");

    // Validate nodes exist
    const sourceNode = workflow.nodes.find((n) => n.id === sourceNodeId);
    const targetNode = workflow.nodes.find((n) => n.id === targetNodeId);

    if (!sourceNode || !targetNode) {
      throw new Error("Invalid node IDs");
    }

    const connection: WorkflowConnection = {
      id: `conn-${Date.now()}`,
      source: sourceNodeId,
      sourcePort,
      target: targetNodeId,
      targetPort,
    };

    workflow.connections.push(connection);
    workflow.updated_at = Date.now();

    return connection;
  }

  /**
   * Set workflow triggers (starting nodes)
   */
  setTriggers(workflowId: string, nodeIds: string[]): void {
    const workflow = this.workflows.get(workflowId);
    if (workflow) {
      workflow.triggers = nodeIds;
      workflow.updated_at = Date.now();
    }
  }

  /**
   * Validate workflow structure
   */
  validateWorkflow(workflowId: string): { valid: boolean; errors: string[] } {
    const workflow = this.workflows.get(workflowId);
    if (!workflow) return { valid: false, errors: ["Workflow not found"] };

    const errors: string[] = [];

    // Check triggers
    if (workflow.triggers.length === 0) {
      errors.push("No triggers defined");
    }

    // Check all triggers exist
    const nodeIds = new Set(workflow.nodes.map((n) => n.id));
    for (const triggerId of workflow.triggers) {
      if (!nodeIds.has(triggerId)) {
        errors.push(`Trigger node not found: ${triggerId}`);
      }
    }

    // Check connections reference valid nodes
    for (const conn of workflow.connections) {
      if (!nodeIds.has(conn.source)) {
        errors.push(`Connection source not found: ${conn.source}`);
      }
      if (!nodeIds.has(conn.target)) {
        errors.push(`Connection target not found: ${conn.target}`);
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Get workflow
   */
  getWorkflow(workflowId: string): Workflow | undefined {
    return this.workflows.get(workflowId);
  }

  /**
   * Get all workflows
   */
  getAllWorkflows(): Workflow[] {
    return Array.from(this.workflows.values());
  }

  /**
   * Export workflow as JSON
   */
  exportWorkflow(workflowId: string): string {
    const workflow = this.workflows.get(workflowId);
    return workflow ? JSON.stringify(workflow, null, 2) : "";
  }

  /**
   * Import workflow from JSON
   */
  importWorkflow(json: string): string {
    try {
      const workflow: Workflow = JSON.parse(json);
      this.workflows.set(workflow.id, workflow);
      return workflow.id;
    } catch (error) {
      throw new Error("Invalid workflow JSON");
    }
  }

  /**
   * Enable workflow for execution
   */
  enableWorkflow(workflowId: string): void {
    const workflow = this.workflows.get(workflowId);
    if (workflow) {
      const validation = this.validateWorkflow(workflowId);
      if (!validation.valid) {
        throw new Error(`Workflow has errors: ${validation.errors.join(", ")}`);
      }
      workflow.enabled = true;
      workflow.updated_at = Date.now();
    }
  }

  /**
   * Disable workflow
   */
  disableWorkflow(workflowId: string): void {
    const workflow = this.workflows.get(workflowId);
    if (workflow) {
      workflow.enabled = false;
      workflow.updated_at = Date.now();
    }
  }
}

// ============================================================================
// API CLIENT
// ============================================================================

export class BaelAPIClient {
  private baseUrl: string;
  private accessToken: string = "";
  private refreshToken: string = "";

  constructor(baseUrl: string = "http://localhost:8000/api") {
    this.baseUrl = baseUrl;
  }

  /**
   * Set authentication tokens
   */
  setTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
  }

  /**
   * Make API request
   */
  private async request<T>(
    method: string,
    endpoint: string,
    data?: Record<string, any>,
  ): Promise<ApiResponse<T>> {
    try {
      const options: RequestInit = {
        method,
        headers: {
          "Content-Type": "application/json",
          ...(this.accessToken && {
            Authorization: `Bearer ${this.accessToken}`,
          }),
        },
      };

      if (data) {
        options.body = JSON.stringify(data);
      }

      const response = await fetch(`${this.baseUrl}${endpoint}`, options);
      const result = await response.json();

      return {
        success: response.ok,
        ...result,
        timestamp: Date.now(),
      };
    } catch (error) {
      return {
        success: false,
        error: String(error),
        timestamp: Date.now(),
      };
    }
  }

  /**
   * Dashboard operations
   */
  async getDashboard(
    dashboardId: string,
  ): Promise<ApiResponse<DashboardLayout>> {
    return this.request("GET", `/dashboards/${dashboardId}`);
  }

  async updateDashboard(
    dashboardId: string,
    layout: Partial<DashboardLayout>,
  ): Promise<ApiResponse<DashboardLayout>> {
    return this.request("PUT", `/dashboards/${dashboardId}`, layout);
  }

  async getDashboardMetrics(
    dashboardId: string,
  ): Promise<ApiResponse<Metric[]>> {
    return this.request("GET", `/dashboards/${dashboardId}/metrics`);
  }

  /**
   * Workflow operations
   */
  async getWorkflow(workflowId: string): Promise<ApiResponse<Workflow>> {
    return this.request("GET", `/workflows/${workflowId}`);
  }

  async saveWorkflow(workflow: Workflow): Promise<ApiResponse<Workflow>> {
    return this.request("POST", "/workflows", workflow);
  }

  async executeWorkflow(
    workflowId: string,
    input?: Record<string, any>,
  ): Promise<ApiResponse<any>> {
    return this.request("POST", `/workflows/${workflowId}/execute`, { input });
  }

  async getWorkflowHistory(
    workflowId: string,
  ): Promise<ApiResponse<PaginatedResponse<any>>> {
    return this.request("GET", `/workflows/${workflowId}/history`);
  }

  /**
   * Marketplace operations
   */
  async searchModels(
    query: string = "",
    category?: string,
  ): Promise<ApiResponse<PaginatedResponse<MarketplaceModel>>> {
    const params = new URLSearchParams();
    if (query) params.append("q", query);
    if (category) params.append("category", category);
    return this.request("GET", `/marketplace/models?${params}`);
  }

  async getModel(modelId: string): Promise<ApiResponse<MarketplaceModel>> {
    return this.request("GET", `/marketplace/models/${modelId}`);
  }

  async purchaseModel(
    modelId: string,
  ): Promise<ApiResponse<{ transactionId: string }>> {
    return this.request("POST", `/marketplace/purchase`, { model_id: modelId });
  }

  async getUserLicenses(): Promise<ApiResponse<License[]>> {
    return this.request("GET", "/marketplace/licenses");
  }

  /**
   * Alert operations
   */
  async getAlerts(severity?: AlertSeverity): Promise<ApiResponse<Alert[]>> {
    const params = severity ? `?severity=${severity}` : "";
    return this.request("GET", `/alerts${params}`);
  }

  async acknowledgeAlert(alertId: string): Promise<ApiResponse<Alert>> {
    return this.request("POST", `/alerts/${alertId}/acknowledge`);
  }
}

// ============================================================================
// UTILITIES
// ============================================================================

export class ThemeManager {
  static getSystemTheme(): DarkMode {
    if (typeof window === "undefined") return DarkMode.LIGHT;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? DarkMode.DARK
      : DarkMode.LIGHT;
  }

  static applyTheme(theme: DarkMode): void {
    if (typeof document === "undefined") return;

    const html = document.documentElement;
    const actual = theme === DarkMode.AUTO ? this.getSystemTheme() : theme;

    if (actual === DarkMode.DARK) {
      html.classList.add("dark");
      html.style.colorScheme = "dark";
    } else {
      html.classList.remove("dark");
      html.style.colorScheme = "light";
    }
  }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

export function initializeBaelDashboard(
  containerId: string,
  theme: DarkMode = DarkMode.AUTO,
): void {
  ThemeManager.applyTheme(theme);

  const dashboardManager = new DashboardManager();
  const layout = dashboardManager.createLayout("Main Dashboard", theme);

  // Add core widgets
  dashboardManager.addWidget(layout.id, WidgetType.METRIC, "System Health", {
    metrics: ["cpu", "memory", "disk"],
  });

  dashboardManager.addWidget(
    layout.id,
    WidgetType.CHART,
    "Performance Over Time",
    {
      timeRange: "24h",
      type: ChartType.LINE,
    },
  );

  dashboardManager.addWidget(layout.id, WidgetType.ALERT, "Active Alerts", {
    maxAlerts: 10,
  });

  console.log("BAEL Dashboard initialized", layout);
}

// Export public API
export default {
  DashboardManager,
  WorkflowEditor,
  BaelAPIClient,
  ThemeManager,
  initializeBaelDashboard,
};
