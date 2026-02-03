import { useState, useCallback, useMemo } from 'react'
import {
  GitBranch,
  Plus,
  Play,
  Pause,
  Save,
  Trash2,
  Settings2,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ChevronRight,
  ChevronDown,
  Code,
  MessageSquare,
  Users,
  Zap,
  FileText,
  AlertCircle,
  CheckCircle,
  Loader2,
  Server,
  Database,
  Globe,
  Terminal,
  FolderOpen,
  Search,
  GitCommit,
  Mail,
  Cloud,
  Shield,
  Clock,
  MousePointer,
  Repeat,
  Filter as FilterIcon,
  X,
  GripVertical,
  ArrowRight,
  Box,
  Layers,
  Activity
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

// Types
interface MCPTool {
  name: string
  server: string
  tier: 'essential' | 'power' | 'enhanced' | 'specialized'
  description?: string
  icon?: React.ElementType
}

interface WorkflowNode {
  id: string
  type: 'trigger' | 'mcp-tool' | 'condition' | 'loop' | 'output' | 'ai-action'
  name: string
  tool?: MCPTool
  config: Record<string, any>
  position: { x: number; y: number }
  connections: string[]
}

interface Workflow {
  id: string
  name: string
  description: string
  nodes: WorkflowNode[]
  status: 'draft' | 'active' | 'paused' | 'running'
  lastRun?: string
  runCount: number
  createdAt: string
}

// MCP Tools organized by category
const MCP_TOOLS: MCPTool[] = [
  // Filesystem
  { name: 'read_file', server: 'filesystem', tier: 'essential', icon: FileText, description: 'Read file contents' },
  { name: 'write_file', server: 'filesystem', tier: 'essential', icon: FileText, description: 'Write to file' },
  { name: 'list_directory', server: 'filesystem', tier: 'essential', icon: FolderOpen, description: 'List directory' },
  { name: 'search_files', server: 'filesystem', tier: 'essential', icon: Search, description: 'Search files' },

  // GitHub
  { name: 'create_issue', server: 'github', tier: 'essential', icon: AlertCircle, description: 'Create GitHub issue' },
  { name: 'create_pull_request', server: 'github', tier: 'essential', icon: GitBranch, description: 'Create PR' },
  { name: 'get_file_contents', server: 'github', tier: 'essential', icon: Code, description: 'Get repo file' },
  { name: 'search_repositories', server: 'github', tier: 'essential', icon: Search, description: 'Search repos' },

  // Search
  { name: 'brave_web_search', server: 'brave-search', tier: 'essential', icon: Globe, description: 'Web search' },
  { name: 'exa_search', server: 'exa', tier: 'enhanced', icon: Search, description: 'Semantic search' },

  // Database
  { name: 'sqlite_query', server: 'sqlite', tier: 'essential', icon: Database, description: 'SQL query' },
  { name: 'postgres_query', server: 'postgres', tier: 'power', icon: Database, description: 'Postgres query' },
  { name: 'redis_get', server: 'redis', tier: 'power', icon: Database, description: 'Redis get' },
  { name: 'redis_set', server: 'redis', tier: 'power', icon: Database, description: 'Redis set' },

  // Memory
  { name: 'create_entities', server: 'memory', tier: 'essential', icon: Box, description: 'Store entities' },
  { name: 'search_nodes', server: 'memory', tier: 'essential', icon: Search, description: 'Search memory' },
  { name: 'read_graph', server: 'memory', tier: 'essential', icon: Layers, description: 'Read graph' },

  // Browser
  { name: 'playwright_navigate', server: 'playwright', tier: 'power', icon: Globe, description: 'Navigate to URL' },
  { name: 'playwright_screenshot', server: 'playwright', tier: 'power', icon: MousePointer, description: 'Take screenshot' },
  { name: 'playwright_click', server: 'playwright', tier: 'power', icon: MousePointer, description: 'Click element' },
  { name: 'playwright_fill', server: 'playwright', tier: 'power', icon: FileText, description: 'Fill form' },

  // Git
  { name: 'git_status', server: 'git', tier: 'power', icon: GitCommit, description: 'Git status' },
  { name: 'git_commit', server: 'git', tier: 'power', icon: GitCommit, description: 'Git commit' },
  { name: 'git_diff', server: 'git', tier: 'power', icon: Code, description: 'Git diff' },

  // Communication
  { name: 'slack_post_message', server: 'slack', tier: 'power', icon: MessageSquare, description: 'Post to Slack' },
  { name: 'post_message', server: 'slack', tier: 'power', icon: Mail, description: 'Send message' },

  // Cloud
  { name: 's3_get_object', server: 's3', tier: 'specialized', icon: Cloud, description: 'Get S3 object' },
  { name: 's3_put_object', server: 's3', tier: 'specialized', icon: Cloud, description: 'Upload to S3' },
  { name: 'cloudflare_kv_get', server: 'cloudflare', tier: 'specialized', icon: Cloud, description: 'KV get' },

  // Code Execution
  { name: 'run_code', server: 'e2b', tier: 'specialized', icon: Code, description: 'Run code in sandbox' },
  { name: 'run_terminal_command', server: 'e2b', tier: 'specialized', icon: Terminal, description: 'Run terminal command' },

  // Productivity
  { name: 'notion_create_page', server: 'notion', tier: 'specialized', icon: FileText, description: 'Create Notion page' },
  { name: 'todoist_create_task', server: 'todoist', tier: 'specialized', icon: CheckCircle, description: 'Create task' },
  { name: 'linear_create_issue', server: 'linear', tier: 'specialized', icon: AlertCircle, description: 'Create Linear issue' },

  // AI Enhancement
  { name: 'sequential_thinking', server: 'sequential-thinking', tier: 'enhanced', icon: Zap, description: 'Step-by-step reasoning' },
]

// Node type configurations
const NODE_TYPES = {
  trigger: { label: 'Trigger', icon: Zap, color: 'bg-yellow-500', border: 'border-yellow-500/50' },
  'mcp-tool': { label: 'MCP Tool', icon: Server, color: 'bg-purple-500', border: 'border-purple-500/50' },
  'ai-action': { label: 'AI Action', icon: Zap, color: 'bg-blue-500', border: 'border-blue-500/50' },
  condition: { label: 'Condition', icon: GitBranch, color: 'bg-orange-500', border: 'border-orange-500/50' },
  loop: { label: 'Loop', icon: Repeat, color: 'bg-pink-500', border: 'border-pink-500/50' },
  output: { label: 'Output', icon: FileText, color: 'bg-green-500', border: 'border-green-500/50' }
}

// Trigger types
const TRIGGERS = [
  { id: 'manual', name: 'Manual Trigger', icon: MousePointer, description: 'Run manually' },
  { id: 'schedule', name: 'Schedule', icon: Clock, description: 'Run on schedule' },
  { id: 'webhook', name: 'Webhook', icon: Globe, description: 'HTTP webhook' },
  { id: 'file-change', name: 'File Change', icon: FolderOpen, description: 'Watch for file changes' },
  { id: 'github-event', name: 'GitHub Event', icon: GitBranch, description: 'PR, Issue, Push' },
  { id: 'slack-message', name: 'Slack Message', icon: MessageSquare, description: 'On message' }
]

// AI Actions
const AI_ACTIONS = [
  { id: 'think', name: 'BAEL Think', description: 'Multi-persona cognitive processing' },
  { id: 'analyze', name: 'Analyze Code', description: 'Code quality analysis' },
  { id: 'research', name: 'Deep Research', description: 'Research a topic' },
  { id: 'generate', name: 'Generate Code', description: 'Generate code from description' },
  { id: 'summarize', name: 'Summarize', description: 'Summarize content' },
  { id: 'council', name: 'Council Deliberate', description: 'Multi-agent deliberation' }
]

// Sample workflows
const SAMPLE_WORKFLOWS: Workflow[] = [
  {
    id: 'wf-code-review',
    name: 'Automated Code Review',
    description: 'Review PRs with AI analysis and post comments',
    nodes: [
      { id: 'n1', type: 'trigger', name: 'On PR Created', config: { trigger: 'github-event' }, position: { x: 100, y: 200 }, connections: ['n2'] },
      { id: 'n2', type: 'mcp-tool', name: 'Get PR Files', tool: MCP_TOOLS.find(t => t.name === 'get_file_contents'), config: {}, position: { x: 300, y: 200 }, connections: ['n3'] },
      { id: 'n3', type: 'ai-action', name: 'Analyze Code', config: { action: 'analyze' }, position: { x: 500, y: 200 }, connections: ['n4'] },
      { id: 'n4', type: 'mcp-tool', name: 'Create Review', tool: MCP_TOOLS.find(t => t.name === 'create_issue'), config: {}, position: { x: 700, y: 200 }, connections: [] }
    ],
    status: 'active',
    runCount: 47,
    createdAt: '2026-01-15'
  },
  {
    id: 'wf-research',
    name: 'Research & Document',
    description: 'Research topics and save to Notion',
    nodes: [
      { id: 'n1', type: 'trigger', name: 'Manual Start', config: { trigger: 'manual' }, position: { x: 100, y: 200 }, connections: ['n2'] },
      { id: 'n2', type: 'mcp-tool', name: 'Web Search', tool: MCP_TOOLS.find(t => t.name === 'brave_web_search'), config: {}, position: { x: 300, y: 200 }, connections: ['n3'] },
      { id: 'n3', type: 'ai-action', name: 'Deep Research', config: { action: 'research' }, position: { x: 500, y: 200 }, connections: ['n4'] },
      { id: 'n4', type: 'mcp-tool', name: 'Save to Notion', tool: MCP_TOOLS.find(t => t.name === 'notion_create_page'), config: {}, position: { x: 700, y: 200 }, connections: [] }
    ],
    status: 'draft',
    runCount: 0,
    createdAt: '2026-01-28'
  }
]

// Tool Palette Component
function ToolPalette({ onDragStart }: { onDragStart: (tool: MCPTool | string, type: string) => void }) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['triggers', 'ai-actions']))
  const [searchQuery, setSearchQuery] = useState('')

  const filteredTools = useMemo(() => {
    if (!searchQuery) return MCP_TOOLS
    const query = searchQuery.toLowerCase()
    return MCP_TOOLS.filter(t =>
      t.name.toLowerCase().includes(query) ||
      t.server.toLowerCase().includes(query) ||
      t.description?.toLowerCase().includes(query)
    )
  }, [searchQuery])

  const toolsByServer = useMemo(() => {
    const grouped: Record<string, MCPTool[]> = {}
    filteredTools.forEach(tool => {
      if (!grouped[tool.server]) grouped[tool.server] = []
      grouped[tool.server].push(tool)
    })
    return grouped
  }, [filteredTools])

  const toggleCategory = (cat: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev)
      if (next.has(cat)) next.delete(cat)
      else next.add(cat)
      return next
    })
  }

  return (
    <div className="w-64 border-r border-gray-700 bg-gray-900/50 flex flex-col">
      <div className="p-3 border-b border-gray-700">
        <h3 className="font-semibold text-white mb-2 flex items-center gap-2">
          <Layers className="w-4 h-4 text-purple-400" />
          Components
        </h3>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search tools..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {/* Triggers */}
        <div>
          <button
            onClick={() => toggleCategory('triggers')}
            className="w-full flex items-center gap-2 px-2 py-1.5 text-sm font-medium text-gray-300 hover:text-white"
          >
            {expandedCategories.has('triggers') ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            <Zap className="w-4 h-4 text-yellow-400" />
            Triggers
          </button>
          {expandedCategories.has('triggers') && (
            <div className="ml-4 space-y-1">
              {TRIGGERS.map(trigger => {
                const Icon = trigger.icon
                return (
                  <div
                    key={trigger.id}
                    draggable
                    onDragStart={() => onDragStart(trigger.id, 'trigger')}
                    className="flex items-center gap-2 px-2 py-1.5 text-xs bg-gray-800/50 rounded cursor-move hover:bg-gray-800 text-gray-300"
                  >
                    <Icon className="w-3 h-3 text-yellow-400" />
                    {trigger.name}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* AI Actions */}
        <div>
          <button
            onClick={() => toggleCategory('ai-actions')}
            className="w-full flex items-center gap-2 px-2 py-1.5 text-sm font-medium text-gray-300 hover:text-white"
          >
            {expandedCategories.has('ai-actions') ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            <Zap className="w-4 h-4 text-blue-400" />
            AI Actions
          </button>
          {expandedCategories.has('ai-actions') && (
            <div className="ml-4 space-y-1">
              {AI_ACTIONS.map(action => (
                <div
                  key={action.id}
                  draggable
                  onDragStart={() => onDragStart(action.id, 'ai-action')}
                  className="flex items-center gap-2 px-2 py-1.5 text-xs bg-gray-800/50 rounded cursor-move hover:bg-gray-800 text-gray-300"
                >
                  <Zap className="w-3 h-3 text-blue-400" />
                  {action.name}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* MCP Tools by Server */}
        {Object.entries(toolsByServer).map(([server, tools]) => (
          <div key={server}>
            <button
              onClick={() => toggleCategory(server)}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-sm font-medium text-gray-300 hover:text-white"
            >
              {expandedCategories.has(server) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <Server className="w-4 h-4 text-purple-400" />
              {server}
              <span className="text-xs text-gray-500 ml-auto">{tools.length}</span>
            </button>
            {expandedCategories.has(server) && (
              <div className="ml-4 space-y-1">
                {tools.map(tool => {
                  const Icon = tool.icon || Code
                  return (
                    <div
                      key={tool.name}
                      draggable
                      onDragStart={() => onDragStart(tool, 'mcp-tool')}
                      className="flex items-center gap-2 px-2 py-1.5 text-xs bg-gray-800/50 rounded cursor-move hover:bg-gray-800 text-gray-300"
                      title={tool.description}
                    >
                      <Icon className="w-3 h-3 text-purple-400" />
                      <span className="truncate">{tool.name}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        ))}

        {/* Logic Nodes */}
        <div>
          <button
            onClick={() => toggleCategory('logic')}
            className="w-full flex items-center gap-2 px-2 py-1.5 text-sm font-medium text-gray-300 hover:text-white"
          >
            {expandedCategories.has('logic') ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            <GitBranch className="w-4 h-4 text-orange-400" />
            Logic
          </button>
          {expandedCategories.has('logic') && (
            <div className="ml-4 space-y-1">
              <div
                draggable
                onDragStart={() => onDragStart('condition', 'condition')}
                className="flex items-center gap-2 px-2 py-1.5 text-xs bg-gray-800/50 rounded cursor-move hover:bg-gray-800 text-gray-300"
              >
                <GitBranch className="w-3 h-3 text-orange-400" />
                Condition (If/Else)
              </div>
              <div
                draggable
                onDragStart={() => onDragStart('loop', 'loop')}
                className="flex items-center gap-2 px-2 py-1.5 text-xs bg-gray-800/50 rounded cursor-move hover:bg-gray-800 text-gray-300"
              >
                <Repeat className="w-3 h-3 text-pink-400" />
                Loop (For Each)
              </div>
              <div
                draggable
                onDragStart={() => onDragStart('output', 'output')}
                className="flex items-center gap-2 px-2 py-1.5 text-xs bg-gray-800/50 rounded cursor-move hover:bg-gray-800 text-gray-300"
              >
                <FileText className="w-3 h-3 text-green-400" />
                Output
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Workflow Node Component
function WorkflowNodeComponent({
  node,
  isSelected,
  onSelect,
  onDelete
}: {
  node: WorkflowNode
  isSelected: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  const config = NODE_TYPES[node.type]
  const Icon = node.tool?.icon || config.icon

  return (
    <motion.div
      layoutId={node.id}
      onClick={onSelect}
      className={`absolute p-3 bg-gray-800 rounded-lg border-2 cursor-pointer min-w-[160px] ${
        isSelected ? 'border-purple-500 ring-2 ring-purple-500/30' : config.border
      }`}
      style={{ left: node.position.x, top: node.position.y }}
      whileHover={{ scale: 1.02 }}
    >
      <div className="flex items-center gap-2 mb-1">
        <div className={`p-1 rounded ${config.color}`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
        <span className="text-sm font-medium text-white truncate">{node.name}</span>
        {isSelected && (
          <button
            onClick={(e) => { e.stopPropagation(); onDelete() }}
            className="ml-auto p-1 hover:bg-red-500/20 rounded"
          >
            <X className="w-3 h-3 text-red-400" />
          </button>
        )}
      </div>
      {node.tool && (
        <div className="text-xs text-gray-400">
          {node.tool.server} • {node.tool.name}
        </div>
      )}
      {/* Connection points */}
      <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-purple-500 rounded-full border-2 border-gray-800" />
      <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-purple-500 rounded-full border-2 border-gray-800" />
    </motion.div>
  )
}

// Main Enhanced Workflow Designer
export function WorkflowDesigner() {
  const [workflows, setWorkflows] = useState<Workflow[]>(SAMPLE_WORKFLOWS)
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(SAMPLE_WORKFLOWS[0])
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [draggedItem, setDraggedItem] = useState<{ item: any; type: string } | null>(null)
  const [zoom, setZoom] = useState(1)

  const handleDragStart = useCallback((item: any, type: string) => {
    setDraggedItem({ item, type })
  }, [])

  const handleCanvasDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    if (!draggedItem || !selectedWorkflow) return

    const canvas = e.currentTarget.getBoundingClientRect()
    const x = (e.clientX - canvas.left) / zoom
    const y = (e.clientY - canvas.top) / zoom

    const newNode: WorkflowNode = {
      id: `node-${Date.now()}`,
      type: draggedItem.type as any,
      name: typeof draggedItem.item === 'string'
        ? TRIGGERS.find(t => t.id === draggedItem.item)?.name || AI_ACTIONS.find(a => a.id === draggedItem.item)?.name || draggedItem.item
        : draggedItem.item.name,
      tool: typeof draggedItem.item === 'object' ? draggedItem.item : undefined,
      config: {},
      position: { x, y },
      connections: []
    }

    setSelectedWorkflow({
      ...selectedWorkflow,
      nodes: [...selectedWorkflow.nodes, newNode]
    })
    setDraggedItem(null)
  }, [draggedItem, selectedWorkflow, zoom])

  const handleDeleteNode = useCallback((nodeId: string) => {
    if (!selectedWorkflow) return
    setSelectedWorkflow({
      ...selectedWorkflow,
      nodes: selectedWorkflow.nodes.filter(n => n.id !== nodeId)
    })
    setSelectedNode(null)
  }, [selectedWorkflow])

  const createNewWorkflow = () => {
    const newWf: Workflow = {
      id: `wf-${Date.now()}`,
      name: 'New Workflow',
      description: 'Describe what this workflow does',
      nodes: [],
      status: 'draft',
      runCount: 0,
      createdAt: new Date().toISOString().split('T')[0]
    }
    setWorkflows([...workflows, newWf])
    setSelectedWorkflow(newWf)
  }

  return (
    <div className="flex h-full bg-gray-900">
      {/* Tool Palette */}
      <ToolPalette onDragStart={handleDragStart} />

      {/* Main Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/50">
          <div className="flex items-center gap-4">
            <select
              value={selectedWorkflow?.id || ''}
              onChange={(e) => setSelectedWorkflow(workflows.find(w => w.id === e.target.value) || null)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-purple-500"
            >
              {workflows.map(wf => (
                <option key={wf.id} value={wf.id}>{wf.name}</option>
              ))}
            </select>
            <button
              onClick={createNewWorkflow}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-purple-400 hover:text-purple-300"
            >
              <Plus className="w-4 h-4" />
              New
            </button>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
              <button
                onClick={() => setZoom(z => Math.max(0.5, z - 0.1))}
                className="p-1 hover:bg-gray-700 rounded"
              >
                <ZoomOut className="w-4 h-4 text-gray-400" />
              </button>
              <span className="text-xs text-gray-400 w-12 text-center">{Math.round(zoom * 100)}%</span>
              <button
                onClick={() => setZoom(z => Math.min(2, z + 0.1))}
                className="p-1 hover:bg-gray-700 rounded"
              >
                <ZoomIn className="w-4 h-4 text-gray-400" />
              </button>
            </div>

            <button className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-700 rounded-lg text-gray-300 hover:text-white hover:border-gray-600">
              <Save className="w-4 h-4" />
              Save
            </button>

            <button className="flex items-center gap-2 px-4 py-1.5 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-500">
              <Play className="w-4 h-4" />
              Run
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div
          className="flex-1 relative overflow-auto bg-gray-900"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleCanvasDrop}
          style={{
            backgroundImage: 'radial-gradient(circle, #374151 1px, transparent 1px)',
            backgroundSize: `${20 * zoom}px ${20 * zoom}px`
          }}
        >
          <div
            className="relative w-full h-full min-w-[2000px] min-h-[1000px]"
            style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}
          >
            {selectedWorkflow?.nodes.map(node => (
              <WorkflowNodeComponent
                key={node.id}
                node={node}
                isSelected={selectedNode === node.id}
                onSelect={() => setSelectedNode(node.id)}
                onDelete={() => handleDeleteNode(node.id)}
              />
            ))}

            {/* Empty state */}
            {selectedWorkflow && selectedWorkflow.nodes.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <Layers className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium">Drop components here</p>
                  <p className="text-sm">Drag triggers, MCP tools, and actions from the left panel</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Status Bar */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-gray-700 bg-gray-800/50 text-xs text-gray-400">
          <div className="flex items-center gap-4">
            <span>{selectedWorkflow?.nodes.length || 0} nodes</span>
            <span>•</span>
            <span>Status: {selectedWorkflow?.status}</span>
            <span>•</span>
            <span>{selectedWorkflow?.runCount || 0} runs</span>
          </div>
          <div className="flex items-center gap-2">
            <Activity className="w-3 h-3" />
            <span>33 MCP servers available</span>
          </div>
        </div>
      </div>
    </div>
  )
}
