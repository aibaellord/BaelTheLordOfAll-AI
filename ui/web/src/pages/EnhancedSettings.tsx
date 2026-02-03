import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { showToast } from '../hooks/useToast'
import {
  Settings,
  Brain,
  Database,
  Lock,
  Palette,
  Zap,
  Key,
  Eye,
  EyeOff,
  Check,
  X,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Save,
  Upload,
  Download,
  Trash2,
  Plus,
  Server,
  Globe,
  Shield,
  Cpu,
  HardDrive,
  Network,
  Bot,
  Sparkles,
  Crown,
  Search,
  ChevronDown,
  ChevronRight,
  Copy,
  ExternalLink,
  Info,
} from 'lucide-react'
import { clsx } from 'clsx'

// Tab definitions
const tabs = [
  { id: 'llm', label: 'LLM Providers', icon: Brain },
  { id: 'secrets', label: 'Secrets Vault', icon: Key },
  { id: 'memory', label: 'Memory', icon: Database },
  { id: 'reasoning', label: 'Reasoning', icon: Sparkles },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'advanced', label: 'Advanced', icon: Zap },
]

// Secret key definitions with validation patterns
const secretDefinitions = [
  {
    key: 'ANTHROPIC_API_KEY',
    label: 'Anthropic API Key',
    provider: 'Anthropic',
    pattern: /^sk-ant-/,
    description: 'For Claude models (claude-3-opus, claude-3-sonnet, etc.)',
    docsUrl: 'https://console.anthropic.com/api-keys',
    required: true,
  },
  {
    key: 'OPENAI_API_KEY',
    label: 'OpenAI API Key',
    provider: 'OpenAI',
    pattern: /^sk-/,
    description: 'For GPT-4, GPT-3.5 and embedding models',
    docsUrl: 'https://platform.openai.com/api-keys',
    required: false,
  },
  {
    key: 'OPENROUTER_API_KEY',
    label: 'OpenRouter API Key',
    provider: 'OpenRouter',
    pattern: /^sk-or-/,
    description: 'Access 100+ models through single API',
    docsUrl: 'https://openrouter.ai/keys',
    required: false,
  },
  {
    key: 'GOOGLE_API_KEY',
    label: 'Google AI API Key',
    provider: 'Google',
    pattern: /^AIza/,
    description: 'For Gemini Pro/Ultra models',
    docsUrl: 'https://makersuite.google.com/app/apikey',
    required: false,
  },
  {
    key: 'GROQ_API_KEY',
    label: 'Groq API Key',
    provider: 'Groq',
    pattern: /^gsk_/,
    description: 'Ultra-fast inference with LPU',
    docsUrl: 'https://console.groq.com/keys',
    required: false,
  },
  {
    key: 'MISTRAL_API_KEY',
    label: 'Mistral API Key',
    provider: 'Mistral',
    pattern: /^[a-zA-Z0-9]+$/,
    description: 'For Mistral and Mixtral models',
    docsUrl: 'https://console.mistral.ai/api-keys/',
    required: false,
  },
  {
    key: 'TOGETHER_API_KEY',
    label: 'Together AI API Key',
    provider: 'Together',
    pattern: /^[a-f0-9]+$/,
    description: 'Access open source models',
    docsUrl: 'https://api.together.xyz/settings/api-keys',
    required: false,
  },
  {
    key: 'PERPLEXITY_API_KEY',
    label: 'Perplexity API Key',
    provider: 'Perplexity',
    pattern: /^pplx-/,
    description: 'Online LLM with web access',
    docsUrl: 'https://www.perplexity.ai/settings/api',
    required: false,
  },
  {
    key: 'HUGGINGFACE_TOKEN',
    label: 'HuggingFace Token',
    provider: 'HuggingFace',
    pattern: /^hf_/,
    description: 'For HuggingFace models and datasets',
    docsUrl: 'https://huggingface.co/settings/tokens',
    required: false,
  },
  {
    key: 'GITHUB_TOKEN',
    label: 'GitHub Token',
    provider: 'GitHub',
    pattern: /^gh[ps]_/,
    description: 'For GitHub API access and integrations',
    docsUrl: 'https://github.com/settings/tokens',
    required: false,
  },
]

export default function EnhancedSettings() {
  const [activeTab, setActiveTab] = useState('llm')
  const [settings, setSettings] = useState<any>({})
  const [secrets, setSecrets] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadSettings()
    loadSecrets()
  }, [])

  const loadSettings = async () => {
    try {
      const response = await fetch('/api/v1/settings')
      if (response.ok) {
        const data = await response.json()
        setSettings(data)
      }
    } catch (err) {
      console.error('Failed to load settings:', err)
      // Load defaults if API unavailable
      setSettings({
        llm: { provider: 'anthropic', model: 'claude-3-sonnet', temperature: 0.7, maxTokens: 4096 },
        memory: { enableEpisodic: true, enableSemantic: true, maxMemories: 1000 },
        reasoning: { enableCausal: true, thinkingDepth: 'deep' },
        security: { requireConfirmation: true, sandboxCode: true },
        appearance: { theme: 'dark', fontSize: 'medium' },
        advanced: { debugMode: false, autoSave: true },
      })
    } finally {
      setLoading(false)
    }
  }

  const loadSecrets = async () => {
    try {
      const response = await fetch('/api/v1/settings/keys')
      if (response.ok) {
        const data = await response.json()
        // Convert API response to simple status map
        const statusMap: Record<string, string> = {}
        for (const key of (data.keys || [])) {
          statusMap[key.provider.toUpperCase() + '_API_KEY'] = key.configured ? 'configured' : 'not-configured'
        }
        setSecrets(statusMap)
      }
    } catch (err) {
      // Load from localStorage as fallback
      const cached = localStorage.getItem('bael_secrets_status')
      if (cached) {
        setSecrets(JSON.parse(cached))
      }
    }
  }

  const updateSettings = (updates: any) => {
    setSettings((prev: any) => ({ ...prev, ...updates }))
    setHasChanges(true)
  }

  const saveSettings = async () => {
    setSaving(true)
    try {
      const response = await fetch('/api/v1/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })
      if (response.ok) {
        setHasChanges(false)
        showToast.success('Settings saved successfully')
      } else {
        showToast.error('Failed to save settings to server')
      }
    } catch (err) {
      console.error('Failed to save settings:', err)
      // Save to localStorage as fallback
      localStorage.setItem('bael_settings', JSON.stringify(settings))
      setHasChanges(false)
      showToast.warning('Settings saved locally (server unavailable)')
    } finally {
      setSaving(false)
    }
  }

  const filteredTabs = searchQuery
    ? tabs.filter(t => t.label.toLowerCase().includes(searchQuery.toLowerCase()))
    : tabs

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 p-6 border-b border-bael-border">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-bael-primary to-bael-secondary rounded-xl">
              <Settings className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-bael-text">Settings</h1>
              <p className="text-sm text-bael-muted">Configure BAEL to your preferences</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {hasChanges && (
              <motion.span
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-sm text-bael-warning"
              >
                Unsaved changes
              </motion.span>
            )}
            <button
              onClick={saveSettings}
              disabled={!hasChanges || saving}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all',
                hasChanges
                  ? 'bg-bael-primary text-white hover:bg-bael-primary/90'
                  : 'bg-bael-surface text-bael-muted cursor-not-allowed'
              )}
            >
              {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Changes
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-bael-muted" />
          <input
            type="text"
            placeholder="Search settings..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-bael-surface border border-bael-border rounded-lg text-bael-text placeholder-bael-muted focus:outline-none focus:border-bael-primary"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Tab Navigation */}
        <div className="w-64 flex-shrink-0 border-r border-bael-border p-4 space-y-1 overflow-y-auto">
          {filteredTabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left',
                  isActive
                    ? 'bg-bael-primary/20 text-bael-primary border border-bael-primary/30'
                    : 'text-bael-muted hover:text-bael-text hover:bg-bael-surface'
                )}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{tab.label}</span>
              </button>
            )
          })}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.15 }}
            >
              {activeTab === 'llm' && <LLMSettings settings={settings} updateSettings={updateSettings} />}
              {activeTab === 'secrets' && <SecretsVault secrets={secrets} setSecrets={setSecrets} />}
              {activeTab === 'memory' && <MemorySettings settings={settings} updateSettings={updateSettings} />}
              {activeTab === 'reasoning' && <ReasoningSettings settings={settings} updateSettings={updateSettings} />}
              {activeTab === 'security' && <SecuritySettings settings={settings} updateSettings={updateSettings} />}
              {activeTab === 'appearance' && <AppearanceSettings settings={settings} updateSettings={updateSettings} />}
              {activeTab === 'advanced' && <AdvancedSettings settings={settings} updateSettings={updateSettings} />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

// ============================================
// LLM Settings
// ============================================

function LLMSettings({ settings, updateSettings }: { settings: any; updateSettings: any }) {
  const providers = [
    { id: 'anthropic', name: 'Anthropic', models: ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307', 'claude-3-5-sonnet-20241022'], icon: '🧠' },
    { id: 'openai', name: 'OpenAI', models: ['gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo', 'gpt-4o', 'gpt-4o-mini'], icon: '🤖' },
    { id: 'openrouter', name: 'OpenRouter', models: ['anthropic/claude-3-opus', 'google/gemini-pro', 'meta-llama/llama-3.1-405b'], icon: '🌐' },
    { id: 'groq', name: 'Groq', models: ['llama-3.1-70b-versatile', 'mixtral-8x7b-32768', 'llama3-8b-8192'], icon: '⚡' },
    { id: 'google', name: 'Google', models: ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-ultra'], icon: '✨' },
    { id: 'local', name: 'Local (Ollama)', models: ['llama3.2', 'mistral', 'codellama', 'phi3'], icon: '💻' },
  ]

  return (
    <div className="space-y-6 max-w-3xl">
      <SectionHeader
        title="LLM Providers"
        description="Configure your AI providers and model preferences"
        icon={Brain}
      />

      {/* Primary Model Selection */}
      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Primary Model</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-bael-muted mb-2">Provider</label>
            <select
              value={settings.llm?.provider ?? 'anthropic'}
              onChange={(e) => updateSettings({ llm: { ...settings.llm, provider: e.target.value } })}
              className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text focus:outline-none focus:border-bael-primary"
            >
              {providers.map(p => (
                <option key={p.id} value={p.id}>{p.icon} {p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-bael-muted mb-2">Model</label>
            <select
              value={settings.llm?.model ?? 'claude-3-opus-20240229'}
              onChange={(e) => updateSettings({ llm: { ...settings.llm, model: e.target.value } })}
              className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text focus:outline-none focus:border-bael-primary"
            >
              {providers.find(p => p.id === (settings.llm?.provider ?? 'anthropic'))?.models.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Model Parameters */}
      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Model Parameters</h4>
        <div className="space-y-4">
          <SliderSetting
            label="Temperature"
            value={settings.llm?.temperature ?? 0.7}
            min={0}
            max={2}
            step={0.1}
            onChange={(v) => updateSettings({ llm: { ...settings.llm, temperature: v } })}
            description="Controls randomness. Lower = more focused, higher = more creative"
          />
          <SliderSetting
            label="Max Tokens"
            value={settings.llm?.maxTokens ?? 4096}
            min={256}
            max={32768}
            step={256}
            onChange={(v) => updateSettings({ llm: { ...settings.llm, maxTokens: v } })}
            description="Maximum response length"
          />
          <SliderSetting
            label="Top P"
            value={settings.llm?.topP ?? 1}
            min={0}
            max={1}
            step={0.05}
            onChange={(v) => updateSettings({ llm: { ...settings.llm, topP: v } })}
            description="Nucleus sampling threshold"
          />
          <SliderSetting
            label="Presence Penalty"
            value={settings.llm?.presencePenalty ?? 0}
            min={-2}
            max={2}
            step={0.1}
            onChange={(v) => updateSettings({ llm: { ...settings.llm, presencePenalty: v } })}
            description="Penalize tokens based on presence in text"
          />
        </div>
      </div>

      {/* Provider Status */}
      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Provider Status</h4>
        <div className="grid grid-cols-2 gap-3">
          {providers.map(provider => (
            <ProviderStatusCard key={provider.id} provider={provider} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ============================================
// Secrets Vault
// ============================================

function SecretsVault({ secrets, setSecrets }: { secrets: Record<string, string>; setSecrets: any }) {
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({})
  const [editing, setEditing] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [saving, setSaving] = useState<string | null>(null)
  const [testingKey, setTestingKey] = useState<string | null>(null)

  const toggleShow = (key: string) => {
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const startEdit = (key: string, currentValue: string) => {
    setEditing(key)
    setEditValue(currentValue || '')
  }

  const cancelEdit = () => {
    setEditing(null)
    setEditValue('')
  }

  const saveSecret = async (key: string) => {
    setSaving(key)
    try {
      // Extract provider name from key (e.g., ANTHROPIC_API_KEY -> anthropic)
      const provider = key.replace('_API_KEY', '').replace('_TOKEN', '').toLowerCase()
      // Save to API
      const response = await fetch('/api/v1/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, key: editValue }),
      })

      if (response.ok) {
        setSecrets((prev: Record<string, string>) => ({
          ...prev,
          [key]: editValue ? 'configured' : 'not-configured',
        }))
        // Also save masked version to localStorage for status
        const maskedValue = editValue ? `${editValue.substring(0, 8)}...${editValue.substring(editValue.length - 4)}` : ''
        const statusData = JSON.parse(localStorage.getItem('bael_secrets_status') || '{}')
        statusData[key] = { status: editValue ? 'configured' : 'not-configured', masked: maskedValue }
        localStorage.setItem('bael_secrets_status', JSON.stringify(statusData))
      }
    } catch (err) {
      // Fallback: save to localStorage
      const existingSecrets = JSON.parse(localStorage.getItem('bael_secrets') || '{}')
      existingSecrets[key] = editValue
      localStorage.setItem('bael_secrets', JSON.stringify(existingSecrets))

      setSecrets((prev: Record<string, string>) => ({
        ...prev,
        [key]: editValue ? 'configured' : 'not-configured',
      }))
    } finally {
      setSaving(null)
      setEditing(null)
      setEditValue('')
    }
  }

  const testSecret = async (key: string) => {
    setTestingKey(key)
    try {
      const provider = key.replace('_API_KEY', '').replace('_TOKEN', '').toLowerCase()
      const response = await fetch(`/api/v1/settings/keys/validate/${provider}`, {
        method: 'POST',
      })
      const data = await response.json()
      alert(data.valid ? '✅ API key is valid!' : `❌ Invalid: ${data.error}`)
    } catch (err) {
      alert('❌ Could not test key: API not available')
    } finally {
      setTestingKey(null)
    }
  }

  const getSecretStatus = (key: string) => {
    const status = secrets[key]
    if (status === 'configured' || (typeof status === 'object' && (status as any).status === 'configured')) {
      return 'configured'
    }
    // Check localStorage as fallback
    const localSecrets = JSON.parse(localStorage.getItem('bael_secrets') || '{}')
    if (localSecrets[key]) return 'configured'
    // Check environment detection
    const envStatus = JSON.parse(localStorage.getItem('bael_env_detection') || '{}')
    if (envStatus[key]) return 'env-detected'
    return 'not-configured'
  }

  const validateKey = (key: string, value: string) => {
    const def = secretDefinitions.find(d => d.key === key)
    if (!def || !value) return { valid: false, message: 'No value provided' }
    if (def.pattern && !def.pattern.test(value)) {
      return { valid: false, message: `Invalid format. Expected pattern: ${def.pattern.toString()}` }
    }
    return { valid: true, message: 'Format looks correct' }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <SectionHeader
        title="Secrets Vault"
        description="Securely manage your API keys and credentials"
        icon={Key}
      />

      {/* Quick Status */}
      <div className="grid grid-cols-4 gap-4">
        <StatusCard
          label="Configured"
          value={secretDefinitions.filter(d => getSecretStatus(d.key) === 'configured').length}
          total={secretDefinitions.length}
          color="success"
        />
        <StatusCard
          label="From Environment"
          value={secretDefinitions.filter(d => getSecretStatus(d.key) === 'env-detected').length}
          total={secretDefinitions.length}
          color="info"
        />
        <StatusCard
          label="Required Missing"
          value={secretDefinitions.filter(d => d.required && getSecretStatus(d.key) === 'not-configured').length}
          total={secretDefinitions.filter(d => d.required).length}
          color="warning"
        />
        <StatusCard
          label="Optional"
          value={secretDefinitions.filter(d => !d.required && getSecretStatus(d.key) !== 'configured').length}
          total={secretDefinitions.filter(d => !d.required).length}
          color="muted"
        />
      </div>

      {/* Secret Entries */}
      <div className="space-y-3">
        {secretDefinitions.map((def) => {
          const status = getSecretStatus(def.key)
          const isEditing = editing === def.key
          const validation = isEditing ? validateKey(def.key, editValue) : null

          return (
            <motion.div
              key={def.key}
              layout
              className={clsx(
                'p-4 bg-bael-surface border rounded-xl transition-colors',
                status === 'configured' ? 'border-bael-success/30' :
                status === 'env-detected' ? 'border-bael-info/30' :
                def.required ? 'border-bael-warning/30' : 'border-bael-border'
              )}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-bael-text">{def.label}</span>
                    {def.required && (
                      <span className="px-1.5 py-0.5 text-xs bg-bael-warning/20 text-bael-warning rounded">
                        Required
                      </span>
                    )}
                    <StatusBadge status={status} />
                  </div>
                  <p className="text-xs text-bael-muted">{def.description}</p>
                  <code className="text-xs text-bael-muted/50 font-mono mt-1 block">{def.key}</code>
                </div>

                <div className="flex items-center gap-2">
                  {!isEditing && (
                    <>
                      {status === 'configured' && (
                        <>
                          <button
                            onClick={() => testSecret(def.key)}
                            disabled={testingKey === def.key}
                            className="p-2 text-bael-muted hover:text-bael-text hover:bg-bael-bg rounded-lg transition-colors"
                            title="Test API key"
                          >
                            {testingKey === def.key ? (
                              <RefreshCw className="w-4 h-4 animate-spin" />
                            ) : (
                              <CheckCircle className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            onClick={() => toggleShow(def.key)}
                            className="p-2 text-bael-muted hover:text-bael-text hover:bg-bael-bg rounded-lg transition-colors"
                            title={showSecrets[def.key] ? 'Hide' : 'Show'}
                          >
                            {showSecrets[def.key] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => startEdit(def.key, '')}
                        className="px-3 py-1.5 text-sm bg-bael-primary/20 text-bael-primary hover:bg-bael-primary/30 rounded-lg transition-colors"
                      >
                        {status === 'configured' ? 'Update' : 'Configure'}
                      </button>
                      <a
                        href={def.docsUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 text-bael-muted hover:text-bael-text hover:bg-bael-bg rounded-lg transition-colors"
                        title="Get API key"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    </>
                  )}
                </div>
              </div>

              {/* Edit Mode */}
              <AnimatePresence>
                {isEditing && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-4 pt-4 border-t border-bael-border">
                      <div className="flex gap-2 mb-2">
                        <div className="flex-1 relative">
                          <input
                            type={showSecrets[def.key] ? 'text' : 'password'}
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            placeholder={`Enter ${def.label}...`}
                            className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text font-mono text-sm focus:outline-none focus:border-bael-primary pr-20"
                            autoFocus
                          />
                          <button
                            onClick={() => toggleShow(def.key)}
                            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-bael-muted hover:text-bael-text"
                          >
                            {showSecrets[def.key] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                        <button
                          onClick={() => saveSecret(def.key)}
                          disabled={saving === def.key || !editValue}
                          className="px-4 py-2 bg-bael-success text-white rounded-lg hover:bg-bael-success/90 disabled:opacity-50 transition-colors"
                        >
                          {saving === def.key ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="px-4 py-2 bg-bael-surface text-bael-muted rounded-lg hover:bg-bael-bg transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                      {validation && (
                        <p className={clsx(
                          'text-xs mt-1',
                          validation.valid ? 'text-bael-success' : 'text-bael-warning'
                        )}>
                          {validation.valid ? '✓' : '⚠'} {validation.message}
                        </p>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>

      {/* Import/Export */}
      <div className="p-4 bg-bael-surface/50 border border-bael-border rounded-xl">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-medium text-bael-text">Bulk Actions</h4>
            <p className="text-xs text-bael-muted mt-1">Import from .env file or export current configuration</p>
          </div>
          <div className="flex gap-2">
            <button className="flex items-center gap-2 px-3 py-2 text-sm bg-bael-bg border border-bael-border rounded-lg text-bael-muted hover:text-bael-text transition-colors">
              <Upload className="w-4 h-4" />
              Import .env
            </button>
            <button className="flex items-center gap-2 px-3 py-2 text-sm bg-bael-bg border border-bael-border rounded-lg text-bael-muted hover:text-bael-text transition-colors">
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================
// Memory Settings
// ============================================

function MemorySettings({ settings, updateSettings }: { settings: any; updateSettings: any }) {
  return (
    <div className="space-y-6 max-w-3xl">
      <SectionHeader
        title="Memory Configuration"
        description="Configure how BAEL remembers and learns"
        icon={Database}
      />

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Memory System</h4>
        <div className="space-y-4">
          <ToggleSetting
            label="Persistent Memory"
            description="Remember context across sessions"
            checked={settings.memory?.persistent ?? true}
            onChange={(v) => updateSettings({ memory: { ...settings.memory, persistent: v } })}
          />
          <ToggleSetting
            label="Semantic Memory"
            description="Use embeddings for semantic retrieval"
            checked={settings.memory?.semantic ?? true}
            onChange={(v) => updateSettings({ memory: { ...settings.memory, semantic: v } })}
          />
          <ToggleSetting
            label="Episodic Memory"
            description="Remember specific interactions and events"
            checked={settings.memory?.episodic ?? true}
            onChange={(v) => updateSettings({ memory: { ...settings.memory, episodic: v } })}
          />
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Memory Limits</h4>
        <div className="space-y-4">
          <SliderSetting
            label="Short-term Memory Tokens"
            value={settings.memory?.shortTermTokens ?? 8192}
            min={1024}
            max={32768}
            step={1024}
            onChange={(v) => updateSettings({ memory: { ...settings.memory, shortTermTokens: v } })}
            description="Maximum tokens for recent context"
          />
          <SliderSetting
            label="Long-term Memory Items"
            value={settings.memory?.longTermItems ?? 1000}
            min={100}
            max={10000}
            step={100}
            onChange={(v) => updateSettings({ memory: { ...settings.memory, longTermItems: v } })}
            description="Maximum stored memory items"
          />
          <SliderSetting
            label="Consolidation Interval"
            value={settings.memory?.consolidationInterval ?? 10}
            min={1}
            max={100}
            step={1}
            onChange={(v) => updateSettings({ memory: { ...settings.memory, consolidationInterval: v } })}
            description="Messages before memory consolidation"
          />
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Vector Store</h4>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-bael-muted mb-2">Backend</label>
            <select
              value={settings.memory?.vectorStore ?? 'chromadb'}
              onChange={(e) => updateSettings({ memory: { ...settings.memory, vectorStore: e.target.value } })}
              className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text"
            >
              <option value="chromadb">ChromaDB (Local)</option>
              <option value="pinecone">Pinecone (Cloud)</option>
              <option value="weaviate">Weaviate</option>
              <option value="qdrant">Qdrant</option>
              <option value="milvus">Milvus</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-bael-muted mb-2">Embedding Model</label>
            <select
              value={settings.memory?.embeddingModel ?? 'text-embedding-3-small'}
              onChange={(e) => updateSettings({ memory: { ...settings.memory, embeddingModel: e.target.value } })}
              className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text"
            >
              <option value="text-embedding-3-small">text-embedding-3-small (OpenAI)</option>
              <option value="text-embedding-3-large">text-embedding-3-large (OpenAI)</option>
              <option value="voyage-2">voyage-2 (Voyage AI)</option>
              <option value="nomic-embed-text">nomic-embed-text (Local)</option>
            </select>
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-bael-surface border border-bael-border rounded-xl text-bael-muted hover:text-bael-text transition-colors">
          <RefreshCw className="w-4 h-4" />
          Rebuild Index
        </button>
        <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-bael-surface border border-bael-warning/50 rounded-xl text-bael-warning hover:bg-bael-warning/10 transition-colors">
          <Trash2 className="w-4 h-4" />
          Clear Memory
        </button>
      </div>
    </div>
  )
}

// ============================================
// Reasoning Settings
// ============================================

function ReasoningSettings({ settings, updateSettings }: { settings: any; updateSettings: any }) {
  const reasoningModes = [
    { id: 'chain', name: 'Chain of Thought', description: 'Linear step-by-step reasoning', icon: '🔗' },
    { id: 'tree', name: 'Tree of Thought', description: 'Explore multiple reasoning branches', icon: '🌳' },
    { id: 'graph', name: 'Graph of Thought', description: 'Full graph reasoning with backtracking', icon: '🕸️' },
    { id: 'meta', name: 'Meta-Cognitive', description: 'Self-aware reasoning about reasoning', icon: '🧠' },
  ]

  return (
    <div className="space-y-6 max-w-3xl">
      <SectionHeader
        title="Reasoning Configuration"
        description="Configure BAEL's cognitive and reasoning capabilities"
        icon={Sparkles}
      />

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Reasoning Mode</h4>
        <div className="grid grid-cols-2 gap-3">
          {reasoningModes.map((mode) => (
            <button
              key={mode.id}
              onClick={() => updateSettings({ reasoning: { ...settings.reasoning, mode: mode.id } })}
              className={clsx(
                'p-4 rounded-xl border text-left transition-all',
                settings.reasoning?.mode === mode.id
                  ? 'bg-bael-primary/20 border-bael-primary/50'
                  : 'bg-bael-bg border-bael-border hover:border-bael-muted'
              )}
            >
              <span className="text-2xl mb-2 block">{mode.icon}</span>
              <span className="font-medium text-bael-text">{mode.name}</span>
              <p className="text-xs text-bael-muted mt-1">{mode.description}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Reasoning Parameters</h4>
        <div className="space-y-4">
          <SliderSetting
            label="Thinking Depth"
            value={settings.reasoning?.depth ?? 3}
            min={1}
            max={10}
            step={1}
            onChange={(v) => updateSettings({ reasoning: { ...settings.reasoning, depth: v } })}
            description="How deep to explore reasoning paths"
          />
          <SliderSetting
            label="Branch Factor"
            value={settings.reasoning?.branchFactor ?? 3}
            min={1}
            max={10}
            step={1}
            onChange={(v) => updateSettings({ reasoning: { ...settings.reasoning, branchFactor: v } })}
            description="Number of alternatives to consider"
          />
          <ToggleSetting
            label="Show Thinking Process"
            description="Display intermediate reasoning steps"
            checked={settings.reasoning?.showThinking ?? false}
            onChange={(v) => updateSettings({ reasoning: { ...settings.reasoning, showThinking: v } })}
          />
          <ToggleSetting
            label="Self-Reflection"
            description="Enable metacognitive reflection loops"
            checked={settings.reasoning?.selfReflection ?? true}
            onChange={(v) => updateSettings({ reasoning: { ...settings.reasoning, selfReflection: v } })}
          />
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Council Configuration</h4>
        <div className="space-y-4">
          <ToggleSetting
            label="Multi-Agent Council"
            description="Use multiple specialized agents for complex tasks"
            checked={settings.reasoning?.councilEnabled ?? true}
            onChange={(v) => updateSettings({ reasoning: { ...settings.reasoning, councilEnabled: v } })}
          />
          <SliderSetting
            label="Council Size"
            value={settings.reasoning?.councilSize ?? 5}
            min={2}
            max={12}
            step={1}
            onChange={(v) => updateSettings({ reasoning: { ...settings.reasoning, councilSize: v } })}
            description="Number of agents in the council"
          />
          <SliderSetting
            label="Consensus Threshold"
            value={(settings.reasoning?.consensusThreshold ?? 0.7) * 100}
            min={50}
            max={100}
            step={5}
            onChange={(v) => updateSettings({ reasoning: { ...settings.reasoning, consensusThreshold: v / 100 } })}
            description="Agreement required for council decisions (%)"
          />
        </div>
      </div>
    </div>
  )
}

// ============================================
// Security Settings
// ============================================

function SecuritySettings({ settings, updateSettings }: { settings: any; updateSettings: any }) {
  return (
    <div className="space-y-6 max-w-3xl">
      <SectionHeader
        title="Security & Privacy"
        description="Control access and protect your data"
        icon={Shield}
      />

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Code Execution</h4>
        <div className="space-y-4">
          <ToggleSetting
            label="Sandbox Mode"
            description="Run code in isolated Docker containers"
            checked={settings.security?.sandboxMode ?? true}
            onChange={(v) => updateSettings({ security: { ...settings.security, sandboxMode: v } })}
          />
          <ToggleSetting
            label="Require Approval"
            description="Ask before executing code or commands"
            checked={settings.security?.requireApproval ?? true}
            onChange={(v) => updateSettings({ security: { ...settings.security, requireApproval: v } })}
          />
          <ToggleSetting
            label="Network Access"
            description="Allow code to access the network"
            checked={settings.security?.networkAccess ?? false}
            onChange={(v) => updateSettings({ security: { ...settings.security, networkAccess: v } })}
          />
          <ToggleSetting
            label="File System Access"
            description="Allow code to read/write files"
            checked={settings.security?.fileSystemAccess ?? true}
            onChange={(v) => updateSettings({ security: { ...settings.security, fileSystemAccess: v } })}
          />
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Data Privacy</h4>
        <div className="space-y-4">
          <ToggleSetting
            label="Local Processing Only"
            description="Never send data to external services"
            checked={settings.security?.localOnly ?? false}
            onChange={(v) => updateSettings({ security: { ...settings.security, localOnly: v } })}
          />
          <ToggleSetting
            label="Encrypt Memory"
            description="Encrypt stored memories at rest"
            checked={settings.security?.encryptMemory ?? true}
            onChange={(v) => updateSettings({ security: { ...settings.security, encryptMemory: v } })}
          />
          <ToggleSetting
            label="Audit Logging"
            description="Log all actions for review"
            checked={settings.security?.auditLog ?? true}
            onChange={(v) => updateSettings({ security: { ...settings.security, auditLog: v } })}
          />
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Path Restrictions</h4>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-bael-muted mb-2">Allowed Paths (one per line)</label>
            <textarea
              value={settings.security?.allowedPaths?.join('\n') ?? '/tmp\n/home\n/Users'}
              onChange={(e) => updateSettings({
                security: {
                  ...settings.security,
                  allowedPaths: e.target.value.split('\n').filter(Boolean)
                }
              })}
              rows={4}
              className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text font-mono text-sm focus:outline-none focus:border-bael-primary"
            />
          </div>
          <div>
            <label className="block text-xs text-bael-muted mb-2">Blocked Commands (comma-separated)</label>
            <input
              type="text"
              value={settings.security?.blockedCommands?.join(', ') ?? 'rm -rf, sudo, shutdown'}
              onChange={(e) => updateSettings({
                security: {
                  ...settings.security,
                  blockedCommands: e.target.value.split(',').map((s: string) => s.trim()).filter(Boolean)
                }
              })}
              className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text font-mono text-sm focus:outline-none focus:border-bael-primary"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================
// Appearance Settings
// ============================================

function AppearanceSettings({ settings, updateSettings }: { settings: any; updateSettings: any }) {
  const themes = [
    { id: 'dark', name: 'Dark', preview: 'bg-gray-900' },
    { id: 'darker', name: 'Darker', preview: 'bg-black' },
    { id: 'light', name: 'Light', preview: 'bg-white' },
    { id: 'system', name: 'System', preview: 'bg-gradient-to-r from-gray-900 to-white' },
  ]

  const accentColors = [
    { id: 'indigo', color: '#6366f1', name: 'Indigo' },
    { id: 'purple', color: '#8b5cf6', name: 'Purple' },
    { id: 'rose', color: '#f43f5e', name: 'Rose' },
    { id: 'emerald', color: '#10b981', name: 'Emerald' },
    { id: 'amber', color: '#f59e0b', name: 'Amber' },
    { id: 'cyan', color: '#06b6d4', name: 'Cyan' },
  ]

  return (
    <div className="space-y-6 max-w-3xl">
      <SectionHeader
        title="Appearance"
        description="Customize the look and feel of BAEL"
        icon={Palette}
      />

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Theme</h4>
        <div className="grid grid-cols-4 gap-3">
          {themes.map((theme) => (
            <button
              key={theme.id}
              onClick={() => updateSettings({ ui: { ...settings.ui, theme: theme.id } })}
              className={clsx(
                'p-4 rounded-xl border text-center transition-all',
                settings.ui?.theme === theme.id
                  ? 'border-bael-primary ring-2 ring-bael-primary/30'
                  : 'border-bael-border hover:border-bael-muted'
              )}
            >
              <div className={clsx('w-full h-8 rounded-lg mb-2', theme.preview)} />
              <span className="text-sm text-bael-text">{theme.name}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Accent Color</h4>
        <div className="flex gap-3 flex-wrap">
          {accentColors.map((color) => (
            <button
              key={color.id}
              onClick={() => updateSettings({ ui: { ...settings.ui, accentColor: color.color } })}
              className={clsx(
                'w-12 h-12 rounded-xl transition-transform hover:scale-110',
                settings.ui?.accentColor === color.color && 'ring-2 ring-offset-2 ring-offset-bael-bg ring-white'
              )}
              style={{ backgroundColor: color.color }}
              title={color.name}
            />
          ))}
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Layout & Display</h4>
        <div className="space-y-4">
          <ToggleSetting
            label="Animations"
            description="Enable smooth transitions and animations"
            checked={settings.ui?.animations ?? true}
            onChange={(v) => updateSettings({ ui: { ...settings.ui, animations: v } })}
          />
          <ToggleSetting
            label="Compact Mode"
            description="Reduce padding and spacing throughout the UI"
            checked={settings.ui?.compact ?? false}
            onChange={(v) => updateSettings({ ui: { ...settings.ui, compact: v } })}
          />
          <ToggleSetting
            label="Show Line Numbers"
            description="Display line numbers in code blocks"
            checked={settings.ui?.lineNumbers ?? true}
            onChange={(v) => updateSettings({ ui: { ...settings.ui, lineNumbers: v } })}
          />
          <ToggleSetting
            label="Word Wrap"
            description="Wrap long lines in code blocks"
            checked={settings.ui?.wordWrap ?? false}
            onChange={(v) => updateSettings({ ui: { ...settings.ui, wordWrap: v } })}
          />
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Typography</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-bael-muted mb-2">Font Size</label>
            <select
              value={settings.ui?.fontSize ?? 'medium'}
              onChange={(e) => updateSettings({ ui: { ...settings.ui, fontSize: e.target.value } })}
              className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text"
            >
              <option value="small">Small</option>
              <option value="medium">Medium</option>
              <option value="large">Large</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-bael-muted mb-2">Code Font</label>
            <select
              value={settings.ui?.codeFont ?? 'fira-code'}
              onChange={(e) => updateSettings({ ui: { ...settings.ui, codeFont: e.target.value } })}
              className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text"
            >
              <option value="fira-code">Fira Code</option>
              <option value="jetbrains-mono">JetBrains Mono</option>
              <option value="source-code-pro">Source Code Pro</option>
              <option value="monospace">System Monospace</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================
// Advanced Settings
// ============================================

function AdvancedSettings({ settings, updateSettings }: { settings: any; updateSettings: any }) {
  return (
    <div className="space-y-6 max-w-3xl">
      <SectionHeader
        title="Advanced Settings"
        description="Expert configuration options for power users"
        icon={Zap}
      />

      <div className="p-4 bg-bael-warning/10 border border-bael-warning/30 rounded-xl flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-bael-warning flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-bael-warning">Warning</p>
          <p className="text-xs text-bael-warning/80">
            These settings are for advanced users. Incorrect configuration may cause issues or unexpected behavior.
          </p>
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Server Configuration</h4>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-bael-muted mb-2">API Server Port</label>
              <input
                type="number"
                value={settings.server?.port ?? 8000}
                onChange={(e) => updateSettings({ server: { ...settings.server, port: parseInt(e.target.value) } })}
                className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-bael-muted mb-2">WebSocket Port</label>
              <input
                type="number"
                value={settings.server?.wsPort ?? 8001}
                onChange={(e) => updateSettings({ server: { ...settings.server, wsPort: parseInt(e.target.value) } })}
                className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text font-mono"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-bael-muted mb-2">Log Level</label>
            <select
              value={settings.server?.logLevel ?? 'info'}
              onChange={(e) => updateSettings({ server: { ...settings.server, logLevel: e.target.value } })}
              className="w-full px-3 py-2 bg-bael-bg border border-bael-border rounded-lg text-bael-text"
            >
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Performance</h4>
        <div className="space-y-4">
          <SliderSetting
            label="Concurrent Agents"
            value={settings.performance?.concurrentAgents ?? 4}
            min={1}
            max={16}
            step={1}
            onChange={(v) => updateSettings({ performance: { ...settings.performance, concurrentAgents: v } })}
            description="Maximum number of agents running simultaneously"
          />
          <SliderSetting
            label="Request Timeout (seconds)"
            value={settings.performance?.timeout ?? 120}
            min={30}
            max={600}
            step={30}
            onChange={(v) => updateSettings({ performance: { ...settings.performance, timeout: v } })}
            description="Maximum time for API requests"
          />
          <SliderSetting
            label="Batch Size"
            value={settings.performance?.batchSize ?? 10}
            min={1}
            max={100}
            step={1}
            onChange={(v) => updateSettings({ performance: { ...settings.performance, batchSize: v } })}
            description="Items to process in parallel batches"
          />
          <ToggleSetting
            label="GPU Acceleration"
            description="Use GPU for local model inference"
            checked={settings.performance?.gpuEnabled ?? false}
            onChange={(v) => updateSettings({ performance: { ...settings.performance, gpuEnabled: v } })}
          />
        </div>
      </div>

      <div className="p-6 bg-bael-surface border border-bael-border rounded-xl">
        <h4 className="text-sm font-medium text-bael-text mb-4">Debug Options</h4>
        <div className="space-y-4">
          <ToggleSetting
            label="Developer Mode"
            description="Enable additional debugging features"
            checked={settings.debug?.devMode ?? false}
            onChange={(v) => updateSettings({ debug: { ...settings.debug, devMode: v } })}
          />
          <ToggleSetting
            label="Verbose Logging"
            description="Log detailed information for debugging"
            checked={settings.debug?.verbose ?? false}
            onChange={(v) => updateSettings({ debug: { ...settings.debug, verbose: v } })}
          />
          <ToggleSetting
            label="API Request Logging"
            description="Log all API requests and responses"
            checked={settings.debug?.logRequests ?? false}
            onChange={(v) => updateSettings({ debug: { ...settings.debug, logRequests: v } })}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <button className="flex items-center justify-center gap-2 px-4 py-3 bg-bael-surface border border-bael-border rounded-xl text-bael-muted hover:text-bael-text transition-colors">
          <Upload className="w-4 h-4" />
          Import Config
        </button>
        <button className="flex items-center justify-center gap-2 px-4 py-3 bg-bael-surface border border-bael-border rounded-xl text-bael-muted hover:text-bael-text transition-colors">
          <Download className="w-4 h-4" />
          Export Config
        </button>
        <button className="flex items-center justify-center gap-2 px-4 py-3 bg-bael-surface border border-bael-error/50 rounded-xl text-bael-error hover:bg-bael-error/10 transition-colors">
          <RefreshCw className="w-4 h-4" />
          Reset All
        </button>
      </div>
    </div>
  )
}

// ============================================
// Helper Components
// ============================================

function SectionHeader({ title, description, icon: Icon }: { title: string; description: string; icon: any }) {
  return (
    <div className="flex items-start gap-3 mb-6">
      <div className="p-2 bg-bael-primary/20 rounded-lg">
        <Icon className="w-5 h-5 text-bael-primary" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-bael-text">{title}</h3>
        <p className="text-sm text-bael-muted">{description}</p>
      </div>
    </div>
  )
}

function ToggleSetting({
  label,
  description,
  checked,
  onChange,
}: {
  label: string
  description: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between p-3 bg-bael-bg rounded-lg">
      <div>
        <span className="text-sm font-medium text-bael-text">{label}</span>
        <p className="text-xs text-bael-muted mt-0.5">{description}</p>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={clsx(
          'w-10 h-5 rounded-full transition-colors relative flex-shrink-0',
          checked ? 'bg-bael-primary' : 'bg-bael-border'
        )}
      >
        <div
          className={clsx(
            'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform',
            checked ? 'left-5' : 'left-0.5'
          )}
        />
      </button>
    </div>
  )
}

function SliderSetting({
  label,
  value,
  min,
  max,
  step,
  onChange,
  description,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
  description: string
}) {
  return (
    <div className="p-3 bg-bael-bg rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-bael-text">{label}</span>
        <span className="text-sm font-mono text-bael-primary">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1.5 bg-bael-border rounded-full appearance-none cursor-pointer accent-bael-primary"
      />
      <p className="text-xs text-bael-muted mt-2">{description}</p>
    </div>
  )
}

function StatusCard({
  label,
  value,
  total,
  color,
}: {
  label: string
  value: number
  total: number
  color: 'success' | 'info' | 'warning' | 'muted'
}) {
  const colorClasses = {
    success: 'text-bael-success',
    info: 'text-bael-info',
    warning: 'text-bael-warning',
    muted: 'text-bael-muted',
  }

  return (
    <div className="p-4 bg-bael-surface border border-bael-border rounded-xl text-center">
      <div className={clsx('text-2xl font-bold', colorClasses[color])}>{value}</div>
      <div className="text-xs text-bael-muted">
        {label} / {total}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: 'configured' | 'env-detected' | 'not-configured' }) {
  const config = {
    configured: { label: 'Configured', color: 'bg-bael-success/20 text-bael-success' },
    'env-detected': { label: 'From ENV', color: 'bg-bael-info/20 text-bael-info' },
    'not-configured': { label: 'Not Set', color: 'bg-bael-muted/20 text-bael-muted' },
  }
  const { label, color } = config[status]
  return <span className={clsx('px-2 py-0.5 text-xs rounded-full', color)}>{label}</span>
}

function ProviderStatusCard({ provider }: { provider: { id: string; name: string; icon: string } }) {
  const [status, setStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')

  useEffect(() => {
    // Simulate checking provider status
    const timer = setTimeout(() => {
      const secrets = JSON.parse(localStorage.getItem('bael_secrets') || '{}')
      const keyMap: Record<string, string> = {
        anthropic: 'ANTHROPIC_API_KEY',
        openai: 'OPENAI_API_KEY',
        openrouter: 'OPENROUTER_API_KEY',
        groq: 'GROQ_API_KEY',
        google: 'GOOGLE_API_KEY',
        local: 'local',
      }
      const key = keyMap[provider.id]
      setStatus(key === 'local' || secrets[key] ? 'connected' : 'disconnected')
    }, 500)
    return () => clearTimeout(timer)
  }, [provider.id])

  return (
    <div
      className={clsx(
        'flex items-center justify-between p-3 rounded-lg border',
        status === 'connected' ? 'bg-bael-success/5 border-bael-success/30' : 'bg-bael-bg border-bael-border'
      )}
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">{provider.icon}</span>
        <span className="text-sm text-bael-text">{provider.name}</span>
      </div>
      {status === 'checking' ? (
        <RefreshCw className="w-4 h-4 text-bael-muted animate-spin" />
      ) : status === 'connected' ? (
        <CheckCircle className="w-4 h-4 text-bael-success" />
      ) : (
        <AlertCircle className="w-4 h-4 text-bael-muted" />
      )}
    </div>
  )
}
