import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Brain,
  Cpu,
  Activity,
  Zap,
  Eye,
  Mic,
  GitBranch,
  Network,
  Target,
  Lightbulb,
  Shield,
  Gauge,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Play,
  Pause,
  Settings,
  RefreshCw,
  ChevronRight,
  Layers,
  Box,
  Code,
  Terminal,
  Wifi,
  Loader2
} from 'lucide-react';

// Types
interface Capability {
  id: string;
  name: string;
  domain: string;
  status: 'active' | 'idle' | 'disabled' | 'error';
  usage: number;
  lastUsed: string;
  description: string;
}

interface DomainStats {
  name: string;
  icon: any;
  color: string;
  capabilities: number;
  active: number;
  usage: number;
}

interface APEXStats {
  mode: string;
  totalRequests: number;
  successRate: number;
  avgResponseTime: number;
  capabilitiesLoaded: number;
  mcpToolsAvailable: number;
  uptime: string;
}

// Domain definitions with icons and colors
const domains: DomainStats[] = [
  { name: 'Reasoning', icon: Brain, color: 'purple', capabilities: 25, active: 20, usage: 78 },
  { name: 'Memory', icon: Layers, color: 'blue', capabilities: 5, active: 5, usage: 92 },
  { name: 'Agents', icon: Network, color: 'green', capabilities: 15, active: 8, usage: 45 },
  { name: 'Learning', icon: TrendingUp, color: 'orange', capabilities: 12, active: 6, usage: 34 },
  { name: 'Knowledge', icon: Lightbulb, color: 'yellow', capabilities: 8, active: 8, usage: 88 },
  { name: 'Execution', icon: Zap, color: 'red', capabilities: 10, active: 10, usage: 65 },
  { name: 'Perception', icon: Eye, color: 'cyan', capabilities: 8, active: 4, usage: 28 },
  { name: 'Communication', icon: Mic, color: 'pink', capabilities: 6, active: 3, usage: 22 },
  { name: 'Evolution', icon: GitBranch, color: 'indigo', capabilities: 5, active: 2, usage: 15 },
  { name: 'MCP Tools', icon: Box, color: 'emerald', capabilities: 52, active: 33, usage: 56 },
];

// Sample capabilities data
const sampleCapabilities: Capability[] = [
  // Reasoning
  { id: 'causal', name: 'Causal Reasoning', domain: 'Reasoning', status: 'active', usage: 89, lastUsed: '2 min ago', description: 'Analyzes cause-effect relationships' },
  { id: 'temporal', name: 'Temporal Reasoning', domain: 'Reasoning', status: 'active', usage: 76, lastUsed: '5 min ago', description: 'Handles time-based logic' },
  { id: 'counterfactual', name: 'Counterfactual', domain: 'Reasoning', status: 'active', usage: 45, lastUsed: '12 min ago', description: 'What-if scenario analysis' },
  { id: 'deductive', name: 'Deductive Reasoning', domain: 'Reasoning', status: 'active', usage: 92, lastUsed: '1 min ago', description: 'Logical deduction from premises' },
  { id: 'inductive', name: 'Inductive Reasoning', domain: 'Reasoning', status: 'idle', usage: 34, lastUsed: '1 hour ago', description: 'Pattern-based inference' },
  { id: 'abductive', name: 'Abductive Reasoning', domain: 'Reasoning', status: 'active', usage: 67, lastUsed: '8 min ago', description: 'Best explanation inference' },

  // Memory
  { id: 'working', name: 'Working Memory', domain: 'Memory', status: 'active', usage: 98, lastUsed: 'now', description: 'Short-term processing buffer' },
  { id: 'episodic', name: 'Episodic Memory', domain: 'Memory', status: 'active', usage: 85, lastUsed: '3 min ago', description: 'Event and experience storage' },
  { id: 'semantic', name: 'Semantic Memory', domain: 'Memory', status: 'active', usage: 91, lastUsed: '1 min ago', description: 'Knowledge and facts storage' },
  { id: 'procedural', name: 'Procedural Memory', domain: 'Memory', status: 'active', usage: 78, lastUsed: '10 min ago', description: 'Skills and procedures' },
  { id: 'meta', name: 'Meta Memory', domain: 'Memory', status: 'active', usage: 45, lastUsed: '30 min ago', description: 'Memory about memory' },

  // Agents
  { id: 'swarm', name: 'Swarm Intelligence', domain: 'Agents', status: 'active', usage: 56, lastUsed: '15 min ago', description: 'Collective agent behavior' },
  { id: 'coordinator', name: 'Agent Coordinator', domain: 'Agents', status: 'active', usage: 78, lastUsed: '5 min ago', description: 'Multi-agent orchestration' },
  { id: 'autonomous', name: 'Autonomous Agent', domain: 'Agents', status: 'idle', usage: 23, lastUsed: '2 hours ago', description: 'Self-directed operation' },

  // Perception
  { id: 'vision', name: 'Vision Processor', domain: 'Perception', status: 'active', usage: 34, lastUsed: '20 min ago', description: 'Image and video analysis' },
  { id: 'voice', name: 'Voice Interface', domain: 'Perception', status: 'idle', usage: 12, lastUsed: '4 hours ago', description: 'Speech recognition & synthesis' },
  { id: 'ocr', name: 'OCR Engine', domain: 'Perception', status: 'active', usage: 45, lastUsed: '15 min ago', description: 'Text extraction from images' },

  // Evolution
  { id: 'evolution', name: 'Evolution Engine', domain: 'Evolution', status: 'active', usage: 15, lastUsed: '1 hour ago', description: 'Self-improvement algorithms' },
  { id: 'metalearning', name: 'Meta Learning', domain: 'Evolution', status: 'idle', usage: 8, lastUsed: '6 hours ago', description: 'Learning to learn' },
];

export default function APEXDashboard() {
  const [apexStats, setApexStats] = useState<APEXStats>({
    mode: 'MAXIMUM',
    totalRequests: 15234,
    successRate: 99.2,
    avgResponseTime: 127,
    capabilitiesLoaded: 146,
    mcpToolsAvailable: 52,
    uptime: '7d 14h 32m'
  });

  const [capabilities, setCapabilities] = useState<Capability[]>(sampleCapabilities);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(true);

  // Fetch singularity status from API
  const { data: singularityStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
    queryKey: ['singularity-status'],
    queryFn: async () => {
      const res = await fetch('/api/singularity/status');
      if (!res.ok) return null;
      return res.json();
    },
    staleTime: 5000,
    refetchInterval: isRunning ? 10000 : false
  });

  // Fetch capabilities from API
  const { data: capabilitiesData, isLoading: capabilitiesLoading } = useQuery({
    queryKey: ['singularity-capabilities'],
    queryFn: async () => {
      const res = await fetch('/api/singularity/capabilities');
      if (!res.ok) return null;
      return res.json();
    },
    staleTime: 30000
  });

  // Update stats when singularity status changes
  useEffect(() => {
    if (singularityStatus?.success && singularityStatus.data) {
      const data = singularityStatus.data;
      setApexStats(prev => ({
        ...prev,
        mode: singularityStatus.mode?.toUpperCase() || prev.mode,
        capabilitiesLoaded: data.capabilities_count || data.total_capabilities || prev.capabilitiesLoaded,
        successRate: data.success_rate || prev.successRate
      }));
    }
  }, [singularityStatus]);

  // Update capabilities when data loads
  useEffect(() => {
    if (capabilitiesData?.success && capabilitiesData.data) {
      const apiCaps = capabilitiesData.data;
      // Merge API capabilities with sample data
      // Keep sample data as fallback for visual structure
    }
  }, [capabilitiesData]);

  // Awaken mutation
  const awakenMutation = useMutation({
    mutationFn: async (mode: string) => {
      const res = await fetch('/api/singularity/awaken', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, enable_all: true })
      });
      if (!res.ok) throw new Error('Failed to awaken');
      return res.json();
    },
    onSuccess: () => {
      refetchStatus();
    }
  });

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setApexStats(prev => ({
        ...prev,
        totalRequests: prev.totalRequests + Math.floor(Math.random() * 5),
        avgResponseTime: Math.floor(100 + Math.random() * 50)
      }));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const filteredCapabilities = selectedDomain
    ? capabilities.filter(c => c.domain === selectedDomain)
    : capabilities;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'idle': return 'bg-yellow-500';
      case 'disabled': return 'bg-gray-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'idle': return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'disabled': return <XCircle className="w-4 h-4 text-gray-500" />;
      case 'error': return <AlertTriangle className="w-4 h-4 text-red-500" />;
      default: return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Cpu className="w-8 h-8 text-purple-500" />
            APEX Orchestrator
          </h1>
          <p className="text-gray-400 mt-1">
            Advanced Processing & Execution eXtreme - Maximum Potential Mode
          </p>
        </div>
        <div className="flex items-center gap-3">
          {singularityStatus?.success && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg">
              <Wifi className="w-4 h-4" />
              <span className="text-sm">Connected</span>
            </div>
          )}
          {statusLoading && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/20 text-blue-400 rounded-lg">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Syncing...</span>
            </div>
          )}
          <button
            onClick={() => awakenMutation.mutate('transcendent')}
            disabled={awakenMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {awakenMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            Awaken
          </button>
          <button
            onClick={() => setIsRunning(!isRunning)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              isRunning
                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
            }`}
          >
            {isRunning ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            {isRunning ? 'Running' : 'Paused'}
          </button>
          <button
            onClick={() => refetchStatus()}
            className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
            title="Refresh Status"
          >
            <RefreshCw className="w-5 h-5 text-gray-400" />
          </button>
          <button className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors" title="Settings">
            <Settings className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>

      {/* APEX Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 border border-purple-500/30 rounded-xl p-4"
        >
          <div className="text-purple-400 text-sm font-medium">Mode</div>
          <div className="text-2xl font-bold text-white mt-1">{apexStats.mode}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Total Requests</div>
          <div className="text-2xl font-bold text-white mt-1">{apexStats.totalRequests.toLocaleString()}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Success Rate</div>
          <div className="text-2xl font-bold text-green-400 mt-1">{apexStats.successRate}%</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Avg Response</div>
          <div className="text-2xl font-bold text-white mt-1">{apexStats.avgResponseTime}ms</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Capabilities</div>
          <div className="text-2xl font-bold text-blue-400 mt-1">{apexStats.capabilitiesLoaded}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">MCP Tools</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{apexStats.mcpToolsAvailable}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Uptime</div>
          <div className="text-2xl font-bold text-white mt-1">{apexStats.uptime}</div>
        </motion.div>
      </div>

      {/* Domains Grid */}
      <div>
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5 text-purple-500" />
          Capability Domains
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {domains.map((domain) => (
            <motion.button
              key={domain.name}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={() => setSelectedDomain(selectedDomain === domain.name ? null : domain.name)}
              className={`p-4 rounded-xl border transition-all text-left ${
                selectedDomain === domain.name
                  ? `bg-${domain.color}-500/20 border-${domain.color}-500/50`
                  : 'bg-gray-800/50 border-gray-700 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <domain.icon className={`w-6 h-6 text-${domain.color}-500`} />
                <span className="text-xs text-gray-400">{domain.active}/{domain.capabilities}</span>
              </div>
              <div className="text-white font-medium mb-1">{domain.name}</div>
              <div className="w-full bg-gray-700 rounded-full h-1.5">
                <div
                  className={`bg-${domain.color}-500 h-1.5 rounded-full transition-all`}
                  style={{ width: `${domain.usage}%` }}
                />
              </div>
              <div className="text-xs text-gray-400 mt-1">{domain.usage}% usage</div>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Capabilities List */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-purple-500" />
            {selectedDomain ? `${selectedDomain} Capabilities` : 'All Capabilities'}
          </h2>
          {selectedDomain && (
            <button
              onClick={() => setSelectedDomain(null)}
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Show all
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <AnimatePresence mode="popLayout">
            {filteredCapabilities.map((capability) => (
              <motion.div
                key={capability.id}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 hover:border-gray-600 transition-all"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(capability.status)}`} />
                    <div>
                      <div className="text-white font-medium">{capability.name}</div>
                      <div className="text-xs text-gray-400">{capability.domain}</div>
                    </div>
                  </div>
                  {getStatusIcon(capability.status)}
                </div>

                <p className="text-sm text-gray-400 mb-3">{capability.description}</p>

                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Gauge className="w-4 h-4 text-gray-500" />
                    <span className="text-gray-400">{capability.usage}%</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-500" />
                    <span className="text-gray-400">{capability.lastUsed}</span>
                  </div>
                </div>

                <div className="w-full bg-gray-700 rounded-full h-1 mt-3">
                  <div
                    className="bg-purple-500 h-1 rounded-full transition-all"
                    style={{ width: `${capability.usage}%` }}
                  />
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <Terminal className="w-5 h-5 text-purple-500" />
          Quick Actions
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button className="flex items-center gap-3 p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
            <Brain className="w-5 h-5 text-purple-500" />
            <span className="text-white">Deep Think</span>
          </button>
          <button className="flex items-center gap-3 p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
            <Network className="w-5 h-5 text-green-500" />
            <span className="text-white">Spawn Swarm</span>
          </button>
          <button className="flex items-center gap-3 p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
            <Code className="w-5 h-5 text-blue-500" />
            <span className="text-white">Execute Code</span>
          </button>
          <button className="flex items-center gap-3 p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
            <GitBranch className="w-5 h-5 text-orange-500" />
            <span className="text-white">Self-Evolve</span>
          </button>
        </div>
      </div>
    </div>
  );
}
