import { useQuery } from '@tanstack/react-query';
import { Activity, Users, Puzzle, Workflow, TrendingUp, AlertCircle } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '@/lib/api';
import { motion } from 'framer-motion';

export function Dashboard() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.get('/health'),
    refetchInterval: 5000,
  });

  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.get('/v1/stats'),
    refetchInterval: 10000,
  });

  const { data: metrics } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => api.get('/metrics'),
    refetchInterval: 5000,
  });

  const cards = [
    {
      name: 'Active Agents',
      value: stats?.active_agents || 0,
      change: '+12%',
      icon: Users,
      color: 'bg-blue-500',
    },
    {
      name: 'Plugins Installed',
      value: stats?.plugins_installed || 0,
      change: '+5',
      icon: Puzzle,
      color: 'bg-purple-500',
    },
    {
      name: 'Workflows Running',
      value: stats?.workflows_running || 0,
      change: '+8',
      icon: Workflow,
      color: 'bg-green-500',
    },
    {
      name: 'Requests/min',
      value: stats?.requests_per_minute || 0,
      change: '+23%',
      icon: TrendingUp,
      color: 'bg-orange-500',
    },
  ];

  const mockChartData = [
    { time: '00:00', requests: 120, tasks: 45 },
    { time: '04:00', requests: 80, tasks: 30 },
    { time: '08:00', requests: 200, tasks: 78 },
    { time: '12:00', requests: 350, tasks: 120 },
    { time: '16:00', requests: 280, tasks: 95 },
    { time: '20:00', requests: 180, tasks: 62 },
  ];

  return (
    <div className="space-y-6">
      {/* System Status Banner */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`p-4 rounded-lg border ${
          health?.status === 'healthy'
            ? 'bg-green-50 border-green-200'
            : 'bg-yellow-50 border-yellow-200'
        }`}
      >
        <div className="flex items-center">
          {health?.status === 'healthy' ? (
            <Activity className="w-5 h-5 mr-2 text-green-600" />
          ) : (
            <AlertCircle className="w-5 h-5 mr-2 text-yellow-600" />
          )}
          <span className="font-medium">
            System Status: <span className="capitalize">{health?.status || 'Unknown'}</span>
          </span>
          <span className="ml-auto text-sm text-gray-600">
            Version {health?.version || '2.1.0'}
          </span>
        </div>
      </motion.div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card, index) => {
          const Icon = card.icon;
          return (
            <motion.div
              key={card.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="relative overflow-hidden bg-white rounded-lg shadow"
            >
              <div className="p-5">
                <div className="flex items-center">
                  <div className={`flex-shrink-0 p-3 rounded-md ${card.color}`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <div className="flex-1 w-0 ml-5">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">{card.name}</dt>
                      <dd className="flex items-baseline">
                        <div className="text-2xl font-semibold text-gray-900">{card.value}</div>
                        <div className="ml-2 text-sm font-medium text-green-600">{card.change}</div>
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Requests Chart */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="p-6 bg-white rounded-lg shadow"
        >
          <h3 className="mb-4 text-lg font-medium text-gray-900">Requests Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={mockChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="requests" stroke="#6366f1" fill="#818cf8" />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Tasks Chart */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
          className="p-6 bg-white rounded-lg shadow"
        >
          <h3 className="mb-4 text-lg font-medium text-gray-900">Task Execution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={mockChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="tasks" stroke="#10b981" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>
      </div>

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="bg-white rounded-lg shadow"
      >
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
        </div>
        <div className="divide-y">
          {[
            { action: 'Plugin installed', name: 'sentiment-analyzer', time: '2 minutes ago', status: 'success' },
            { action: 'Workflow completed', name: 'data-pipeline-001', time: '5 minutes ago', status: 'success' },
            { action: 'Agent spawned', name: 'researcher-agent-12', time: '8 minutes ago', status: 'success' },
            { action: 'Task failed', name: 'analysis-task-456', time: '12 minutes ago', status: 'error' },
          ].map((activity, index) => (
            <div key={index} className="px-6 py-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">{activity.action}</p>
                  <p className="text-sm text-gray-500">{activity.name}</p>
                </div>
                <div className="flex items-center space-x-4">
                  <span className="text-sm text-gray-500">{activity.time}</span>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded-full ${
                      activity.status === 'success'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {activity.status}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
