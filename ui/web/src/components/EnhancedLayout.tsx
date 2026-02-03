import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import { ProjectProvider, ProjectSwitcher, useProjects } from '../pages/Projects'
import {
  LayoutDashboard,
  MessageSquare,
  Terminal,
  Users,
  Settings,
  GitBranch,
  Wrench,
  Menu,
  X,
  Wifi,
  WifiOff,
  ChevronRight,
  Bot,
  Database,
  Server,
  Zap,
  Boxes,
  Layers,
  Flame,
  FolderOpen,
  Search,
  Command,
  Bell,
  Moon,
  Sun,
  User,
  LogOut,
  HelpCircle,
  Crown,
  Sparkles,
  FileText,
  Brain,
  RefreshCw,
  Download
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'
import { useState, useEffect, useCallback } from 'react'

// Import new UX components
import { Breadcrumbs } from './Breadcrumbs'
import { NotificationCenter } from './NotificationCenter'
import { FavoritesBar, FavoriteButton } from './Favorites'

// Navigation items grouped by section
const navSections = [
  {
    title: 'Core',
    items: [
      { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
      { path: '/god-mode', icon: Flame, label: '⚡ GOD MODE', highlight: true },
      { path: '/chat', icon: MessageSquare, label: 'Chat' },
    ]
  },
  {
    title: 'Intelligence',
    items: [
      { path: '/apex', icon: Zap, label: 'APEX Control' },
      { path: '/swarm', icon: Boxes, label: 'Swarm' },
      { path: '/council', icon: Users, label: 'Council' },
      { path: '/agents', icon: Bot, label: 'Agents' },
    ]
  },
  {
    title: 'Workspace',
    items: [
      { path: '/projects', icon: FolderOpen, label: 'Projects' },
      { path: '/files', icon: FileText, label: 'Files' },
      { path: '/terminals', icon: Terminal, label: 'Terminals' },
      { path: '/workflows', icon: GitBranch, label: 'Workflows' },
    ]
  },
  {
    title: 'Tools',
    items: [
      { path: '/tools', icon: Wrench, label: 'Tools' },
      { path: '/mcp', icon: Server, label: 'MCP Hub' },
    ]
  },
  {
    title: 'Data',
    items: [
      { path: '/memory', icon: Database, label: 'Memory' },
      { path: '/memory-explorer', icon: Layers, label: 'Explorer' },
    ]
  }
]

// Command Palette
function CommandPalette({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const navigate = useNavigate()

  // Recent pages (could be persisted in localStorage)
  const recentPages = [
    { path: '/chat', label: 'Recent: Chat', icon: MessageSquare },
    { path: '/council', label: 'Recent: Council', icon: Brain },
  ]

  // All searchable items with categories
  const allItems = [
    // Quick Actions
    { action: 'new-chat', icon: MessageSquare, label: 'New Chat', category: 'Actions', description: 'Start a new conversation' },
    { action: 'open-council', icon: Brain, label: 'Open Council', category: 'Actions', description: 'Multi-perspective deliberation' },
    { action: 'run-workflow', icon: Zap, label: 'Run Workflow', category: 'Actions', description: 'Execute automation workflow' },
    { action: 'search-memory', icon: Database, label: 'Search Memory', category: 'Actions', description: 'Query stored memories' },
    { action: 'show-shortcuts', icon: Command, label: 'Keyboard Shortcuts', category: 'Actions', description: 'View all shortcuts (?)' },

    // Navigation
    ...navSections.flatMap(s => s.items.map(i => ({
      ...i,
      type: 'nav' as const,
      category: s.title,
      description: `Navigate to ${i.label}`
    }))),
    { path: '/settings', icon: Settings, label: 'Settings', type: 'nav' as const, category: 'System', description: 'Configure BAEL' },

    // System
    { action: 'toggle-theme', icon: Moon, label: 'Toggle Theme', category: 'System', description: 'Switch dark/light mode' },
    { action: 'clear-cache', icon: RefreshCw, label: 'Clear Cache', category: 'System', description: 'Reset local cache' },
    { action: 'export-data', icon: Download, label: 'Export Data', category: 'System', description: 'Download conversation history' },
  ]

  const filteredItems = query
    ? allItems.filter(item =>
        item.label.toLowerCase().includes(query.toLowerCase()) ||
        (item.description?.toLowerCase().includes(query.toLowerCase()))
      )
    : allItems.slice(0, 10)

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  const handleSelect = (item: typeof allItems[0]) => {
    if ('path' in item && item.path) {
      navigate(item.path)
    } else if ('action' in item && item.action) {
      // Handle actions
      switch (item.action) {
        case 'new-chat':
          navigate('/chat')
          break
        case 'open-council':
          navigate('/council')
          break
        case 'run-workflow':
          navigate('/workflows')
          break
        case 'search-memory':
          navigate('/memory')
          break
        case 'show-shortcuts':
          // Dispatch keyboard event to trigger shortcuts modal
          window.dispatchEvent(new KeyboardEvent('keydown', { key: '?' }))
          break
        case 'toggle-theme':
          // Toggle theme logic
          document.documentElement.classList.toggle('light')
          break
        case 'clear-cache':
          localStorage.clear()
          window.location.reload()
          break
        case 'export-data':
          // Export conversations
          const data = localStorage.getItem('bael-chat') || '{}'
          const blob = new Blob([data], { type: 'application/json' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = 'bael-export.json'
          a.click()
          break
      }
    }
    onClose()
  }

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(i => Math.min(i + 1, filteredItems.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && filteredItems[selectedIndex]) {
      e.preventDefault()
      handleSelect(filteredItems[selectedIndex])
    }
  }

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
    }
  }, [isOpen])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="fixed left-1/2 top-[20%] -translate-x-1/2 w-full max-w-xl bg-bael-surface border border-bael-border rounded-xl shadow-2xl z-50 overflow-hidden"
            onKeyDown={handleKeyDown}
          >
            {/* Search Input */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-bael-border">
              <Search size={20} className="text-bael-muted" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a command or search..."
                className="flex-1 bg-transparent text-bael-text placeholder:text-bael-muted outline-none"
                autoFocus
              />
              <kbd className="px-2 py-0.5 bg-bael-border rounded text-xs text-bael-muted">ESC</kbd>
            </div>

            {/* Results */}
            <div className="max-h-80 overflow-y-auto py-2">
              {filteredItems.map((item, i) => (
                <button
                  key={i}
                  onClick={() => handleSelect(item)}
                  className={clsx(
                    "w-full flex items-center gap-3 px-4 py-2.5 transition-colors text-left",
                    selectedIndex === i
                      ? "bg-bael-primary/20 border-l-2 border-bael-primary"
                      : "hover:bg-bael-border/50"
                  )}
                >
                  <item.icon size={18} className={selectedIndex === i ? "text-bael-primary" : "text-bael-muted"} />
                  <div className="flex-1">
                    <span className="text-bael-text">{item.label}</span>
                    {item.description && (
                      <p className="text-xs text-bael-muted">{item.description}</p>
                    )}
                  </div>
                  {item.category && (
                    <span className="text-xs bg-bael-bg px-2 py-0.5 rounded text-bael-muted">{item.category}</span>
                  )}
                </button>
              ))}
              {filteredItems.length === 0 && (
                <p className="px-4 py-8 text-center text-bael-muted">No results found</p>
              )}
            </div>

            {/* Footer hint */}
            <div className="px-4 py-2 border-t border-bael-border bg-bael-bg/50 flex items-center gap-4 text-xs text-bael-muted">
              <span><kbd className="px-1 py-0.5 bg-bael-border rounded mx-1">↑↓</kbd> Navigate</span>
              <span><kbd className="px-1 py-0.5 bg-bael-border rounded mx-1">↵</kbd> Select</span>
              <span><kbd className="px-1 py-0.5 bg-bael-border rounded mx-1">esc</kbd> Close</span>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

// Notification Panel
function NotificationPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const notifications = [
    { id: 1, title: 'Model updated', message: 'Switched to Claude 3.5 Sonnet', time: '2m ago', read: false },
    { id: 2, title: 'Task completed', message: 'Workflow "Data Analysis" finished', time: '15m ago', read: true },
    { id: 3, title: 'Memory saved', message: 'Episodic memory snapshot created', time: '1h ago', read: true },
  ]

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={onClose} />
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="absolute right-0 top-full mt-2 w-80 bg-bael-surface border border-bael-border rounded-xl shadow-xl z-50 overflow-hidden"
          >
            <div className="p-3 border-b border-bael-border flex items-center justify-between">
              <span className="font-medium text-bael-text">Notifications</span>
              <button className="text-xs text-bael-primary hover:underline">Mark all read</button>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {notifications.map((n) => (
                <div
                  key={n.id}
                  className={clsx(
                    'p-3 border-b border-bael-border hover:bg-bael-border/30 transition-colors',
                    !n.read && 'bg-bael-primary/5'
                  )}
                >
                  <div className="flex items-start gap-2">
                    {!n.read && <span className="w-2 h-2 mt-1.5 rounded-full bg-bael-primary" />}
                    <div className="flex-1">
                      <p className="text-sm font-medium text-bael-text">{n.title}</p>
                      <p className="text-xs text-bael-muted">{n.message}</p>
                      <p className="text-xs text-bael-muted mt-1">{n.time}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

// User Menu
function UserMenu({ isOpen, onClose, onNavigate }: { isOpen: boolean; onClose: () => void; onNavigate: (path: string) => void }) {
  const handleNav = (path: string) => {
    onNavigate(path)
    onClose()
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={onClose} />
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute right-0 top-full mt-2 w-56 bg-bael-surface border border-bael-border rounded-xl shadow-xl z-50 overflow-hidden"
          >
            <div className="p-3 border-b border-bael-border">
              <p className="font-medium text-bael-text">The Alchemist</p>
              <p className="text-xs text-bael-muted">Supreme Mode Active</p>
            </div>
            <div className="py-1">
              <button
                onClick={() => handleNav('/settings')}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-bael-text hover:bg-bael-border/50 transition-colors"
              >
                <User size={14} /> Profile
              </button>
              <button
                onClick={() => handleNav('/settings')}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-bael-text hover:bg-bael-border/50 transition-colors"
              >
                <Settings size={14} /> Settings
              </button>
              <button
                onClick={() => handleNav('/god-mode')}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-bael-text hover:bg-bael-border/50 transition-colors"
              >
                <HelpCircle size={14} /> Help
              </button>
            </div>
            <div className="border-t border-bael-border py-1">
              <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-bael-error hover:bg-bael-error/10 transition-colors">
                <LogOut size={14} /> Sign Out
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

// Main Layout Component
function LayoutInner() {
  const { sidebarOpen, toggleSidebar, status, theme } = useStore()
  const navigate = useNavigate()
  const [commandOpen, setCommandOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set())

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandOpen(true)
      }
      if (e.key === 'Escape') {
        setCommandOpen(false)
        setUserMenuOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const toggleSection = (title: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev)
      if (next.has(title)) next.delete(title)
      else next.add(title)
      return next
    })
  }

  return (
    <div className="flex h-screen bg-bael-bg">
      {/* Sidebar */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="bg-bael-surface border-r border-bael-border flex flex-col"
          >
            {/* Logo */}
            <div className="h-16 flex items-center px-4 border-b border-bael-border">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <img src="/logo.svg" alt="BAEL" className="w-10 h-10" />
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-br from-amber-500/20 to-orange-600/20 rounded-lg"
                    animate={{ opacity: [0.5, 0.8, 0.5] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                </div>
                <div>
                  <h1 className="font-bold text-white flex items-center gap-1">
                    BAEL
                    <Crown size={12} className="text-amber-400" />
                  </h1>
                  <p className="text-xs text-bael-muted">Lord of All AI Agents</p>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-3 overflow-y-auto">
              {navSections.map((section) => (
                <div key={section.title} className="mb-1">
                  <button
                    onClick={() => toggleSection(section.title)}
                    className="w-full flex items-center justify-between px-4 py-1.5 text-xs uppercase tracking-wide text-bael-muted hover:text-bael-text transition-colors"
                  >
                    {section.title}
                    <ChevronRight
                      size={12}
                      className={clsx(
                        'transition-transform',
                        !collapsedSections.has(section.title) && 'rotate-90'
                      )}
                    />
                  </button>

                  <AnimatePresence>
                    {!collapsedSections.has(section.title) && (
                      <motion.ul
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden px-2"
                      >
                        {section.items.map(({ path, icon: Icon, label, highlight }) => (
                          <li key={path}>
                            <NavLink
                              to={path}
                              className={({ isActive }) => clsx(
                                'flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 my-0.5',
                                isActive
                                  ? 'bg-bael-primary/20 text-bael-primary'
                                  : highlight
                                    ? 'text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 border border-amber-500/30'
                                    : 'text-bael-muted hover:text-bael-text hover:bg-bael-border/50'
                              )}
                            >
                              <Icon size={18} className={highlight ? 'animate-pulse' : ''} />
                              <span className="font-medium text-sm">{label}</span>
                              {highlight && (
                                <span className="ml-auto px-1.5 py-0.5 text-xs bg-amber-500/20 text-amber-400 rounded">
                                  NEW
                                </span>
                              )}
                            </NavLink>
                          </li>
                        ))}
                      </motion.ul>
                    )}
                  </AnimatePresence>
                </div>
              ))}

              {/* Settings at bottom */}
              <div className="px-2 mt-2 pt-2 border-t border-bael-border">
                <NavLink
                  to="/settings"
                  className={({ isActive }) => clsx(
                    'flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200',
                    isActive
                      ? 'bg-bael-primary/20 text-bael-primary'
                      : 'text-bael-muted hover:text-bael-text hover:bg-bael-border/50'
                  )}
                >
                  <Settings size={18} />
                  <span className="font-medium text-sm">Settings</span>
                </NavLink>
              </div>
            </nav>

            {/* Status Footer */}
            <div className="p-4 border-t border-bael-border">
              <div className="flex items-center gap-2 text-sm">
                {status.connected ? (
                  <>
                    <Wifi size={14} className="text-bael-success" />
                    <span className="text-bael-success">Connected</span>
                  </>
                ) : (
                  <>
                    <WifiOff size={14} className="text-bael-error" />
                    <span className="text-bael-error">Disconnected</span>
                  </>
                )}
              </div>
              {status.activeModel && (
                <p className="text-xs text-bael-muted mt-1 truncate flex items-center gap-1">
                  <Sparkles size={10} />
                  {status.activeModel}
                </p>
              )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-14 flex items-center justify-between px-4 border-b border-bael-border bg-bael-surface/80 backdrop-blur-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={toggleSidebar}
              className="p-2 hover:bg-bael-border rounded-lg transition-colors"
            >
              {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
            </button>

            {/* Project Switcher */}
            <ProjectSwitcher />

            {/* Breadcrumbs */}
            <Breadcrumbs />

            {/* Favorites Bar */}
            <FavoritesBar />
          </div>

          <div className="flex items-center gap-2">
            {/* Command Palette Trigger */}
            <button
              onClick={() => setCommandOpen(true)}
              className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-bael-bg border border-bael-border rounded-lg text-sm text-bael-muted hover:text-bael-text hover:border-bael-primary/50 transition-colors"
            >
              <Search size={14} />
              <span>Search...</span>
              <kbd className="ml-2 px-1.5 py-0.5 bg-bael-border rounded text-xs">⌘K</kbd>
            </button>

            {/* Quick Stats */}
            <div className="hidden lg:flex items-center gap-4 px-4 text-sm">
              <div className="flex items-center gap-1.5">
                <Wrench size={14} className="text-bael-muted" />
                <span className="text-bael-text">{status.tools}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Server size={14} className="text-bael-muted" />
                <span className="text-bael-text">{status.mcpServers}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Database size={14} className="text-bael-muted" />
                <span className="text-bael-text">{status.memory.working}</span>
              </div>
            </div>

            {/* Notifications - Using new NotificationCenter */}
            <NotificationCenter />

            {/* Theme Toggle */}
            <button
              className="p-2 hover:bg-bael-border rounded-lg transition-colors"
              title="Toggle theme"
            >
              {theme === 'dark' ? (
                <Moon size={18} className="text-bael-muted" />
              ) : (
                <Sun size={18} className="text-bael-muted" />
              )}
            </button>

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="w-8 h-8 rounded-lg bg-gradient-to-br from-bael-primary to-bael-secondary flex items-center justify-center"
              >
                <span className="text-sm font-bold text-white">A</span>
              </button>
              <UserMenu isOpen={userMenuOpen} onClose={() => setUserMenuOpen(false)} onNavigate={navigate} />
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>

      {/* Command Palette */}
      <CommandPalette isOpen={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>
  )
}

// Wrap with ProjectProvider
export function EnhancedLayout() {
  return (
    <ProjectProvider>
      <LayoutInner />
    </ProjectProvider>
  )
}

export default EnhancedLayout
