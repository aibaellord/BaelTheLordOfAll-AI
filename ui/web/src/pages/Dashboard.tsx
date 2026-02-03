import { useStore } from '../store'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Activity,
  Brain,
  Users,
  Zap,
  MessageSquare,
  Terminal,
  CheckCircle,
  AlertCircle,
  Clock,
  TrendingUp,
  Server,
  Database
} from 'lucide-react'
import { motion } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'

// Mock activity data - will be replaced with real API
const mockActivity = Array.from({ length: 24 }, (_, i) => ({
  hour: `${i}:00`,
  messages: Math.floor(Math.random() * 50) + 10,
  tokens: Math.floor(Math.random() * 10000) + 1000,
}))

interface StatCardProps {
  title: string
  value: string | number
  icon: React.ElementType
  trend?: string
  color: string
}

function StatCard({ title, value, icon: Icon, trend, color }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-bael-surface border border-bael-border rounded-xl p-6"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-bael-muted text-sm">{title}</p>
          <p className="text-2xl font-bold text-bael-text mt-1">{value}</p>
          {trend && (
            <p className="text-xs text-bael-success mt-2 flex items-center gap-1">
              <TrendingUp size={12} />
              {trend}
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon size={20} className="text-white" />
        </div>
      </div>
    </motion.div>
  )
}

interface QuickActionProps {
  title: string
  description: string
  icon: React.ElementType
  onClick: () => void
}

function QuickAction({ title, description, icon: Icon, onClick }: QuickActionProps) {
  return (
    <button
      onClick={onClick}
      className="flex items-start gap-4 p-4 bg-bael-surface border border-bael-border rounded-xl hover:border-bael-primary/50 transition-all text-left group"
    >
      <div className="p-2 rounded-lg bg-bael-primary/10 text-bael-primary group-hover:bg-bael-primary group-hover:text-white transition-all">
        <Icon size={20} />
      </div>
      <div>
        <h3 className="font-medium text-bael-text">{title}</h3>
        <p className="text-sm text-bael-muted">{description}</p>
      </div>
    </button>
  )
}

export function Dashboard() {
  const { status, councilMembers, terminals, messages } = useStore()
  const navigate = useNavigate()

  // Fetch system status from API
  const { data: systemStatus } = useQuery({
    queryKey: ['system-status'],
    queryFn: async () => {
      const res = await fetch('/api/v1/status')
      return res.json()
    },
    refetchInterval: 5000,
  })

  const activeCouncil = councilMembers.filter(m => m.active).length
  const activeTerminals = terminals.length
  const recentMessages = messages.length

  return (
    <div className="p-6 space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Tools"
          value={status.tools}
          icon={Zap}
          trend="+12 this week"
          color="bg-bael-primary"
        />
        <StatCard
          title="MCP Servers"
          value={status.mcpServers}
          icon={Server}
          color="bg-bael-secondary"
        />
        <StatCard
          title="Council Members"
          value={`${activeCouncil}/${councilMembers.length}`}
          icon={Users}
          color="bg-purple-600"
        />
        <StatCard
          title="Active Terminals"
          value={activeTerminals}
          icon={Terminal}
          color="bg-emerald-600"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Chart */}
        <div className="lg:col-span-2 bg-bael-surface border border-bael-border rounded-xl p-6">
          <h2 className="font-semibold text-bael-text mb-4">Activity Overview</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockActivity}>
                <defs>
                  <linearGradient id="colorMessages" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#2e2e3e" />
                <XAxis dataKey="hour" stroke="#6b7280" fontSize={12} />
                <YAxis stroke="#6b7280" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e1e2e',
                    border: '1px solid #2e2e3e',
                    borderRadius: '8px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="messages"
                  stroke="#6366f1"
                  fillOpacity={1}
                  fill="url(#colorMessages)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* System Status */}
        <div className="bg-bael-surface border border-bael-border rounded-xl p-6">
          <h2 className="font-semibold text-bael-text mb-4">System Status</h2>
          <div className="space-y-4">
            <StatusItem
              label="Brain"
              status={systemStatus?.brain?.active ? 'online' : 'offline'}
            />
            <StatusItem
              label="Memory"
              status="online"
              detail={`${status.memory.working} working, ${status.memory.episodic} episodic`}
            />
            <StatusItem
              label="MCP Server"
              status={status.connected ? 'online' : 'offline'}
            />
            <StatusItem
              label="API Server"
              status="online"
              detail="Port 7777"
            />
            <StatusItem
              label="Active Model"
              status="online"
              detail={status.activeModel || 'Not configured'}
            />
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-bael-surface border border-bael-border rounded-xl p-6">
        <h2 className="font-semibold text-bael-text mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <QuickAction
            title="Start Chat"
            description="Begin a new conversation"
            icon={MessageSquare}
            onClick={() => navigate('/chat')}
          />
          <QuickAction
            title="Run Auto-Setup"
            description="Configure services automatically"
            icon={Zap}
            onClick={() => navigate('/settings')}
          />
          <QuickAction
            title="Council Session"
            description="Start a council deliberation"
            icon={Users}
            onClick={() => navigate('/council')}
          />
          <QuickAction
            title="New Terminal"
            description="Open a terminal session"
            icon={Terminal}
            onClick={() => navigate('/terminals')}
          />
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Messages */}
        <div className="bg-bael-surface border border-bael-border rounded-xl p-6">
          <h2 className="font-semibold text-bael-text mb-4">Recent Messages</h2>
          <div className="space-y-3">
            {messages.slice(-5).reverse().map((msg) => (
              <div
                key={msg.id}
                className="flex items-start gap-3 p-3 rounded-lg bg-bael-bg"
              >
                <div className={`p-1.5 rounded ${msg.role === 'user' ? 'bg-bael-primary/20 text-bael-primary' : 'bg-bael-secondary/20 text-bael-secondary'}`}>
                  {msg.role === 'user' ? <MessageSquare size={14} /> : <Brain size={14} />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-bael-muted capitalize">{msg.role}</p>
                  <p className="text-sm text-bael-text truncate">{msg.content}</p>
                </div>
                <span className="text-xs text-bael-muted">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
            {messages.length === 0 && (
              <p className="text-bael-muted text-sm text-center py-4">No recent messages</p>
            )}
          </div>
        </div>

        {/* Council Status */}
        <div className="bg-bael-surface border border-bael-border rounded-xl p-6">
          <h2 className="font-semibold text-bael-text mb-4">Council Status</h2>
          <div className="space-y-3">
            {councilMembers.length === 0 && (
              <p className="text-bael-muted text-sm text-center py-4">No council members active</p>
            )}
            {councilMembers.map((member) => {
              const memberColor = member.color || '#6366f1'
              return (
                <div
                  key={member.id}
                  className="flex items-center gap-3 p-3 rounded-lg bg-bael-bg"
                >
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
                    style={{ backgroundColor: memberColor + '33', color: memberColor }}
                  >
                    {member.name.charAt(0)}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-bael-text">{member.name}</p>
                    <p className="text-xs text-bael-muted">{member.role || member.persona}</p>
                  </div>
                  <div className={`w-2 h-2 rounded-full ${member.active || member.status === 'speaking' ? 'bg-bael-success' : 'bg-bael-muted'}`} />
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

interface StatusItemProps {
  label: string
  status: 'online' | 'offline' | 'pending'
  detail?: string
}

function StatusItem({ label, status, detail }: StatusItemProps) {
  const statusColors = {
    online: 'text-bael-success',
    offline: 'text-bael-error',
    pending: 'text-bael-warning',
  }

  const statusIcons = {
    online: CheckCircle,
    offline: AlertCircle,
    pending: Clock,
  }

  const Icon = statusIcons[status]

  return (
    <div className="flex items-center justify-between py-2 border-b border-bael-border last:border-0">
      <div>
        <p className="text-sm text-bael-text">{label}</p>
        {detail && <p className="text-xs text-bael-muted">{detail}</p>}
      </div>
      <div className={`flex items-center gap-1.5 ${statusColors[status]}`}>
        <Icon size={14} />
        <span className="text-xs capitalize">{status}</span>
      </div>
    </div>
  )
}
