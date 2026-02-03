import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  Cpu,
  HardDrive,
  Wifi,
  Clock,
  Zap,
  Brain,
  Database,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw
} from 'lucide-react';

interface SystemMetric {
  id: string;
  label: string;
  value: number | string;
  unit?: string;
  icon: React.ElementType;
  color: string;
  trend?: 'up' | 'down' | 'stable';
}

interface SystemStatusData {
  uptime: string;
  memoryUsed: number;
  memoryTotal: number;
  activeAgents: number;
  activeTasks: number;
  apiLatency: number;
  modelLoaded: string;
  memoryCount: number;
}

export function SystemStatusWidget() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [data, setData] = useState<SystemStatusData>({
    uptime: '0m',
    memoryUsed: 0,
    memoryTotal: 100,
    activeAgents: 0,
    activeTasks: 0,
    apiLatency: 0,
    modelLoaded: 'None',
    memoryCount: 0
  });

  // Fetch system status
  const fetchStatus = async () => {
    try {
      const [healthRes, statusRes] = await Promise.all([
        fetch('/api/health').catch(() => null),
        fetch('/api/v1/status').catch(() => null)
      ]);

      let newData = { ...data };

      if (healthRes?.ok) {
        const health = await healthRes.json();
        newData.uptime = health.uptime || '0m';
        newData.modelLoaded = health.model || 'Claude 3.5';
      }

      if (statusRes?.ok) {
        const status = await statusRes.json();
        newData.activeAgents = status.active_agents || 0;
        newData.activeTasks = status.active_tasks || 0;
        newData.memoryCount = status.memory_count || 0;
      }

      // Simulate some metrics
      newData.memoryUsed = Math.floor(Math.random() * 40 + 30);
      newData.memoryTotal = 100;
      newData.apiLatency = Math.floor(Math.random() * 100 + 50);

      setData(newData);
      setIsLoading(false);
    } catch (e) {
      console.error('Failed to fetch system status:', e);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Update every 30s
    return () => clearInterval(interval);
  }, []);

  const metrics: SystemMetric[] = [
    {
      id: 'uptime',
      label: 'Uptime',
      value: data.uptime,
      icon: Clock,
      color: 'text-green-400',
      trend: 'stable'
    },
    {
      id: 'memory',
      label: 'Memory',
      value: data.memoryUsed,
      unit: '%',
      icon: HardDrive,
      color: data.memoryUsed > 80 ? 'text-red-400' : data.memoryUsed > 60 ? 'text-yellow-400' : 'text-blue-400',
      trend: 'stable'
    },
    {
      id: 'latency',
      label: 'API Latency',
      value: data.apiLatency,
      unit: 'ms',
      icon: Wifi,
      color: data.apiLatency > 200 ? 'text-red-400' : data.apiLatency > 100 ? 'text-yellow-400' : 'text-green-400',
      trend: data.apiLatency > 150 ? 'up' : 'down'
    },
    {
      id: 'agents',
      label: 'Active Agents',
      value: data.activeAgents,
      icon: Brain,
      color: 'text-purple-400',
      trend: 'stable'
    },
    {
      id: 'tasks',
      label: 'Tasks',
      value: data.activeTasks,
      icon: Zap,
      color: 'text-amber-400',
      trend: data.activeTasks > 0 ? 'up' : 'stable'
    },
    {
      id: 'memories',
      label: 'Memories',
      value: data.memoryCount,
      icon: Database,
      color: 'text-cyan-400',
      trend: 'stable'
    },
  ];

  const TrendIcon = ({ trend }: { trend?: 'up' | 'down' | 'stable' }) => {
    if (trend === 'up') return <TrendingUp className="w-3 h-3 text-green-400" />;
    if (trend === 'down') return <TrendingDown className="w-3 h-3 text-red-400" />;
    return <Minus className="w-3 h-3 text-bael-muted" />;
  };

  return (
    <div className="fixed top-4 right-4 z-30">
      {/* Compact View */}
      <motion.button
        onClick={() => setIsExpanded(!isExpanded)}
        whileHover={{ scale: 1.02 }}
        className="flex items-center gap-2 px-3 py-2 bg-bael-surface border border-bael-border rounded-xl shadow-lg hover:border-bael-primary/30 transition-colors"
      >
        <Activity className="w-4 h-4 text-green-400" />
        <span className="text-xs text-bael-muted hidden sm:inline">
          {isLoading ? 'Loading...' : data.uptime}
        </span>
        <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
      </motion.button>

      {/* Expanded Panel */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            className="absolute top-full right-0 mt-2 w-80 bg-bael-surface border border-bael-border rounded-xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-bael-border bg-bael-bg/50">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-green-400" />
                <span className="text-sm font-medium text-bael-text">System Status</span>
              </div>
              <button
                onClick={fetchStatus}
                className="p-1.5 text-bael-muted hover:text-bael-text hover:bg-bael-border rounded-lg transition-colors"
                title="Refresh"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-2 p-3">
              {metrics.map(metric => {
                const Icon = metric.icon;
                return (
                  <div
                    key={metric.id}
                    className="flex items-center gap-3 p-3 bg-bael-bg rounded-lg"
                  >
                    <div className={`w-8 h-8 rounded-lg bg-bael-surface flex items-center justify-center`}>
                      <Icon className={`w-4 h-4 ${metric.color}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-bael-muted">{metric.label}</p>
                      <div className="flex items-center gap-1">
                        <span className="text-sm font-medium text-bael-text">
                          {metric.value}{metric.unit || ''}
                        </span>
                        <TrendIcon trend={metric.trend} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Model Info */}
            <div className="px-4 py-3 border-t border-bael-border bg-bael-bg/50">
              <div className="flex items-center justify-between">
                <span className="text-xs text-bael-muted">Active Model</span>
                <span className="text-xs font-medium text-bael-text">{data.modelLoaded}</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default SystemStatusWidget;
