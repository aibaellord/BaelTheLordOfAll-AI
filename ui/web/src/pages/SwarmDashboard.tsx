import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Users,
  Network,
  Activity,
  Zap,
  Target,
  Brain,
  MessageSquare,
  Clock,
  Play,
  Pause,
  Plus,
  Settings,
  RefreshCw,
  ChevronRight,
  Crown,
  Shield,
  Search,
  Truck,
  Heart,
  Radio,
  TrendingUp,
  AlertTriangle,
  Wifi,
  WifiOff,
  Loader2
} from 'lucide-react';

// Types
interface SwarmAgent {
  id: string;
  role: 'queen' | 'scout' | 'worker' | 'soldier' | 'nurse' | 'forager' | 'messenger';
  state: 'idle' | 'searching' | 'working' | 'resting' | 'communicating';
  position: { x: number; y: number };
  energy: number;
  performance: number;
  currentTask?: string;
  messages: number;
}

interface SwarmStats {
  totalAgents: number;
  activeAgents: number;
  state: 'idle' | 'exploring' | 'exploiting' | 'converging' | 'stalled' | 'emergency';
  efficiency: number;
  convergenceRate: number;
  bestSolutionScore: number;
  iterationsCompleted: number;
  messagesExchanged: number;
}

interface Pheromone {
  x: number;
  y: number;
  intensity: number;
  type: 'success' | 'failure' | 'exploration';
}

// Role configurations
const roleConfig = {
  queen: { icon: Crown, color: 'yellow', description: 'Coordinates and spawns agents' },
  scout: { icon: Search, color: 'blue', description: 'Explores new solutions' },
  worker: { icon: Truck, color: 'green', description: 'Exploits known solutions' },
  soldier: { icon: Shield, color: 'red', description: 'Defends and validates' },
  nurse: { icon: Heart, color: 'pink', description: 'Maintains and heals' },
  forager: { icon: Target, color: 'orange', description: 'Gathers resources' },
  messenger: { icon: Radio, color: 'cyan', description: 'Spreads information' }
};

// Generate sample agents
const generateAgents = (): SwarmAgent[] => {
  const roles: SwarmAgent['role'][] = ['queen', 'scout', 'scout', 'scout', 'worker', 'worker', 'worker', 'worker', 'soldier', 'soldier', 'nurse', 'forager', 'forager', 'messenger', 'messenger'];
  const states: SwarmAgent['state'][] = ['idle', 'searching', 'working', 'resting', 'communicating'];

  return roles.map((role, i) => ({
    id: `agent-${i}`,
    role,
    state: states[Math.floor(Math.random() * states.length)],
    position: {
      x: Math.random() * 100,
      y: Math.random() * 100
    },
    energy: 50 + Math.random() * 50,
    performance: 60 + Math.random() * 40,
    currentTask: role === 'queen' ? 'Coordinating swarm' : undefined,
    messages: Math.floor(Math.random() * 20)
  }));
};

export default function SwarmDashboard() {
  const [agents, setAgents] = useState<SwarmAgent[]>(generateAgents());
  const [stats, setStats] = useState<SwarmStats>({
    totalAgents: 15,
    activeAgents: 12,
    state: 'exploring',
    efficiency: 78,
    convergenceRate: 45,
    bestSolutionScore: 0.89,
    iterationsCompleted: 1247,
    messagesExchanged: 8932
  });
  const [selectedAgent, setSelectedAgent] = useState<SwarmAgent | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState<any>(null);
  const [objective, setObjective] = useState('');
  const [showOptimizeModal, setShowOptimizeModal] = useState(false);

  // Fetch singularity status for real data
  const { data: singularityStatus, refetch: refetchStatus } = useQuery({
    queryKey: ['singularity-status'],
    queryFn: async () => {
      const res = await fetch('/api/singularity/status');
      if (!res.ok) return null;
      return res.json();
    },
    staleTime: 5000,
    refetchInterval: 10000
  });

  // Swarm optimization mutation
  const optimizeMutation = useMutation({
    mutationFn: async (params: { objective: string; agentCount: number; iterations: number }) => {
      const res = await fetch('/api/singularity/collective/swarm/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      if (!res.ok) throw new Error('Optimization failed');
      return res.json();
    },
    onMutate: () => {
      setIsOptimizing(true);
      setStats(prev => ({ ...prev, state: 'exploring' }));
    },
    onSuccess: (data) => {
      setOptimizationResult(data);
      setStats(prev => ({
        ...prev,
        state: 'converging',
        bestSolutionScore: data.data?.best_score || prev.bestSolutionScore,
        iterationsCompleted: prev.iterationsCompleted + (data.data?.iterations || 100)
      }));
      setIsOptimizing(false);
      setShowOptimizeModal(false);
    },
    onError: () => {
      setIsOptimizing(false);
    }
  });

  // Swarm solve mutation
  const solveMutation = useMutation({
    mutationFn: async (params: { problem: string; algorithm: string }) => {
      const res = await fetch('/api/singularity/collective/swarm/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      if (!res.ok) throw new Error('Solve failed');
      return res.json();
    }
  });

  const handleOptimize = () => {
    if (!objective.trim()) return;
    optimizeMutation.mutate({
      objective,
      agentCount: agents.length,
      iterations: 100
    });
  };
  const [isRunning, setIsRunning] = useState(true);
  const [pheromones, setPheromones] = useState<Pheromone[]>([]);

  // Simulate agent movement
  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      setAgents(prev => prev.map(agent => ({
        ...agent,
        position: {
          x: Math.max(0, Math.min(100, agent.position.x + (Math.random() - 0.5) * 5)),
          y: Math.max(0, Math.min(100, agent.position.y + (Math.random() - 0.5) * 5))
        },
        energy: Math.max(20, Math.min(100, agent.energy + (Math.random() - 0.5) * 5)),
        messages: agent.messages + (Math.random() > 0.7 ? 1 : 0)
      })));

      setStats(prev => ({
        ...prev,
        iterationsCompleted: prev.iterationsCompleted + 1,
        messagesExchanged: prev.messagesExchanged + Math.floor(Math.random() * 10),
        efficiency: Math.min(100, prev.efficiency + (Math.random() - 0.4) * 2),
        convergenceRate: Math.min(100, prev.convergenceRate + (Math.random() - 0.3) * 1)
      }));

      // Add pheromone trails
      if (Math.random() > 0.7) {
        setPheromones(prev => [
          ...prev.slice(-20),
          {
            x: Math.random() * 100,
            y: Math.random() * 100,
            intensity: 0.8,
            type: Math.random() > 0.3 ? 'success' : 'exploration'
          }
        ]);
      }
    }, 500);

    return () => clearInterval(interval);
  }, [isRunning]);

  const getStateColor = (state: string) => {
    switch (state) {
      case 'idle': return 'bg-gray-500';
      case 'searching': return 'bg-blue-500';
      case 'working': return 'bg-green-500';
      case 'resting': return 'bg-yellow-500';
      case 'communicating': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const getSwarmStateColor = (state: string) => {
    switch (state) {
      case 'exploring': return 'text-blue-400';
      case 'exploiting': return 'text-green-400';
      case 'converging': return 'text-purple-400';
      case 'stalled': return 'text-yellow-400';
      case 'emergency': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const agentsByRole = agents.reduce((acc, agent) => {
    acc[agent.role] = (acc[agent.role] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Network className="w-8 h-8 text-green-500" />
            Swarm Intelligence
          </h1>
          <p className="text-gray-400 mt-1">
            Multi-agent collective intelligence with emergent behavior
          </p>
        </div>
        <div className="flex items-center gap-3">
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
            onClick={() => setShowOptimizeModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 rounded-lg hover:bg-purple-500 transition-colors"
          >
            <Zap className="w-4 h-4" />
            Optimize
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-green-600 rounded-lg hover:bg-green-500 transition-colors">
            <Plus className="w-4 h-4" />
            Spawn Agent
          </button>
          <button className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors" title="Settings">
            <Settings className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Optimization Modal */}
      <AnimatePresence>
        {showOptimizeModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowOptimizeModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-purple-400" />
                Swarm Optimization
              </h3>
              <p className="text-gray-400 text-sm mb-4">
                Define an objective for the swarm to optimize using particle swarm optimization.
              </p>
              <textarea
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                placeholder="Enter optimization objective (e.g., 'Maximize response quality while minimizing latency')"
                rows={3}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 resize-none focus:outline-none focus:border-purple-500 mb-4"
              />
              <div className="flex gap-3">
                <button
                  onClick={() => setShowOptimizeModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleOptimize}
                  disabled={!objective.trim() || isOptimizing}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isOptimizing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Optimizing...
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4" />
                      Start Optimization
                    </>
                  )}
                </button>
              </div>
              {optimizationResult && (
                <div className="mt-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
                  <p className="text-green-400 text-sm font-medium">Optimization Complete</p>
                  <p className="text-gray-300 text-xs mt-1">
                    Best score: {optimizationResult.data?.best_score?.toFixed(4) || 'N/A'}
                  </p>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Swarm Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-green-500/20 to-green-600/10 border border-green-500/30 rounded-xl p-4"
        >
          <div className="text-green-400 text-sm font-medium">State</div>
          <div className={`text-xl font-bold mt-1 capitalize ${getSwarmStateColor(stats.state)}`}>
            {stats.state}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Agents</div>
          <div className="text-xl font-bold text-white mt-1">
            {stats.activeAgents}/{stats.totalAgents}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Efficiency</div>
          <div className="text-xl font-bold text-blue-400 mt-1">{stats.efficiency.toFixed(1)}%</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Convergence</div>
          <div className="text-xl font-bold text-purple-400 mt-1">{stats.convergenceRate.toFixed(1)}%</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Best Score</div>
          <div className="text-xl font-bold text-green-400 mt-1">{stats.bestSolutionScore.toFixed(2)}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Iterations</div>
          <div className="text-xl font-bold text-white mt-1">{stats.iterationsCompleted.toLocaleString()}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Messages</div>
          <div className="text-xl font-bold text-cyan-400 mt-1">{stats.messagesExchanged.toLocaleString()}</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
        >
          <div className="text-gray-400 text-sm font-medium">Pheromones</div>
          <div className="text-xl font-bold text-orange-400 mt-1">{pheromones.length}</div>
        </motion.div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Swarm Visualization */}
        <div className="lg:col-span-2 bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-green-500" />
            Swarm Visualization
          </h2>

          <div className="relative w-full h-96 bg-gray-900 rounded-lg overflow-hidden">
            {/* Pheromone trails */}
            {pheromones.map((p, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0.8, scale: 0 }}
                animate={{ opacity: p.intensity * 0.3, scale: 1 }}
                className={`absolute w-8 h-8 rounded-full ${
                  p.type === 'success' ? 'bg-green-500' : 'bg-blue-500'
                }`}
                style={{
                  left: `${p.x}%`,
                  top: `${p.y}%`,
                  filter: 'blur(8px)'
                }}
              />
            ))}

            {/* Agents */}
            {agents.map((agent) => {
              const config = roleConfig[agent.role];
              const Icon = config.icon;
              return (
                <motion.button
                  key={agent.id}
                  initial={false}
                  animate={{
                    left: `${agent.position.x}%`,
                    top: `${agent.position.y}%`
                  }}
                  transition={{ type: 'spring', stiffness: 100, damping: 20 }}
                  onClick={() => setSelectedAgent(agent)}
                  className={`absolute w-8 h-8 -ml-4 -mt-4 rounded-full flex items-center justify-center transition-all ${
                    selectedAgent?.id === agent.id
                      ? `ring-2 ring-${config.color}-400 ring-offset-2 ring-offset-gray-900`
                      : ''
                  }`}
                  style={{
                    backgroundColor: `var(--${config.color}-500)`,
                    opacity: agent.energy / 100
                  }}
                >
                  <Icon className="w-4 h-4 text-white" />
                </motion.button>
              );
            })}

            {/* Legend */}
            <div className="absolute bottom-2 left-2 flex flex-wrap gap-2">
              {Object.entries(roleConfig).map(([role, config]) => (
                <div key={role} className="flex items-center gap-1 text-xs text-gray-400">
                  <config.icon className={`w-3 h-3 text-${config.color}-500`} />
                  <span className="capitalize">{role}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Agent Detail / Role Distribution */}
        <div className="space-y-6">
          {/* Role Distribution */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-green-500" />
              Role Distribution
            </h2>

            <div className="space-y-3">
              {Object.entries(roleConfig).map(([role, config]) => {
                const count = agentsByRole[role] || 0;
                const percentage = (count / agents.length) * 100;

                return (
                  <div key={role}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <config.icon className={`w-4 h-4 text-${config.color}-500`} />
                        <span className="text-sm text-white capitalize">{role}</span>
                      </div>
                      <span className="text-sm text-gray-400">{count}</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${percentage}%` }}
                        className={`bg-${config.color}-500 h-2 rounded-full`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Selected Agent */}
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Brain className="w-5 h-5 text-green-500" />
              Agent Details
            </h2>

            {selectedAgent ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  {(() => {
                    const config = roleConfig[selectedAgent.role];
                    return (
                      <>
                        <div className={`w-12 h-12 rounded-full bg-${config.color}-500/20 flex items-center justify-center`}>
                          <config.icon className={`w-6 h-6 text-${config.color}-500`} />
                        </div>
                        <div>
                          <div className="text-white font-medium capitalize">{selectedAgent.role}</div>
                          <div className="text-sm text-gray-400">{selectedAgent.id}</div>
                        </div>
                      </>
                    );
                  })()}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-400">State</div>
                    <div className="flex items-center gap-2 mt-1">
                      <div className={`w-2 h-2 rounded-full ${getStateColor(selectedAgent.state)}`} />
                      <span className="text-white capitalize">{selectedAgent.state}</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-400">Energy</div>
                    <div className="text-white mt-1">{selectedAgent.energy.toFixed(0)}%</div>
                  </div>
                </div>

                <div>
                  <div className="text-sm text-gray-400 mb-1">Performance</div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full"
                      style={{ width: `${selectedAgent.performance}%` }}
                    />
                  </div>
                  <div className="text-sm text-gray-400 mt-1">{selectedAgent.performance.toFixed(1)}%</div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-400">Messages</div>
                    <div className="text-xl font-bold text-cyan-400 mt-1">{selectedAgent.messages}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-400">Position</div>
                    <div className="text-white mt-1">
                      ({selectedAgent.position.x.toFixed(0)}, {selectedAgent.position.y.toFixed(0)})
                    </div>
                  </div>
                </div>

                {selectedAgent.currentTask && (
                  <div>
                    <div className="text-sm text-gray-400">Current Task</div>
                    <div className="text-white mt-1">{selectedAgent.currentTask}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <Users className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">Click an agent to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-green-500" />
          Swarm Controls
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <button className="flex items-center gap-3 p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
            <Search className="w-5 h-5 text-blue-500" />
            <span className="text-white">Start Exploration</span>
          </button>
          <button className="flex items-center gap-3 p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
            <Target className="w-5 h-5 text-green-500" />
            <span className="text-white">Exploit Best</span>
          </button>
          <button className="flex items-center gap-3 p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
            <TrendingUp className="w-5 h-5 text-purple-500" />
            <span className="text-white">Force Convergence</span>
          </button>
          <button className="flex items-center gap-3 p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
            <RefreshCw className="w-5 h-5 text-orange-500" />
            <span className="text-white">Reset Swarm</span>
          </button>
          <button className="flex items-center gap-3 p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <span className="text-white">Emergency Stop</span>
          </button>
        </div>
      </div>
    </div>
  );
}
