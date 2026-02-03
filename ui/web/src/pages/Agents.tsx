import React, { useState, useEffect, useCallback } from 'react';
import {
  Bot,
  Play,
  Pause,
  Plus,
  Trash2,
  RefreshCw,
  Settings,
  ChevronDown,
  ChevronRight,
  Activity,
  Clock,
  CheckCircle,
  XCircle,
  Loader,
  Users,
  Brain,
  Code,
  Search as SearchIcon,
  FileText,
  Zap
} from 'lucide-react';

// =============================================================================
// TYPES
// =============================================================================

interface AgentPersona {
  name: string;
  role: string;
  description: string;
  capabilities: string[];
  temperature: number;
}

interface AgentState {
  id: string;
  persona: AgentPersona;
  status: 'idle' | 'thinking' | 'executing' | 'waiting' | 'completed' | 'failed';
  currentTask?: string;
  taskHistory: string[];
  totalTasks: number;
  successfulTasks: number;
  createdAt: string;
  lastActive: string;
}

interface Task {
  id: string;
  description: string;
  priority: 'critical' | 'high' | 'normal' | 'low' | 'background';
  status: 'pending' | 'running' | 'completed' | 'failed';
  assignedAgent?: string;
  result?: any;
  error?: string;
  createdAt: string;
  completedAt?: string;
}

interface BackendStatus {
  running: boolean;
  totalAgents: number;
  idleAgents: number;
  pendingTasks: number;
  totalTasks: number;
}

// =============================================================================
// PERSONA TEMPLATES
// =============================================================================

const PERSONA_TEMPLATES: AgentPersona[] = [
  {
    name: 'Assistant',
    role: 'General Assistant',
    description: 'A helpful AI assistant for various tasks',
    capabilities: ['general', 'analysis', 'writing'],
    temperature: 0.7
  },
  {
    name: 'Developer',
    role: 'Software Developer',
    description: 'Expert programmer who writes clean, efficient code',
    capabilities: ['coding', 'debugging', 'architecture'],
    temperature: 0.3
  },
  {
    name: 'Researcher',
    role: 'Research Analyst',
    description: 'Thorough researcher who finds and synthesizes information',
    capabilities: ['research', 'analysis', 'synthesis'],
    temperature: 0.5
  },
  {
    name: 'Writer',
    role: 'Content Writer',
    description: 'Creative writer for documentation and content',
    capabilities: ['writing', 'editing', 'creative'],
    temperature: 0.8
  },
  {
    name: 'Planner',
    role: 'Strategic Planner',
    description: 'Breaks down complex tasks into actionable steps',
    capabilities: ['planning', 'organization', 'strategy'],
    temperature: 0.4
  }
];

// =============================================================================
// COMPONENTS
// =============================================================================

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const config: Record<string, { color: string; icon: React.ReactNode }> = {
    idle: { color: 'bg-gray-500', icon: <Clock className="w-3 h-3" /> },
    thinking: { color: 'bg-blue-500', icon: <Brain className="w-3 h-3 animate-pulse" /> },
    executing: { color: 'bg-yellow-500', icon: <Loader className="w-3 h-3 animate-spin" /> },
    waiting: { color: 'bg-purple-500', icon: <Clock className="w-3 h-3" /> },
    completed: { color: 'bg-green-500', icon: <CheckCircle className="w-3 h-3" /> },
    failed: { color: 'bg-red-500', icon: <XCircle className="w-3 h-3" /> },
    pending: { color: 'bg-gray-500', icon: <Clock className="w-3 h-3" /> },
    running: { color: 'bg-blue-500', icon: <Loader className="w-3 h-3 animate-spin" /> }
  };

  const { color, icon } = config[status] || config.idle;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 ${color} text-white text-xs rounded-full`}>
      {icon}
      {status}
    </span>
  );
};

const AgentCard: React.FC<{
  agent: AgentState;
  onStop: () => void;
  isExpanded: boolean;
  onToggle: () => void;
}> = ({ agent, onStop, isExpanded, onToggle }) => {
  const successRate = agent.totalTasks > 0
    ? ((agent.successfulTasks / agent.totalTasks) * 100).toFixed(0)
    : '100';

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <div
        className="p-4 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-white">{agent.persona.name}</h3>
                <StatusBadge status={agent.status} />
              </div>
              <p className="text-sm text-gray-400">{agent.persona.role}</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-xs text-gray-500">Success Rate</p>
              <p className="text-lg font-bold text-green-400">{successRate}%</p>
            </div>
            {isExpanded ? (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronRight className="w-5 h-5 text-gray-400" />
            )}
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="p-4 pt-0 border-t border-border mt-4">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-bg rounded p-3">
              <p className="text-xs text-gray-500 mb-1">Total Tasks</p>
              <p className="text-xl font-bold text-white">{agent.totalTasks}</p>
            </div>
            <div className="bg-bg rounded p-3">
              <p className="text-xs text-gray-500 mb-1">Successful</p>
              <p className="text-xl font-bold text-green-400">{agent.successfulTasks}</p>
            </div>
            <div className="bg-bg rounded p-3">
              <p className="text-xs text-gray-500 mb-1">Last Active</p>
              <p className="text-sm text-gray-300">
                {new Date(agent.lastActive).toLocaleTimeString()}
              </p>
            </div>
          </div>

          <div className="mb-4">
            <p className="text-xs text-gray-500 mb-2">Capabilities</p>
            <div className="flex flex-wrap gap-2">
              {agent.persona.capabilities.map((cap, i) => (
                <span
                  key={i}
                  className="px-2 py-1 bg-primary/20 text-primary text-xs rounded"
                >
                  {cap}
                </span>
              ))}
            </div>
          </div>

          {agent.currentTask && (
            <div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded">
              <p className="text-xs text-blue-400 mb-1">Current Task</p>
              <p className="text-sm text-white">{agent.currentTask}</p>
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onStop();
              }}
              className="px-3 py-1.5 bg-red-500/20 text-red-400 text-sm rounded hover:bg-red-500/30 transition-colors"
            >
              <Trash2 className="w-4 h-4 inline mr-1" />
              Remove
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const TaskItem: React.FC<{ task: Task }> = ({ task }) => {
  const priorityColors: Record<string, string> = {
    critical: 'border-l-red-500',
    high: 'border-l-orange-500',
    normal: 'border-l-blue-500',
    low: 'border-l-gray-500',
    background: 'border-l-gray-700'
  };

  return (
    <div className={`bg-surface border border-border border-l-4 ${priorityColors[task.priority]} rounded-lg p-3`}>
      <div className="flex items-center justify-between mb-2">
        <StatusBadge status={task.status} />
        <span className="text-xs text-gray-500">
          {new Date(task.createdAt).toLocaleTimeString()}
        </span>
      </div>
      <p className="text-sm text-gray-200 line-clamp-2">{task.description}</p>
      {task.error && (
        <p className="text-xs text-red-400 mt-2">{task.error}</p>
      )}
    </div>
  );
};

const SpawnAgentModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onSpawn: (persona: AgentPersona) => void;
}> = ({ isOpen, onClose, onSpawn }) => {
  const [selectedTemplate, setSelectedTemplate] = useState(0);
  const [customPersona, setCustomPersona] = useState<AgentPersona>(PERSONA_TEMPLATES[0]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-surface border border-border rounded-xl w-full max-w-lg p-6">
        <h2 className="text-xl font-bold text-white mb-4">Spawn New Agent</h2>

        <div className="mb-4">
          <p className="text-sm text-gray-400 mb-2">Select Template</p>
          <div className="grid grid-cols-2 gap-2">
            {PERSONA_TEMPLATES.map((template, i) => (
              <button
                key={i}
                onClick={() => {
                  setSelectedTemplate(i);
                  setCustomPersona(template);
                }}
                className={`p-3 rounded-lg text-left transition-colors ${
                  selectedTemplate === i
                    ? 'bg-primary/20 border-primary'
                    : 'bg-bg hover:bg-white/5'
                } border border-border`}
              >
                <p className="font-medium text-white">{template.name}</p>
                <p className="text-xs text-gray-400">{template.role}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-3 mb-6">
          <div>
            <label className="text-sm text-gray-400 block mb-1">Name</label>
            <input
              type="text"
              value={customPersona.name}
              onChange={(e) => setCustomPersona({ ...customPersona, name: e.target.value })}
              className="w-full px-3 py-2 bg-bg border border-border rounded text-white"
            />
          </div>
          <div>
            <label className="text-sm text-gray-400 block mb-1">Role</label>
            <input
              type="text"
              value={customPersona.role}
              onChange={(e) => setCustomPersona({ ...customPersona, role: e.target.value })}
              className="w-full px-3 py-2 bg-bg border border-border rounded text-white"
            />
          </div>
          <div>
            <label className="text-sm text-gray-400 block mb-1">Temperature ({customPersona.temperature})</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={customPersona.temperature}
              onChange={(e) => setCustomPersona({ ...customPersona, temperature: parseFloat(e.target.value) })}
              className="w-full"
            />
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onSpawn(customPersona);
              onClose();
            }}
            className="flex-1 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/80 transition-colors"
          >
            Spawn Agent
          </button>
        </div>
      </div>
    </div>
  );
};

const NewTaskModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (description: string, priority: string) => void;
}> = ({ isOpen, onClose, onSubmit }) => {
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('normal');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-surface border border-border rounded-xl w-full max-w-lg p-6">
        <h2 className="text-xl font-bold text-white mb-4">Submit New Task</h2>

        <div className="space-y-4 mb-6">
          <div>
            <label className="text-sm text-gray-400 block mb-1">Task Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what you want the agent to do..."
              rows={4}
              className="w-full px-3 py-2 bg-bg border border-border rounded text-white resize-none"
            />
          </div>
          <div>
            <label className="text-sm text-gray-400 block mb-1">Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full px-3 py-2 bg-bg border border-border rounded text-white"
            >
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="normal">Normal</option>
              <option value="low">Low</option>
              <option value="background">Background</option>
            </select>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              if (description.trim()) {
                onSubmit(description, priority);
                setDescription('');
                onClose();
              }
            }}
            disabled={!description.trim()}
            className="flex-1 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/80 transition-colors disabled:opacity-50"
          >
            Submit Task
          </button>
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// MAIN PAGE
// =============================================================================

export const Agents: React.FC = () => {
  const [agents, setAgents] = useState<AgentState[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [status, setStatus] = useState<BackendStatus>({
    running: false,
    totalAgents: 0,
    idleAgents: 0,
    pendingTasks: 0,
    totalTasks: 0
  });
  const [loading, setLoading] = useState(true);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [showSpawnModal, setShowSpawnModal] = useState(false);
  const [showTaskModal, setShowTaskModal] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [agentsRes, tasksRes, statusRes] = await Promise.all([
        fetch('/api/v1/agents'),
        fetch('/api/v1/agents/tasks'),
        fetch('/api/v1/agents/status')
      ]);

      if (agentsRes.ok) {
        const data = await agentsRes.json();
        setAgents(data.agents || []);
      }

      if (tasksRes.ok) {
        const data = await tasksRes.json();
        setTasks(data.tasks || []);
      }

      if (statusRes.ok) {
        const data = await statusRes.json();
        setStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch agent data:', error);
      // Mock data for development
      setAgents([
        {
          id: 'agent-001',
          persona: PERSONA_TEMPLATES[0],
          status: 'idle',
          taskHistory: [],
          totalTasks: 5,
          successfulTasks: 4,
          createdAt: new Date().toISOString(),
          lastActive: new Date().toISOString()
        },
        {
          id: 'agent-002',
          persona: PERSONA_TEMPLATES[1],
          status: 'executing',
          currentTask: 'Analyzing codebase structure...',
          taskHistory: [],
          totalTasks: 12,
          successfulTasks: 11,
          createdAt: new Date().toISOString(),
          lastActive: new Date().toISOString()
        }
      ]);
      setTasks([
        {
          id: 'task-001',
          description: 'Review and refactor the authentication module',
          priority: 'high',
          status: 'running',
          assignedAgent: 'agent-002',
          createdAt: new Date().toISOString()
        },
        {
          id: 'task-002',
          description: 'Generate documentation for API endpoints',
          priority: 'normal',
          status: 'pending',
          createdAt: new Date().toISOString()
        }
      ]);
      setStatus({
        running: true,
        totalAgents: 2,
        idleAgents: 1,
        pendingTasks: 1,
        totalTasks: 2
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleSpawnAgent = async (persona: AgentPersona) => {
    try {
      await fetch('/api/v1/agents/spawn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ persona })
      });
      fetchData();
    } catch (error) {
      console.error('Failed to spawn agent:', error);
    }
  };

  const handleRemoveAgent = async (agentId: string) => {
    try {
      await fetch(`/api/v1/agents/${agentId}`, { method: 'DELETE' });
      setAgents(prev => prev.filter(a => a.id !== agentId));
    } catch (error) {
      console.error('Failed to remove agent:', error);
    }
  };

  const handleSubmitTask = async (description: string, priority: string) => {
    try {
      await fetch('/api/v1/agents/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, priority })
      });
      fetchData();
    } catch (error) {
      console.error('Failed to submit task:', error);
    }
  };

  const handleToggleBackend = async () => {
    try {
      await fetch('/api/v1/agents/backend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: status.running ? 'stop' : 'start' })
      });
      fetchData();
    } catch (error) {
      console.error('Failed to toggle backend:', error);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-none p-6 border-b border-border">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <Users className="w-7 h-7 text-primary" />
              Agents
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Manage AI agents and delegate tasks
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleToggleBackend}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                status.running
                  ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                  : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
              }`}
            >
              {status.running ? (
                <>
                  <Pause className="w-4 h-4" />
                  Stop Backend
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Start Backend
                </>
              )}
            </button>
            <button
              onClick={() => setShowSpawnModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/80 text-white rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Spawn Agent
            </button>
          </div>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Users className="w-4 h-4" />
              <span className="text-xs uppercase">Total Agents</span>
            </div>
            <div className="text-2xl font-bold text-white">{status.totalAgents}</div>
          </div>

          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Activity className="w-4 h-4" />
              <span className="text-xs uppercase">Active</span>
            </div>
            <div className="text-2xl font-bold text-green-400">
              {status.totalAgents - status.idleAgents}
            </div>
          </div>

          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Clock className="w-4 h-4" />
              <span className="text-xs uppercase">Pending Tasks</span>
            </div>
            <div className="text-2xl font-bold text-yellow-400">{status.pendingTasks}</div>
          </div>

          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 text-gray-400 mb-2">
              <Zap className="w-4 h-4" />
              <span className="text-xs uppercase">Total Tasks</span>
            </div>
            <div className="text-2xl font-bold text-blue-400">{status.totalTasks}</div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex">
        {/* Agents Panel */}
        <div className="flex-1 overflow-y-auto p-6 border-r border-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Active Agents</h2>
            <button
              onClick={fetchData}
              className="p-2 hover:bg-white/10 rounded transition-colors"
            >
              <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {agents.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Bot className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">No agents spawned</p>
                <button
                  onClick={() => setShowSpawnModal(true)}
                  className="mt-4 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/80 transition-colors"
                >
                  Spawn Your First Agent
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {agents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  isExpanded={expandedAgent === agent.id}
                  onToggle={() => setExpandedAgent(expandedAgent === agent.id ? null : agent.id)}
                  onStop={() => handleRemoveAgent(agent.id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Tasks Panel */}
        <div className="w-96 overflow-y-auto p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Task Queue</h2>
            <button
              onClick={() => setShowTaskModal(true)}
              className="p-2 hover:bg-white/10 rounded transition-colors"
            >
              <Plus className="w-4 h-4 text-gray-400" />
            </button>
          </div>

          {tasks.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <FileText className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400 text-sm">No tasks in queue</p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {tasks.map((task) => (
                <TaskItem key={task.id} task={task} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <SpawnAgentModal
        isOpen={showSpawnModal}
        onClose={() => setShowSpawnModal(false)}
        onSpawn={handleSpawnAgent}
      />
      <NewTaskModal
        isOpen={showTaskModal}
        onClose={() => setShowTaskModal(false)}
        onSubmit={handleSubmitTask}
      />
    </div>
  );
};

export default Agents;
