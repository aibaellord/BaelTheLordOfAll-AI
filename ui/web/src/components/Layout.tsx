import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useStore } from '../store'
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
  Flame
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/god-mode', icon: Flame, label: '⚡ GOD MODE', highlight: true },
  { path: '/apex', icon: Zap, label: 'APEX Control' },
  { path: '/chat', icon: MessageSquare, label: 'Chat' },
  { path: '/swarm', icon: Boxes, label: 'Swarm Intelligence' },
  { path: '/memory-explorer', icon: Layers, label: 'Memory Explorer' },
  { path: '/terminals', icon: Terminal, label: 'Terminals' },
  { path: '/council', icon: Users, label: 'Council' },
  { path: '/agents', icon: Bot, label: 'Agents' },
  { path: '/workflows', icon: GitBranch, label: 'Workflows' },
  { path: '/tools', icon: Wrench, label: 'Tools' },
  { path: '/mcp', icon: Server, label: 'MCP Hub' },
  { path: '/memory', icon: Database, label: 'Memory' },
  { path: '/settings', icon: Settings, label: 'Settings' },
]

export function Layout() {
  const { sidebarOpen, toggleSidebar, status } = useStore()
  const location = useLocation()

  return (
    <div className="flex h-screen bg-bael-bg">
      {/* Sidebar */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 240, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="bg-bael-surface border-r border-bael-border flex flex-col"
          >
            {/* Logo */}
            <div className="h-16 flex items-center px-4 border-b border-bael-border">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-bael-primary to-bael-secondary flex items-center justify-center">
                  <span className="text-white font-bold text-sm">B</span>
                </div>
                <div>
                  <h1 className="font-bold text-white">BAEL</h1>
                  <p className="text-xs text-bael-muted">v2.1.0</p>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4 overflow-y-auto">
              <ul className="space-y-1 px-2">
                {navItems.map(({ path, icon: Icon, label, highlight }) => (
                  <li key={path}>
                    <NavLink
                      to={path}
                      className={({ isActive }) => clsx(
                        'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                        isActive
                          ? 'bg-bael-primary/20 text-bael-primary'
                          : highlight
                            ? 'text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 border border-amber-500/30'
                            : 'text-bael-muted hover:text-bael-text hover:bg-bael-border/50'
                      )}
                    >
                      <Icon size={18} className={highlight && !path ? 'animate-pulse' : ''} />
                      <span className="font-medium">{label}</span>
                      {highlight && (
                        <span className="ml-auto px-1.5 py-0.5 text-xs bg-amber-500/20 text-amber-400 rounded">
                          NEW
                        </span>
                      )}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </nav>

            {/* Status */}
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
                <p className="text-xs text-bael-muted mt-1 truncate">
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
        <header className="h-16 flex items-center justify-between px-4 border-b border-bael-border bg-bael-surface">
          <div className="flex items-center gap-4">
            <button
              onClick={toggleSidebar}
              className="p-2 hover:bg-bael-border rounded-lg transition-colors"
            >
              {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>

            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm">
              <span className="text-bael-muted">BAEL</span>
              <ChevronRight size={14} className="text-bael-muted" />
              <span className="text-bael-text capitalize">
                {location.pathname === '/' ? 'Dashboard' : location.pathname.slice(1).split('/')[0]}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Quick stats */}
            <div className="hidden md:flex items-center gap-6 text-sm">
              <div>
                <span className="text-bael-muted">Tools:</span>
                <span className="ml-2 text-bael-text">{status.tools}</span>
              </div>
              <div>
                <span className="text-bael-muted">MCP:</span>
                <span className="ml-2 text-bael-text">{status.mcpServers}</span>
              </div>
              <div>
                <span className="text-bael-muted">Memory:</span>
                <span className="ml-2 text-bael-text">{status.memory.working}</span>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
