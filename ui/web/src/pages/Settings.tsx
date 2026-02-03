import { useState } from 'react'
import { useStore } from '../store'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Settings,
  Server,
  Brain,
  Database,
  Palette,
  Shield,
  Plug,
  Key,
  Save,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Loader2,
  ChevronRight,
  Eye,
  EyeOff,
  Zap,
  Globe
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'

type SettingsTab = 'llm' | 'memory' | 'integrations' | 'security' | 'appearance' | 'advanced'

const tabs: { id: SettingsTab; label: string; icon: React.ElementType }[] = [
  { id: 'llm', label: 'LLM Configuration', icon: Brain },
  { id: 'memory', label: 'Memory & Storage', icon: Database },
  { id: 'integrations', label: 'Integrations', icon: Plug },
  { id: 'security', label: 'Security & API Keys', icon: Shield },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'advanced', label: 'Advanced', icon: Settings },
]

const models = [
  { id: 'claude-3.5-sonnet', name: 'Claude 3.5 Sonnet', provider: 'Anthropic', recommended: true },
  { id: 'claude-3-opus', name: 'Claude 3 Opus', provider: 'Anthropic' },
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI' },
  { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', provider: 'OpenAI' },
  { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', provider: 'Google' },
  { id: 'llama-3.1-70b', name: 'Llama 3.1 70B', provider: 'Meta (via OpenRouter)' },
  { id: 'mixtral-8x22b', name: 'Mixtral 8x22B', provider: 'Mistral' },
  { id: 'local-ollama', name: 'Local (Ollama)', provider: 'Local' },
]

export function SettingsPage() {
  const { settings, updateSettings } = useStore()
  const [activeTab, setActiveTab] = useState<SettingsTab>('llm')
  const [saving, setSaving] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)

  // Save settings
  const saveSettings = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      })
      return res.json()
    },
    onMutate: () => setSaving(true),
    onSettled: () => setSaving(false)
  })

  // Auto-setup
  const runAutoSetup = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/autonomous/setup', {
        method: 'POST'
      })
      return res.json()
    }
  })

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-64 border-r border-bael-border bg-bael-surface flex flex-col">
        <div className="p-4 border-b border-bael-border flex flex-col gap-2">
          <h2 className="font-semibold text-bael-text">Settings</h2>
          <p className="text-xs text-bael-muted">Configure BAEL to your preferences</p>
          <PersonaSwitcher />
          <GlobalSearchBar />
        </div>

        <nav className="flex-1 p-2">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={clsx(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left',
                activeTab === id
                  ? 'bg-bael-primary/20 text-bael-primary'
                  : 'text-bael-muted hover:text-bael-text hover:bg-bael-border/50'
              )}
            >
              <Icon size={18} />
              <span className="text-sm font-medium">{label}</span>
            </button>
          ))}
        </nav>

        {/* Quick actions */}
        <div className="p-4 border-t border-bael-border space-y-2">
          <button
            onClick={() => runAutoSetup.mutate()}
            disabled={runAutoSetup.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-bael-secondary text-white rounded-lg hover:bg-bael-secondary/80 transition-colors disabled:opacity-50"
          >
            {runAutoSetup.isPending ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Zap size={16} />
            )}
            <span className="text-sm">Auto-Setup</span>
          </button>

          <button
            onClick={() => saveSettings.mutate()}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-bael-primary text-white rounded-lg hover:bg-bael-primary/80 transition-colors disabled:opacity-50"
          >
            {saving ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Save size={16} />
            )}
            <span className="text-sm">Save Settings</span>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="max-w-3xl"
          >
            {activeTab === 'llm' && <LLMSettings settings={settings} updateSettings={updateSettings} />}
            {activeTab === 'memory' && <MemorySettings settings={settings} updateSettings={updateSettings} />}
            {activeTab === 'integrations' && <IntegrationsSettings />}
            {activeTab === 'security' && <SecuritySettings settings={settings} updateSettings={updateSettings} showApiKey={showApiKey} setShowApiKey={setShowApiKey} />}
            {activeTab === 'appearance' && <AppearanceSettings settings={settings} updateSettings={updateSettings} />}
            {activeTab === 'advanced' && <AdvancedSettings />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}

function LLMSettings({ settings, updateSettings }: { settings: any; updateSettings: any }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-bael-text mb-1">LLM Configuration</h3>
        <p className="text-sm text-bael-muted">Choose your preferred language model and configure parameters</p>
      </div>

      {/* Model selection */}
      <div className="space-y-4">
        <label className="block">
          <span className="text-sm font-medium text-bael-text">Model</span>
          <select
            value={settings.llm.model}
            onChange={(e) => updateSettings({ llm: { ...settings.llm, model: e.target.value } })}
            className="mt-1 w-full px-4 py-3 bg-bael-surface border border-bael-border rounded-xl text-bael-text focus:outline-none focus:border-bael-primary transition-colors"
          >
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name} ({model.provider}) {model.recommended ? '⭐ Recommended' : ''}
              </option>
            ))}
          </select>
        </label>

        {/* Temperature */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-bael-text">Temperature</span>
            <span className="text-sm text-bael-muted">{settings.llm.temperature}</span>
          </div>
          <input
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={settings.llm.temperature}
            onChange={(e) => updateSettings({ llm: { ...settings.llm, temperature: parseFloat(e.target.value) } })}
            className="w-full accent-bael-primary"
          />
          <div className="flex justify-between text-xs text-bael-muted mt-1">
            <span>Precise</span>
            <span>Creative</span>
          </div>
        </div>

        {/* Max tokens */}
        <label className="block">
          <span className="text-sm font-medium text-bael-text">Max Tokens</span>
          <input
            type="number"
            value={settings.llm.maxTokens}
            onChange={(e) => updateSettings({ llm: { ...settings.llm, maxTokens: parseInt(e.target.value) } })}
            className="mt-1 w-full px-4 py-3 bg-bael-surface border border-bael-border rounded-xl text-bael-text focus:outline-none focus:border-bael-primary transition-colors"
          />
        </label>

        {/* Streaming */}
        <div className="flex items-center justify-between p-4 bg-bael-surface border border-bael-border rounded-xl">
          <div>
            <span className="text-sm font-medium text-bael-text">Streaming Responses</span>
            <p className="text-xs text-bael-muted mt-1">Show responses as they're generated</p>
          </div>
          <Toggle
            checked={settings.llm.streaming}
            onChange={(v) => updateSettings({ llm: { ...settings.llm, streaming: v } })}
          />
        </div>
      </div>

      {/* Provider status */}
      <div className="p-4 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-3">Provider Status</h4>
        <div className="grid grid-cols-2 gap-3">
          <ProviderStatus name="Anthropic" status="connected" />
          <ProviderStatus name="OpenAI" status="not-configured" />
          <ProviderStatus name="OpenRouter" status="connected" />
          <ProviderStatus name="Ollama" status="offline" />
        </div>
      </div>
    </div>
  )
}

function MemorySettings({ settings, updateSettings }: { settings: any; updateSettings: any }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-bael-text mb-1">Memory & Storage</h3>
        <p className="text-sm text-bael-muted">Configure how BAEL stores and retrieves information</p>
      </div>

      <div className="space-y-4">
        {/* Working memory limit */}
        <label className="block">
          <span className="text-sm font-medium text-bael-text">Working Memory Limit</span>
          <input
            type="number"
            value={settings.memory.workingLimit}
            onChange={(e) => updateSettings({ memory: { ...settings.memory, workingLimit: parseInt(e.target.value) } })}
            className="mt-1 w-full px-4 py-3 bg-bael-surface border border-bael-border rounded-xl text-bael-text focus:outline-none focus:border-bael-primary transition-colors"
          />
          <p className="text-xs text-bael-muted mt-1">Maximum items in working memory</p>
        </label>

        {/* Auto-consolidate */}
        <div className="flex items-center justify-between p-4 bg-bael-surface border border-bael-border rounded-xl">
          <div>
            <span className="text-sm font-medium text-bael-text">Auto-Consolidate</span>
            <p className="text-xs text-bael-muted mt-1">Automatically move old memories to long-term storage</p>
          </div>
          <Toggle
            checked={settings.memory.autoConsolidate}
            onChange={(v) => updateSettings({ memory: { ...settings.memory, autoConsolidate: v } })}
          />
        </div>

        {/* Vector backend */}
        <label className="block">
          <span className="text-sm font-medium text-bael-text">Vector Database</span>
          <select
            value={settings.memory.vectorBackend}
            onChange={(e) => updateSettings({ memory: { ...settings.memory, vectorBackend: e.target.value } })}
            className="mt-1 w-full px-4 py-3 bg-bael-surface border border-bael-border rounded-xl text-bael-text focus:outline-none focus:border-bael-primary transition-colors"
          >
            <option value="chromadb">ChromaDB (Local)</option>
            <option value="qdrant">Qdrant</option>
            <option value="pinecone">Pinecone</option>
            <option value="weaviate">Weaviate</option>
          </select>
        </label>
      </div>

      {/* Storage stats */}
      <div className="p-4 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-3">Storage Statistics</h4>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-bael-primary">42</p>
            <p className="text-xs text-bael-muted">Working</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-bael-secondary">1,234</p>
            <p className="text-xs text-bael-muted">Long-term</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-purple-400">256 MB</p>
            <p className="text-xs text-bael-muted">Disk Used</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function IntegrationsSettings() {
  const integrations = [
    { id: 'github', name: 'GitHub', status: 'connected', icon: '🐙' },
    { id: 'slack', name: 'Slack', status: 'not-configured', icon: '💬' },
    { id: 'notion', name: 'Notion', status: 'not-configured', icon: '📝' },
    { id: 'google', name: 'Google Workspace', status: 'not-configured', icon: '🔵' },
    { id: 'jira', name: 'Jira', status: 'not-configured', icon: '🔷' },
    { id: 'discord', name: 'Discord', status: 'not-configured', icon: '🎮' },
  ]

  const mcpServers = [
    { id: 'filesystem', name: 'Filesystem MCP', status: 'running', tools: 12 },
    { id: 'github', name: 'GitHub MCP', status: 'running', tools: 8 },
    { id: 'brave', name: 'Brave Search MCP', status: 'stopped', tools: 3 },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-bael-text mb-1">Integrations</h3>
        <p className="text-sm text-bael-muted">Connect BAEL to external services and MCP servers</p>
      </div>

      {/* MCP Servers */}
      <div>
        <h4 className="text-sm font-medium text-bael-text mb-3 flex items-center gap-2">
          <Server size={16} />
          MCP Servers
        </h4>
        <div className="space-y-2">
          {mcpServers.map((server) => (
            <div key={server.id} className="flex items-center justify-between p-4 bg-bael-surface border border-bael-border rounded-xl">
              <div className="flex items-center gap-3">
                <div className={clsx(
                  'w-2 h-2 rounded-full',
                  server.status === 'running' ? 'bg-bael-success' : 'bg-bael-muted'
                )} />
                <div>
                  <p className="text-sm font-medium text-bael-text">{server.name}</p>
                  <p className="text-xs text-bael-muted">{server.tools} tools available</p>
                </div>
              </div>
              <button className="px-3 py-1.5 text-sm border border-bael-border rounded-lg text-bael-muted hover:text-bael-text transition-colors">
                Configure
              </button>
            </div>
          ))}

          <button className="w-full flex items-center justify-center gap-2 p-3 border border-dashed border-bael-border rounded-xl text-bael-muted hover:text-bael-text hover:border-bael-primary transition-colors">
            <Plug size={16} />
            <span className="text-sm">Add MCP Server</span>
          </button>
        </div>
      </div>

      {/* External Integrations */}
      <div>
        <h4 className="text-sm font-medium text-bael-text mb-3 flex items-center gap-2">
          <Globe size={16} />
          External Services
        </h4>
        <div className="grid grid-cols-2 gap-3">
          {integrations.map((integration) => (
            <div key={integration.id} className="flex items-center justify-between p-4 bg-bael-surface border border-bael-border rounded-xl">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{integration.icon}</span>
                <div>
                  <p className="text-sm font-medium text-bael-text">{integration.name}</p>
                  <p className={clsx(
                    'text-xs',
                    integration.status === 'connected' ? 'text-bael-success' : 'text-bael-muted'
                  )}>
                    {integration.status === 'connected' ? 'Connected' : 'Not configured'}
                  </p>
                </div>
              </div>
              <ChevronRight size={16} className="text-bael-muted" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function SecuritySettings({ settings, updateSettings, showApiKey, setShowApiKey }: { settings: any; updateSettings: any; showApiKey: boolean; setShowApiKey: (v: boolean) => void }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-bael-text mb-1">Security & API Keys</h3>
        <p className="text-sm text-bael-muted">Manage your API keys and security settings</p>
      </div>

      <div className="space-y-4">
        {/* API Keys */}
        <div className="p-4 bg-bael-surface border border-bael-border rounded-xl space-y-4">
          <h4 className="text-sm font-medium text-bael-text flex items-center gap-2">
            <Key size={16} />
            API Keys
          </h4>

          {['ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'OPENROUTER_API_KEY'].map((key) => (
            <label key={key} className="block">
              <span className="text-xs text-bael-muted">{key}</span>
              <div className="relative mt-1">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  placeholder="sk-..."
                  className="w-full px-4 py-2 pr-10 bg-bael-bg border border-bael-border rounded-lg text-bael-text text-sm focus:outline-none focus:border-bael-primary transition-colors font-mono"
                />
                <button
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-bael-muted hover:text-bael-text"
                >
                  {showApiKey ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </label>
          ))}
        </div>

        {/* Security options */}
        <div className="flex items-center justify-between p-4 bg-bael-surface border border-bael-border rounded-xl">
          <div>
            <span className="text-sm font-medium text-bael-text">Require Confirmation</span>
            <p className="text-xs text-bael-muted mt-1">Ask before executing destructive actions</p>
          </div>
          <Toggle
            checked={settings.security?.requireConfirmation ?? true}
            onChange={(v) => updateSettings({ security: { ...settings.security, requireConfirmation: v } })}
          />
        </div>

        <div className="flex items-center justify-between p-4 bg-bael-surface border border-bael-border rounded-xl">
          <div>
            <span className="text-sm font-medium text-bael-text">Sandbox Mode</span>
            <p className="text-xs text-bael-muted mt-1">Run code in isolated containers</p>
          </div>
          <Toggle
            checked={settings.security?.sandboxMode ?? false}
            onChange={(v) => updateSettings({ security: { ...settings.security, sandboxMode: v } })}
          />
        </div>
      </div>
    </div>
  )
}

function AppearanceSettings({ settings, updateSettings }: { settings: any; updateSettings: any }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-bael-text mb-1">Appearance</h3>
        <p className="text-sm text-bael-muted">Customize the look and feel of BAEL</p>
      </div>

      <div className="space-y-4">
        <label className="block">
          <span className="text-sm font-medium text-bael-text">Accent Color</span>
          <div className="flex gap-3 mt-2">
            {['#6366f1', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b'].map((color) => (
              <button
                key={color}
                onClick={() => updateSettings({ ui: { ...settings.ui, accentColor: color } })}
                className={clsx(
                  'w-8 h-8 rounded-full transition-transform hover:scale-110',
                  settings.ui?.accentColor === color && 'ring-2 ring-offset-2 ring-offset-bael-bg ring-white'
                )}
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        </label>
      </div>
    </div>
  )
}

function AdvancedSettings() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-bael-text mb-1">Advanced Settings</h3>
        <p className="text-sm text-bael-muted">Expert configuration options</p>
      </div>

      <div className="space-y-4">
        <div className="p-4 bg-bael-warning/10 border border-bael-warning/30 rounded-xl">
          <p className="text-sm text-bael-warning">
            ⚠️ These settings are for advanced users. Incorrect configuration may cause issues.
          </p>
        </div>

        <label className="block">
          <span className="text-sm font-medium text-bael-text">Log Level</span>
          <select className="mt-1 w-full px-4 py-3 bg-bael-surface border border-bael-border rounded-xl text-bael-text focus:outline-none focus:border-bael-primary transition-colors">
            <option value="info">Info</option>
            <option value="debug">Debug</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>
        </label>

        <label className="block">
          <span className="text-sm font-medium text-bael-text">API Server Port</span>
          <input
            type="number"
            defaultValue={7777}
            className="mt-1 w-full px-4 py-3 bg-bael-surface border border-bael-border rounded-xl text-bael-text focus:outline-none focus:border-bael-primary transition-colors"
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium text-bael-text">Concurrent Agents</span>
          <input
            type="number"
            defaultValue={4}
            className="mt-1 w-full px-4 py-3 bg-bael-surface border border-bael-border rounded-xl text-bael-text focus:outline-none focus:border-bael-primary transition-colors"
          />
        </label>

        <div className="flex gap-3">
          <button className="flex-1 px-4 py-2 border border-bael-border rounded-lg text-bael-muted hover:text-bael-text transition-colors">
            Export Config
          </button>
          <button className="flex-1 px-4 py-2 border border-bael-border rounded-lg text-bael-muted hover:text-bael-text transition-colors">
            Import Config
          </button>
          <button className="flex-1 px-4 py-2 border border-bael-error/50 rounded-lg text-bael-error hover:bg-bael-error/10 transition-colors">
            Reset to Defaults
          </button>
        </div>
      </div>
    </div>
  )
}

// Quick persona switcher
function PersonaSwitcher() {
  // ...implement persona switching logic here...
  return (
    <div className="flex gap-2 items-center">
      <span className="text-xs text-bael-muted">Persona:</span>
      <select className="px-2 py-1 rounded bg-bael-bg text-bael-text">
        <option>Architect Prime</option>
        <option>Code Master</option>
        <option>Security Sentinel</option>
        <option>QA Perfectionist</option>
      </select>
    </div>
  )
}

// Global search bar
function GlobalSearchBar() {
  // ...implement global search logic here...
  return (
    <input className="w-full px-2 py-1 rounded bg-bael-bg text-bael-text mt-2" placeholder="Search memories, personas, tools..." />
  )
}

// Helper components
function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={clsx(
        'w-10 h-5 rounded-full transition-colors relative',
        checked ? 'bg-bael-primary' : 'bg-bael-border'
      )}
    >
      <div className={clsx(
        'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform',
        checked ? 'left-5' : 'left-0.5'
      )} />
    </button>
  )
}

function ProviderStatus({ name, status }: { name: string; status: 'connected' | 'not-configured' | 'offline' }) {
  const statusConfig = {
    connected: { color: 'text-bael-success', icon: CheckCircle, label: 'Connected' },
    'not-configured': { color: 'text-bael-muted', icon: AlertCircle, label: 'Not configured' },
    offline: { color: 'text-bael-error', icon: AlertCircle, label: 'Offline' },
  }

  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <div className="flex items-center justify-between p-2 bg-bael-bg rounded-lg">
      <span className="text-sm text-bael-text">{name}</span>
      <div className={clsx('flex items-center gap-1', config.color)}>
        <Icon size={12} />
        <span className="text-xs">{config.label}</span>
      </div>
    </div>
  )
}
