import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Server,
  Wifi,
  WifiOff,
  Play,
  Square,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Search,
  Filter,
  Settings,
  Terminal,
  Database,
  Globe,
  FolderOpen,
  GitBranch,
  Cloud,
  Shield,
  Zap,
  Box,
  Activity,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  Cpu,
  HardDrive,
  BarChart3,
  Layers,
  ExternalLink,
  Copy,
  MoreVertical,
  Power,
  Trash2
} from 'lucide-react'

// Types
interface MCPServer {
  name: string
  tier: 'essential' | 'power' | 'enhanced' | 'specialized'
  status: 'running' | 'stopped' | 'error' | 'starting'
  health: 'healthy' | 'unhealthy' | 'unknown'
  tools: string[]
  cpu_percent?: number
  memory_mb?: number
  memory_percent?: number
  container_id?: string
  image?: string
  ports?: string[]
  last_checked?: string
  required_env?: string[]
  description?: string
}

interface TierStats {
  total: number
  running: number
  percentage: number
}

interface MCPStatus {
  timestamp: string
  uptime_seconds: number
  summary: {
    total_containers: number
    running: number
    healthy: number
    stopped: number
  }
  tiers: {
    essential: TierStats
    power: TierStats
    enhanced: TierStats
    specialized: TierStats
  }
  containers: MCPServer[]
}

// Tier configurations
const TIER_CONFIG = {
  essential: {
    name: 'Essential',
    color: 'emerald',
    bgColor: 'bg-emerald-500/10',
    textColor: 'text-emerald-400',
    borderColor: 'border-emerald-500/30',
    icon: Zap,
    description: 'Core functionality for AI agents'
  },
  power: {
    name: 'Power Tools',
    color: 'blue',
    bgColor: 'bg-blue-500/10',
    textColor: 'text-blue-400',
    borderColor: 'border-blue-500/30',
    icon: Terminal,
    description: 'Advanced development & automation'
  },
  enhanced: {
    name: 'Enhanced',
    color: 'purple',
    bgColor: 'bg-purple-500/10',
    textColor: 'text-purple-400',
    borderColor: 'border-purple-500/30',
    icon: Layers,
    description: 'Extended capabilities'
  },
  specialized: {
    name: 'Specialized',
    color: 'amber',
    bgColor: 'bg-amber-500/10',
    textColor: 'text-amber-400',
    borderColor: 'border-amber-500/30',
    icon: Box,
    description: 'Domain-specific tools'
  }
}

// MCP Server definitions with tools
const MCP_SERVERS: MCPServer[] = [
  // Essential Tier
  { name: 'filesystem', tier: 'essential', status: 'stopped', health: 'unknown', tools: ['read_file', 'write_file', 'list_directory', 'search_files', 'get_file_info', 'create_directory', 'move_file'], description: 'File system operations' },
  { name: 'brave-search', tier: 'essential', status: 'stopped', health: 'unknown', tools: ['brave_web_search', 'brave_local_search'], required_env: ['BRAVE_API_KEY'], description: 'Web search via Brave API' },
  { name: 'github', tier: 'essential', status: 'stopped', health: 'unknown', tools: ['create_repository', 'search_repositories', 'get_file_contents', 'create_or_update_file', 'push_files', 'create_issue', 'create_pull_request', 'fork_repository', 'create_branch'], required_env: ['GITHUB_TOKEN'], description: 'GitHub repository management' },
  { name: 'sqlite', tier: 'essential', status: 'stopped', health: 'unknown', tools: ['read_query', 'write_query', 'create_table', 'list_tables', 'describe_table', 'append_insight'], description: 'SQLite database operations' },
  { name: 'memory', tier: 'essential', status: 'stopped', health: 'unknown', tools: ['create_entities', 'create_relations', 'add_observations', 'delete_entities', 'delete_observations', 'delete_relations', 'read_graph', 'search_nodes', 'open_nodes'], description: 'Persistent knowledge graph' },

  // Power Tier
  { name: 'playwright', tier: 'power', status: 'stopped', health: 'unknown', tools: ['playwright_navigate', 'playwright_screenshot', 'playwright_click', 'playwright_fill', 'playwright_select', 'playwright_hover', 'playwright_evaluate'], description: 'Browser automation' },
  { name: 'docker', tier: 'power', status: 'stopped', health: 'unknown', tools: ['list_containers', 'create_container', 'run_container', 'stop_container', 'remove_container', 'get_logs', 'list_images'], description: 'Container management' },
  { name: 'git', tier: 'power', status: 'stopped', health: 'unknown', tools: ['git_status', 'git_diff', 'git_commit', 'git_add', 'git_reset', 'git_log', 'git_create_branch', 'git_checkout', 'git_show'], description: 'Git version control' },
  { name: 'postgres', tier: 'power', status: 'stopped', health: 'unknown', tools: ['query', 'execute', 'list_tables', 'describe_table'], required_env: ['POSTGRES_USER', 'POSTGRES_PASSWORD'], description: 'PostgreSQL database' },
  { name: 'redis', tier: 'power', status: 'stopped', health: 'unknown', tools: ['get', 'set', 'delete', 'list_keys', 'publish', 'subscribe'], description: 'Redis cache & pub/sub' },
  { name: 'slack', tier: 'power', status: 'stopped', health: 'unknown', tools: ['list_channels', 'post_message', 'reply_to_thread', 'add_reaction', 'get_channel_history', 'get_thread_replies', 'search_messages', 'get_users'], required_env: ['SLACK_BOT_TOKEN'], description: 'Slack communication' },

  // Enhanced Tier
  { name: 'fetch', tier: 'enhanced', status: 'stopped', health: 'unknown', tools: ['fetch'], description: 'HTTP requests' },
  { name: 'puppeteer', tier: 'enhanced', status: 'stopped', health: 'unknown', tools: ['puppeteer_navigate', 'puppeteer_screenshot', 'puppeteer_click', 'puppeteer_fill', 'puppeteer_select', 'puppeteer_hover', 'puppeteer_evaluate'], description: 'Browser automation (alternative)' },
  { name: 'sequential-thinking', tier: 'enhanced', status: 'stopped', health: 'unknown', tools: ['sequentialthinking'], description: 'Step-by-step reasoning' },
  { name: 'time', tier: 'enhanced', status: 'stopped', health: 'unknown', tools: ['get_current_time', 'convert_time'], description: 'Time operations' },
  { name: 'exa', tier: 'enhanced', status: 'stopped', health: 'unknown', tools: ['search', 'find_similar', 'get_contents'], required_env: ['EXA_API_KEY'], description: 'Advanced web search' },
  { name: 'firecrawl', tier: 'enhanced', status: 'stopped', health: 'unknown', tools: ['firecrawl_scrape', 'firecrawl_map', 'firecrawl_crawl', 'firecrawl_check_crawl_status'], required_env: ['FIRECRAWL_API_KEY'], description: 'Web scraping' },
  { name: 'context7', tier: 'enhanced', status: 'stopped', health: 'unknown', tools: ['resolve-library-id', 'get-library-docs'], description: 'Library documentation' },
  { name: 'everything', tier: 'enhanced', status: 'stopped', health: 'unknown', tools: ['search'], description: 'File indexing' },

  // Specialized Tier
  { name: 'youtube', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['get_transcript'], description: 'YouTube transcripts' },
  { name: 'google-drive', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['search', 'read_file', 'list_folder'], required_env: ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'], description: 'Google Drive access' },
  { name: 'google-maps', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['maps_geocode', 'maps_reverse_geocode', 'maps_search_places', 'maps_place_details', 'maps_distance_matrix', 'maps_directions', 'maps_elevation'], required_env: ['GOOGLE_MAPS_API_KEY'], description: 'Google Maps & Places' },
  { name: 'aws-kb', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['retrieve_from_knowledge_base'], required_env: ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'], description: 'AWS Knowledge Base' },
  { name: 's3', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['list_buckets', 'list_objects', 'get_object', 'put_object', 'delete_object'], required_env: ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'], description: 'AWS S3 storage' },
  { name: 'cloudflare', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['kv_get', 'kv_put', 'kv_list', 'kv_delete', 'r2_get', 'r2_put', 'r2_list', 'r2_delete', 'd1_query', 'workers_list', 'workers_deploy'], required_env: ['CLOUDFLARE_API_TOKEN'], description: 'Cloudflare Workers/KV/R2' },
  { name: 'sentry', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['list_issues', 'get_issue', 'resolve_issue', 'list_projects', 'get_event'], required_env: ['SENTRY_AUTH_TOKEN'], description: 'Error monitoring' },
  { name: 'raygun', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['list_errors', 'get_error', 'resolve_error'], required_env: ['RAYGUN_API_KEY'], description: 'Crash reporting' },
  { name: 'linear', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['list_issues', 'create_issue', 'update_issue', 'search_issues', 'list_projects', 'list_teams'], required_env: ['LINEAR_API_KEY'], description: 'Issue tracking' },
  { name: 'notion', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['search', 'get_page', 'create_page', 'update_page', 'list_databases', 'query_database'], required_env: ['NOTION_API_KEY'], description: 'Notion workspace' },
  { name: 'obsidian', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['list_notes', 'read_note', 'create_note', 'update_note', 'search_notes', 'get_tags'], description: 'Obsidian notes' },
  { name: 'todoist', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['list_tasks', 'create_task', 'update_task', 'complete_task', 'list_projects', 'create_project'], required_env: ['TODOIST_API_TOKEN'], description: 'Task management' },
  { name: 'e2b', tier: 'specialized', status: 'stopped', health: 'unknown', tools: ['create_sandbox', 'run_code', 'run_terminal_command', 'read_file', 'write_file', 'list_files'], required_env: ['E2B_API_KEY'], description: 'Code sandbox' },
]

// Status badge component
function StatusBadge({ status, health }: { status: string; health: string }) {
  const config = {
    running: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/20' },
    stopped: { icon: XCircle, color: 'text-gray-400', bg: 'bg-gray-500/20' },
    error: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-500/20' },
    starting: { icon: RefreshCw, color: 'text-yellow-400', bg: 'bg-yellow-500/20' }
  }[status] || { icon: Clock, color: 'text-gray-400', bg: 'bg-gray-500/20' }

  const Icon = config.icon

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${config.bg} ${config.color}`}>
      <Icon className={`w-3 h-3 ${status === 'starting' ? 'animate-spin' : ''}`} />
      {status}
    </span>
  )
}

// Server Card component
function ServerCard({ server, onStart, onStop, onRestart, expanded, onToggle }: {
  server: MCPServer
  onStart: () => void
  onStop: () => void
  onRestart: () => void
  expanded: boolean
  onToggle: () => void
}) {
  const tierConfig = TIER_CONFIG[server.tier]
  const isRunning = server.status === 'running'
  const hasRequiredEnv = server.required_env && server.required_env.length > 0

  return (
    <motion.div
      layout
      className={`bg-gray-800/50 border rounded-lg overflow-hidden ${tierConfig.borderColor}`}
    >
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${tierConfig.bgColor}`}>
              <Server className={`w-5 h-5 ${tierConfig.textColor}`} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-white">{server.name}</h3>
                <StatusBadge status={server.status} health={server.health} />
              </div>
              <p className="text-sm text-gray-400">{server.description}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Action buttons */}
            {isRunning ? (
              <>
                <button
                  onClick={onRestart}
                  className="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-white transition"
                  title="Restart"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
                <button
                  onClick={onStop}
                  className="p-1.5 rounded-lg hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition"
                  title="Stop"
                >
                  <Square className="w-4 h-4" />
                </button>
              </>
            ) : (
              <button
                onClick={onStart}
                className="p-1.5 rounded-lg hover:bg-emerald-500/20 text-gray-400 hover:text-emerald-400 transition"
                title="Start"
              >
                <Play className="w-4 h-4" />
              </button>
            )}

            <button
              onClick={onToggle}
              className="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-white transition"
            >
              {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Stats row when running */}
        {isRunning && server.cpu_percent !== undefined && (
          <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              <Cpu className="w-3 h-3" />
              {server.cpu_percent}% CPU
            </span>
            <span className="flex items-center gap-1">
              <HardDrive className="w-3 h-3" />
              {server.memory_mb?.toFixed(1)} MB
            </span>
            <span className="flex items-center gap-1">
              <Activity className="w-3 h-3" />
              {server.tools.length} tools
            </span>
          </div>
        )}
      </div>

      {/* Expanded content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-gray-700/50"
          >
            <div className="p-4 space-y-4">
              {/* Required environment variables */}
              {hasRequiredEnv && (
                <div>
                  <h4 className="text-xs font-medium text-gray-400 uppercase mb-2">Required API Keys</h4>
                  <div className="flex flex-wrap gap-2">
                    {server.required_env?.map(env => (
                      <span key={env} className="px-2 py-1 bg-yellow-500/10 text-yellow-400 text-xs rounded border border-yellow-500/30">
                        {env}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Tools */}
              <div>
                <h4 className="text-xs font-medium text-gray-400 uppercase mb-2">Available Tools ({server.tools.length})</h4>
                <div className="flex flex-wrap gap-2">
                  {server.tools.map(tool => (
                    <span key={tool} className="px-2 py-1 bg-gray-700/50 text-gray-300 text-xs rounded font-mono">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>

              {/* Container info when running */}
              {isRunning && server.container_id && (
                <div className="text-xs text-gray-500">
                  <span>Container: {server.container_id}</span>
                  {server.image && <span className="ml-4">Image: {server.image}</span>}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// Main MCP Servers page
export function MCPServers() {
  const [servers, setServers] = useState<MCPServer[]>(MCP_SERVERS)
  const [expandedServers, setExpandedServers] = useState<Set<string>>(new Set())
  const [selectedTier, setSelectedTier] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [isHubRunning, setIsHubRunning] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  // Calculate stats
  const stats = {
    total: servers.length,
    running: servers.filter(s => s.status === 'running').length,
    totalTools: servers.reduce((sum, s) => sum + s.tools.length, 0)
  }

  // Filter servers
  const filteredServers = servers.filter(server => {
    if (selectedTier && server.tier !== selectedTier) return false
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        server.name.toLowerCase().includes(query) ||
        server.description?.toLowerCase().includes(query) ||
        server.tools.some(t => t.toLowerCase().includes(query))
      )
    }
    return true
  })

  // Group by tier
  const serversByTier = {
    essential: filteredServers.filter(s => s.tier === 'essential'),
    power: filteredServers.filter(s => s.tier === 'power'),
    enhanced: filteredServers.filter(s => s.tier === 'enhanced'),
    specialized: filteredServers.filter(s => s.tier === 'specialized')
  }

  // Actions
  const handleStartServer = async (name: string) => {
    setServers(prev => prev.map(s =>
      s.name === name ? { ...s, status: 'starting' as const } : s
    ))
    // Simulate start
    setTimeout(() => {
      setServers(prev => prev.map(s =>
        s.name === name ? { ...s, status: 'running', health: 'healthy', cpu_percent: Math.random() * 10, memory_mb: Math.random() * 100 + 50 } : s
      ))
    }, 1500)
  }

  const handleStopServer = async (name: string) => {
    setServers(prev => prev.map(s =>
      s.name === name ? { ...s, status: 'stopped', health: 'unknown', cpu_percent: undefined, memory_mb: undefined } : s
    ))
  }

  const handleStartHub = async () => {
    setIsLoading(true)
    // Start essential tier first
    for (const server of servers.filter(s => s.tier === 'essential')) {
      await handleStartServer(server.name)
    }
    setIsHubRunning(true)
    setIsLoading(false)
  }

  const handleStopHub = async () => {
    setIsLoading(true)
    for (const server of servers.filter(s => s.status === 'running')) {
      await handleStopServer(server.name)
    }
    setIsHubRunning(false)
    setIsLoading(false)
  }

  const toggleExpanded = (name: string) => {
    setExpandedServers(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Server className="w-8 h-8 text-purple-400" />
            MCP Hub
          </h1>
          <p className="text-gray-400 mt-1">33 MCP servers • {stats.totalTools} tools available</p>
        </div>

        <div className="flex items-center gap-3">
          {isHubRunning ? (
            <button
              onClick={handleStopHub}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition disabled:opacity-50"
            >
              <Power className="w-4 h-4" />
              Stop Hub
            </button>
          ) : (
            <button
              onClick={handleStartHub}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg hover:bg-emerald-500/30 transition disabled:opacity-50"
            >
              <Power className="w-4 h-4" />
              Start Hub
            </button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        {Object.entries(TIER_CONFIG).map(([key, config]) => {
          const tierServers = servers.filter(s => s.tier === key)
          const running = tierServers.filter(s => s.status === 'running').length
          const Icon = config.icon

          return (
            <button
              key={key}
              onClick={() => setSelectedTier(selectedTier === key ? null : key)}
              className={`p-4 rounded-lg border transition ${
                selectedTier === key
                  ? `${config.bgColor} ${config.borderColor}`
                  : 'bg-gray-800/30 border-gray-700/50 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center justify-between">
                <Icon className={`w-5 h-5 ${config.textColor}`} />
                <span className={`text-sm ${config.textColor}`}>
                  {running}/{tierServers.length}
                </span>
              </div>
              <h3 className="text-lg font-semibold text-white mt-2">{config.name}</h3>
              <p className="text-xs text-gray-400">{config.description}</p>
            </button>
          )
        })}
      </div>

      {/* Search and filters */}
      <div className="flex items-center gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search servers or tools..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-gray-400 hover:text-white transition">
          <Filter className="w-4 h-4" />
          Filters
        </button>
      </div>

      {/* Server Lists by Tier */}
      <div className="space-y-6">
        {Object.entries(serversByTier).map(([tier, tierServers]) => {
          if (tierServers.length === 0) return null
          const config = TIER_CONFIG[tier as keyof typeof TIER_CONFIG]

          return (
            <div key={tier}>
              <div className="flex items-center gap-2 mb-3">
                <config.icon className={`w-5 h-5 ${config.textColor}`} />
                <h2 className={`text-lg font-semibold ${config.textColor}`}>{config.name}</h2>
                <span className="text-sm text-gray-400">({tierServers.length} servers)</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {tierServers.map(server => (
                  <ServerCard
                    key={server.name}
                    server={server}
                    onStart={() => handleStartServer(server.name)}
                    onStop={() => handleStopServer(server.name)}
                    onRestart={() => {
                      handleStopServer(server.name)
                      setTimeout(() => handleStartServer(server.name), 500)
                    }}
                    expanded={expandedServers.has(server.name)}
                    onToggle={() => toggleExpanded(server.name)}
                  />
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Empty state */}
      {filteredServers.length === 0 && (
        <div className="text-center py-12">
          <Server className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-400">No servers found</h3>
          <p className="text-sm text-gray-500">Try adjusting your search or filters</p>
        </div>
      )}
    </div>
  )
}
