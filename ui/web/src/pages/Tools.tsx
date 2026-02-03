import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Wrench,
  Search,
  Filter,
  Play,
  Star,
  StarOff,
  ChevronRight,
  Code,
  FileText,
  Globe,
  Database,
  Terminal,
  Folder,
  Settings2,
  Loader2,
  Check,
  AlertCircle
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'

interface Tool {
  id: string
  name: string
  description: string
  category: string
  schema: {
    parameters: Record<string, any>
    required: string[]
  }
  favorite: boolean
  lastUsed?: number
  usageCount: number
}

const categories = [
  { id: 'all', label: 'All Tools', icon: Wrench },
  { id: 'file', label: 'File Operations', icon: Folder },
  { id: 'code', label: 'Code Execution', icon: Code },
  { id: 'web', label: 'Web & API', icon: Globe },
  { id: 'data', label: 'Data Processing', icon: Database },
  { id: 'terminal', label: 'Terminal', icon: Terminal },
]

// Mock tools data - fallback when API unavailable
const mockTools: Tool[] = [
  { id: 'read_file', name: 'Read File', description: 'Read contents of a file from the filesystem', category: 'file', schema: { parameters: { path: { type: 'string', description: 'File path' } }, required: ['path'] }, favorite: true, usageCount: 156 },
  { id: 'write_file', name: 'Write File', description: 'Write content to a file', category: 'file', schema: { parameters: { path: { type: 'string' }, content: { type: 'string' } }, required: ['path', 'content'] }, favorite: true, usageCount: 89 },
  { id: 'execute_python', name: 'Execute Python', description: 'Run Python code in a sandbox', category: 'code', schema: { parameters: { code: { type: 'string' } }, required: ['code'] }, favorite: false, usageCount: 234 },
  { id: 'web_search', name: 'Web Search', description: 'Search the web using Brave Search', category: 'web', schema: { parameters: { query: { type: 'string' } }, required: ['query'] }, favorite: false, usageCount: 67 },
  { id: 'http_request', name: 'HTTP Request', description: 'Make HTTP requests to APIs', category: 'web', schema: { parameters: { url: { type: 'string' }, method: { type: 'string' } }, required: ['url'] }, favorite: false, usageCount: 45 },
  { id: 'run_shell', name: 'Run Shell Command', description: 'Execute shell commands', category: 'terminal', schema: { parameters: { command: { type: 'string' } }, required: ['command'] }, favorite: true, usageCount: 178 },
  { id: 'query_db', name: 'Query Database', description: 'Run SQL queries on connected databases', category: 'data', schema: { parameters: { query: { type: 'string' } }, required: ['query'] }, favorite: false, usageCount: 23 },
  { id: 'transform_json', name: 'Transform JSON', description: 'Transform JSON data using JQ expressions', category: 'data', schema: { parameters: { data: { type: 'object' }, expression: { type: 'string' } }, required: ['data', 'expression'] }, favorite: false, usageCount: 34 },
]

// Utility to map API tools to our format
function mapApiToolsToFormat(apiTools: any[]): Tool[] {
  if (!Array.isArray(apiTools)) return mockTools
  return apiTools.map((tool: any) => ({
    id: tool.id || tool.name,
    name: tool.name,
    description: tool.description || 'No description',
    category: tool.category || 'other',
    schema: tool.schema || { parameters: {}, required: [] },
    favorite: false,
    usageCount: tool.usageCount || 0
  }))
}

export function Tools() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null)
  const [favorites, setFavorites] = useState<Set<string>>(() => {
    const saved = localStorage.getItem('bael-favorite-tools')
    return saved ? new Set(JSON.parse(saved)) : new Set(['read_file', 'write_file', 'run_shell'])
  })

  // Fetch tools from API
  const { data: apiTools, isLoading, error } = useQuery({
    queryKey: ['tools'],
    queryFn: async () => {
      const res = await fetch('/api/v1/tools')
      if (!res.ok) throw new Error('Failed to fetch tools')
      return res.json()
    },
    staleTime: 30000,
    retry: 2
  })

  // Use API tools if available, otherwise fallback to mock
  const tools: Tool[] = apiTools ? mapApiToolsToFormat(apiTools.tools || apiTools) : mockTools

  // Apply favorites to tools
  const toolsWithFavorites = tools.map(t => ({
    ...t,
    favorite: favorites.has(t.id)
  }))

  const filteredTools = toolsWithFavorites.filter(tool => {
    const matchesSearch = tool.name.toLowerCase().includes(search.toLowerCase()) ||
                         tool.description.toLowerCase().includes(search.toLowerCase())
    const matchesCategory = category === 'all' || tool.category === category
    return matchesSearch && matchesCategory
  })

  const toggleFavorite = (toolId: string) => {
    const newFavorites = new Set(favorites)
    if (newFavorites.has(toolId)) {
      newFavorites.delete(toolId)
    } else {
      newFavorites.add(toolId)
    }
    setFavorites(newFavorites)
    localStorage.setItem('bael-favorite-tools', JSON.stringify([...newFavorites]))
  }

  return (
    <div className="flex h-full">
      {/* Sidebar - Categories */}
      <div className="w-64 border-r border-bael-border bg-bael-surface flex flex-col">
        <div className="p-4 border-b border-bael-border">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-bael-muted" />
            <input
              type="text"
              placeholder="Search tools..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text text-sm placeholder-bael-muted focus:outline-none focus:border-bael-primary transition-colors"
            />
          </div>
        </div>

        <nav className="flex-1 p-2 overflow-y-auto">
          {categories.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setCategory(id)}
              className={clsx(
                'w-full flex items-center justify-between px-3 py-2.5 rounded-lg transition-all text-left',
                category === id
                  ? 'bg-bael-primary/20 text-bael-primary'
                  : 'text-bael-muted hover:text-bael-text hover:bg-bael-border/50'
              )}
            >
              <div className="flex items-center gap-3">
                <Icon size={18} />
                <span className="text-sm font-medium">{label}</span>
              </div>
              <span className="text-xs bg-bael-border px-1.5 py-0.5 rounded">
                {id === 'all' ? toolsWithFavorites.length : toolsWithFavorites.filter(t => t.category === id).length}
              </span>
            </button>
          ))}
        </nav>

        {/* Favorites */}
        <div className="p-4 border-t border-bael-border">
          <h4 className="text-xs font-medium text-bael-muted uppercase mb-2">Favorites</h4>
          <div className="space-y-1">
            {toolsWithFavorites.filter(t => t.favorite).slice(0, 4).map((tool) => (
              <button
                key={tool.id}
                onClick={() => setSelectedTool(tool)}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm text-bael-muted hover:text-bael-text hover:bg-bael-border/50 transition-colors"
              >
                <Star size={12} className="text-bael-warning" />
                <span className="truncate">{tool.name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tools Grid */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-bael-border bg-bael-surface">
          <div>
            <h2 className="font-semibold text-bael-text">
              {categories.find(c => c.id === category)?.label || 'All Tools'}
            </h2>
            <p className="text-xs text-bael-muted">{filteredTools.length} tools available</p>
          </div>

          <div className="flex items-center gap-2">
            <button className="p-2 hover:bg-bael-border rounded-lg transition-colors text-bael-muted hover:text-bael-text">
              <Filter size={18} />
            </button>
            <button className="p-2 hover:bg-bael-border rounded-lg transition-colors text-bael-muted hover:text-bael-text">
              <Settings2 size={18} />
            </button>
          </div>
        </div>

        {/* Tools List */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 size={24} className="animate-spin text-bael-primary" />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {filteredTools.map((tool, i) => (
                  <motion.div
                    key={tool.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    onClick={() => setSelectedTool(tool)}
                    className={clsx(
                      'p-4 bg-bael-surface border rounded-xl cursor-pointer transition-all',
                      selectedTool?.id === tool.id
                        ? 'border-bael-primary'
                        : 'border-bael-border hover:border-bael-primary/50'
                    )}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="p-2 rounded-lg bg-bael-primary/10 text-bael-primary">
                          <Wrench size={16} />
                        </div>
                        <div>
                          <h3 className="font-medium text-bael-text">{tool.name}</h3>
                          <span className="text-xs text-bael-muted capitalize">{tool.category}</span>
                        </div>
                      </div>

                      <button
                        onClick={(e) => { e.stopPropagation(); toggleFavorite(tool.id) }}
                        className="p-1 hover:bg-bael-border rounded transition-colors"
                      >
                        {tool.favorite ? (
                          <Star size={14} className="text-bael-warning fill-bael-warning" />
                        ) : (
                          <StarOff size={14} className="text-bael-muted" />
                        )}
                      </button>
                    </div>

                    <p className="text-sm text-bael-muted line-clamp-2">{tool.description}</p>

                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-bael-border">
                      <span className="text-xs text-bael-muted">
                        Used {tool.usageCount} times
                      </span>
                      <ChevronRight size={14} className="text-bael-muted" />
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>

      {/* Tool Detail Panel */}
      <AnimatePresence>
        {selectedTool && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 400, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="border-l border-bael-border bg-bael-surface flex flex-col overflow-hidden"
          >
            <ToolDetailPanel
              tool={selectedTool}
              onClose={() => setSelectedTool(null)}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ToolDetailPanel({ tool, onClose }: { tool: Tool; onClose: () => void }) {
  const [params, setParams] = useState<Record<string, string>>({})
  const [result, setResult] = useState<{ success: boolean; output: string } | null>(null)

  const executeTool = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/v1/tools/${tool.id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parameters: params })
      })
      return res.json()
    },
    onSuccess: (data) => {
      setResult({ success: true, output: JSON.stringify(data, null, 2) })
    },
    onError: (error) => {
      setResult({ success: false, output: error.message })
    }
  })

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-bael-border">
        <h3 className="font-semibold text-bael-text">{tool.name}</h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-bael-border rounded transition-colors text-bael-muted"
        >
          ×
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <p className="text-sm text-bael-muted">{tool.description}</p>
        </div>

        {/* Parameters */}
        <div>
          <h4 className="text-sm font-medium text-bael-text mb-3">Parameters</h4>
          <div className="space-y-3">
            {Object.entries(tool.schema.parameters).map(([key, param]: [string, any]) => (
              <label key={key} className="block">
                <span className="text-xs text-bael-muted flex items-center gap-1">
                  {key}
                  {tool.schema.required.includes(key) && (
                    <span className="text-bael-error">*</span>
                  )}
                </span>
                <input
                  type="text"
                  value={params[key] || ''}
                  onChange={(e) => setParams({ ...params, [key]: e.target.value })}
                  placeholder={param.description}
                  className="mt-1 w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text text-sm placeholder-bael-muted focus:outline-none focus:border-bael-primary transition-colors"
                />
              </label>
            ))}
          </div>
        </div>

        {/* Execute */}
        <button
          onClick={() => executeTool.mutate()}
          disabled={executeTool.isPending}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-bael-primary text-white rounded-lg hover:bg-bael-primary/80 transition-colors disabled:opacity-50"
        >
          {executeTool.isPending ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Play size={16} />
          )}
          <span>Execute</span>
        </button>

        {/* Result */}
        {result && (
          <div className={clsx(
            'p-3 rounded-lg',
            result.success ? 'bg-bael-success/10 border border-bael-success/30' : 'bg-bael-error/10 border border-bael-error/30'
          )}>
            <div className="flex items-center gap-2 mb-2">
              {result.success ? (
                <Check size={14} className="text-bael-success" />
              ) : (
                <AlertCircle size={14} className="text-bael-error" />
              )}
              <span className={clsx('text-sm font-medium', result.success ? 'text-bael-success' : 'text-bael-error')}>
                {result.success ? 'Success' : 'Error'}
              </span>
            </div>
            <pre className="text-xs text-bael-text font-mono overflow-x-auto whitespace-pre-wrap">
              {result.output}
            </pre>
          </div>
        )}

        {/* Schema */}
        <div>
          <h4 className="text-sm font-medium text-bael-text mb-2">JSON Schema</h4>
          <pre className="p-3 bg-bael-bg rounded-lg text-xs text-bael-muted font-mono overflow-x-auto">
            {JSON.stringify(tool.schema, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  )
}
