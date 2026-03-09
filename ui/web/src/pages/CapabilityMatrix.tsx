import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Cpu,
  Search,
  Filter,
  RefreshCw,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronRight,
  Package,
  Zap,
  Brain,
  Workflow,
  Plug,
  Bot,
} from 'lucide-react'

interface Capability {
  id: string
  name: string
  item_type: string
  description: string
  version: string
  enabled: boolean
  tags: string[]
  metadata: Record<string, unknown>
}

interface RegistryStats {
  total: number
  by_type: Record<string, number>
  enabled: number
  disabled: number
}

const TYPE_ICONS: Record<string, React.FC<{ className?: string }>> = {
  agent: Bot,
  skill: Brain,
  plugin: Plug,
  workflow: Workflow,
  tool: Zap,
  integration: Package,
}

const TYPE_COLORS: Record<string, string> = {
  agent: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  skill: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  plugin: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  workflow: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  tool: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
  integration: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
}

async function fetchCapabilities(type?: string, search?: string): Promise<Capability[]> {
  const params = new URLSearchParams()
  if (type) params.set('type', type)
  if (search) params.set('search', search)
  params.set('limit', '500')
  const res = await fetch(`/api/registry/capabilities?${params}`)
  if (!res.ok) throw new Error('Failed to fetch capabilities')
  return res.json()
}

async function fetchStats(): Promise<RegistryStats> {
  const res = await fetch('/api/registry/stats')
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}

async function reloadRegistry(): Promise<void> {
  await fetch('/api/registry/reload', { method: 'POST' })
}

export default function CapabilityMatrix() {
  const [search, setSearch] = useState('')
  const [selectedType, setSelectedType] = useState<string | undefined>()
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['registry-stats'],
    queryFn: fetchStats,
    refetchInterval: 30_000,
  })

  const { data: capabilities = [], isLoading, refetch } = useQuery({
    queryKey: ['capabilities', selectedType, search],
    queryFn: () => fetchCapabilities(selectedType, search || undefined),
    refetchInterval: 60_000,
  })

  const handleReload = async () => {
    await reloadRegistry()
    refetch()
    refetchStats()
  }

  const types = stats ? Object.keys(stats.by_type) : []

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-violet-600 to-purple-700">
            <Cpu className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Capability Matrix</h1>
            <p className="text-sm text-gray-400">All discovered BAEL capabilities</p>
          </div>
        </div>
        <button
          onClick={handleReload}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Reload Registry
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white/5 rounded-xl p-4 border border-white/10">
            <div className="text-3xl font-bold text-white">{stats.total}</div>
            <div className="text-sm text-gray-400 mt-1">Total Capabilities</div>
          </div>
          <div className="bg-white/5 rounded-xl p-4 border border-white/10">
            <div className="text-3xl font-bold text-emerald-400">{stats.enabled}</div>
            <div className="text-sm text-gray-400 mt-1">Enabled</div>
          </div>
          <div className="bg-white/5 rounded-xl p-4 border border-white/10">
            <div className="text-3xl font-bold text-red-400">{stats.disabled}</div>
            <div className="text-sm text-gray-400 mt-1">Disabled</div>
          </div>
          <div className="bg-white/5 rounded-xl p-4 border border-white/10">
            <div className="text-3xl font-bold text-blue-400">{types.length}</div>
            <div className="text-sm text-gray-400 mt-1">Capability Types</div>
          </div>
        </div>
      )}

      {/* Type breakdown */}
      {stats && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedType(undefined)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
              !selectedType
                ? 'bg-violet-600 text-white border-violet-500'
                : 'bg-white/5 text-gray-400 border-white/10 hover:bg-white/10'
            }`}
          >
            All ({stats.total})
          </button>
          {Object.entries(stats.by_type).map(([t, count]) => {
            const Icon = TYPE_ICONS[t] || Package
            return (
              <button
                key={t}
                onClick={() => setSelectedType(t === selectedType ? undefined : t)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                  selectedType === t
                    ? 'bg-violet-600 text-white border-violet-500'
                    : `${TYPE_COLORS[t] || 'bg-white/5 text-gray-400 border-white/10'} hover:opacity-80`
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {t} ({count})
              </button>
            )
          })}
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          placeholder="Search capabilities, tags, descriptions…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 text-sm"
        />
      </div>

      {/* Capability List */}
      <div className="space-y-2">
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 text-violet-400 animate-spin" />
          </div>
        )}

        {!isLoading && capabilities.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <Cpu className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p>No capabilities found{search ? ` for "${search}"` : ''}</p>
            <p className="text-xs mt-1">Start the API and click "Reload Registry"</p>
          </div>
        )}

        {capabilities.map(cap => {
          const Icon = TYPE_ICONS[cap.item_type] || Package
          const colorClass = TYPE_COLORS[cap.item_type] || 'bg-white/5 text-gray-400 border-white/10'
          const isExpanded = expandedId === cap.id

          return (
            <div key={cap.id} className="bg-white/5 rounded-xl border border-white/10 overflow-hidden">
              <button
                onClick={() => setExpandedId(isExpanded ? null : cap.id)}
                className="w-full flex items-center gap-3 p-3 text-left hover:bg-white/5 transition-colors"
              >
                <div className={`p-1.5 rounded-lg border ${colorClass}`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white truncate">{cap.name}</span>
                    {cap.enabled ? (
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                    )}
                  </div>
                  <div className="text-xs text-gray-500 truncate">{cap.description || cap.version}</div>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full border shrink-0 ${colorClass}`}>
                  {cap.item_type}
                </span>
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />
                )}
              </button>

              {isExpanded && (
                <div className="px-4 pb-4 pt-1 border-t border-white/5 space-y-2">
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
                    <div><span className="text-gray-600">ID:</span> {cap.id}</div>
                    <div><span className="text-gray-600">Version:</span> {cap.version}</div>
                  </div>
                  {cap.description && (
                    <p className="text-xs text-gray-300">{cap.description}</p>
                  )}
                  {cap.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {cap.tags.map(tag => (
                        <span key={tag} className="text-xs px-1.5 py-0.5 rounded bg-white/10 text-gray-300">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
