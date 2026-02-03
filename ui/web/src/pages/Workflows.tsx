import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
  Code,
  MessageSquare,
  Users,
  Zap,
  FileText,
  AlertCircle,
  CheckCircle,
  Loader2
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'

// Simple workflow node types
type NodeType = 'trigger' | 'action' | 'condition' | 'loop' | 'output'

interface WorkflowNode {
  id: string
  type: NodeType
  name: string
  config: Record<string, any>
  position: { x: number; y: number }
  connections: string[]
}

interface Workflow {
  id: string
  name: string
  description: string
  nodes: WorkflowNode[]
  status: 'draft' | 'active' | 'paused'
  lastRun?: number
  runCount: number
}

const nodeTypes: { type: NodeType; label: string; icon: React.ElementType; color: string }[] = [
  { type: 'trigger', label: 'Trigger', icon: Zap, color: 'bg-yellow-500' },
  { type: 'action', label: 'Action', icon: Code, color: 'bg-blue-500' },
  { type: 'condition', label: 'Condition', icon: GitBranch, color: 'bg-purple-500' },
  { type: 'loop', label: 'Loop', icon: AlertCircle, color: 'bg-orange-500' },
  { type: 'output', label: 'Output', icon: FileText, color: 'bg-green-500' },
]

// Mock workflows - fallback when API unavailable
const mockWorkflows: Workflow[] = [
  {
    id: 'wf-1',
    name: 'Code Review Workflow',
    description: 'Automatically review code changes and provide suggestions',
    nodes: [
      { id: 'n1', type: 'trigger', name: 'On PR Created', config: {}, position: { x: 100, y: 100 }, connections: ['n2'] },
      { id: 'n2', type: 'action', name: 'Analyze Code', config: {}, position: { x: 300, y: 100 }, connections: ['n3'] },
      { id: 'n3', type: 'action', name: 'Generate Review', config: {}, position: { x: 500, y: 100 }, connections: ['n4'] },
      { id: 'n4', type: 'output', name: 'Post Comment', config: {}, position: { x: 700, y: 100 }, connections: [] },
    ],
    status: 'active',
    runCount: 23
  },
  {
    id: 'wf-2',
    name: 'Daily Summary',
    description: 'Generate and send daily activity summaries',
    nodes: [
      { id: 'n1', type: 'trigger', name: 'Schedule: 9 AM', config: {}, position: { x: 100, y: 100 }, connections: ['n2'] },
      { id: 'n2', type: 'action', name: 'Collect Data', config: {}, position: { x: 300, y: 100 }, connections: ['n3'] },
      { id: 'n3', type: 'output', name: 'Send Email', config: {}, position: { x: 500, y: 100 }, connections: [] },
    ],
    status: 'paused',
    runCount: 45
  },
]

// Map API workflow to frontend format
function mapApiWorkflow(apiWf: any): Workflow {
  return {
    id: apiWf.id || `wf-${Date.now()}`,
    name: apiWf.name || 'Untitled',
    description: apiWf.description || '',
    nodes: apiWf.nodes || [],
    status: apiWf.status || 'draft',
    lastRun: apiWf.lastRun,
    runCount: apiWf.runCount || 0
  }
}

export function Workflows() {
  const queryClient = useQueryClient()
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)
  const [isEditing, setIsEditing] = useState(false)

  // Fetch workflows from API
  const { data: apiWorkflows, isLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: async () => {
      const res = await fetch('/api/v1/workflows')
      if (!res.ok) throw new Error('Failed to fetch workflows')
      const data = await res.json()
      return data.workflows || []
    },
    staleTime: 30000,
    retry: 2
  })

  // Use API workflows if available, otherwise fallback to mock
  const workflows: Workflow[] = apiWorkflows
    ? apiWorkflows.map(mapApiWorkflow)
    : mockWorkflows

  // Create workflow mutation
  const createMutation = useMutation({
    mutationFn: async (workflow: Partial<Workflow>) => {
      const res = await fetch('/api/v1/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflow)
      })
      if (!res.ok) throw new Error('Failed to create workflow')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
    }
  })

  const handleCreateWorkflow = async () => {
    const newWorkflow = {
      name: 'New Workflow',
      description: 'Describe your workflow',
      nodes: [
        { id: 'n1', type: 'trigger', name: 'Trigger', config: {}, position: { x: 100, y: 200 }, connections: [] }
      ],
      status: 'draft',
      runCount: 0
    }

    try {
      await createMutation.mutateAsync(newWorkflow)
    } catch (e) {
      // Fallback: just select a temp workflow for editing
      const tempWf: Workflow = {
        id: `wf-${Date.now()}`,
        name: newWorkflow.name,
        description: newWorkflow.description,
        nodes: [
          { id: 'n1', type: 'trigger' as NodeType, name: 'Trigger', config: {}, position: { x: 100, y: 200 }, connections: [] }
        ],
        status: 'draft' as const,
        runCount: 0
      }
      setSelectedWorkflow(tempWf)
      setIsEditing(true)
    }
  }

  return (
    <div className="flex h-full">
      {/* Sidebar - Workflow List */}
      <div className="w-72 border-r border-bael-border bg-bael-surface flex flex-col">
        <div className="p-4 border-b border-bael-border">
          <button
            onClick={handleCreateWorkflow}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-bael-primary text-white rounded-lg hover:bg-bael-primary/80 transition-colors"
          >
            <Plus size={16} />
            <span>New Workflow</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {workflows.map((wf) => (
            <button
              key={wf.id}
              onClick={() => { setSelectedWorkflow(wf); setIsEditing(false) }}
              className={clsx(
                'w-full text-left p-3 rounded-xl transition-all mb-2',
                selectedWorkflow?.id === wf.id
                  ? 'bg-bael-primary/20 border border-bael-primary/50'
                  : 'bg-bael-bg border border-bael-border hover:border-bael-primary/30'
              )}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium text-bael-text">{wf.name}</h3>
                  <p className="text-xs text-bael-muted line-clamp-1">{wf.description}</p>
                </div>
                <span className={clsx(
                  'text-xs px-1.5 py-0.5 rounded',
                  wf.status === 'active' && 'bg-bael-success/20 text-bael-success',
                  wf.status === 'paused' && 'bg-bael-warning/20 text-bael-warning',
                  wf.status === 'draft' && 'bg-bael-border text-bael-muted'
                )}>
                  {wf.status}
                </span>
              </div>
              <div className="flex items-center gap-4 mt-2 text-xs text-bael-muted">
                <span>{wf.nodes.length} nodes</span>
                <span>{wf.runCount} runs</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {selectedWorkflow ? (
          <>
            {/* Toolbar */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-bael-border bg-bael-surface">
              <div className="flex items-center gap-4">
                <div>
                  <h2 className="font-semibold text-bael-text">{selectedWorkflow.name}</h2>
                  <p className="text-xs text-bael-muted">{selectedWorkflow.description}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {isEditing ? (
                  <>
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-3 py-1.5 text-sm border border-bael-border rounded-lg text-bael-muted hover:text-bael-text transition-colors"
                    >
                      Cancel
                    </button>
                    <button className="flex items-center gap-2 px-3 py-1.5 text-sm bg-bael-primary text-white rounded-lg hover:bg-bael-primary/80 transition-colors">
                      <Save size={14} />
                      Save
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => setIsEditing(true)}
                      className="px-3 py-1.5 text-sm border border-bael-border rounded-lg text-bael-muted hover:text-bael-text transition-colors"
                    >
                      Edit
                    </button>
                    <button className="flex items-center gap-2 px-3 py-1.5 text-sm bg-bael-success text-white rounded-lg hover:bg-bael-success/80 transition-colors">
                      <Play size={14} />
                      Run
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Canvas */}
            <div className="flex-1 relative overflow-hidden bg-bael-bg">
              {/* Grid background */}
              <div
                className="absolute inset-0"
                style={{
                  backgroundImage: 'radial-gradient(circle, #2e2e3e 1px, transparent 1px)',
                  backgroundSize: '20px 20px'
                }}
              />

              {/* Nodes */}
              <svg className="absolute inset-0 pointer-events-none">
                {/* Connection lines */}
                {selectedWorkflow.nodes.map((node) =>
                  node.connections.map((targetId) => {
                    const target = selectedWorkflow.nodes.find(n => n.id === targetId)
                    if (!target) return null
                    return (
                      <line
                        key={`${node.id}-${targetId}`}
                        x1={node.position.x + 100}
                        y1={node.position.y + 30}
                        x2={target.position.x}
                        y2={target.position.y + 30}
                        stroke="#6366f1"
                        strokeWidth="2"
                        strokeDasharray="5,5"
                      />
                    )
                  })
                )}
              </svg>

              {selectedWorkflow.nodes.map((node) => (
                <WorkflowNodeComponent
                  key={node.id}
                  node={node}
                  isEditing={isEditing}
                />
              ))}

              {/* Zoom controls */}
              <div className="absolute bottom-4 right-4 flex items-center gap-2 bg-bael-surface border border-bael-border rounded-lg p-1">
                <button className="p-1.5 hover:bg-bael-border rounded transition-colors text-bael-muted hover:text-bael-text">
                  <ZoomOut size={16} />
                </button>
                <span className="text-xs text-bael-muted px-2">100%</span>
                <button className="p-1.5 hover:bg-bael-border rounded transition-colors text-bael-muted hover:text-bael-text">
                  <ZoomIn size={16} />
                </button>
                <button className="p-1.5 hover:bg-bael-border rounded transition-colors text-bael-muted hover:text-bael-text">
                  <Maximize2 size={16} />
                </button>
              </div>
            </div>

            {/* Node palette (when editing) */}
            {isEditing && (
              <div className="flex items-center gap-4 px-4 py-3 border-t border-bael-border bg-bael-surface">
                <span className="text-sm text-bael-muted">Add node:</span>
                {nodeTypes.map(({ type, label, icon: Icon, color }) => (
                  <button
                    key={type}
                    className="flex items-center gap-2 px-3 py-1.5 bg-bael-bg border border-bael-border rounded-lg hover:border-bael-primary/50 transition-colors"
                  >
                    <div className={clsx('w-4 h-4 rounded flex items-center justify-center', color)}>
                      <Icon size={10} className="text-white" />
                    </div>
                    <span className="text-sm text-bael-text">{label}</span>
                  </button>
                ))}
              </div>
            )}
          </>
        ) : (
          <EmptyState onNew={handleCreateWorkflow} />
        )}
      </div>
    </div>
  )
}

function WorkflowNodeComponent({
  node,
  isEditing
}: {
  node: WorkflowNode
  isEditing: boolean
}) {
  const nodeType = nodeTypes.find(t => t.type === node.type)
  const Icon = nodeType?.icon || Code

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={clsx(
        'absolute w-48 bg-bael-surface border rounded-xl shadow-lg',
        isEditing ? 'cursor-move' : 'cursor-pointer',
        'border-bael-border hover:border-bael-primary/50'
      )}
      style={{ left: node.position.x, top: node.position.y }}
    >
      <div className="flex items-center gap-3 p-3 border-b border-bael-border">
        <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center', nodeType?.color || 'bg-bael-primary')}>
          <Icon size={16} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-bael-text truncate">{node.name}</p>
          <p className="text-xs text-bael-muted capitalize">{node.type}</p>
        </div>
      </div>

      {/* Connection points */}
      {node.type !== 'trigger' && (
        <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-bael-border rounded-full border-2 border-bael-surface" />
      )}
      {node.type !== 'output' && (
        <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-bael-primary rounded-full border-2 border-bael-surface" />
      )}
    </motion.div>
  )
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <div className="w-20 h-20 rounded-full bg-bael-surface border border-bael-border flex items-center justify-center mb-6">
        <GitBranch size={40} className="text-bael-muted" />
      </div>

      <h2 className="text-xl font-semibold text-bael-text mb-2">No Workflow Selected</h2>
      <p className="text-bael-muted mb-6 max-w-md">
        Create automated workflows to handle repetitive tasks. Chain together triggers,
        actions, and conditions to build powerful automations.
      </p>

      <button
        onClick={onNew}
        className="flex items-center gap-2 px-4 py-2 bg-bael-primary text-white rounded-lg hover:bg-bael-primary/80 transition-colors"
      >
        <Plus size={18} />
        <span>Create Workflow</span>
      </button>
    </div>
  )
}
