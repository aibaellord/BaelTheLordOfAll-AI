"""
Example GraphQL queries, mutations, and subscriptions for BAEL API.
"""

# =============================================================================
# QUERIES
# =============================================================================

# Get all agents
QUERY_ALL_AGENTS = """
query GetAgents {
  agents(limit: 10) {
    id
    name
    persona
    status
    capabilities
    activeTasks
    totalTasksCompleted
    averageResponseTime
    lastActive
  }
}
"""

# Get agents with filter
QUERY_FILTERED_AGENTS = """
query GetFilteredAgents($status: AgentStatus, $persona: String) {
  agents(filter: { status: $status, persona: $persona }) {
    id
    name
    status
    persona
  }
}
"""

# Get single agent
QUERY_AGENT = """
query GetAgent($id: ID!) {
  agent(id: $id) {
    id
    name
    persona
    status
    capabilities
    activeTasks
    totalTasksCompleted
    averageResponseTime
    createdAt
    lastActive
  }
}
"""

# Get all workflows
QUERY_ALL_WORKFLOWS = """
query GetWorkflows {
  workflows(limit: 10) {
    id
    name
    description
    version
    tasks
    executionCount
    successRate
    createdAt
  }
}
"""

# Get workflow execution history
QUERY_WORKFLOW_EXECUTIONS = """
query GetWorkflowExecutions($workflowId: ID!) {
  workflowExecutions(workflowId: $workflowId, limit: 20) {
    id
    workflowId
    status
    startedAt
    completedAt
    durationSeconds
    progress
    currentTask
    error
  }
}
"""

# Get workflow execution details
QUERY_WORKFLOW_EXECUTION = """
query GetWorkflowExecution($id: ID!) {
  workflowExecution(id: $id) {
    id
    workflowId
    status
    startedAt
    completedAt
    durationSeconds
    progress
    currentTask
    result
    error
  }
}
"""

# Get all plugins
QUERY_ALL_PLUGINS = """
query GetPlugins {
  plugins(limit: 20) {
    id
    name
    description
    category
    version
    author
    downloads
    rating
    ratingCount
    installed
    trusted
    createdAt
  }
}
"""

# Get plugins with filter
QUERY_FILTERED_PLUGINS = """
query GetFilteredPlugins($category: PluginCategory, $installed: Boolean) {
  plugins(filter: { category: $category, installed: $installed }) {
    id
    name
    category
    installed
    rating
  }
}
"""

# Get cluster status
QUERY_CLUSTER_STATUS = """
query GetClusterStatus {
  clusterStatus {
    totalNodes
    healthyNodes
    leaderNode
    totalAgents
    totalTasks
    averageLoad
  }
}
"""

# Get cluster nodes
QUERY_CLUSTER_NODES = """
query GetClusterNodes {
  clusterNodes {
    id
    hostname
    port
    role
    status
    load
    agentsCount
    tasksCount
    lastHeartbeat
  }
}
"""

# Get system metrics
QUERY_METRICS = """
query GetMetrics($timeRange: TimeRange!) {
  metrics(timeRange: $timeRange) {
    timestamp
    requestsPerMinute
    activeConnections
    cacheHitRate
    averageResponseTime
    errorRate
    cpuUsage
    memoryUsage
  }
}
"""

# Get system health
QUERY_HEALTH = """
query GetHealth {
  health {
    status
    version
    uptimeSeconds
    components
  }
}
"""

# Get tasks
QUERY_TASKS = """
query GetTasks($agentId: ID) {
  tasks(agentId: $agentId, limit: 20) {
    id
    type
    status
    agentId
    workflowId
    startedAt
    completedAt
    durationSeconds
    result
    error
  }
}
"""

# =============================================================================
# MUTATIONS
# =============================================================================

# Create agent
MUTATION_CREATE_AGENT = """
mutation CreateAgent($input: CreateAgentInput!) {
  createAgent(input: $input) {
    agent {
      id
      name
      persona
      capabilities
    }
    success
    message
  }
}
"""

# Delete agent
MUTATION_DELETE_AGENT = """
mutation DeleteAgent($id: ID!) {
  deleteAgent(id: $id) {
    success
    message
  }
}
"""

# Create workflow
MUTATION_CREATE_WORKFLOW = """
mutation CreateWorkflow($input: CreateWorkflowInput!) {
  createWorkflow(input: $input) {
    workflow {
      id
      name
      description
      version
    }
    success
    message
  }
}
"""

# Delete workflow
MUTATION_DELETE_WORKFLOW = """
mutation DeleteWorkflow($id: ID!) {
  deleteWorkflow(id: $id) {
    success
    message
  }
}
"""

# Execute workflow
MUTATION_EXECUTE_WORKFLOW = """
mutation ExecuteWorkflow($input: ExecuteWorkflowInput!) {
  executeWorkflow(input: $input) {
    execution {
      id
      workflowId
      status
      startedAt
      progress
    }
    success
    message
  }
}
"""

# Cancel workflow
MUTATION_CANCEL_WORKFLOW = """
mutation CancelWorkflow($executionId: ID!) {
  cancelWorkflow(executionId: $executionId) {
    success
    message
  }
}
"""

# Install plugin
MUTATION_INSTALL_PLUGIN = """
mutation InstallPlugin($pluginId: ID!) {
  installPlugin(pluginId: $pluginId) {
    plugin {
      id
      name
      installed
    }
    success
    message
  }
}
"""

# Uninstall plugin
MUTATION_UNINSTALL_PLUGIN = """
mutation UninstallPlugin($pluginId: ID!) {
  uninstallPlugin(pluginId: $pluginId) {
    success
    message
  }
}
"""

# =============================================================================
# SUBSCRIPTIONS
# =============================================================================

# Subscribe to agent activity
SUBSCRIPTION_AGENT_ACTIVITY = """
subscription AgentActivity($agentId: ID) {
  agentActivity(agentId: $agentId) {
    agentId
    eventType
    timestamp
    data
  }
}
"""

# Subscribe to workflow progress
SUBSCRIPTION_WORKFLOW_PROGRESS = """
subscription WorkflowProgress($executionId: ID!) {
  workflowProgress(executionId: $executionId) {
    executionId
    progress
    status
    currentTask
    timestamp
  }
}
"""

# Subscribe to system health
SUBSCRIPTION_SYSTEM_HEALTH = """
subscription SystemHealth {
  systemHealth {
    status
    version
    uptimeSeconds
    components
  }
}
"""

# =============================================================================
# EXAMPLE VARIABLES
# =============================================================================

EXAMPLE_VARIABLES = {
    # Agent filter
    "agent_filter": {
        "status": "IDLE",
        "persona": "assistant"
    },

    # Create agent input
    "create_agent_input": {
        "input": {
            "name": "Research Agent",
            "persona": "researcher",
            "capabilities": ["web_search", "data_analysis"]
        }
    },

    # Create workflow input
    "create_workflow_input": {
        "input": {
            "name": "Data Pipeline",
            "description": "ETL pipeline for data processing",
            "tasks": [
                {"id": "extract", "action": "extract_data"},
                {"id": "transform", "action": "transform_data"},
                {"id": "load", "action": "load_data"}
            ]
        }
    },

    # Execute workflow input
    "execute_workflow_input": {
        "input": {
            "workflowId": "workflow-123",
            "parameters": {
                "source": "database",
                "destination": "warehouse"
            }
        }
    },

    # Time range
    "time_range": {
        "timeRange": {
            "start": "2026-02-02T00:00:00Z",
            "end": "2026-02-02T23:59:59Z"
        }
    },

    # Plugin filter
    "plugin_filter": {
        "category": "TOOL",
        "installed": True
    }
}
